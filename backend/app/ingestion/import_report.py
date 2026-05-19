from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ImportReport(BaseModel):
    source_name: str
    source_type: str = "local_file"
    platform: str | None = None
    live_mode: bool = False
    source_file: str | None = None
    source_url: str | None = None
    imported_canonical_products: int = 0
    imported_platform_products: int = 0
    imported_specs: int = 0
    imported_prices: int = 0
    imported_benefits: int = 0
    imported_return_policies: int = 0
    imported_comments: int = 0
    imported_redbook_notes: int = 0
    updated_records: int = 0
    skipped_records: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    field_completeness_summary: dict = Field(default_factory=dict)
    compliance_notes: list[str] = Field(
        default_factory=lambda: [
            "No account password, Cookie, captcha handling, private content, or personal privacy data is used.",
            "Official APIs are disabled unless explicit environment variables enable them.",
            "Missing platform fields generate warnings and lower data confidence instead of being silently treated as complete.",
        ]
    )

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)


class FetchReport(BaseModel):
    source: str
    source_type: str = "official_api"
    keyword: str
    live_mode: bool
    requested_limit: int = 20
    fetched_count: int = 0
    normalized_count: int = 0
    imported_count: int = 0
    dry_run: bool = False
    fetched_items: int = 0
    imported_products: int = 0
    imported_comments: int = 0
    imported_redbook_notes: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    official_api_error_code: str | None = None
    official_api_error_message: str | None = None
    saved_json_path: str | None = None
    field_completeness_summary: dict = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)

    def set_official_error(self, error_code: str | None, error_message: str | None) -> None:
        self.official_api_error_code = error_code
        self.official_api_error_message = error_message

    def finish(self) -> "FetchReport":
        self.fetched_items = self.fetched_count or self.fetched_items
        self.imported_products = self.imported_count or self.imported_products
        self.finished_at = datetime.now(UTC)
        return self
