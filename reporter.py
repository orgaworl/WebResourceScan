CSV_COLUMNS = [
    "url", "status", "total_resources",
    "res_script", "res_stylesheet", "res_image", "res_media",
    "res_font", "res_xhr", "res_other",
    "cat_gambling", "cat_gaming", "cat_ad", "cat_payment", "cat_cdn", "cat_other",
    "third_party_domains",
]

_RES_TYPES = ["script", "stylesheet", "image", "media", "font", "xhr", "other"]
_CAT_TYPES = ["gambling", "gaming", "ad", "payment", "cdn", "other"]


def _etld1(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def build_row(crawl_result: dict, domain_cache: dict, source_domain: str) -> dict:
    source_etld1 = _etld1(source_domain)
    resources = crawl_result.get("resources", [])

    res_counts = {t: 0 for t in _RES_TYPES}
    cat_counts = {c: 0 for c in _CAT_TYPES}
    third_party_domains: set[str] = set()

    for r in resources:
        res_counts[r.get("type", "other")] += 1
        domain = r.get("domain", "")
        if domain and _etld1(domain) != source_etld1:
            third_party_domains.add(domain)

    for domain in third_party_domains:
        cat = domain_cache.get(domain, "other")
        cat_counts[cat] += 1

    return {
        "url": crawl_result["url"],
        "status": crawl_result["status"],
        "total_resources": len(resources),
        "res_script": res_counts["script"],
        "res_stylesheet": res_counts["stylesheet"],
        "res_image": res_counts["image"],
        "res_media": res_counts["media"],
        "res_font": res_counts["font"],
        "res_xhr": res_counts["xhr"],
        "res_other": res_counts["other"],
        "cat_gambling": cat_counts["gambling"],
        "cat_gaming": cat_counts["gaming"],
        "cat_ad": cat_counts["ad"],
        "cat_payment": cat_counts["payment"],
        "cat_cdn": cat_counts["cdn"],
        "cat_other": cat_counts["other"],
        "third_party_domains": ",".join(sorted(third_party_domains)),
    }
