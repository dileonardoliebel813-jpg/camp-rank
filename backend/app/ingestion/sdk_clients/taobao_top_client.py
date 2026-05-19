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


class TaobaoTopClient(BaseOfficialClient):
    def __init__(self):
        super().__init__(
            enabled=env_enabled(os.getenv("TAOBAO_API_ENABLED")),
            base_url=os.getenv("TAOBAO_BASE_URL", ""),
            timeout_seconds=int(os.getenv("TAOBAO_TIMEOUT_SECONDS", "10")),
            max_results=int(os.getenv("TAOBAO_MAX_RESULTS", "20")),
            rate_limit_seconds=float(os.getenv("TAOBAO_RATE_LIMIT_SECONDS", "1.0")),
        )
        self.app_key = os.getenv("TAOBAO_APP_KEY", "")
        self.app_secret = os.getenv("TAOBAO_APP_SECRET", "")
        self.adzone_id = os.getenv("TAOBAO_ADZONE_ID", "")
        self.search_method = os.getenv("TAOBAO_SEARCH_METHOD", "taobao.tbk.dg.material.optional")

    def validate_config(self) -> None:
        if not self.enabled:
            raise OfficialAPIConfigError("TAOBAO_API_ENABLED=false; enable it only when Taobao/Tmall TOP access is configured.")
        missing = []
        if not self.base_url:
            missing.append("TAOBAO_BASE_URL")
        for name, value in (
            ("TAOBAO_APP_KEY", self.app_key),
            ("TAOBAO_APP_SECRET", self.app_secret),
            ("TAOBAO_ADZONE_ID", self.adzone_id),
        ):
            if not value:
                missing.append(name)
        if missing:
            raise OfficialAPIConfigError(f"Taobao TOP API config missing: {', '.join(missing)}.")

    def sign_params(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.app_key or not self.app_secret:
            raise OfficialAPIConfigError("TAOBAO_APP_KEY and TAOBAO_APP_SECRET are required before signing TOP parameters.")
        signed = {
            "app_key": self.app_key,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "2.0",
            "sign_method": "md5",
            **params,
        }
        # TOP MD5 signing: secret + sorted key/value pairs + secret. Keep method params configurable.
        sign_text = self.app_secret + "".join(f"{key}{signed[key]}" for key in sorted(signed)) + self.app_secret
        signed["sign"] = hashlib.md5(sign_text.encode("utf-8")).hexdigest().upper()
        return signed

    def search_material(self, keyword: str, limit: int = 20) -> dict[str, Any]:
        self.validate_config()
        params = self.sign_params(
            {
                "method": self.search_method,
                "q": keyword,
                "adzone_id": self.adzone_id,
                "page_size": min(limit, self.max_results),
            }
        )
        return self.request("GET", "", params=params)

    def smoke_test(self, keyword: str, limit: int = 5) -> dict[str, Any]:
        raw = self.search_material(keyword, limit)
        return {"raw_response": raw, "items": self.normalize_response(raw)}

    def normalize_response(self, raw_response: Any) -> list[dict[str, Any]]:
        items = flatten_items(raw_response, ("map_data", "results", "items", "list", "data", "result", "n_tbk_item"))
        normalized = []
        for raw in items:
            item = {
                "platform_product_id": str(first_value(raw, "item_id", "num_iid", "platform_product_id") or ""),
                "title": first_value(raw, "title", "short_title"),
                "current_price": first_value(raw, "zk_final_price", "price", "final_price", "current_price"),
                "theoretical_lowest_price": first_value(raw, "coupon_after_price", "coupon_final_price", "theoretical_lowest_price"),
                "image_url": first_value(raw, "pict_url", "image_url", "small_images"),
                "product_url": first_value(raw, "coupon_share_url", "item_url", "url", "product_url"),
                "shop_name": first_value(raw, "shop_title", "shop_name", "nick"),
                "shop_type": first_value(raw, "user_type", "shop_type"),
                "sales_volume": first_value(raw, "volume", "sales_volume"),
                "coupon_text": first_value(raw, "coupon_info", "coupon_text"),
                "coupon_amount": first_value(raw, "coupon_amount"),
                "raw_source": raw,
            }
            item["_warnings"] = collect_missing(item, ("platform_product_id", "title", "current_price"), "TAOBAO")
            normalized.append(item)
        return normalized
