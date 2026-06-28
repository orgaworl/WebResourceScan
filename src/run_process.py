import argparse
import csv
import glob
import gzip
import io
import os

from .classifier import DomainClassifier
from .raw_io import read_raw, RAW_COLUMNS
from .reporter import build_row, CSV_COLUMNS
from .analysis.categories import build_site_category_map, get_site_category

import pandas as pd

CAT_COLS = ["cat_gambling", "cat_gaming", "cat_ad", "cat_payment", "cat_cdn", "cat_other"]


def _aggregate(raw_dir: str, output: str) -> None:
    raw_files = sorted(
        glob.glob(os.path.join(raw_dir, "*.csv.gz")) +
        glob.glob(os.path.join(raw_dir, "*.csv"))
    )
    if not raw_files:
        print(f"No raw files found in {raw_dir}")
        return

    classifier = DomainClassifier()
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    written = 0

    with open(output, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for raw_file in raw_files:
            stem = raw_file
            for ext in (".csv.gz", ".csv"):
                if stem.endswith(ext):
                    stem = stem[: -len(ext)]
                    break
            meta_file = stem + ".meta"
            if not os.path.exists(meta_file):
                print(f"Skipping {raw_file} (no .meta file)")
                continue

            with open(meta_file) as f:
                meta = dict(line.strip().split("=", 1) for line in f if "=" in line)
            source_url = meta.get("url", "")
            status = meta.get("status", "ok")
            if not source_url:
                continue

            rows = read_raw(raw_file)
            domains = list({
                r["domain"] for r in rows
                if r.get("is_third_party", "").lower() == "true" and r.get("domain")
            })
            if domains:
                classifier.classify(domains)
                for r in rows:
                    if r.get("is_third_party", "").lower() == "true":
                        r["domain_category"] = classifier.cache.get(r["domain"], "other")
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=RAW_COLUMNS)
                w.writeheader()
                w.writerows(rows)
                if raw_file.endswith(".gz"):
                    with gzip.open(raw_file, "wt", encoding="utf-8", newline="") as gf:
                        gf.write(buf.getvalue())
                else:
                    with open(raw_file, "w", newline="") as f:
                        f.write(buf.getvalue())

            writer.writerow(build_row(source_url, status, rows))
            written += 1

    print(f"Aggregated {written} sites → {output}")


def _clean(input_csv: str, output_csv: str, urls_file: str) -> None:
    df = pd.read_csv(input_csv)
    total = len(df)

    df["_url_norm"] = df["url"].str.rstrip("/")
    df = df.drop_duplicates(subset="_url_norm", keep="first").drop(columns="_url_norm")
    df = df[df["status"] == "ok"].copy()
    dropped = total - len(df)

    numeric_cols = [c for c in df.columns if c.startswith("res_") or c.startswith("cat_") or c == "total_resources"]
    df[numeric_cols] = df[numeric_cols].fillna(0).astype(int)
    df["third_party_domains"] = df["third_party_domains"].fillna("")

    try:
        cat_map = build_site_category_map(urls_file)
        df["site_category"] = df["url"].apply(lambda u: get_site_category(u, cat_map))
    except FileNotFoundError:
        df["site_category"] = "unknown"

    total_res = df["total_resources"].replace(0, pd.NA)
    df["script_ratio"]    = ((df["res_script"] + df["res_xhr"]) / total_res).fillna(0).round(4)
    df["image_ratio"]     = (df["res_image"] / total_res).fillna(0).round(4)
    df["ad_intensity"]    = (df["cat_ad"] / total_res).fillna(0).round(4)
    df["tp_ratio"]        = (df[CAT_COLS].sum(axis=1) / total_res).fillna(0).round(4)
    df["tp_domain_count"] = df["third_party_domains"].apply(
        lambda s: len([x for x in s.split(",") if x.strip()]) if s else 0
    )

    df.to_csv(output_csv, index=False)
    print(f"Kept {len(df)} rows, dropped {dropped} rows (status != ok or duplicate)")
    print(f"Site categories: {df['site_category'].value_counts().to_dict()}")
    print(f"Saved to {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="Re-aggregate raw CSVs then clean and compute derived metrics")
    parser.add_argument("--raw-dir",   default="data/raw",             help="Directory of per-site raw CSVs")
    parser.add_argument("--results",   default="data/results.csv",     help="Aggregated summary CSV (output of aggregate step)")
    parser.add_argument("--output",    default="data/results_clean.csv", help="Final cleaned CSV")
    parser.add_argument("--urls-file", default="urls.txt",             help="urls.txt for site category mapping")
    parser.add_argument("--skip-aggregate", action="store_true",
                        help="Skip re-aggregation, only run clean on existing --results file")
    args = parser.parse_args()

    if not args.skip_aggregate:
        _aggregate(args.raw_dir, args.results)

    _clean(args.results, args.output, args.urls_file)


if __name__ == "__main__":
    main()
