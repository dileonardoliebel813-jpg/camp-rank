import json
from pathlib import Path

from app.ingestion.platform_adapters.base_adapter import BasePlatformAdapter


class JsonAdapter(BasePlatformAdapter):
    source_name = "manual_json"

    def __init__(self, input_path: str | None = None, source_name: str | None = None):
        self.input_path = input_path
        if source_name:
            self.source_name = source_name

    def fetch_raw_data(self, keyword: str = "", limit: int = 20) -> dict:
        if not self.input_path:
            return {}
        with Path(self.input_path).open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data

    def normalize(self, raw_data: dict) -> dict:
        return raw_data if isinstance(raw_data, dict) else {}

