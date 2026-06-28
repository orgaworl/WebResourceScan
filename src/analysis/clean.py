import argparse

import pandas as pd

from .categories import build_site_category_map, get_site_category

CAT_COLS = ["cat_gambling", "cat_gaming", "cat_ad", "cat_analytics",
            "cat_social", "cat_payment", "cat_cdn", "cat_other"]
RES_COLS = ["res_script", "res_stylesheet", "res_image", "res_media", "res_font", "res_xhr", "res_other"]
QUALITY_COLS = ["https_resources", "error_resources", "iframe_resources",
                "first_party_resources", "unique_domains"]


def main():
    parser = argparse.ArgumentParser(description="Clean results CSV and compute derived metrics")
    parser.add_argument("--input", default="data/results.csv")
    parser.add_argument("--output", default="data/results_clean.csv")
    parser.add_argument("--urls-file", default="urls.txt", help="urls.txt for site category mapping")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    total = len(df)

    # Deduplicate on normalized URL (strip trailing slash), keep first
    df["_url_norm"] = df["url"].str.rstrip("/")
    df = df.drop_duplicates(subset="_url_norm", keep="first").drop(columns="_url_norm")

    df = df[df["status"] == "ok"].copy()
    dropped = total - len(df)

    numeric_cols = [c for c in df.columns if c.startswith("res_") or c.startswith("cat_")
                    or c in ("total_resources",) + tuple(QUALITY_COLS)]
    df[numeric_cols] = df[numeric_cols].fillna(0).astype(int)
    df["third_party_domains"] = df["third_party_domains"].fillna("")

    # Site category from urls.txt
    try:
        cat_map = build_site_category_map(args.urls_file)
        df["site_category"] = df["url"].apply(lambda u: get_site_category(u, cat_map))
    except FileNotFoundError:
        df["site_category"] = "unknown"

    # Derived metrics
    total_res = df["total_resources"].replace(0, pd.NA)
    df["script_ratio"] = ((df["res_script"] + df["res_xhr"]) / total_res).fillna(0).round(4)
    df["image_ratio"]  = (df["res_image"] / total_res).fillna(0).round(4)
    df["ad_intensity"] = (df["cat_ad"] / total_res).fillna(0).round(4)
    df["tp_ratio"]     = (df[CAT_COLS].sum(axis=1) / total_res).fillna(0).round(4)
    df["tp_domain_count"] = df["third_party_domains"].apply(
        lambda s: len([x for x in s.split(",") if x.strip()]) if s else 0
    )

    # New derived metrics
    # Fraction of resources loaded over HTTPS (security posture)
    if "https_resources" in df.columns:
        df["https_ratio"] = (df["https_resources"] / total_res).fillna(0).round(4)

    # Fraction of resources returning HTTP errors (site reliability signal)
    if "error_resources" in df.columns:
        df["error_ratio"] = (df["error_resources"] / total_res).fillna(0).round(4)

    # Fraction of resources from an iframe context (ad-load proxy)
    if "iframe_resources" in df.columns:
        df["iframe_ratio"] = (df["iframe_resources"] / total_res).fillna(0).round(4)

    # Fraction of resources loaded from the site's own domain
    if "first_party_resources" in df.columns:
        df["self_hosted_ratio"] = (df["first_party_resources"] / total_res).fillna(0).round(4)

    # Privacy risk score: fraction of resources from ad + analytics + social
    privacy_cols = [c for c in ["cat_ad", "cat_analytics", "cat_social"] if c in df.columns]
    if privacy_cols:
        df["privacy_score"] = (df[privacy_cols].sum(axis=1) / total_res).fillna(0).round(4)

    # Domain diversity: number of unique eTLD+1s per resource (how spread-out requests are)
    if "unique_domains" in df.columns:
        df["domain_diversity"] = (df["unique_domains"] / total_res.fillna(1)).fillna(0).round(4)

    df.to_csv(args.output, index=False)
    print(f"Kept {len(df)} rows, dropped {dropped} rows (status != ok or duplicate)")
    print(f"Site categories: {df['site_category'].value_counts().to_dict()}")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
