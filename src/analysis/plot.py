import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .style import apply_style, RES_COLORS, DOMAIN_CAT_COLORS

CAT_COLS   = ["cat_gambling", "cat_gaming", "cat_ad", "cat_payment", "cat_cdn", "cat_other"]
RES_COLS   = ["res_script", "res_stylesheet", "res_image", "res_media", "res_font", "res_xhr", "res_other"]
CAT_LABELS = ["Gambling", "Gaming", "Ads/Tracking", "Payment", "CDN", "Other"]
RES_LABELS = ["Script", "Stylesheet", "Image", "Media", "Font", "XHR", "Other"]


def plot_resource_category_donut(df: pd.DataFrame, out_dir: str) -> None:
    totals = df[CAT_COLS].sum()
    totals = totals[totals > 0]
    if totals.empty:
        print("No category data (donut skipped)")
        return
    labels = [CAT_LABELS[CAT_COLS.index(c)] for c in totals.index]
    colors = [list(DOMAIN_CAT_COLORS.values())[i % len(DOMAIN_CAT_COLORS)] for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        totals, labels=labels, autopct="%1.1f%%", startangle=140,
        colors=colors, wedgeprops={"width": 0.5, "edgecolor": "white", "linewidth": 1.5},
        pctdistance=0.75,
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax.text(0, 0, f"Total\n{int(totals.sum())}", ha="center", va="center", fontsize=11, fontweight="bold")
    ax.set_title("Third-Party Domain Categories (All Sites)")
    fig.savefig(os.path.join(out_dir, "resource_category_donut.png"))
    plt.close(fig)
    print("Saved resource_category_donut.png")


def plot_resource_bar(df: pd.DataFrame, out_dir: str) -> None:
    totals = df[RES_COLS].sum()
    totals = totals.sort_values(ascending=False)
    grand_total = totals.sum()
    labels = [RES_LABELS[RES_COLS.index(c)] for c in totals.index]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, totals.values, color=RES_COLORS[: len(labels)], edgecolor="white", linewidth=0.8)
    for bar, v in zip(bars, totals.values):
        pct = v / grand_total * 100 if grand_total else 0
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + grand_total * 0.005,
                f"{pct:.1f}%", ha="center", va="bottom", fontsize=8, color="#444444")
    ax.set_xlabel("Resource Type")
    ax.set_ylabel("Total Count")
    ax.set_title("Resource Type Distribution Across All Sites")
    ax.yaxis.grid(True, color="white")
    fig.savefig(os.path.join(out_dir, "resource_bar.png"))
    plt.close(fig)
    print("Saved resource_bar.png")


def plot_heatmap(df: pd.DataFrame, out_dir: str) -> None:
    # Sort by site_category if available, else alphabetically by URL
    if "site_category" in df.columns:
        df = df.sort_values(["site_category", "url"])
    else:
        df = df.sort_values("url")

    # Cap rows for legibility
    if len(df) > 50:
        df = df.head(50)

    heat_df = df.set_index("url")[CAT_COLS].copy()
    heat_df.columns = CAT_LABELS

    n_rows = len(heat_df)
    fig_h = max(6, n_rows * 0.35 + 2)
    fig, ax = plt.subplots(figsize=(max(8, len(CAT_COLS) * 1.8), fig_h))
    im = ax.imshow(heat_df.values, aspect="auto", cmap="RdYlGn", vmin=0)
    ax.set_xticks(range(len(CAT_LABELS)))
    ax.set_xticklabels(CAT_LABELS, rotation=30, ha="right")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(
        [f"{row.split('//')[-1].split('/')[0]}" for row in heat_df.index],
        fontsize=6,
    )
    ax.set_title("Third-Party Domain Category Counts per Site")
    fig.colorbar(im, ax=ax, label="Domain Count", shrink=0.6)
    fig.savefig(os.path.join(out_dir, "url_heatmap.png"))
    plt.close(fig)
    print("Saved url_heatmap.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot overview charts")
    parser.add_argument("--input", default="data/results_clean.csv")
    parser.add_argument("--output-dir", default="data/charts")
    args = parser.parse_args()

    apply_style()
    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.read_csv(args.input)

    if df.empty:
        print("No data to plot.")
        return

    plot_resource_category_donut(df, args.output_dir)
    plot_resource_bar(df, args.output_dir)
    plot_heatmap(df, args.output_dir)


if __name__ == "__main__":
    main()
