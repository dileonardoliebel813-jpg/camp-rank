from scripts.fetch_jd_comments import run_cli


class FakeFetcher:
    instances = []

    def __init__(self):
        self.calls = []
        self.saved = None
        FakeFetcher.instances.append(self)

    def fetch_comments(self, sku_id, max_pages=5, page_size=10, delay_seconds=2.0):
        self.calls.append(
            {
                "sku_id": sku_id,
                "max_pages": max_pages,
                "page_size": page_size,
                "delay_seconds": delay_seconds,
            }
        )
        return {
            "comments": [{"platform": "JD", "comment_text": "mock comment", "rating": 5}],
            "warnings": [],
            "errors": [],
        }

    def save_comments_json(self, sku_id, comments):
        self.saved = {"sku_id": sku_id, "comments": comments}
        return f"backend/data/real_samples/jd_comments_{sku_id}.json"


def test_fetch_jd_comments_save_only_does_not_write_database():
    imported = []

    exit_code = run_cli(
        ["--sku-id", "100000000000", "--max-pages", "3", "--save-only"],
        fetcher_factory=FakeFetcher,
        importer=lambda db, path: imported.append(path),
    )

    assert exit_code == 0
    assert imported == []


def test_fetch_jd_comments_import_db_calls_importer():
    class FakeReport:
        warnings = []
        errors = []

        def model_dump(self):
            return {"imported_comments": 1, "warnings": [], "errors": []}

    imported = []

    exit_code = run_cli(
        ["--sku-id", "100000000000", "--max-pages", "3", "--import-db"],
        fetcher_factory=FakeFetcher,
        importer=lambda db, path: imported.append(path) or FakeReport(),
        db_session_factory=lambda: object(),
    )

    assert exit_code == 0
    assert imported == ["backend/data/real_samples/jd_comments_100000000000.json"]


def test_fetch_jd_comments_max_pages_parameter_is_used():
    FakeFetcher.instances = []

    run_cli(
        ["--sku-id", "100000000000", "--max-pages", "7", "--page-size", "9", "--delay", "0"],
        fetcher_factory=FakeFetcher,
    )

    assert FakeFetcher.instances[-1].calls[0]["max_pages"] == 7
    assert FakeFetcher.instances[-1].calls[0]["page_size"] == 9


def test_fetch_jd_comments_uses_no_cookie_header():
    headers_seen = []

    class Response:
        status_code = 200
        text = '{"comments":[]}'

        def json(self):
            return {"comments": []}

    from app.ingestion.jd_public_comments import JDPublicCommentFetcher

    def fake_get(url, params=None, headers=None, timeout=None):
        headers_seen.append(headers or {})
        return Response()

    fetcher = JDPublicCommentFetcher(request_get=fake_get, sleep_func=lambda _seconds: None)
    fetcher.fetch_comments("100000000000", max_pages=1, page_size=10, delay_seconds=0)

    assert headers_seen
    assert "Cookie" not in headers_seen[0]
