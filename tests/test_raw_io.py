import os
import tempfile
from src.raw_io import raw_path, write_raw, read_raw, RAW_COLUMNS


def _make_crawl_result(url="https://example.com"):
    return {
        "url": url,
        "status": "ok",
        "resources": [
            {
                "resource_url": "https://cdn.example.com/a.js",
                "resource_type": "script",
                "domain": "cdn.example.com",
                "method": "GET",
                "status_code": 200,
                "content_type": "application/javascript",
                "content_length_bytes": 1234,
                "source_page": url,
                "initiator": "parser",
                "from_iframe": "",
            }
        ],
    }


def test_raw_path_ends_with_csv_gz():
    path = raw_path("https://example.com", "/tmp/raw")
    assert path.endswith(".csv.gz"), f"Expected .csv.gz, got {path}"


def test_write_and_read_raw_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        crawl_result = _make_crawl_result()
        path = write_raw(crawl_result, {"cdn.example.com": "cdn"}, "example.com", tmpdir)
        assert os.path.exists(path)
        assert path.endswith(".csv.gz")
        rows = read_raw(path)
        assert len(rows) == 1
        assert rows[0]["resource_type"] == "script"
        assert rows[0]["domain"] == "cdn.example.com"
        assert rows[0]["is_third_party"] == "True"
        assert rows[0]["domain_category"] == "cdn"


def test_read_raw_columns_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        crawl_result = _make_crawl_result()
        path = write_raw(crawl_result, {}, "example.com", tmpdir)
        rows = read_raw(path)
        assert list(rows[0].keys()) == RAW_COLUMNS
