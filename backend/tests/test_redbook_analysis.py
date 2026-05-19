from app.nlp.redbook_analyzer import (
    analyze_redbook_note,
    calculate_redbook_credibility_score,
    is_suspected_ad_note,
)


def test_redbook_ad_note_detected():
    assert is_suspected_ad_note("闭眼入", "姐妹们冲，私信链接") is True


def test_real_camping_note_has_higher_credibility():
    real = calculate_redbook_credibility_score(
        "真实体验",
        "周末露营用了，两个人过夜遇到下雨，搭建不难但收纳有点费劲，缺点是早上有冷凝水。",
        "评论区也有人说下雨表现一般",
    )
    ad = calculate_redbook_credibility_score("必买帐篷", "闭眼入，姐妹们冲，私信链接")

    assert real > ad


def test_avoid_and_fail_content_generates_risk_tags():
    result = analyze_redbook_note("避坑", "这次露营翻车了，下雨漏水，收纳也不好收。")

    assert "避坑" in result["risk_tags"]
    assert "翻车" in result["risk_tags"]
    assert "漏水" in result["risk_tags"]

