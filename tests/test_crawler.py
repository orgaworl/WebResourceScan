from unittest.mock import MagicMock, patch

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


def test_abort_binary_types():
    """_should_abort returns True for image/media/font, False for script/xhr."""
    from src.crawler import _should_abort
    assert _should_abort("image") is True
    assert _should_abort("media") is True
    assert _should_abort("font") is True
    assert _should_abort("script") is False
    assert _should_abort("stylesheet") is False
    assert _should_abort("xhr") is False
    assert _should_abort("other") is False


def test_crawl_page_fast_timeout_constant():
    from src.crawler import FAST_TIMEOUT_MS
    assert isinstance(FAST_TIMEOUT_MS, int)
    assert FAST_TIMEOUT_MS == 8_000


def test_should_skip_path_blocks_auth_paths():
    from src.crawler import _should_skip_path
    assert _should_skip_path("https://example.com/login") is True
    assert _should_skip_path("https://example.com/user/logout") is True
    assert _should_skip_path("https://example.com/cart") is True
    assert _should_skip_path("https://example.com/checkout/payment") is True
    assert _should_skip_path("https://example.com/account/settings") is True
    assert _should_skip_path("https://example.com/register") is True
    assert _should_skip_path("https://example.com/about") is False
    assert _should_skip_path("https://example.com/games/poker") is False
    assert _should_skip_path("https://example.com/") is False


def test_checkpoint_helpers():
    import tempfile
    from src.crawler import _checkpoint_path, _is_checkpointed, _mark_checkpointed

    with tempfile.TemporaryDirectory() as tmpdir:
        _checkpoint_path("https://example.com/page?q=1", tmpdir)
        assert not _is_checkpointed("https://example.com/page?q=1", tmpdir)
        _mark_checkpointed("https://example.com/page?q=1", tmpdir)
        assert _is_checkpointed("https://example.com/page?q=1", tmpdir)


def test_crawl_site_accepts_page_workers_param():
    """crawl_site accepts page_workers without error (signature check)."""
    import inspect
    from src.crawler import crawl_site
    sig = inspect.signature(crawl_site)
    assert "page_workers" in sig.parameters
    assert sig.parameters["page_workers"].default == 1
