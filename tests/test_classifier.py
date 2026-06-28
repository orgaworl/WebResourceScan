from src.classifier import DomainClassifier, VALID_CATEGORIES, classify_domain


def test_cache_hit_no_reclassify():
    clf = DomainClassifier()
    clf.cache["example.com"] = "gaming"
    result = clf.classify(["example.com"])
    assert result["example.com"] == "gaming"


def test_known_domain_exact():
    assert classify_domain("bet365.com") == "gambling"
    assert classify_domain("stripe.com") == "payment"
    assert classify_domain("cloudflare.com") == "cdn"


def test_subdomain_matched_via_etld1():
    assert classify_domain("sub.bet365.com") == "gambling"
    assert classify_domain("static.cloudfront.net") == "cdn"


def test_keyword_fallback():
    assert classify_domain("mycasino-games.io") in ("gambling", "gaming")
    assert classify_domain("ad-tracker.net") == "ad"


def test_unknown_domain_returns_other():
    assert classify_domain("totally-unknown-xyz.example") == "other"


def test_valid_categories_set():
    assert VALID_CATEGORIES == {"gambling", "gaming", "ad", "payment", "cdn", "other"}
