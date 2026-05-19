import json
from pathlib import Path

from app.config import Settings
from app.ingestion.platform_adapters.base_adapter import BasePlatformAdapter
from app.ingestion.sdk_clients import TaobaoTopClient


class TaobaoAdapter(BasePlatformAdapter):
    source_name = "taobao_adapter"
    platform = "TAOBAO"

    def __init__(self, input_path: str | None = None):
        self.input_path = input_path
        settings = Settings.from_env()
        self.api_enabled = settings.taobao_api_enabled
        self.base_url = settings.taobao_base_url

    def fetch_raw_data(self, keyword: str, limit: int = 20) -> dict:
        if not self.input_path:
            return {}
        with Path(self.input_path).open("r", encoding="utf-8") as file:
            return json.load(file)

    def fetch_live(self, keyword: str, limit: int = 20) -> dict:
        client = TaobaoTopClient()
        raw = client.search_material(keyword=keyword, limit=limit)
        return {
            "items": client.normalize_response(raw),
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
        return str(self._first(raw, "item_id", "num_iid", "platform_product_id") or "")

    def _warn_missing(self, product_id: str, field_name: str, value) -> None:
        if value in (None, ""):
            self.warn(f"TAOBAO item {product_id or 'unknown'}: missing {field_name}")

    def map_raw_item_to_platform_product(self, raw: dict) -> dict:
        product_id = self._platform_product_id(raw)
        title = self._first(raw, "title")
        self._warn_missing(product_id, "item_id", product_id)
        self._warn_missing(product_id, "title", title)
        return {
            "platform": "TAOBAO",
            "platform_product_id": product_id,
            "title": title,
            "shop_name": self._first(raw, "shop_title", "shop_name"),
            "shop_type": self._first(raw, "user_type", "shop_type"),
            "product_url": self._first(raw, "product_url", "item_url", "url"),
            "image_url": self._first(raw, "pict_url", "image_url"),
            "sales_volume": self._first(raw, "sales_volume", "volume"),
        }

    def map_raw_item_to_price(self, raw: dict) -> dict:
        product_id = self._platform_product_id(raw)
        price = self._first(raw, "zk_final_price", "price", "current_price")
        self._warn_missing(product_id, "zk_final_price", price)
        return {
            "platform_product_id": product_id,
            "original_price": self._first(raw, "reserve_price", "original_price") or price,
            "current_price": price,
            "shop_coupon_amount": self._first(raw, "coupon_amount", "shop_coupon_amount"),
            "coupon_text": self._first(raw, "coupon_info", "coupon_text"),
            "promotion_text": self._first(raw, "promotion_text"),
        }

    def map_raw_item_to_benefit(self, raw: dict) -> dict:
        self.warn("TAOBAO: benefit fields require authorized detail data and may be missing.")
        return {}

    def map_raw_item_to_spec(self, raw: dict) -> dict:
        specs = raw.get("specs") if isinstance(raw.get("specs"), dict) else {}
        if not specs:
            self.warn("TAOBAO: spec fields are missing.")
            return {}
        mapped = dict(specs)
        mapped["platform_product_id"] = self._platform_product_id(raw)
        return mapped

    def map_raw_item_to_comments(self, raw: dict) -> list[dict]:
        self.warn("TAOBAO: login-only comments are not collected; only authorized/manual comments may be imported.")
        return []

    def map_raw_item_to_return_policy(self, raw: dict) -> dict:
        self.warn("TAOBAO: return policy fields require authorized detail data and may be missing.")
        return {}

    def map_raw_item_to_redbook_note(self, raw: dict) -> dict:
        self.warn("TAOBAO: RedBook note fields are not supported by Taobao data.")
        return {}

    def normalize(self, raw_data: dict) -> dict:
        if not isinstance(raw_data, dict):
            return {}
        if "canonical_products" in raw_data:
            return raw_data
        items = raw_data.get("items") or raw_data.get("data") or []
        if isinstance(items, dict):
            items = items.get("items") or items.get("list") or []
        payload = {
            "canonical_products": [],
            "platform_products": [],
            "product_prices": [],
            "product_specs": [],
            "_warnings": [],
            "live_mode": bool(raw_data.get("live_mode")),
        }
        for item in items[: raw_data.get("limit", 20) or 20]:
            for warning in item.get("_warnings", []):
                self.warn(str(warning))
            product = self.map_raw_item_to_platform_product(item)
            product_id = product.get("platform_product_id")
            title = product.get("title")
            group_id = str(item.get("external_group_id") or product_id or title or "")
            payload["canonical_products"].append(
                {
                    "external_group_id": group_id,
                    "normalized_name": item.get("normalized_name") or title or product_id,
                    "brand": item.get("brand"),
                    "model_name": item.get("model_name"),
                    "capacity": item.get("capacity"),
                    "use_case": item.get("use_case"),
                    "main_image_url": product.get("image_url"),
                    "source": "TAOBAO",
                }
            )
            product["external_group_id"] = group_id
            payload["platform_products"].append(product)
            price = self.map_raw_item_to_price(item)
            if price:
                payload["product_prices"].append(price)
            spec = self.map_raw_item_to_spec(item)
            if spec:
                payload["product_specs"].append(spec)
            self.map_raw_item_to_benefit(item)
            self.map_raw_item_to_return_policy(item)
            self.map_raw_item_to_comments(item)
        payload["_warnings"].extend(self.pop_warnings())
        return payload
