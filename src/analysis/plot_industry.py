import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from .categories import build_site_category_map, get_site_category
from .style import apply_style, CATEGORY_COLORS, DOMAIN_CAT_COLORS, RES_COLORS

CAT_COLS   = ["cat_gambling", "cat_gaming", "cat_ad", "cat_payment", "cat_cdn", "cat_other"]
RES_COLS   = ["res_script", "res_stylesheet", "res_image", "res_media", "res_font", "res_xhr", "res_other"]
CAT_LABELS = ["Gambling", "Gaming", "Ads", "Payment", "CDN", "Other"]
RES_LABELS = ["Script", "Stylesheet", "Image", "Media", "Font", "XHR", "Other"]
SITE_CATS  = ["gambling", "gaming", "esports", "crypto", "payment", "ad-tech",
               "social", "news", "ecommerce", "adult", "cdn-infra", "streaming", "reference"]


def plot_crawl_success_by_industry(df_raw: pd.DataFrame, out_dir: str) -> None:
    """Horizontal bar: crawl success rate per site category."""
    if "site_category" not in df_raw.columns:
        print("site_category column missing, skipping crawl success chart")
        return
    grouped = df_raw.groupby("site_category")["status"].apply(
        lambda s: (s == "ok").sum() / len(s) * 100
    ).sort_values(ascending=True)

    colors = ["#2a9d8f" if v >= 70 else "#f4a261" if v >= 40 else "#e63946"
              for v in grouped.values]

    fig, ax = plt.subplots(figsize=(9, max(4, len(grouped) * 0.55)))
    bars = ax.barh(grouped.index, grouped.values, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Crawl Success Rate (%)")
    ax.set_title("Crawl Success Rate by Site Category")
    for bar, v in zip(bars, grouped.values):
        ax.text(v + 1, bar.get_y() + bar.get_height() / 2,
                f"{v:.0f}%", va="center", fontsize=8)
    patches = [
        mpatches.Patch(color="#2a9d8f", label="≥ 70%"),
        mpatches.Patch(color="#f4a261", label="40–70%"),
        mpatches.Patch(color="#e63946", label="< 40%"),
    ]
    ax.legend(handles=patches, frameon=False, fontsize=8)
    fig.savefig(os.path.join(out_dir, "crawl_success_rate.png"))
    plt.close(fig)
    print("Saved crawl_success_rate.png")


def plot_resource_mix_by_industry(df: pd.DataFrame, out_dir: str) -> None:
    """100% stacked horizontal bar: resource type mix per site category."""
    if "site_category" not in df.columns:
        return
    group = df.groupby("site_category")[RES_COLS].mean()
    row_sums = group.sum(axis=1).replace(0, np.nan)
    pct = group.div(row_sums, axis=0).fillna(0) * 100
    pct = pct.loc[pct.index.isin(SITE_CATS + ["unknown"])]

    fig, ax = plt.subplots(figsize=(12, max(4, len(pct) * 0.6)))
    lefts = np.zeros(len(pct))
    for i, (col, label) in enumerate(zip(RES_COLS, RES_LABELS)):
        vals = pct[col].values
        ax.barh(pct.index, vals, left=lefts, color=RES_COLORS[i],
                label=label, edgecolor="white", linewidth=0.5)
        for j, (v, l) in enumerate(zip(vals, lefts)):
            if v > 5:
                ax.text(l + v / 2, j, f"{v:.0f}%", ha="center", va="center",
                        fontsize=7, color="white", fontweight="bold")
        lefts += vals
    ax.set_xlim(0, 100)
    ax.set_xlabel("Resource Mix (%)")
    ax.set_title("Resource Type Composition by Site Category")
    ax.legend(loc="lower right", frameon=False, fontsize=8, ncol=4)
    fig.savefig(os.path.join(out_dir, "resource_mix_by_industry.png"))
    plt.close(fig)
    print("Saved resource_mix_by_industry.png")


def plot_tp_load_by_industry(df: pd.DataFrame, out_dir: str) -> None:
    """Grouped bar: mean third-party domain count per category, by domain category."""
    if "site_category" not in df.columns:
        return
    group = df.groupby("site_category")[CAT_COLS].mean()
    group = group.loc[group.index.isin(SITE_CATS + ["unknown"])]

    n_cats = len(group)
    n_groups = len(CAT_COLS)
    x = np.arange(n_cats)
    width = 0.13

    fig, ax = plt.subplots(figsize=(14, 5))
    for i, (col, label) in enumerate(zip(CAT_COLS, CAT_LABELS)):
        color = list(DOMAIN_CAT_COLORS.values())[i % len(DOMAIN_CAT_COLORS)]
        offset = (i - n_groups / 2 + 0.5) * width
        ax.bar(x + offset, group[col].values, width, label=label, color=color,
               edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(group.index, rotation=30, ha="right")
    ax.set_ylabel("Mean Domain Count per Site")
    ax.set_title("Third-Party Domain Load by Site Category")
    ax.legend(frameon=False, fontsize=8, ncol=3)
    fig.savefig(os.path.join(out_dir, "tp_load_by_industry.png"))
    plt.close(fig)
    print("Saved tp_load_by_industry.png")


def plot_script_ratio_boxplot(df: pd.DataFrame, out_dir: str) -> None:
    """Box plot of script_ratio distribution per site category."""
    if "site_category" not in df.columns or "script_ratio" not in df.columns:
        return
    groups = df.groupby("site_category")["script_ratio"]
    present = {k: v.dropna().values for k, v in groups if len(v) > 0}
    # Sort by median descending
    order = sorted(present.keys(), key=lambda k: float(np.median(present[k])), reverse=True)
    data = [present[k] for k in order]
    colors = [CATEGORY_COLORS.get(k, "#aaaaaa") for k in order]

    fig, ax = plt.subplots(figsize=(12, 5))
    bp = ax.boxplot(data, patch_artist=True, notch=False,
                    medianprops={"color": "white", "linewidth": 2},
                    whiskerprops={"color": "#888888"},
                    capprops={"color": "#888888"},
                    flierprops={"marker": "o", "markersize": 3, "alpha": 0.5})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    ax.set_xticks(range(1, len(order) + 1))
    ax.set_xticklabels(order, rotation=30, ha="right")
    ax.set_ylabel("Script Ratio  (script + XHR) / total")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Script/XHR Intensity Distribution by Site Category")
    # Annotate medians
    for i, d in enumerate(data):
        med = float(np.median(d))
        ax.text(i + 1, med + 0.03, f"{med:.2f}", ha="center", fontsize=7, color="#333333")
    fig.savefig(os.path.join(out_dir, "script_ratio_boxplot.png"))
    plt.close(fig)
    print("Saved script_ratio_boxplot.png")


def plot_resource_count_scatter(df: pd.DataFrame, out_dir: str) -> None:
    """Jittered scatter of total_resources per site, colored by site_category."""
    if "site_category" not in df.columns:
        return
    cats = sorted(df["site_category"].unique())
    cat_idx = {c: i for i, c in enumerate(cats)}

    fig, ax = plt.subplots(figsize=(13, 5))
    rng = np.random.default_rng(42)
    for cat in cats:
        sub = df[df["site_category"] == cat]
        x_pos = cat_idx[cat]
        jitter = rng.uniform(-0.3, 0.3, len(sub))
        ax.scatter(x_pos + jitter, np.log10(sub["total_resources"].clip(lower=1)),
                   color=CATEGORY_COLORS.get(cat, "#aaaaaa"), alpha=0.7, s=25, zorder=3)
        mean_val = np.log10(sub["total_resources"].clip(lower=1)).mean()
        ax.scatter(x_pos, mean_val, marker="D", color="black", s=60, zorder=5)

    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=35, ha="right")
    ax.set_ylabel("log₁₀(Total Resources)")
    ax.set_title("Resource Count Distribution by Site Category  (◆ = mean)")
    # Add color legend
    handles = [mpatches.Patch(color=CATEGORY_COLORS.get(c, "#aaaaaa"), label=c) for c in cats]
    ax.legend(handles=handles, frameon=False, fontsize=7, ncol=3, loc="upper right")
    fig.savefig(os.path.join(out_dir, "resource_count_scatter.png"))
    plt.close(fig)
    print("Saved resource_count_scatter.png")


def _add_site_category(df: pd.DataFrame, urls_file: str) -> pd.DataFrame:
    """Add site_category column if missing."""
    if "site_category" in df.columns:
        return df
    try:
        cat_map = build_site_category_map(urls_file)
        df = df.copy()
        df["site_category"] = df["url"].apply(lambda u: get_site_category(u, cat_map))
    except FileNotFoundError:
        df = df.copy()
        df["site_category"] = "unknown"
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-industry comparison charts")
    parser.add_argument("--input", default="data/results_clean.csv",
                        help="Cleaned results CSV with site_category column")
    parser.add_argument("--raw-results", default="data/results.csv",
                        help="Full results CSV (all statuses) for success-rate chart")
    parser.add_argument("--urls-file", default="urls.txt")
    parser.add_argument("--output-dir", default="data/charts")
    args = parser.parse_args()

    apply_style()
    os.makedirs(args.output_dir, exist_ok=True)

    df = pd.read_csv(args.input)
    if df.empty:
        print("No data.")
        return
    df = _add_site_category(df, args.urls_file)

    numeric_cols = [c for c in df.columns if c.startswith("res_") or c.startswith("cat_") or c == "total_resources"]
    df[numeric_cols] = df[numeric_cols].fillna(0)
    if "script_ratio" not in df.columns:
        total = df["total_resources"].replace(0, float("nan"))
        df["script_ratio"] = ((df["res_script"] + df["res_xhr"]) / total).fillna(0)

    # Success-rate chart uses the unfiltered results
    if os.path.exists(args.raw_results):
        df_raw = pd.read_csv(args.raw_results)
        df_raw = _add_site_category(df_raw, args.urls_file)
        plot_crawl_success_by_industry(df_raw, args.output_dir)
    else:
        print(f"Raw results not found at {args.raw_results}, skipping success rate chart")

    plot_resource_mix_by_industry(df, args.output_dir)
    plot_tp_load_by_industry(df, args.output_dir)
    plot_script_ratio_boxplot(df, args.output_dir)
    plot_resource_count_scatter(df, args.output_dir)


if __name__ == "__main__":
    main()
