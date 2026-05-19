from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from app.ingestion.sdk_clients.base_client import (
    BaseOfficialClient,
    OfficialAPIConfigError,
    collect_missing,
    env_enabled,
    first_value,
    flatten_items,
)


def cents_to_yuan(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return round(float(str(value).replace(",", "")) / 100, 2)
    except (TypeError, ValueError):
        return None


class PddOpenClient(BaseOfficialClient):
    def __init__(self):
        super().__init__(
            enabled=env_enabled(os.getenv("PDD_API_ENABLED")),
            base_url=os.getenv("PDD_BASE_URL", ""),
            timeout_seconds=int(os.getenv("PDD_TIMEOUT_SECONDS", "10")),
            max_results=int(os.getenv("PDD_MAX_RESULTS", "20")),
            rate_limit_seconds=float(os.getenv("PDD_RATE_LIMIT_SECONDS", "1.0")),
        )
        self.client_id = os.getenv("PDD_CLIENT_ID", "")
        self.client_secret = os.getenv("PDD_CLIENT_SECRET", "")
        self.search_method = os.getenv("PDD_SEARCH_METHOD", "pdd.ddk.goods.search")
        self.detail_method = os.getenv("PDD_DETAIL_METHOD", "pdd.ddk.goods.detail")

    def validate_config(self) -> None:
        if not self.enabled:
            raise OfficialAPIConfigError("PDD_API_ENABLED=false; enable it only when PDD official/open API access is configured.")
        missing = []
        if not self.base_url:
            missing.append("PDD_BASE_URL")
        if not self.client_id:
            missing.append("PDD_CLIENT_ID")
        if not self.client_secret:
            missing.append("PDD_CLIENT_SECRET")
        if missing:
            raise OfficialAPIConfigError(f"PDD official API config missing: {', '.join(missing)}.")

    def sign_params(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.client_id or not self.client_secret:
            raise OfficialAPIConfigError("PDD_CLIENT_ID and PDD_CLIENT_SECRET are required before signing PDD parameters.")
        signed = {
            "client_id": self.client_id,
            "timestamp": int(time.time()),
            "data_type": "JSON",
            **params,
        }
        # PDD Open Platform signing: client_secret + sorted key/value pairs + client_secret, MD5 uppercase.
        sign_text = self.client_secret + "".join(f"{key}{signed[key]}" for key in sorted(signed)) + self.client_secret
        signed["sign"] = hashlib.md5(sign_text.encode("utf-8")).hexdigest().upper()
        return signed

    def search_goods(self, keyword: str, limit: int = 20) -> dict[str, Any]:
        self.validate_config()
        params = self.sign_params({"type": self.search_method, "keyword": keyword, "page_size": min(limit, self.max_results)})
        return self.request("POST", "", json_body=params)

    def get_goods_detail(self, goods_sign: str) -> dict[str, Any]:
        self.validate_config()
        params = self.sign_params({"type": self.detail_method, "goods_sign_list": json.dumps([goods_sign], ensure_ascii=False)})
        return self.request("POST", "", json_body=params)

    def smoke_test(self, keyword: str, limit: int = 5) -> dict[str, Any]:
        raw = self.search_goods(keyword, limit)
        return {"raw_response": raw, "items": self.normalize_response(raw)}

    def normalize_response(self, raw_response: Any) -> list[dict[str, Any]]:
        goods = flatten_items(raw_response, ("goods_list", "goods", "items", "list", "data", "result"))
        normalized = []
        for raw in goods:
            current_price = cents_to_yuan(first_value(raw, "min_group_price", "price"))
            theoretical_lowest = cents_to_yuan(first_value(raw, "min_normal_price", "theoretical_lowest_price"))
            coupon_amount = cents_to_yuan(first_value(raw, "coupon_discount", "platform_coupon_amount"))
            item = {
                "platform_product_id": str(first_value(raw, "goods_sign", "goods_id", "platform_product_id") or ""),
                "goods_id": first_value(raw, "goods_id"),
                "goods_sign": first_value(raw, "goods_sign"),
                "title": first_value(raw, "goods_name", "title"),
                "current_price": current_price,
                "theoretical_lowest_price": theoretical_lowest or (round(current_price - coupon_amount, 2) if current_price and coupon_amount else current_price),
                "coupon_text": first_value(raw, "coupon_text", "coupon_remain_quantity"),
                "coupon_amount": coupon_amount,
                "image_url": first_value(raw, "goods_thumbnail_url", "goods_image_url", "image_url"),
                "product_url": first_value(raw, "goods_url", "mobile_url", "product_url", "url"),
                "sales_volume": first_value(raw, "sales_tip", "sales_volume"),
                "shop_name": first_value(raw, "mall_name", "shop_name"),
                "raw_source": raw,
            }
            item["_warnings"] = collect_missing(item, ("platform_product_id", "title", "current_price"), "PDD")
            normalized.append(item)
        return normalized
