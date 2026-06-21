import argparse
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

CAT_COLS = ["cat_gambling", "cat_gaming", "cat_ad", "cat_payment", "cat_cdn", "cat_other"]
RES_COLS = ["res_script", "res_stylesheet", "res_image", "res_media", "res_font", "res_xhr", "res_other"]
CAT_LABELS = ["Gambling", "Gaming", "Ads/Tracking", "Payment", "CDN", "Other"]
RES_LABELS = ["Script", "Stylesheet", "Image", "Media", "Font", "XHR", "Other"]


def plot_industry_pie(df: pd.DataFrame, out_dir: str):
    totals = df[CAT_COLS].sum()
    totals = totals[totals > 0]
    if totals.empty:
        print("No category data to plot (pie chart skipped)")
        return
    labels = [CAT_LABELS[CAT_COLS.index(c)] for c in totals.index]
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(totals, labels=labels, autopct="%1.1f%%", startangle=140)
    ax.set_title("Third-Party Domain Categories (All Pages)")
    fig.savefig(os.path.join(out_dir, "industry_pie.png"), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print("Saved industry_pie.png")


def plot_resource_bar(df: pd.DataFrame, out_dir: str):
    totals = df[RES_COLS].sum()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(RES_LABELS, totals.values, color="steelblue")
    ax.set_xlabel("Resource Type")
    ax.set_ylabel("Total Count")
    ax.set_title("Resource Type Distribution (All Pages)")
    fig.savefig(os.path.join(out_dir, "resource_bar.png"), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print("Saved resource_bar.png")


def plot_heatmap(df: pd.DataFrame, out_dir: str):
    heat_df = df.set_index("url")[CAT_COLS].copy()
    heat_df.columns = CAT_LABELS
    fig, ax = plt.subplots(figsize=(max(8, len(CAT_COLS) * 1.5), max(6, len(df) * 0.4 + 2)))
    im = ax.imshow(heat_df.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(CAT_LABELS)))
    ax.set_xticklabels(CAT_LABELS, rotation=30, ha="right")
    ax.set_yticks(range(len(heat_df)))
    ax.set_yticklabels(heat_df.index, fontsize=7)
    ax.set_title("Industry Domain Counts Per URL")
    fig.colorbar(im, ax=ax, label="Unique Domain Count")
    fig.savefig(os.path.join(out_dir, "url_heatmap.png"), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print("Saved url_heatmap.png")


def main():
    parser = argparse.ArgumentParser(description="Plot results charts")
    parser.add_argument("--input", default="data/results_clean.csv")
    parser.add_argument("--output-dir", default="data/charts")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.read_csv(args.input)

    if df.empty:
        print("No data to plot.")
        return

    plot_industry_pie(df, args.output_dir)
    plot_resource_bar(df, args.output_dir)
    plot_heatmap(df, args.output_dir)


if __name__ == "__main__":
    main()
