from pydantic import BaseModel


class RawCanonicalProductInput(BaseModel):
    external_group_id: str | None = None
    normalized_name: str | None = None
    brand: str | None = None
    model_name: str | None = None
    capacity: str | None = None
    use_case: str | None = None
    main_image_url: str | None = None
    source: str | None = None


class RawPlatformProductInput(BaseModel):
    external_group_id: str | None = None
    platform: str | None = None
    platform_product_id: str | None = None
    title: str | None = None
    shop_name: str | None = None
    shop_type: str | None = None
    product_url: str | None = None
    image_url: str | None = None
    sales_volume: int | str | None = None
    rating_count: int | str | None = None
    positive_rate: float | str | None = None


class RawProductSpecInput(BaseModel):
    platform_product_id: str | None = None
    waterproof_index_outer: float | str | None = None
    waterproof_index_floor: float | str | None = None
    weight: float | str | None = None
    expanded_size: str | None = None
    packed_size: str | None = None
    pole_material: str | None = None
    outer_material: str | None = None
    setup_type: str | None = None
    tent_type: str | None = None
    raw_specs_json: dict | str | None = None


class RawPriceInput(BaseModel):
    platform_product_id: str | None = None
    original_price: float | str | None = None
    current_price: float | str | None = None
    shop_coupon_amount: float | str | None = None
    platform_coupon_amount: float | str | None = None
    member_coupon_amount: float | str | None = None
    limited_coupon_amount: float | str | None = None
    red_packet_amount: float | str | None = None
    discount_amount: float | str | None = None
    shipping_fee: float | str | None = None
    coupon_text: str | None = None
    promotion_text: str | None = None
    price_update_time: str | None = None


class RawBenefitInput(BaseModel):
    platform_product_id: str | None = None
    free_shipping: bool | str | int | None = None
    shipping_insurance: bool | str | int | None = None
    return_7_days: bool | str | int | None = None
    fast_refund: bool | str | int | None = None
    price_protection: bool | str | int | None = None
    official_store: bool | str | int | None = None
    self_operated: bool | str | int | None = None
    gift_items: list[str] | str | None = None


class RawReturnPolicyInput(BaseModel):
    platform_product_id: str | None = None
    return_shipping_insurance: bool | str | int | None = None
    return_shipping_payer: str | None = None
    return_condition_text: str | None = None
    opened_return_allowed: bool | str | int | None = None
    used_return_allowed: bool | str | int | None = None
    quality_issue_free_return: bool | str | int | None = None
    refund_speed_type: str | None = None
    refund_full_amount: bool | str | int | None = None
    partial_refund_risk: bool | str | int | None = None
    seller_return_attitude: str | None = None
    return_policy_clarity: float | str | None = None


class RawCommentInput(BaseModel):
    platform_product_id: str | None = None
    platform: str | None = None
    comment_text: str | None = None
    rating: float | str | None = None
    comment_type: str | None = None
    has_image: bool | str | int | None = None
    is_follow_up: bool | str | int | None = None
    comment_time: str | None = None
    seller_reply: str | None = None


class RawRedBookNoteInput(BaseModel):
    external_group_id: str | None = None
    title: str | None = None
    content: str | None = None
    comments_text: str | None = None
    likes: int | str | None = None
    favorites: int | str | None = None
    comment_count: int | str | None = None
    note_url: str | None = None

