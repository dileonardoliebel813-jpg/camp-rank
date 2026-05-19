from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any

from app.ingestion.sdk_clients.base_client import (
    BaseOfficialClient,
    OfficialAPIConfigError,
    collect_missing,
    env_enabled,
    first_value,
    flatten_items,
)


class JDUnionClient(BaseOfficialClient):
    def __init__(self):
        super().__init__(
            enabled=env_enabled(os.getenv("JD_API_ENABLED")),
            base_url=os.getenv("JD_BASE_URL", ""),
            timeout_seconds=int(os.getenv("JD_TIMEOUT_SECONDS", "10")),
            max_results=int(os.getenv("JD_MAX_RESULTS", "20")),
            rate_limit_seconds=float(os.getenv("JD_RATE_LIMIT_SECONDS", "1.0")),
        )
        self.app_key = os.getenv("JD_APP_KEY", "")
        self.app_secret = os.getenv("JD_APP_SECRET", "")
        self.search_method = os.getenv("JD_API_METHOD_SEARCH") or os.getenv("JD_API_METHOD", "")
        self.detail_method = os.getenv("JD_API_METHOD_DETAIL", "")

    def validate_config(self) -> None:
        if not self.enabled:
            raise OfficialAPIConfigError("JD_API_ENABLED=false; enable it only when JD official/open API access is configured.")
        missing = []
        if not self.base_url:
            missing.append("JD_BASE_URL")
        if not self.app_key:
            missing.append("JD_APP_KEY")
        if not self.app_secret:
            missing.append("JD_APP_SECRET")
        if not self.search_method:
            missing.append("JD_API_METHOD_SEARCH")
        if missing:
            raise OfficialAPIConfigError(f"JD official API config missing: {', '.join(missing)}.")

    def sign_params(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.app_key or not self.app_secret:
            raise OfficialAPIConfigError("JD_APP_KEY and JD_APP_SECRET are required before signing JD parameters.")
        signed = {
            "app_key": self.app_key,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "1.0",
            **params,
        }
        # JD Open Platform commonly signs secret + sorted key/value pairs + secret with MD5.
        # TODO: confirm method-specific body/query naming against the exact official API product before live use.
        sign_text = self.app_secret + "".join(f"{key}{signed[key]}" for key in sorted(signed)) + self.app_secret
        signed["sign"] = hashlib.md5(sign_text.encode("utf-8")).hexdigest().upper()
        return signed

    def search_goods(self, keyword: str, limit: int = 20) -> dict[str, Any]:
        self.validate_config()
        params = self.sign_params({"method": self.search_method, "keyword": keyword, "limit": min(limit, self.max_results)})
        return self.request("GET", "", params=params)

    def get_goods_detail(self, sku_id: str) -> dict[str, Any]:
        self.validate_config()
        if not self.detail_method:
            raise OfficialAPIConfigError("JD_API_METHOD_DETAIL is required for JD detail lookup.")
        params = self.sign_params({"method": self.detail_method, "sku_id": sku_id})
        return self.request("GET", "", params=params)

    def smoke_test(self, keyword: str, limit: int = 5) -> dict[str, Any]:
        raw = self.search_goods(keyword, limit)
        return {"raw_response": raw, "items": self.normalize_response(raw)}

    def normalize_response(self, raw_response: Any) -> list[dict[str, Any]]:
        items = flatten_items(raw_response, ("items", "list", "goods", "data", "result", "skuInfo"))
        normalized = []
        for raw in items:
            item = {
                "platform_product_id": str(first_value(raw, "sku_id", "skuId", "sku", "wareId", "platform_product_id") or ""),
                "title": first_value(raw, "ware_name", "skuName", "title", "name"),
                "brand": first_value(raw, "brand", "brandName"),
                "current_price": first_value(raw, "price", "wlPrice", "current_price", "finalPrice"),
                "image_url": first_value(raw, "image_url", "imageUrl", "imgUrl", "whiteImage"),
                "product_url": first_value(raw, "product_url", "url", "materialUrl", "clickURL"),
                "shop_name": first_value(raw, "shop_name", "shopName", "owner"),
                "shop_type": first_value(raw, "shop_type", "shopType"),
                "sales_volume": first_value(raw, "sales_volume", "inOrderCount30Days", "comments"),
                "coupon_text": first_value(raw, "coupon_text", "couponInfo", "coupon", "discount"),
                "service_tags": first_value(raw, "service_tags", "serviceInfo", "skuLabelList"),
                "is_self_operated": first_value(raw, "is_self_operated", "isSelf", "self_operated"),
                "raw_source": raw,
            }
            item["_warnings"] = collect_missing(item, ("platform_product_id", "title", "current_price"), "JD")
            normalized.append(item)
        return normalized
