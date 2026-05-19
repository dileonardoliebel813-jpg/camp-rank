COUPON_TYPE_SCORES = {
    "direct_price": 1.0,
    "shop_coupon": 0.9,
    "platform_coupon": 0.85,
    "discount": 0.75,
    "member_coupon": 0.6,
    "new_user_coupon": 0.4,
    "live_coupon": 0.3,
    "limited_coupon": 0.3,
    "red_packet": 0.2,
    "group_price": 0.5,
}


COUPON_KEYWORDS = {
    "direct_price": ["direct", "price drop", "直降", "页面价", "到手价"],
    "shop_coupon": ["shop coupon", "店铺券", "店铺优惠", "店铺"],
    "platform_coupon": ["platform coupon", "平台券", "平台补贴", "平台"],
    "discount": ["discount", "满减", "立减", "促销"],
    "member_coupon": ["member", "会员券", "会员"],
    "new_user_coupon": ["new user", "新人券", "新人", "新客"],
    "live_coupon": ["live", "直播券", "直播间", "口令券"],
    "limited_coupon": ["limited", "限量券", "抢券", "限时券", "秒杀"],
    "red_packet": ["red packet", "红包"],
    "group_price": ["group", "拼团", "团购", "拼单"],
}


def calculate_coupon_reliability_score(coupon_types: list[str]) -> float:
    if not coupon_types:
        return 1.0
    scores = [COUPON_TYPE_SCORES.get(str(coupon_type), 0.5) for coupon_type in coupon_types]
    return round(max(0.0, min(sum(scores) / len(scores), 1.0)), 4)


def normalize_coupon_type(text: str) -> list[str]:
    if not text:
        return []
    normalized = text.lower()
    result = []
    for coupon_type, keywords in COUPON_KEYWORDS.items():
        if any(keyword.lower() in normalized for keyword in keywords):
            result.append(coupon_type)
    return result

