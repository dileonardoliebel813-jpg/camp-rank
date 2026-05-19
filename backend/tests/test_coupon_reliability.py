from app.scoring.coupon_reliability import calculate_coupon_reliability_score, normalize_coupon_type


def test_shop_coupon_scores_high():
    assert calculate_coupon_reliability_score(["shop_coupon"]) > 0.85


def test_new_user_live_and_limited_coupons_score_low():
    score = calculate_coupon_reliability_score(["new_user_coupon", "live_coupon", "limited_coupon"])
    assert score < 0.4


def test_normalize_coupon_type_recognizes_promotion_text():
    result = normalize_coupon_type("店铺券叠加平台券，直播间限量券和红包需要抢")
    assert {"shop_coupon", "platform_coupon", "live_coupon", "limited_coupon", "red_packet"}.issubset(result)

