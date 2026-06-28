"""
Read/write per-site raw resource CSV files under data/raw/<slug>.csv.gz
One row per captured network request, full attributes preserved.
"""

import csv
import gzip
import io
import os
import re

RAW_COLUMNS = [
    "resource_url",
    "resource_type",
    "domain",
    "method",
    "status_code",
    "content_type",
    "content_length_bytes",
    "is_third_party",
    "domain_category",
    "source_page",
    "initiator",
    "from_iframe",
]


def _slug(url: str) -> str:
    url = re.sub(r"^https?://", "", url)
    return re.sub(r"[^\w.-]", "_", url)[:120]


def raw_path(url: str, raw_dir: str) -> str:
    return os.path.join(raw_dir, f"{_slug(url)}.csv.gz")


def write_raw(crawl_result: dict, domain_cache: dict, source_etld1: str, raw_dir: str) -> str:
    os.makedirs(raw_dir, exist_ok=True)
    path = raw_path(crawl_result["url"], raw_dir)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=RAW_COLUMNS)
    writer.writeheader()
    for r in crawl_result.get("resources", []):
        domain = r.get("domain", "")
        is_third = _etld1(domain) != source_etld1 if domain else False
        writer.writerow({
            "resource_url": r.get("resource_url", ""),
            "resource_type": r.get("resource_type", "other"),
            "domain": domain,
            "method": r.get("method", ""),
            "status_code": r.get("status_code", ""),
            "content_type": r.get("content_type", ""),
            "content_length_bytes": r.get("content_length_bytes", -1),
            "is_third_party": is_third,
            "domain_category": domain_cache.get(domain, "other") if is_third else "",
            "source_page": r.get("source_page", ""),
            "initiator": r.get("initiator", ""),
            "from_iframe": r.get("from_iframe", ""),
        })
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())
    return path


def read_raw(path: str) -> list[dict]:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _etld1(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain
