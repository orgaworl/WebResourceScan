from reporter import build_row, CSV_COLUMNS


def _make_crawl_result(url, status, resources):
    return {"url": url, "status": status, "resources": resources}


def test_empty_resources_all_zeros():
    result = _make_crawl_result("https://example.com", "ok", [])
    row = build_row(result, {}, source_domain="example.com")
    assert row["url"] == "https://example.com"
    assert row["status"] == "ok"
    assert row["total_resources"] == 0
    assert row["res_script"] == 0
    assert row["cat_gambling"] == 0
    assert row["third_party_domains"] == ""


def test_counts_resource_types():
    resources = [
        {"url": "https://example.com/a.js", "type": "script", "domain": "example.com"},
        {"url": "https://example.com/b.js", "type": "script", "domain": "example.com"},
        {"url": "https://example.com/c.css", "type": "stylesheet", "domain": "example.com"},
    ]
    result = _make_crawl_result("https://example.com", "ok", resources)
    row = build_row(result, {}, source_domain="example.com")
    assert row["total_resources"] == 3
    assert row["res_script"] == 2
    assert row["res_stylesheet"] == 1


def test_counts_third_party_domain_categories():
    resources = [
        {"url": "https://bet365.com/track.js", "type": "script", "domain": "bet365.com"},
        {"url": "https://bet365.com/img.png", "type": "image", "domain": "bet365.com"},
        {"url": "https://unity3d.com/sdk.js", "type": "script", "domain": "unity3d.com"},
        {"url": "https://example.com/self.js", "type": "script", "domain": "example.com"},
    ]
    domain_cache = {"bet365.com": "gambling", "unity3d.com": "gaming"}
    result = _make_crawl_result("https://example.com", "ok", resources)
    row = build_row(result, domain_cache, source_domain="example.com")
    assert row["cat_gambling"] == 1
    assert row["cat_gaming"] == 1
    assert row["cat_cdn"] == 0
    assert "bet365.com" in row["third_party_domains"]
    assert "unity3d.com" in row["third_party_domains"]
    assert "example.com" not in row["third_party_domains"]


def test_error_status_row():
    result = _make_crawl_result("https://bad.com", "error", [])
    row = build_row(result, {}, source_domain="bad.com")
    assert row["status"] == "error"
    assert row["total_resources"] == 0


def test_csv_columns_complete():
    expected = [
        "url", "status", "total_resources",
        "res_script", "res_stylesheet", "res_image", "res_media",
        "res_font", "res_xhr", "res_other",
        "cat_gambling", "cat_gaming", "cat_ad", "cat_payment", "cat_cdn", "cat_other",
        "third_party_domains",
    ]
    assert CSV_COLUMNS == expected
