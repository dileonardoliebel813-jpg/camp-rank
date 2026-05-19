from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.ingestion.import_report import ImportReport
from app.ingestion.import_service import import_normalized_payload


class BasePlatformAdapter(ABC):
    source_name = "base"
    platform = "UNKNOWN"

    def warn(self, message: str) -> None:
        if not hasattr(self, "_warnings"):
            self._warnings = []
        if message not in self._warnings:
            self._warnings.append(message)

    def pop_warnings(self) -> list[str]:
        warnings = list(getattr(self, "_warnings", []))
        self._warnings = []
        return warnings

    @abstractmethod
    def fetch_raw_data(self, keyword: str, limit: int = 20) -> dict:
        raise NotImplementedError

    def fetch_live(self, keyword: str, limit: int = 20) -> dict:
        raise NotImplementedError(f"{self.source_name} live API is not enabled or not implemented.")

    @abstractmethod
    def normalize(self, raw_data: dict) -> dict:
        raise NotImplementedError

    def validate(self, normalized_data: dict) -> list[str]:
        warnings = []
        if not normalized_data.get("canonical_products"):
            warnings.append("adapter output has no canonical_products")
        if not normalized_data.get("platform_products"):
            warnings.append("adapter output has no platform_products")
        return warnings

    def import_to_db(self, db: Session, normalized_data: dict) -> ImportReport:
        report = import_normalized_payload(
            db,
            normalized_data,
            source_name=self.source_name,
            source_type="official_api" if bool(normalized_data.get("live_mode")) else "platform_adapter",
            platform=self.platform,
            source_file=getattr(self, "input_path", None),
            source_url=getattr(self, "base_url", None) or None,
            live_mode=bool(normalized_data.get("live_mode")),
        )
        for warning in self.validate(normalized_data):
            report.warn(warning)
        for warning in self.pop_warnings():
            report.warn(warning)
        return report

    def _unsupported(self, field_type: str):
        self.warn(f"{self.platform}: {field_type} fields are not supported by this adapter/input.")
        return {}

    def map_raw_item_to_platform_product(self, raw: dict) -> dict:
        return self._unsupported("platform_product")

    def map_raw_item_to_price(self, raw: dict) -> dict:
        return self._unsupported("price")

    def map_raw_item_to_benefit(self, raw: dict) -> dict:
        return self._unsupported("benefit")

    def map_raw_item_to_spec(self, raw: dict) -> dict:
        return self._unsupported("spec")

    def map_raw_item_to_comments(self, raw: dict) -> list[dict]:
        self.warn(f"{self.platform}: comment fields are not supported by this adapter/input.")
        return []

    def map_raw_item_to_return_policy(self, raw: dict) -> dict:
        return self._unsupported("return_policy")

    def map_raw_item_to_redbook_note(self, raw: dict) -> dict:
        return self._unsupported("redbook")
