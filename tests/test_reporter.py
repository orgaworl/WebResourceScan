from src.reporter import build_row, CSV_COLUMNS


def test_raw_columns_include_new_fields():
    from src.raw_io import RAW_COLUMNS
    assert "source_page" in RAW_COLUMNS
    assert "initiator" in RAW_COLUMNS
    assert "from_iframe" in RAW_COLUMNS


def test_empty_resources_all_zeros():
    row = build_row("https://example.com", "ok", [])
    assert row["url"] == "https://example.com"
    assert row["status"] == "ok"
    assert row["total_resources"] == 0
    assert row["res_script"] == 0
    assert row["cat_gambling"] == 0
    assert row["third_party_domains"] == ""


def test_counts_resource_types():
    resources = [
        {"resource_type": "script", "domain": "example.com", "is_third_party": "False",
         "domain_category": "", "source_page": "https://example.com", "initiator": "parser", "from_iframe": ""},
        {"resource_type": "script", "domain": "example.com", "is_third_party": "False",
         "domain_category": "", "source_page": "https://example.com", "initiator": "parser", "from_iframe": ""},
        {"resource_type": "stylesheet", "domain": "example.com", "is_third_party": "False",
         "domain_category": "", "source_page": "https://example.com", "initiator": "parser", "from_iframe": ""},
    ]
    row = build_row("https://example.com", "ok", resources)
    assert row["total_resources"] == 3
    assert row["res_script"] == 2
    assert row["res_stylesheet"] == 1


def test_counts_third_party_domain_categories():
    resources = [
        {"resource_type": "script", "domain": "bet365.com", "is_third_party": "True",
         "domain_category": "gambling", "source_page": "https://example.com", "initiator": "script", "from_iframe": ""},
        {"resource_type": "image", "domain": "bet365.com", "is_third_party": "True",
         "domain_category": "gambling", "source_page": "https://example.com", "initiator": "parser", "from_iframe": ""},
        {"resource_type": "script", "domain": "unity3d.com", "is_third_party": "True",
         "domain_category": "gaming", "source_page": "https://example.com/game", "initiator": "script", "from_iframe": "https://example.com/iframe-host"},
        {"resource_type": "script", "domain": "example.com", "is_third_party": "False",
         "domain_category": "", "source_page": "https://example.com", "initiator": "parser", "from_iframe": ""},
    ]
    row = build_row("https://example.com", "ok", resources)
    assert row["cat_gambling"] == 1
    assert row["cat_gaming"] == 1
    assert row["cat_cdn"] == 0
    assert "bet365.com" in row["third_party_domains"]
    assert "unity3d.com" in row["third_party_domains"]
    assert "example.com" not in row["third_party_domains"]


def test_error_status_row():
    row = build_row("https://bad.com", "error", [])
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
