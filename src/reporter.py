from .raw_io import _etld1

CSV_COLUMNS = [
    "url", "status", "total_resources",
    "res_script", "res_stylesheet", "res_image", "res_media",
    "res_font", "res_xhr", "res_other",
    "cat_gambling", "cat_gaming", "cat_ad", "cat_payment", "cat_cdn", "cat_other",
    "third_party_domains",
]

_RES_TYPES = ["script", "stylesheet", "image", "media", "font", "xhr", "other"]
_CAT_TYPES = ["gambling", "gaming", "ad", "payment", "cdn", "other"]


def build_row(source_url: str, status: str, resources: list[dict]) -> dict:
    """Aggregate a per-site resource list (from raw CSV rows) into one summary row."""
    source_etld1 = _etld1(source_url.split("//")[-1].split("/")[0])

    res_counts = {t: 0 for t in _RES_TYPES}
    cat_counts = {c: 0 for c in _CAT_TYPES}
    third_party_domains: set[str] = set()

    for r in resources:
        res_counts[r.get("resource_type", "other")] += 1
        domain = r.get("domain", "")
        is_third = r.get("is_third_party", "False")
        if str(is_third).lower() == "true" and domain:
            third_party_domains.add(domain)
            cat = r.get("domain_category", "other") or "other"
            cat_counts[cat] += 1

    return {
        "url": source_url,
        "status": status,
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
