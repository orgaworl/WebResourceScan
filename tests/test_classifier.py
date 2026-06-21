import json
import pytest
from unittest.mock import patch, MagicMock
from classifier import DomainClassifier, VALID_CATEGORIES


def test_cache_hit_returns_without_llm(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps({"example.com": "gaming"}))
    clf = DomainClassifier(str(cache_file))
    result = clf.classify(["example.com"])
    assert result["example.com"] == "gaming"


def test_new_domain_calls_llm_and_caches(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")
    clf = DomainClassifier(str(cache_file))

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text='{"bet365.com": "gambling"}')]

    with patch.object(clf.client.messages, "create", return_value=fake_response):
        result = clf.classify(["bet365.com"])

    assert result["bet365.com"] == "gambling"
    saved = json.loads(cache_file.read_text())
    assert saved["bet365.com"] == "gambling"


def test_invalid_llm_json_retries_then_marks_other(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")
    clf = DomainClassifier(str(cache_file))

    bad_response = MagicMock()
    bad_response.content = [MagicMock(text="not json at all")]

    with patch.object(clf.client.messages, "create", return_value=bad_response):
        result = clf.classify(["unknown.com"])

    assert result["unknown.com"] == "other"


def test_valid_categories_set():
    assert "gambling" in VALID_CATEGORIES
    assert "gaming" in VALID_CATEGORIES
    assert "ad" in VALID_CATEGORIES
    assert "payment" in VALID_CATEGORIES
    assert "cdn" in VALID_CATEGORIES
    assert "other" in VALID_CATEGORIES
