from app.ingestion.jd_public_comments import JDPublicCommentFetcher


def test_jd_comment_response_parses_and_normalizes_fields():
    fetcher = JDPublicCommentFetcher(sleep_func=lambda _seconds: None)
    raw = {
        "comments": [
            {
                "content": "公园露营用了一晚，帐篷内没有渗水。",
                "score": 5,
                "creationTime": "2026-04-20 10:30:00",
                "afterUserComment": {"content": "追评：下雨后地布也没湿。"},
                "productColor": "绿色",
                "productCommentSummaryList": [{"summary": "防水好"}],
                "imageCount": 2,
            }
        ]
    }

    comments = fetcher.parse_comment_response(raw)
    normalized = fetcher.normalize_comment(comments[0], "100000000000")

    assert normalized["comment_text"] == "公园露营用了一晚，帐篷内没有渗水。"
    assert normalized["rating"] == 5
    assert normalized["comment_time"] == "2026-04-20 10:30:00"
    assert normalized["follow_up_text"] == "追评：下雨后地布也没湿。"
    assert normalized["is_follow_up"] is True
    assert normalized["has_image"] is True
    assert normalized["user_tags"] == ["绿色", "防水好"]


def test_empty_jd_comment_response_does_not_crash():
    fetcher = JDPublicCommentFetcher()

    comments = fetcher.parse_comment_response({})

    assert comments == []
    assert fetcher.warnings


def test_changed_jd_comment_response_structure_warns():
    fetcher = JDPublicCommentFetcher()

    comments = fetcher.parse_comment_response({"unexpected": []})

    assert comments == []
    assert "comments list missing" in fetcher.warnings[0]

