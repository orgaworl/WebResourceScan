import argparse
import csv
import os
from urllib.parse import urlparse

from tqdm import tqdm

from crawler import crawl
from classifier import DomainClassifier
from reporter import build_row, CSV_COLUMNS


def _load_done_urls(output_path: str) -> set[str]:
    if not os.path.exists(output_path):
        return set()
    with open(output_path, newline="") as f:
        reader = csv.DictReader(f)
        return {row["url"] for row in reader}


def main():
    parser = argparse.ArgumentParser(description="Web resource classifier")
    parser.add_argument("--input", required=True, help="Path to URL list file (one URL per line)")
    parser.add_argument("--output", default="data/results.csv", help="Output CSV path")
    parser.add_argument("--cache", default="data/domain_cache.json", help="Domain cache JSON path")
    args = parser.parse_args()

    with open(args.input) as f:
        urls = [line.strip() for line in f if line.strip()]

    done_urls = _load_done_urls(args.output)
    pending = [u for u in urls if u not in done_urls]

    if not pending:
        print("All URLs already processed.")
        return

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    write_header = not os.path.exists(args.output)

    classifier = DomainClassifier(args.cache)

    with open(args.output, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()

        for url in tqdm(pending, desc="Crawling", unit="url"):
            crawl_result = crawl(url)
            source_domain = urlparse(url).netloc

            all_domains = list({
                r["domain"] for r in crawl_result.get("resources", [])
                if r["domain"] and r["domain"] != source_domain
            })
            if all_domains:
                classifier.classify(all_domains)

            row = build_row(crawl_result, classifier.cache, source_domain=source_domain)
            writer.writerow(row)
            csvfile.flush()


if __name__ == "__main__":
    main()
