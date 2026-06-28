import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Clean results CSV")
    parser.add_argument("--input", default="data/results.csv")
    parser.add_argument("--output", default="data/results_clean.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    total = len(df)
    df = df[df["status"] == "ok"].copy()
    dropped = total - len(df)

    numeric_cols = [c for c in df.columns if c.startswith("res_") or c.startswith("cat_") or c == "total_resources"]
    df[numeric_cols] = df[numeric_cols].fillna(0).astype(int)
    df["third_party_domains"] = df["third_party_domains"].fillna("")

    df.to_csv(args.output, index=False)
    print(f"Kept {len(df)} rows, dropped {dropped} rows (status != ok)")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
