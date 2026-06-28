import argparse
import csv
import glob
import os

from .classifier import DomainClassifier
from .raw_io import read_raw, RAW_COLUMNS
from .reporter import build_row, CSV_COLUMNS


def main():
    parser = argparse.ArgumentParser(description="Re-aggregate summary from raw per-site CSVs")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory containing per-site raw CSVs")
    parser.add_argument("--output", default="data/results.csv", help="Output summary CSV path")
    args = parser.parse_args()

    raw_files = sorted(glob.glob(os.path.join(args.raw_dir, "*.csv")))
    if not raw_files:
        print(f"No raw CSV files found in {args.raw_dir}")
        return

    classifier = DomainClassifier()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    written = 0
    with open(args.output, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for raw_file in raw_files:
            meta_file = raw_file.replace(".csv", ".meta")
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
                with open(raw_file, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=RAW_COLUMNS)
                    w.writeheader()
                    w.writerows(rows)

            writer.writerow(build_row(source_url, status, rows))
            written += 1

    print(f"Aggregated {written} sites → {args.output}")


if __name__ == "__main__":
    main()
