import json
from pathlib import Path

from app.config import Settings
from app.ingestion.platform_adapters.base_adapter import BasePlatformAdapter
from app.ingestion.sdk_clients import SMZDMOpenClient


class SMZDMAdapter(BasePlatformAdapter):
    source_name = "smzdm_adapter"
    platform = "SMZDM"

    def __init__(self, input_path: str | None = None):
        self.input_path = input_path
        settings = Settings.from_env()
        self.api_enabled = settings.smzdm_api_enabled
        self.api_key = settings.smzdm_api_key
        self.base_url = settings.smzdm_base_url

    def fetch_raw_data(self, keyword: str, limit: int = 20) -> dict:
        if not self.input_path:
            return {"deals": [], "warning": "SMZDMAdapter offline mode needs a local JSON input_path."}
        with Path(self.input_path).open("r", encoding="utf-8") as file:
            return json.load(file)

    def fetch_live(self, keyword: str, limit: int = 20) -> dict:
        client = SMZDMOpenClient()
        raw = client.search_deals(keyword=keyword, limit=limit)
        return {
            "deals": client.normalize_response(raw),
            "raw_response": raw,
            "limit": limit,
            "keyword": keyword,
            "live_mode": True,
        }

    def _first(self, raw: dict, *names):
        for name in names:
            value = raw.get(name)
            if value not in (None, ""):
                return value
        return None

    def _platform_product_id(self, raw: dict) -> str:
        return str(self._first(raw, "article_id", "id", "platform_product_id") or "")

    def _warn_missing(self, product_id: str, field_name: str, value) -> None:
        if value in (None, ""):
            self.warn(f"SMZDM item {product_id or 'unknown'}: missing {field_name}")

    def map_raw_item_to_platform_product(self, raw: dict) -> dict:
        product_id = self._platform_product_id(raw)
        title = self._first(raw, "title", "article_title", "name")
        product_url = self._first(raw, "article_url", "url", "product_url")
        for field_name, value in {"article_id": product_id, "title": title, "product_url": product_url}.items():
            self._warn_missing(product_id, field_name, value)
        return {
            "platform": "SMZDM",
            "platform_product_id": product_id,
            "title": title,
            "shop_name": self._first(raw, "mall", "platform") or "SMZDM",
            "shop_type": "deal_reference",
            "product_url": product_url,
            "image_url": self._first(raw, "image_url", "cover_url"),
        }

    def map_raw_item_to_price(self, raw: dict) -> dict:
        product_id = self._platform_product_id(raw)
        price = self._first(raw, "price", "deal_price", "current_price")
        self._warn_missing(product_id, "price", price)
        return {
            "platform_product_id": product_id,
            "original_price": self._first(raw, "original_price") or price,
            "current_price": price,
            "coupon_text": self._first(raw, "coupon_text", "coupon"),
            "promotion_text": self._first(raw, "content", "description", "promotion_text"),
            "price_update_time": self._first(raw, "publish_time", "price_update_time"),
        }

    def map_raw_item_to_benefit(self, raw: dict) -> dict:
        self.warn("SMZDM: benefit fields are usually unavailable in deal records.")
        return {}

    def map_raw_item_to_spec(self, raw: dict) -> dict:
        self.warn("SMZDM: product spec fields are usually unavailable in deal records.")
        return {}

    def map_raw_item_to_comments(self, raw: dict) -> list[dict]:
        self.warn("SMZDM: ecommerce product comments are not imported from deal records.")
        return []

    def map_raw_item_to_return_policy(self, raw: dict) -> dict:
        self.warn("SMZDM: return policy fields are not authoritative in deal records.")
        return {}

    def map_raw_item_to_redbook_note(self, raw: dict) -> dict:
        self.warn("SMZDM: RedBook note fields are not supported by SMZDM records.")
        return {}

    def normalize(self, raw_data: dict) -> dict:
        if "canonical_products" in raw_data:
            return raw_data
        payload = {
            "canonical_products": [],
            "platform_products": [],
            "product_prices": [],
            "_warnings": [],
            "live_mode": bool(raw_data.get("live_mode")),
        }
        deals = raw_data.get("deals") or raw_data.get("items") or raw_data.get("data") or []
        if isinstance(deals, dict):
            deals = deals.get("items") or deals.get("list") or deals.get("deals") or []
        for deal in deals[: raw_data.get("limit", 20) or 20]:
            for warning in deal.get("_warnings", []):
                self.warn(str(warning))
            platform_product = self.map_raw_item_to_platform_product(deal)
            price = self.map_raw_item_to_price(deal)
            title = platform_product.get("title")
            group_id = str(deal.get("external_group_id") or deal.get("article_id") or deal.get("id") or title or "")
            payload["canonical_products"].append(
                {
                    "external_group_id": group_id,
                    "normalized_name": deal.get("normalized_name") or title,
                    "brand": deal.get("brand"),
                    "model_name": deal.get("model_name"),
                    "capacity": deal.get("capacity"),
                    "use_case": deal.get("use_case") or "price_reference",
                    "source": "SMZDM",
                }
            )
            platform_product["external_group_id"] = group_id
            payload["platform_products"].append(platform_product)
            payload["product_prices"].append(price)
            self.map_raw_item_to_spec(deal)
            self.map_raw_item_to_return_policy(deal)
            self.map_raw_item_to_comments(deal)
        payload["_warnings"].extend(self.pop_warnings())
        return payload
