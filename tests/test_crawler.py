from src.crawler import _normalize_url, _same_site


def test_normalize_strips_fragment():
    assert _normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_strips_session_params():
    assert _normalize_url("https://example.com/p?token=abc&page=1") == "https://example.com/p?page=1"
    assert _normalize_url("https://example.com/p?session=xyz") == "https://example.com/p"
    assert _normalize_url("https://example.com/p?sid=1&q=hi") == "https://example.com/p?q=hi"


def test_normalize_preserves_meaningful_params():
    assert _normalize_url("https://example.com/search?q=poker") == "https://example.com/search?q=poker"


def test_same_site_true_for_subdomains():
    assert _same_site("https://www.example.com/page", "example.com") is True
    assert _same_site("https://sub.example.com/x", "example.com") is True


def test_same_site_false_for_other_domains():
    assert _same_site("https://other.com/page", "example.com") is False
    assert _same_site("https://example.org/page", "example.com") is False


def test_same_site_rejects_non_http():
    assert _same_site("mailto:user@example.com", "example.com") is False
    assert _same_site("javascript:void(0)", "example.com") is False
