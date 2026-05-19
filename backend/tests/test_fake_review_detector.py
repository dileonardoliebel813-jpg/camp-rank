from app.nlp.fake_review_detector import (
    calculate_fake_review_risk_score,
    calculate_template_similarity_score,
)


def test_template_positive_review_has_high_fake_risk():
    text = "质量很好，物流很快，值得购买，下次还来"

    assert calculate_fake_review_risk_score(text) >= 0.55


def test_specific_experience_review_has_low_fake_risk():
    text = "周末公园露营两个人用了一晚，下雨后地垫没湿，就是收纳袋有点紧。"

    assert calculate_fake_review_risk_score(text) < 0.5


def test_repeated_corpus_increases_similarity_and_fake_score():
    text = "质量很好，物流很快，值得购买，下次还来"
    corpus = [text, text, "包装不错，物流很快"]

    assert calculate_template_similarity_score(text, corpus) >= 0.95
    assert calculate_fake_review_risk_score(text, corpus) > calculate_fake_review_risk_score(text)

