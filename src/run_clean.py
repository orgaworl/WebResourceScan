import argparse
import glob
import os
import shutil


def main():
    parser = argparse.ArgumentParser(description="Delete crawl output data")
    parser.add_argument("--raw-dir",    default="data/raw",              help="Per-site raw resource directory")
    parser.add_argument("--results",    default="data/results.csv",      help="Aggregated summary CSV")
    parser.add_argument("--clean-csv",  default="data/results_clean.csv", help="Cleaned CSV")
    parser.add_argument("--charts-dir", default="data/charts",           help="Charts directory")
    parser.add_argument("--all",  action="store_true", help="Delete everything (raw + csvs + charts)")
    parser.add_argument("--raw",  action="store_true", help="Delete raw resource files only")
    parser.add_argument("--csv",  action="store_true", help="Delete results CSVs only")
    parser.add_argument("--charts", action="store_true", help="Delete charts only")
    parser.add_argument("--yes",  action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    # Default: everything if no specific flag given
    if not any([args.all, args.raw, args.csv, args.charts]):
        args.all = True

    targets: list[tuple[str, str]] = []

    if args.all or args.raw:
        raw_files = (
            glob.glob(os.path.join(args.raw_dir, "*.csv.gz")) +
            glob.glob(os.path.join(args.raw_dir, "*.csv")) +
            glob.glob(os.path.join(args.raw_dir, "*.meta")) +
            glob.glob(os.path.join(args.raw_dir, "*__ckpt"))
        )
        for f in raw_files:
            targets.append(("file" if os.path.isfile(f) else "dir", f))

    if args.all or args.csv:
        for path in [args.results, args.clean_csv]:
            if os.path.exists(path):
                targets.append(("file", path))

    if args.all or args.charts:
        if os.path.isdir(args.charts_dir):
            png_files = glob.glob(os.path.join(args.charts_dir, "*.png"))
            for f in png_files:
                targets.append(("file", f))

    if not targets:
        print("Nothing to delete.")
        return

    print("Will delete:")
    for kind, path in targets:
        print(f"  {path}")

    if not args.yes:
        confirm = input(f"\nDelete {len(targets)} item(s)? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    deleted = 0
    for kind, path in targets:
        try:
            if kind == "dir":
                shutil.rmtree(path)
            else:
                os.remove(path)
            deleted += 1
        except OSError as e:
            print(f"  Error deleting {path}: {e}")

    print(f"Deleted {deleted}/{len(targets)} items.")


if __name__ == "__main__":
    main()
