"""
Static JS library vulnerability database and URL-based version extractor.

Scans raw resource CSVs for known-vulnerable frontend library versions by
matching URL patterns (e.g. jquery-3.2.1.min.js, lodash@4.17.10/lodash.js).

No network requests. No NVD API. Purely offline pattern matching.
"""

import csv
import gzip
import os
import re

VULN_COLUMNS = [
    "site_url", "resource_url", "library", "version",
    "cve", "severity", "affected_below", "description",
]

# Each entry: library name, list of URL regex patterns (first capture group = version),
# CVE id, severity (critical/high/medium/low), affected_below as version tuple,
# short description.
_DB: list[dict] = [
    # ── jQuery ────────────────────────────────────────────────────────────────
    {
        "library": "jQuery",
        "patterns": [r"jquery[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js"],
        "cve": "CVE-2020-11022",
        "severity": "medium",
        "affected_below": (3, 5, 0),
        "description": "XSS via jQuery.htmlPrefilter",
    },
    {
        "library": "jQuery",
        "patterns": [r"jquery[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js"],
        "cve": "CVE-2019-11358",
        "severity": "medium",
        "affected_below": (3, 4, 0),
        "description": "Prototype pollution via jQuery.extend",
    },
    {
        "library": "jQuery",
        "patterns": [r"jquery[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js"],
        "cve": "CVE-2015-9251",
        "severity": "medium",
        "affected_below": (3, 0, 0),
        "description": "XSS when passing HTML containing HTML from untrusted source",
    },
    # ── jQuery UI ─────────────────────────────────────────────────────────────
    {
        "library": "jQuery UI",
        "patterns": [r"jquery[.-]ui[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"jquery-ui@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2021-41182",
        "severity": "medium",
        "affected_below": (1, 13, 0),
        "description": "XSS in the Datepicker widget",
    },
    {
        "library": "jQuery UI",
        "patterns": [r"jquery[.-]ui[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"jquery-ui@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2022-31160",
        "severity": "medium",
        "affected_below": (1, 13, 2),
        "description": "XSS in checkboxradio widget",
    },
    # ── Bootstrap ─────────────────────────────────────────────────────────────
    {
        "library": "Bootstrap",
        "patterns": [r"bootstrap[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"bootstrap@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2019-8331",
        "severity": "medium",
        "affected_below": (4, 3, 1),
        "description": "XSS in tooltip/popover data-template attribute",
    },
    {
        "library": "Bootstrap",
        "patterns": [r"bootstrap[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"bootstrap@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2018-14041",
        "severity": "medium",
        "affected_below": (3, 4, 0),
        "description": "XSS in collapse data-parent attribute",
    },
    # ── Lodash ────────────────────────────────────────────────────────────────
    {
        "library": "Lodash",
        "patterns": [r"lodash[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"lodash@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2021-23337",
        "severity": "high",
        "affected_below": (4, 17, 21),
        "description": "Command injection via template",
    },
    {
        "library": "Lodash",
        "patterns": [r"lodash[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"lodash@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2020-28500",
        "severity": "medium",
        "affected_below": (4, 17, 21),
        "description": "ReDoS via string methods",
    },
    {
        "library": "Lodash",
        "patterns": [r"lodash[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"lodash@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2019-10744",
        "severity": "critical",
        "affected_below": (4, 17, 12),
        "description": "Prototype pollution via defaultsDeep",
    },
    # ── Moment.js ─────────────────────────────────────────────────────────────
    {
        "library": "Moment.js",
        "patterns": [r"moment[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"moment@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2022-31129",
        "severity": "high",
        "affected_below": (2, 29, 4),
        "description": "ReDoS via crafted date string",
    },
    {
        "library": "Moment.js",
        "patterns": [r"moment[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"moment@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2016-4055",
        "severity": "medium",
        "affected_below": (2, 11, 2),
        "description": "ReDoS via user-controlled date format string",
    },
    # ── Handlebars ────────────────────────────────────────────────────────────
    {
        "library": "Handlebars",
        "patterns": [r"handlebars[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"handlebars@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2021-23369",
        "severity": "critical",
        "affected_below": (4, 7, 7),
        "description": "Remote code execution via prototype pollution",
    },
    # ── Underscore ────────────────────────────────────────────────────────────
    {
        "library": "Underscore",
        "patterns": [r"underscore[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"underscore@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2021-23358",
        "severity": "high",
        "affected_below": (1, 13, 0),
        "description": "Arbitrary code execution via template",
    },
    # ── Highlight.js ──────────────────────────────────────────────────────────
    {
        "library": "Highlight.js",
        "patterns": [r"highlight[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"highlight\.js@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2020-26237",
        "severity": "medium",
        "affected_below": (10, 4, 1),
        "description": "ReDoS in several language parsers",
    },
    # ── Axios ─────────────────────────────────────────────────────────────────
    {
        "library": "Axios",
        "patterns": [r"axios[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"axios@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2020-28168",
        "severity": "medium",
        "affected_below": (0, 21, 1),
        "description": "SSRF via URL-encoded redirect",
    },
    # ── Angular ───────────────────────────────────────────────────────────────
    {
        "library": "AngularJS",
        "patterns": [r"angular[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"angularjs@(\d+\.\d+\.?\d*)/",
                     r"angular\.js@(\d+\.\d+\.?\d*)/"],
        "cve": "CVE-2022-25844",
        "severity": "medium",
        "affected_below": (1, 8, 0),
        "description": "ReDoS via angular.copy on deeply nested object",
    },
    # ── Vue ───────────────────────────────────────────────────────────────────
    {
        "library": "Vue.js",
        "patterns": [r"vue[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js",
                     r"vue@(\d+\.\d+\.?\d*)/dist/"],
        "cve": "CVE-2021-43577",
        "severity": "medium",
        "affected_below": (2, 6, 14),
        "description": "XSS in v-bind directive with user-controlled keys",
    },
    # ── Prototype.js ──────────────────────────────────────────────────────────
    {
        "library": "Prototype.js",
        "patterns": [r"prototype[./-](\d+\.\d+\.?\d*)(?:\.min)?\.js"],
        "cve": "CVE-2020-27511",
        "severity": "medium",
        "affected_below": (1, 7, 4),
        "description": "Prototype pollution",
    },
]


def _parse_version(ver_str: str) -> tuple[int, ...] | None:
    parts = re.sub(r"[^0-9.]", "", ver_str).split(".")
    try:
        return tuple(int(p) for p in parts if p)
    except ValueError:
        return None


def _is_affected(version: tuple[int, ...], affected_below: tuple[int, int, int]) -> bool:
    # Pad to same length for comparison
    v = version + (0,) * (3 - len(version))
    return v < affected_below


def _compiled_patterns() -> list[tuple[re.Pattern, dict]]:
    compiled = []
    for entry in _DB:
        for pat in entry["patterns"]:
            compiled.append((re.compile(pat, re.IGNORECASE), entry))
    return compiled


def scan_raw_dir(raw_dir: str) -> list[dict]:
    """Scan all raw CSV.gz files in raw_dir for vulnerable JS libraries."""
    patterns = _compiled_patterns()
    seen: set[tuple] = set()  # deduplicate (site, resource_url, cve)
    results: list[dict] = []

    for fname in sorted(os.listdir(raw_dir)):
        if not fname.endswith(".meta"):
            continue
        meta_path = os.path.join(raw_dir, fname)
        with open(meta_path) as f:
            meta = dict(line.strip().split("=", 1) for line in f if "=" in line)
        site_url = meta.get("url", "")
        if not site_url:
            continue

        # Find corresponding raw file
        stem = fname[: -len(".meta")]
        raw_gz = os.path.join(raw_dir, stem + ".csv.gz")
        raw_csv = os.path.join(raw_dir, stem + ".csv")
        if os.path.exists(raw_gz):
            raw_file = raw_gz
        elif os.path.exists(raw_csv):
            raw_file = raw_csv
        else:
            continue

        try:
            if raw_file.endswith(".gz"):
                fh = gzip.open(raw_file, "rt", encoding="utf-8", newline="")
            else:
                fh = open(raw_file, newline="", encoding="utf-8")
            rows = list(csv.DictReader(fh))
            fh.close()
        except Exception:
            continue

        for row in rows:
            resource_url = row.get("resource_url", "")
            if not resource_url:
                continue
            for pat, entry in patterns:
                m = pat.search(resource_url)
                if not m:
                    continue
                ver_tuple = _parse_version(m.group(1))
                if ver_tuple is None:
                    continue
                if not _is_affected(ver_tuple, entry["affected_below"]):
                    continue
                key = (site_url, resource_url, entry["cve"])
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "site_url": site_url,
                    "resource_url": resource_url,
                    "library": entry["library"],
                    "version": m.group(1),
                    "cve": entry["cve"],
                    "severity": entry["severity"],
                    "affected_below": ".".join(str(x) for x in entry["affected_below"]),
                    "description": entry["description"],
                })

    return results


def write_vulns(results: list[dict], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VULN_COLUMNS)
        writer.writeheader()
        writer.writerows(results)
