from types import SimpleNamespace

from app.nlp.review_quality import (
    calculate_comment_credibility_score,
    is_low_information_review,
)


def test_short_praise_is_low_information():
    assert is_low_information_review("好评") is True


def test_unused_first_praise_is_low_information():
    assert is_low_information_review("还没用，先好评") is True


def test_weather_people_context_comment_has_higher_credibility():
    rich_comment = SimpleNamespace(
        comment_text="周末湖边露营，两个人用了一晚，晚上下雨，搭建还算顺，早上内帐有一点冷凝水。",
        has_image=True,
        is_follow_up=True,
    )
    low_comment = SimpleNamespace(comment_text="不错，物流快", has_image=False, is_follow_up=False)

    assert calculate_comment_credibility_score(rich_comment) > calculate_comment_credibility_score(low_comment)

