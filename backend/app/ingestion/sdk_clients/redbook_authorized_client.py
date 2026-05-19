from __future__ import annotations

import os

from app.ingestion.sdk_clients.base_client import BaseOfficialClient, OfficialAPIConfigError, UnsupportedAuthorizedSourceError, env_enabled


class RedBookAuthorizedClient(BaseOfficialClient):
    def __init__(self):
        super().__init__(
            enabled=env_enabled(os.getenv("REDBOOK_API_ENABLED")),
            base_url=os.getenv("REDBOOK_BASE_URL", ""),
            timeout_seconds=int(os.getenv("REDBOOK_TIMEOUT_SECONDS", "10")),
            max_results=int(os.getenv("REDBOOK_MAX_RESULTS", "20")),
            rate_limit_seconds=float(os.getenv("REDBOOK_RATE_LIMIT_SECONDS", "1.0")),
        )
        self.app_id = os.getenv("REDBOOK_APP_ID", "")
        self.app_secret = os.getenv("REDBOOK_APP_SECRET", "")

    def validate_config(self) -> None:
        if not self.enabled:
            raise OfficialAPIConfigError("REDBOOK_API_ENABLED=false; RedBook supports only authorized data or manual import.")
        if not self.app_id or not self.app_secret or not self.base_url:
            raise OfficialAPIConfigError("RedBook authorized API config missing: REDBOOK_APP_ID, REDBOOK_APP_SECRET, REDBOOK_BASE_URL.")

    def smoke_test(self, keyword: str, limit: int = 5) -> dict:
        self.validate_config()
        raise UnsupportedAuthorizedSourceError(
            "RedBook authorized API is not implemented for this project. Only authorized data exports or manual JSON/CSV import are supported; public-note crawling is not allowed."
        )

    def normalize_response(self, raw_response):
        raise UnsupportedAuthorizedSourceError("RedBook public content fetching is unsupported. Use authorized/manual data only.")
