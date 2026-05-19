from app.nlp.negative_review_classifier import classify_negative_review, is_valid_negative_review


def test_rain_soaked_review_is_waterproof_high_risk():
    result = classify_negative_review("晚上一场雨全湿了，睡袋也湿了")

    assert result["is_negative"] is True
    assert "waterproof" in result["affected_dimensions"]
    assert result["risk_level"] == "high"


def test_wind_broken_pole_is_windproof_high_risk():
    result = classify_negative_review("风一吹杆子断了，结构不稳")

    assert "windproof" in result["affected_dimensions"]
    assert result["risk_level"] == "high"


def test_smell_headache_is_medium_risk():
    result = classify_negative_review("味道大，熏得头疼")

    assert "smell" in result["affected_dimensions"]
    assert result["risk_level"] == "medium"


def test_space_mismatch_review_is_spec_mismatch():
    result = classify_negative_review("说是双人帐篷，放个双人垫关不上门")

    assert "space" in result["affected_dimensions"]
    assert result["negative_type"] == "spec_mismatch"
    assert is_valid_negative_review("说是双人帐篷，放个双人垫关不上门") is True


def test_slow_delivery_does_not_strongly_affect_product_performance():
    result = classify_negative_review("快递慢")

    assert result["negative_type"] == "logistics_or_preference"
    assert result["risk_level"] == "low"
    assert is_valid_negative_review("快递慢") is False

