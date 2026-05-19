from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import requests


FORBIDDEN_AUTH_FIELDS = {"cookie", "cookies", "password", "passwd", "account", "captcha", "验证码"}


class OfficialAPIError(RuntimeError):
    error_code: str | None = None
    error_message: str | None = None


class OfficialAPIConfigError(OfficialAPIError):
    pass


class OfficialAPIRequestError(OfficialAPIError):
    def __init__(self, message: str, error_code: str | None = None, error_message: str | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.error_message = error_message or message


class UnsupportedAuthorizedSourceError(OfficialAPIError):
    pass


def env_enabled(value: str | None) -> bool:
    return str(value or "false").strip().lower() in {"1", "true", "yes", "on"}


def first_value(raw: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = raw.get(name)
        if value not in (None, ""):
            return value
    return None


def flatten_items(raw_response: Any, candidate_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(raw_response, list):
        return [item for item in raw_response if isinstance(item, dict)]
    if not isinstance(raw_response, dict):
        return []
    for key in candidate_keys:
        value = raw_response.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = flatten_items(value, candidate_keys)
            if nested:
                return nested
    for value in raw_response.values():
        if isinstance(value, dict):
            nested = flatten_items(value, candidate_keys)
            if nested:
                return nested
    return []


def collect_missing(item: dict[str, Any], required_fields: tuple[str, ...], label: str) -> list[str]:
    warnings = []
    item_id = item.get("platform_product_id") or item.get("article_id") or item.get("title") or "unknown"
    for field_name in required_fields:
        if item.get(field_name) in (None, ""):
            warnings.append(f"{label} item {item_id}: missing {field_name}")
    return warnings


def reject_forbidden_fields(payload: Any, path: str = "") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key).strip().lower()
            if key_text in FORBIDDEN_AUTH_FIELDS:
                raise OfficialAPIConfigError(f"Forbidden official API field '{path + str(key)}' is not allowed.")
            reject_forbidden_fields(value, f"{path}{key}.")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            reject_forbidden_fields(value, f"{path}{index}.")


@dataclass
class BaseOfficialClient:
    enabled: bool = False
    base_url: str = ""
    timeout_seconds: int = 10
    max_results: int = 20
    rate_limit_seconds: float = 1.0
    _last_request_time: float = field(default=0.0, init=False, repr=False)

    def build_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": "CampRank/official-api-client",
        }

    def validate_config(self) -> None:
        if not self.enabled:
            raise OfficialAPIConfigError("Official API is disabled. Set the platform *_API_ENABLED=true to use live mode.")
        if not self.base_url:
            raise OfficialAPIConfigError("Official API base_url is required.")

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.monotonic()

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path:
            return self.base_url
        return urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.validate_config()
        reject_forbidden_fields(params or {})
        reject_forbidden_fields(json_body or {})
        self._wait_for_rate_limit()
        try:
            response = requests.request(
                method.upper(),
                self._url(path),
                params=params,
                json=json_body,
                headers=self.build_headers(),
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise OfficialAPIRequestError(f"Official API network request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OfficialAPIRequestError("Official API response is not valid JSON.") from exc

        if not response.ok:
            code = None
            message = response.text
            if isinstance(payload, dict):
                code = str(first_value(payload, "error_code", "code", "sub_code", "errcode") or response.status_code)
                message = str(first_value(payload, "error_message", "msg", "message", "sub_msg") or message)
            raise OfficialAPIRequestError(
                f"Official API returned HTTP {response.status_code}: {message}",
                error_code=code,
                error_message=message,
            )
        if isinstance(payload, dict):
            api_error_code = first_value(payload, "error_code", "code", "sub_code", "errcode")
            api_error_message = first_value(payload, "error_message", "msg", "message", "sub_msg")
            if api_error_code and str(api_error_code) not in {"0", "200", "success"}:
                raise OfficialAPIRequestError(
                    f"Official API returned error {api_error_code}: {api_error_message}",
                    error_code=str(api_error_code),
                    error_message=str(api_error_message or api_error_code),
                )
            return payload
        return {"items": payload}

    def smoke_test(self, keyword: str, limit: int = 5) -> dict[str, Any]:
        raise NotImplementedError

    def normalize_response(self, raw_response: Any) -> list[dict[str, Any]]:
        raise NotImplementedError
