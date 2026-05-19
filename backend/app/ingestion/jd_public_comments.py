import json
import random
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests


class JDPublicCommentFetcher:
    source_name = "jd_public_comment"
    platform = "JD"
    public_comment_url = "https://club.jd.com/comment/productPageComments.action"
    max_pages_limit = 20
    page_size_limit = 20
    max_comments_limit = 200
    timeout_seconds = 8.0

    def __init__(self, output_dir: str | Path | None = None, request_get=None, sleep_func=None):
        backend_root = Path(__file__).resolve().parents[2]
        self.output_dir = Path(output_dir) if output_dir else backend_root / "data" / "real_samples"
        self.request_get = request_get or requests.get
        self.sleep_func = sleep_func or time.sleep
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)

    def fetch_comments(
        self,
        sku_id: str,
        max_pages: int = 5,
        page_size: int = 10,
        delay_seconds: float = 2.0,
    ) -> dict:
        self.warnings = []
        self.errors = []
        sku_id = str(sku_id or "").strip()
        if not sku_id:
            self.error("sku_id is required.")
            return self._build_result(sku_id, max_pages, page_size, [])

        requested_pages = max(1, int(max_pages or 1))
        requested_page_size = max(1, int(page_size or 1))
        safe_pages = min(requested_pages, self.max_pages_limit)
        safe_page_size = min(requested_page_size, self.page_size_limit)
        self.last_max_pages = safe_pages
        self.last_page_size = safe_page_size
        if requested_pages > self.max_pages_limit:
            self.warn(f"max_pages capped at {self.max_pages_limit}.")
        if requested_page_size > self.page_size_limit:
            self.warn(f"page_size capped at {self.page_size_limit}.")

        comments: list[dict] = []
        headers = {
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": "CampRank/1.0 public-comment-ingestion",
            "Referer": f"https://item.jd.com/{sku_id}.html",
        }
        for page in range(safe_pages):
            if len(comments) >= self.max_comments_limit:
                self.warn(f"max_comments capped at {self.max_comments_limit}.")
                break
            try:
                response = self.request_get(
                    self.public_comment_url,
                    params={
                        "productId": sku_id,
                        "score": 0,
                        "sortType": 5,
                        "page": page,
                        "pageSize": safe_page_size,
                        "isShadowSku": 0,
                        "fold": 1,
                    },
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                self.warn(f"JD public comment request stopped: {exc.__class__.__name__}.")
                break

            if getattr(response, "status_code", None) == 403:
                self.warn("JD public comment request stopped: access returned 403.")
                break
            if getattr(response, "status_code", None) != 200:
                self.warn(f"JD public comment request stopped: HTTP {getattr(response, 'status_code', 'unknown')}.")
                break

            raw_response = self._decode_response(response)
            if raw_response is None:
                break
            page_comments = [
                self.normalize_comment(raw_comment, sku_id)
                for raw_comment in self.parse_comment_response(raw_response)
            ]
            if not page_comments:
                self.warn(f"JD public comment request stopped: no comments on page {page}.")
                break
            remaining = self.max_comments_limit - len(comments)
            comments.extend(page_comments[:remaining])

            if page < safe_pages - 1:
                jitter = random.uniform(0, min(0.5, max(0.0, delay_seconds * 0.2)))
                self.sleep_func(max(0.0, delay_seconds) + jitter)

        return self._build_result(sku_id, safe_pages, safe_page_size, comments)

    def parse_comment_response(self, raw_response: dict) -> list[dict]:
        if not isinstance(raw_response, dict) or not raw_response:
            self.warn("JD public comment response is empty or not a JSON object.")
            return []
        candidates = [
            raw_response.get("comments"),
            raw_response.get("data", {}).get("comments") if isinstance(raw_response.get("data"), dict) else None,
            raw_response.get("result", {}).get("comments") if isinstance(raw_response.get("result"), dict) else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        self.warn("JD public comment response structure changed: comments list missing.")
        return []

    def normalize_comment(self, raw_comment: dict, sku_id: str) -> dict:
        raw_comment = raw_comment if isinstance(raw_comment, dict) else {}
        follow_up_text = self._extract_follow_up_text(raw_comment)
        rating = self._normalize_rating(
            raw_comment.get("score")
            or raw_comment.get("commentScore")
            or raw_comment.get("productScore")
            or raw_comment.get("rating")
        )
        return {
            "platform": self.platform,
            "platform_product_id": str(sku_id),
            "comment_text": str(raw_comment.get("content") or raw_comment.get("comment_text") or "").strip(),
            "rating": rating,
            "comment_type": self._comment_type(rating, raw_comment),
            "has_image": self._has_image(raw_comment),
            "is_follow_up": bool(follow_up_text),
            "follow_up_text": follow_up_text,
            "comment_time": raw_comment.get("creationTime")
            or raw_comment.get("comment_time")
            or raw_comment.get("referenceTime"),
            "user_tags": self._extract_user_tags(raw_comment),
            "seller_reply": self._extract_seller_reply(raw_comment),
            "source": self.source_name,
            "raw_comment_json": self._sanitize_raw_comment(raw_comment),
        }

    def save_comments_json(self, sku_id: str, comments: list[dict]) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_sku_id = re.sub(r"[^0-9A-Za-z_-]+", "", str(sku_id))
        path = self.output_dir / f"jd_comments_{safe_sku_id}.json"
        payload = {
            "source_name": self.source_name,
            "platform": self.platform,
            "sku_id": str(sku_id),
            "fetched_at": datetime.now(UTC).isoformat(),
            "max_pages": getattr(self, "last_max_pages", None),
            "page_size": getattr(self, "last_page_size", None),
            "comments": comments,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
        return str(path)

    def _build_result(self, sku_id: str, max_pages: int, page_size: int, comments: list[dict]) -> dict:
        return {
            "source_name": self.source_name,
            "platform": self.platform,
            "sku_id": sku_id,
            "fetched_at": datetime.now(UTC).isoformat(),
            "max_pages": max_pages,
            "page_size": page_size,
            "comments": comments,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    def _decode_response(self, response) -> dict | None:
        text = getattr(response, "text", "") or ""
        if not text.strip():
            self.warn("JD public comment request stopped: empty response.")
            return None
        if self._looks_restricted(text):
            self.warn("JD public comment request stopped: login, captcha, or restricted page detected.")
            return None
        try:
            data = response.json()
            if isinstance(data, dict):
                return data
        except (ValueError, AttributeError):
            pass
        json_text = text.strip()
        match = re.match(r"^[\w$]+\((.*)\)\s*;?$", json_text, flags=re.DOTALL)
        if match:
            json_text = match.group(1)
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            self.warn("JD public comment request stopped: response is not valid JSON.")
            return None
        if not isinstance(data, dict):
            self.warn("JD public comment request stopped: JSON response is not an object.")
            return None
        return data

    @staticmethod
    def _looks_restricted(text: str) -> bool:
        lower = text.lower()
        restricted_markers = ("captcha", "verify", "login", "passport.jd.com", "验证码", "登录")
        return any(marker in lower for marker in restricted_markers) or "<html" in lower

    @staticmethod
    def _normalize_rating(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _comment_type(rating: float | None, raw_comment: dict) -> str:
        if raw_comment.get("comment_type"):
            return str(raw_comment["comment_type"])
        if rating is None:
            return "unknown"
        if rating >= 4:
            return "positive"
        if rating <= 2:
            return "negative"
        return "neutral"

    @staticmethod
    def _has_image(raw_comment: dict) -> bool:
        images = raw_comment.get("images")
        if isinstance(images, list) and images:
            return True
        image_count = raw_comment.get("imageCount") or raw_comment.get("image_count")
        try:
            return int(image_count or 0) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _extract_follow_up_text(raw_comment: dict) -> str:
        for key in ("afterUserComment", "after_comment", "appendComment", "againComment"):
            value = raw_comment.get(key)
            if isinstance(value, dict):
                text = value.get("content") or value.get("comment_text")
                if text:
                    return str(text).strip()
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _extract_user_tags(raw_comment: dict) -> list[str]:
        tags: list[str] = []
        for key in ("productColor", "productSize", "skuInfo"):
            value = raw_comment.get(key)
            if value:
                tags.append(str(value).strip())
        summaries = raw_comment.get("productCommentSummaryList") or raw_comment.get("user_tags")
        if isinstance(summaries, list):
            for item in summaries:
                if isinstance(item, dict):
                    label = item.get("summary") or item.get("name") or item.get("tag")
                else:
                    label = item
                if label:
                    tags.append(str(label).strip())
        return [tag for index, tag in enumerate(tags) if tag and tag not in tags[:index]]

    @staticmethod
    def _extract_seller_reply(raw_comment: dict) -> str | None:
        replies = raw_comment.get("replies") or raw_comment.get("reply")
        if isinstance(replies, list) and replies:
            first = replies[0]
            if isinstance(first, dict):
                return first.get("content") or first.get("replyContent")
            return str(first)
        if isinstance(replies, dict):
            return replies.get("content") or replies.get("replyContent")
        if isinstance(replies, str) and replies.strip():
            return replies.strip()
        return None

    def _sanitize_raw_comment(self, raw_comment: dict) -> dict:
        blocked_keys = {
            "nickname",
            "nickName",
            "userImage",
            "userImageUrl",
            "userImgURL",
            "userId",
            "guid",
            "ip",
            "ipLocation",
            "userProvince",
        }

        def scrub(value):
            if isinstance(value, dict):
                return {key: scrub(item) for key, item in value.items() if key not in blocked_keys}
            if isinstance(value, list):
                return [scrub(item) for item in value]
            return value

        return scrub(raw_comment)
