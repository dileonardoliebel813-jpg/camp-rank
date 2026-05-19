import json
from pathlib import Path

from app.config import Settings
from app.ingestion.platform_adapters.base_adapter import BasePlatformAdapter
from app.ingestion.sdk_clients import JDUnionClient


class JDAdapter(BasePlatformAdapter):
    source_name = "jd_adapter"
    platform = "JD"

    def __init__(self, input_path: str | None = None):
        self.input_path = input_path
        settings = Settings.from_env()
        self.api_enabled = settings.jd_api_enabled
        self.app_key = settings.jd_app_key
        self.app_secret = settings.jd_app_secret
        self.base_url = settings.jd_base_url
        self.api_method = settings.jd_api_method_search

    def fetch_raw_data(self, keyword: str, limit: int = 20) -> dict:
        if not self.input_path:
            return {"items": [], "warning": "JDAdapter offline mode needs a local JSON input_path."}
        with Path(self.input_path).open("r", encoding="utf-8") as file:
            return json.load(file)

    def sign_params(self, params: dict) -> dict:
        return JDUnionClient().sign_params(params)

    def fetch_live(self, keyword: str, limit: int = 20) -> dict:
        client = JDUnionClient()
        raw = client.search_goods(keyword=keyword, limit=limit)
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
        return str(self._first(raw, "sku_id", "skuId", "sku", "platform_product_id") or "")

    def _warn_missing(self, product_id: str, field_name: str, value) -> None:
        if value in (None, ""):
            self.warn(f"JD item {product_id or 'unknown'}: missing {field_name}")

    def map_raw_item_to_platform_product(self, raw: dict) -> dict:
        sku_id = self._platform_product_id(raw)
        title = self._first(raw, "ware_name", "title", "skuName", "name")
        shop_name = self._first(raw, "shop_name", "shopName")
        image_url = self._first(raw, "image_url", "imageUrl", "imgUrl")
        product_url = self._first(raw, "product_url", "url", "materialUrl")
        for field_name, value in {
            "sku_id": sku_id,
            "title": title,
            "shop_name": shop_name,
            "image_url": image_url,
            "product_url": product_url,
        }.items():
            self._warn_missing(sku_id, field_name, value)
        return {
            "platform": "JD",
            "platform_product_id": sku_id,
            "title": title,
            "shop_name": shop_name,
            "shop_type": self._first(raw, "shop_type", "shopType"),
            "product_url": product_url,
            "image_url": image_url,
            "sales_volume": raw.get("sales_volume"),
            "rating_count": raw.get("rating_count"),
            "positive_rate": raw.get("positive_rate"),
        }

    def map_raw_item_to_price(self, raw: dict) -> dict:
        sku_id = self._platform_product_id(raw)
        price = self._first(raw, "price", "current_price", "wlPrice")
        coupon_amount = self._first(raw, "coupon_amount", "couponAmount")
        self._warn_missing(sku_id, "price", price)
        return {
            "platform_product_id": sku_id,
            "original_price": self._first(raw, "original_price", "originalPrice") or price,
            "current_price": price,
            "shop_coupon_amount": self._first(raw, "shop_coupon_amount") or coupon_amount,
            "platform_coupon_amount": self._first(raw, "platform_coupon_amount"),
            "coupon_text": self._first(raw, "coupon_text", "coupon", "couponInfo"),
            "promotion_text": self._first(raw, "promotion_text", "promotion"),
            "price_update_time": self._first(raw, "price_update_time", "update_time"),
        }

    def map_raw_item_to_benefit(self, raw: dict) -> dict:
        sku_id = self._platform_product_id(raw)
        benefit = {
            "platform_product_id": sku_id,
            "free_shipping": self._first(raw, "free_shipping", "is_free_shipping"),
            "shipping_insurance": self._first(raw, "shipping_insurance", "freight_insurance"),
            "return_7_days": self._first(raw, "return_7_days", "seven_days_return"),
            "fast_refund": self._first(raw, "fast_refund"),
            "price_protection": self._first(raw, "price_protection"),
            "official_store": self._first(raw, "official_store"),
            "self_operated": self._first(raw, "is_self_operated", "self_operated"),
            "gift_items": raw.get("gift_items"),
        }
        if not any(value not in (None, "") for key, value in benefit.items() if key != "platform_product_id"):
            self.warn(f"JD item {sku_id or 'unknown'}: missing benefit fields")
        return benefit

    def map_raw_item_to_spec(self, raw: dict) -> dict:
        sku_id = self._platform_product_id(raw)
        specs = raw.get("specs") if isinstance(raw.get("specs"), dict) else {}
        if not specs:
            self.warn(f"JD item {sku_id or 'unknown'}: missing spec fields")
            return {}
        mapped = dict(specs)
        mapped["platform_product_id"] = sku_id
        return mapped

    def map_raw_item_to_comments(self, raw: dict) -> list[dict]:
        sku_id = self._platform_product_id(raw)
        comments = raw.get("comments") or []
        if not comments:
            self.warn(f"JD item {sku_id or 'unknown'}: missing comments")
            return []
        mapped = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            text = self._first(comment, "comment_text", "content", "text")
            if text in (None, ""):
                self.warn(f"JD item {sku_id or 'unknown'}: skipped comment missing text")
                continue
            mapped.append(
                {
                    "platform_product_id": sku_id,
                    "platform": "JD",
                    "comment_text": text,
                    "rating": self._first(comment, "rating", "score"),
                    "comment_type": self._first(comment, "comment_type", "type") or "unknown",
                    "has_image": self._first(comment, "has_image", "hasImage"),
                    "is_follow_up": self._first(comment, "is_follow_up", "isFollowUp"),
                    "comment_time": self._first(comment, "comment_time", "time"),
                    "seller_reply": self._first(comment, "seller_reply", "reply"),
                }
            )
        return mapped

    def map_raw_item_to_return_policy(self, raw: dict) -> dict:
        sku_id = self._platform_product_id(raw)
        source = raw.get("return_policy") if isinstance(raw.get("return_policy"), dict) else raw
        mapped = {
            "platform_product_id": sku_id,
            "return_shipping_insurance": self._first(source, "return_shipping_insurance"),
            "return_shipping_payer": self._first(source, "return_shipping_payer"),
            "return_condition_text": self._first(source, "return_condition_text"),
            "opened_return_allowed": self._first(source, "opened_return_allowed"),
            "used_return_allowed": self._first(source, "used_return_allowed"),
            "quality_issue_free_return": self._first(source, "quality_issue_free_return"),
            "refund_speed_type": self._first(source, "refund_speed_type"),
            "refund_full_amount": self._first(source, "refund_full_amount"),
            "partial_refund_risk": self._first(source, "partial_refund_risk"),
            "seller_return_attitude": self._first(source, "seller_return_attitude"),
            "return_policy_clarity": self._first(source, "return_policy_clarity"),
        }
        required = ("return_shipping_insurance", "return_shipping_payer", "quality_issue_free_return", "refund_speed_type")
        if any(mapped.get(field) in (None, "") for field in required):
            self.warn(f"JD item {sku_id or 'unknown'}: missing return policy fields")
        return mapped

    def map_raw_item_to_redbook_note(self, raw: dict) -> dict:
        self.warn("JD: RedBook note fields are not supported by JD data.")
        return {}

    def normalize(self, raw_data: dict) -> dict:
        if "canonical_products" in raw_data:
            return raw_data
        payload = {
            "canonical_products": [],
            "platform_products": [],
            "product_prices": [],
            "product_specs": [],
            "product_benefits": [],
            "return_policies": [],
            "comments": [],
            "redbook_notes": [],
            "_warnings": [],
            "live_mode": bool(raw_data.get("live_mode")),
        }
        items = raw_data.get("items") or raw_data.get("data") or raw_data.get("result") or []
        if isinstance(items, dict):
            items = items.get("items") or items.get("list") or items.get("goods") or []
        for item in items[: raw_data.get("limit", 20) or 20]:
            for warning in item.get("_warnings", []):
                self.warn(str(warning))
            platform_product = self.map_raw_item_to_platform_product(item)
            title = platform_product.get("title")
            sku_id = platform_product.get("platform_product_id")
            group_id = str(item.get("external_group_id") or sku_id or title or "")
            payload["canonical_products"].append(
                {
                    "external_group_id": group_id,
                    "normalized_name": item.get("normalized_name") or title or sku_id,
                    "brand": item.get("brand"),
                    "model_name": item.get("model_name"),
                    "capacity": item.get("capacity"),
                    "use_case": item.get("use_case"),
                    "main_image_url": platform_product.get("image_url"),
                    "source": "JD",
                }
            )
            platform_product["external_group_id"] = group_id
            payload["platform_products"].append(platform_product)
            for key, mapped in (
                ("product_prices", self.map_raw_item_to_price(item)),
                ("product_specs", self.map_raw_item_to_spec(item)),
                ("product_benefits", self.map_raw_item_to_benefit(item)),
                ("return_policies", self.map_raw_item_to_return_policy(item)),
            ):
                if mapped:
                    payload[key].append(mapped)
            payload["comments"].extend(self.map_raw_item_to_comments(item))
        payload["_warnings"].extend(self.pop_warnings())
        return payload
