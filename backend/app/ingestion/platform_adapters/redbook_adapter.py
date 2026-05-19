import json
from pathlib import Path

from app.config import Settings
from app.ingestion.platform_adapters.base_adapter import BasePlatformAdapter
from app.ingestion.sdk_clients import RedBookAuthorizedClient


class RedBookAdapter(BasePlatformAdapter):
    source_name = "redbook_adapter"
    platform = "REDBOOK"

    def __init__(self, input_path: str | None = None):
        self.input_path = input_path
        settings = Settings.from_env()
        self.api_enabled = settings.redbook_api_enabled
        self.base_url = settings.redbook_base_url

    def fetch_raw_data(self, keyword: str, limit: int = 20) -> dict:
        if not self.input_path:
            return {}
        with Path(self.input_path).open("r", encoding="utf-8") as file:
            return json.load(file)

    def fetch_live(self, keyword: str, limit: int = 20) -> dict:
        client = RedBookAuthorizedClient()
        return client.smoke_test(keyword=keyword, limit=limit)

    def _first(self, raw: dict, *names):
        for name in names:
            value = raw.get(name)
            if value not in (None, ""):
                return value
        return None

    def map_raw_item_to_platform_product(self, raw: dict) -> dict:
        self.warn("REDBOOK: notes are external reputation data, not ecommerce platform products.")
        return {}

    def map_raw_item_to_price(self, raw: dict) -> dict:
        self.warn("REDBOOK: price fields are not supported.")
        return {}

    def map_raw_item_to_benefit(self, raw: dict) -> dict:
        self.warn("REDBOOK: benefit fields are not supported.")
        return {}

    def map_raw_item_to_spec(self, raw: dict) -> dict:
        self.warn("REDBOOK: spec fields are not authoritative and are not mapped.")
        return {}

    def map_raw_item_to_comments(self, raw: dict) -> list[dict]:
        self.warn("REDBOOK: note comments stay in comments_text and are not imported as ecommerce comments.")
        return []

    def map_raw_item_to_return_policy(self, raw: dict) -> dict:
        self.warn("REDBOOK: return policy fields are not supported.")
        return {}

    def map_raw_item_to_redbook_note(self, raw: dict) -> dict:
        title = self._first(raw, "title")
        content = self._first(raw, "content", "desc")
        note_id = self._first(raw, "note_id", "id", "note_url")
        if title in (None, ""):
            self.warn(f"REDBOOK note {note_id or 'unknown'}: missing title")
        if content in (None, ""):
            self.warn(f"REDBOOK note {note_id or 'unknown'}: missing content")
        return {
            "external_group_id": self._first(raw, "external_group_id", "product_id") or str(note_id or ""),
            "note_url": self._first(raw, "note_url", "url") or str(note_id or ""),
            "title": title,
            "content": content,
            "comments_text": self._first(raw, "comments_text", "comments"),
            "likes": self._first(raw, "likes"),
            "favorites": self._first(raw, "favorites", "collects"),
            "comment_count": self._first(raw, "comment_count"),
        }

    def normalize(self, raw_data: dict) -> dict:
        if not isinstance(raw_data, dict):
            return {}
        if "canonical_products" in raw_data:
            return raw_data
        notes = raw_data.get("redbook_notes") or raw_data.get("notes") or raw_data.get("items") or []
        payload = {
            "canonical_products": [],
            "platform_products": [],
            "redbook_notes": [],
            "_warnings": [],
            "live_mode": bool(raw_data.get("live_mode")),
        }
        for note in notes[: raw_data.get("limit", 20) or 20]:
            mapped = self.map_raw_item_to_redbook_note(note)
            if not mapped:
                continue
            group_id = mapped.get("external_group_id") or mapped.get("note_url") or mapped.get("title")
            payload["canonical_products"].append(
                {
                    "external_group_id": group_id,
                    "normalized_name": note.get("normalized_name") or mapped.get("title") or group_id,
                    "brand": note.get("brand"),
                    "model_name": note.get("model_name"),
                    "capacity": note.get("capacity"),
                    "use_case": note.get("use_case") or "external_reputation",
                    "source": "REDBOOK",
                }
            )
            mapped["external_group_id"] = group_id
            payload["redbook_notes"].append(mapped)
        payload["_warnings"].extend(self.pop_warnings())
        return payload
