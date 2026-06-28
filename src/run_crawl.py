import argparse
import csv
import os
from multiprocessing import Pool
from urllib.parse import urlparse

from tqdm import tqdm

from . import config
from .classifier import DomainClassifier
from .crawler import crawl_site
from .raw_io import _etld1, raw_path, read_raw, write_raw
from .reporter import CSV_COLUMNS, build_row


def _load_done_urls(output_path: str) -> set[str]:
    if not os.path.exists(output_path):
        return set()
    with open(output_path, newline="") as f:
        reader = csv.DictReader(f)
        return {row["url"] for row in reader}


def _worker(args: tuple) -> dict:
    """Runs in a subprocess: crawl one site, classify domains, write raw files, return summary row."""
    url, raw_dir, max_pages, depth, stealth = args
    crawl_result = crawl_site(url, max_pages=max_pages, depth=depth, stealth=stealth)
    source_etld1 = _etld1(urlparse(url).netloc)

    third_party_domains = list({
        r["domain"] for r in crawl_result.get("resources", [])
        if r["domain"] and _etld1(r["domain"]) != source_etld1
    })

    classifier = DomainClassifier()
    if third_party_domains:
        classifier.classify(third_party_domains)

    write_raw(crawl_result, classifier.cache, source_etld1, raw_dir)

    meta_file = raw_path(url, raw_dir).replace(".csv", ".meta")
    with open(meta_file, "w") as mf:
        mf.write(f"url={url}\nstatus={crawl_result['status']}\n")

    raw_rows = read_raw(raw_path(url, raw_dir))
    return build_row(url, crawl_result["status"], raw_rows)


def main():
    parser = argparse.ArgumentParser(description="Web resource classifier")
    parser.add_argument("--input", default=config.INPUT_FILE, help="Path to URL list file. Env: INPUT_FILE")
    parser.add_argument("--output", default="data/results.csv", help="Output summary CSV path")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory for per-site raw resource CSVs")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel crawler processes")
    parser.add_argument("--max-pages", type=int, default=20, help="Max pages to crawl per site")
    parser.add_argument("--depth", type=int, default=2, help="BFS link-follow depth (0=entry page only)")
    parser.add_argument("--no-stealth", action="store_true", help="Disable anti-bot evasion (faster, less stealthy)")
    args = parser.parse_args()

    with open(args.input) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    done_urls = _load_done_urls(args.output)
    pending = [u for u in urls if u not in done_urls]

    if not pending:
        print("All URLs already processed.")
        return

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    os.makedirs(args.raw_dir, exist_ok=True)
    write_header = not os.path.exists(args.output)

    tasks = [(url, args.raw_dir, args.max_pages, args.depth, not args.no_stealth) for url in pending]

    with open(args.output, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()

        with Pool(processes=args.workers) as pool:
            for row in tqdm(
                pool.imap_unordered(_worker, tasks),
                total=len(tasks),
                desc="Crawling",
                unit="site",
            ):
                writer.writerow(row)
                csvfile.flush()


if __name__ == "__main__":
    main()
