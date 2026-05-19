from urllib.parse import urlparse


PLACEHOLDER_HOSTS = {"example.com", "www.example.com"}


def public_product_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(str(url).strip())
    if parsed.hostname in PLACEHOLDER_HOSTS:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    return str(url).strip()
