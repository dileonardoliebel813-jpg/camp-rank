from __future__ import annotations

import os
from typing import Any

from app.ingestion.sdk_clients.base_client import (
    BaseOfficialClient,
    OfficialAPIConfigError,
    collect_missing,
    env_enabled,
    first_value,
    flatten_items,
)


class SMZDMOpenClient(BaseOfficialClient):
    def __init__(self):
        super().__init__(
            enabled=env_enabled(os.getenv("SMZDM_API_ENABLED")),
            base_url=os.getenv("SMZDM_BASE_URL", ""),
            timeout_seconds=int(os.getenv("SMZDM_TIMEOUT_SECONDS", "10")),
            max_results=int(os.getenv("SMZDM_MAX_RESULTS", "20")),
            rate_limit_seconds=float(os.getenv("SMZDM_RATE_LIMIT_SECONDS", "1.0")),
        )
        self.api_key = os.getenv("SMZDM_API_KEY", "")
        self.search_path = os.getenv("SMZDM_SEARCH_PATH", "")
        self.detail_path = os.getenv("SMZDM_DETAIL_PATH", "")

    def build_headers(self) -> dict[str, str]:
        headers = super().build_headers()
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def validate_config(self) -> None:
        if not self.enabled:
            raise OfficialAPIConfigError("SMZDM_API_ENABLED=false; enable it only when a valid official/open API source is configured.")
        missing = []
        if not self.base_url:
            missing.append("SMZDM_BASE_URL")
        if not self.api_key:
            missing.append("SMZDM_API_KEY")
        if missing:
            raise OfficialAPIConfigError(f"SMZDM official API config missing: {', '.join(missing)}.")

    def search_deals(self, keyword: str, limit: int = 20) -> dict[str, Any]:
        self.validate_config()
        return self.request(
            "GET",
            self.search_path,
            params={"keyword": keyword, "limit": min(limit, self.max_results), "api_key": self.api_key},
        )

    def get_deal_detail(self, article_id: str) -> dict[str, Any]:
        self.validate_config()
        if not self.detail_path:
            raise OfficialAPIConfigError("SMZDM_DETAIL_PATH is required for SMZDM detail lookup.")
        return self.request("GET", self.detail_path, params={"article_id": article_id, "api_key": self.api_key})

    def smoke_test(self, keyword: str, limit: int = 5) -> dict[str, Any]:
        raw = self.search_deals(keyword, limit)
        return {"raw_response": raw, "items": self.normalize_response(raw)}

    def normalize_response(self, raw_response: Any) -> list[dict[str, Any]]:
        deals = flatten_items(raw_response, ("deals", "items", "list", "data", "result", "rows"))
        normalized = []
        for raw in deals:
            item = {
                "platform_product_id": str(first_value(raw, "article_id", "id", "articleId", "platform_product_id") or ""),
                "article_id": str(first_value(raw, "article_id", "id", "articleId") or ""),
                "title": first_value(raw, "title", "article_title", "name"),
                "current_price": first_value(raw, "price", "deal_price", "current_price", "article_price"),
                "promotion_text": first_value(raw, "promotion_text", "content", "description", "article_content"),
                "product_url": first_value(raw, "article_url", "url", "product_url", "redirect_url"),
                "source_platform": first_value(raw, "mall", "platform", "source_platform", "article_mall"),
                "publish_time": first_value(raw, "publish_time", "article_date", "time"),
                "content_summary": first_value(raw, "content_summary", "summary", "description"),
                "worth_count": first_value(raw, "worth_count", "worthy_count", "zhi_count"),
                "unworth_count": first_value(raw, "unworth_count", "unworthy_count", "buzhi_count"),
                "image_url": first_value(raw, "image_url", "cover_url", "article_pic"),
                "raw_source": raw,
            }
            item["_warnings"] = collect_missing(item, ("platform_product_id", "title", "current_price"), "SMZDM")
            normalized.append(item)
        return normalized
