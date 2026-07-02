import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from .style import apply_style, CATEGORY_COLORS, DOMAIN_CAT_COLORS

try:
    from ..classifier import classify_domain
except ImportError:
    def classify_domain(d: str) -> str:  # type: ignore[misc]
        return "other"

SITE_CATS = ["gambling", "gaming", "esports", "crypto", "payment", "ad-tech",
              "social", "news", "ecommerce", "adult", "cdn-infra", "streaming", "reference"]


def _explode_domains(df: pd.DataFrame) -> pd.Series:
    """Return a flat Series of all third-party domain strings across all sites."""
    series = (
        df["third_party_domains"]
        .dropna()
        .str.split(",")
        .explode()
        .str.strip()
    )
    return series[series != ""]


def plot_top_domains_global(df: pd.DataFrame, out_dir: str, n: int = 25) -> None:
    """Horizontal ranked bar: top N third-party domains by site count."""
    domains = _explode_domains(df)
    # Count unique sites per domain
    domain_site_counts = (
        df.assign(_domains=df["third_party_domains"].fillna(""))
        .explode("_domains") if False else None
    )
    # Simple value_counts gives token frequency; we want site-level presence
    # Build per-site domain sets then count
    site_domain_sets = (
        df["third_party_domains"]
        .fillna("")
        .apply(lambda s: {x.strip() for x in s.split(",") if x.strip()})
    )
    from collections import Counter
    counter: Counter = Counter()
    for s in site_domain_sets:
        counter.update(s)

    top = pd.Series(counter).sort_values(ascending=False).head(n)
    if top.empty:
        print("No third-party domains found, skipping top_tp_domains chart")
        return

    colors = [DOMAIN_CAT_COLORS.get(classify_domain(d), "#aaaaaa") for d in top.index]

    fig, ax = plt.subplots(figsize=(10, max(6, n * 0.32)))
    ax.barh(range(len(top)), top.values[::-1], color=colors[::-1],
            edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top.index[::-1], fontsize=10)
    ax.set_xlabel("Number of Sites Containing Domain")
    ax.set_title(f"Top {n} Third-Party Domains by Site Presence")
    # Domain category legend
    legend_handles = [mpatches.Patch(color=c, label=cat) for cat, c in DOMAIN_CAT_COLORS.items()]
    ax.legend(handles=legend_handles, frameon=False, fontsize=10, loc="lower right")
    fig.savefig(os.path.join(out_dir, "top_tp_domains.png"))
    plt.close(fig)
    print("Saved top_tp_domains.png")


def plot_domain_presence_heatmap(df: pd.DataFrame, out_dir: str, n: int = 20) -> None:
    """Heatmap: top N domains (rows) × site_category (columns), cell = % presence."""
    if "site_category" not in df.columns:
        print("site_category missing, skipping domain_presence_heatmap")
        return

    # Build per-site domain sets
    df = df.copy()
    df["_domain_set"] = df["third_party_domains"].fillna("").apply(
        lambda s: {x.strip() for x in s.split(",") if x.strip()}
    )

    from collections import Counter
    counter: Counter = Counter()
    for s in df["_domain_set"]:
        counter.update(s)
    top_domains = [d for d, _ in counter.most_common(n)]
    if not top_domains:
        return

    cats = [c for c in SITE_CATS if c in df["site_category"].values]
    if not cats:
        cats = sorted(df["site_category"].unique())

    matrix = np.zeros((len(top_domains), len(cats)))
    for ci, cat in enumerate(cats):
        sub = df[df["site_category"] == cat]
        if len(sub) == 0:
            continue
        for di, dom in enumerate(top_domains):
            matrix[di, ci] = sub["_domain_set"].apply(lambda s: dom in s).mean() * 100

    fig, ax = plt.subplots(figsize=(max(10, len(cats) * 1.1), max(6, n * 0.45)))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=35, ha="right", fontsize=11)
    ax.set_yticks(range(len(top_domains)))
    ax.set_yticklabels(top_domains, fontsize=10)
    ax.set_title(f"Top {n} Third-Party Domains: Presence Rate by Site Category (%)")
    # Annotate cells > 15%
    for di in range(len(top_domains)):
        for ci in range(len(cats)):
            v = matrix[di, ci]
            if v > 15:
                ax.text(ci, di, f"{v:.0f}", ha="center", va="center",
                        fontsize=9, color="black" if v < 60 else "white")
    fig.colorbar(im, ax=ax, label="% of Sites", shrink=0.6)
    fig.savefig(os.path.join(out_dir, "domain_presence_heatmap.png"))
    plt.close(fig)
    print("Saved domain_presence_heatmap.png")


def plot_tp_count_vs_resources_bubble(df: pd.DataFrame, out_dir: str) -> None:
    """Bubble scatter: total_resources vs tp_domain_count, sized by script_ratio."""
    if "tp_domain_count" not in df.columns:
        df = df.copy()
        df["tp_domain_count"] = df["third_party_domains"].fillna("").apply(
            lambda s: len([x for x in s.split(",") if x.strip()])
        )
    if "script_ratio" not in df.columns:
        total = df["total_resources"].replace(0, float("nan"))
        df = df.copy()
        df["script_ratio"] = ((df["res_script"] + df["res_xhr"]) / total).fillna(0)

    valid = df[(df["total_resources"] > 0)].copy()
    if valid.empty:
        return

    x = np.log10(valid["total_resources"].clip(lower=1))
    y = valid["tp_domain_count"]
    sizes = (valid["script_ratio"] * 300).clip(lower=20)
    cats = valid["site_category"] if "site_category" in valid.columns else pd.Series(["unknown"] * len(valid))
    colors = [CATEGORY_COLORS.get(c, "#aaaaaa") for c in cats]

    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(x, y, s=sizes, c=colors, alpha=0.75, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("log₁₀(Total Resources)")
    ax.set_ylabel("Unique Third-Party Domain Count")
    ax.set_title("Resource Count vs. Third-Party Diversity\n(bubble size = script+XHR ratio)")

    # Category legend
    cat_list = sorted(set(cats))
    cat_handles = [mpatches.Patch(color=CATEGORY_COLORS.get(c, "#aaaaaa"), label=c) for c in cat_list]
    leg1 = ax.legend(handles=cat_handles, frameon=False, fontsize=9, loc="upper left",
                     title="Site Category", title_fontsize=10, ncol=2)
    ax.add_artist(leg1)

    # Size legend
    for sr, label in [(0.1, "10%"), (0.5, "50%"), (1.0, "100%")]:
        ax.scatter([], [], s=sr * 300, color="#888888", alpha=0.6, label=f"Script ratio {label}")
    ax.legend(frameon=False, fontsize=9, loc="lower right", title="Script Ratio", title_fontsize=10)

    fig.savefig(os.path.join(out_dir, "tp_bubble.png"))
    plt.close(fig)
    print("Saved tp_bubble.png")


def plot_domain_ubiquity_histogram(df: pd.DataFrame, out_dir: str) -> None:
    """Histogram of third-party domain ubiquity scores (how many sites contain each domain)."""
    from collections import Counter
    counter: Counter = Counter()
    for s in df["third_party_domains"].fillna(""):
        for d in s.split(","):
            d = d.strip()
            if d:
                counter[d] += 1

    if not counter:
        print("No third-party domain data, skipping ubiquity histogram")
        return

    scores = np.array(list(counter.values()))
    total_sites = len(df)

    fig, ax = plt.subplots(figsize=(9, 5))
    bins = range(1, scores.max() + 2)
    ax.hist(scores, bins=bins, color="#457b9d", edgecolor="white", linewidth=0.5)
    ax.set_yscale("log")
    ax.set_xlabel("Number of Sites Containing Domain")
    ax.set_ylabel("Number of Domains (log scale)")
    ax.set_title("Third-Party Domain Ubiquity Distribution")

    # Percentile reference lines
    for pct, label, color in [(25, "p25", "#f4a261"), (50, "p50", "#e63946"), (75, "p75", "#2a9d8f")]:
        val = float(np.percentile(scores, pct))
        ax.axvline(val, color=color, linestyle="--", linewidth=1.2, label=f"{label}={val:.0f}")

    # Annotation
    single_site = (scores == 1).sum()
    pct_single = single_site / len(scores) * 100
    ax.text(0.98, 0.95, f"{pct_single:.0f}% of domains\nappear on only 1 site",
            transform=ax.transAxes, ha="right", va="top", fontsize=11, color="#555555")

    ax.legend(frameon=False, fontsize=10)
    fig.savefig(os.path.join(out_dir, "domain_ubiquity_hist.png"))
    plt.close(fig)
    print("Saved domain_ubiquity_hist.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="Third-party domain landscape charts")
    parser.add_argument("--input", default="data/results_clean.csv")
    parser.add_argument("--output-dir", default="plot")
    args = parser.parse_args()

    apply_style()
    os.makedirs(args.output_dir, exist_ok=True)

    df = pd.read_csv(args.input)
    if df.empty:
        print("No data.")
        return

    numeric_cols = [c for c in df.columns if c.startswith("res_") or c.startswith("cat_") or c == "total_resources"]
    df[numeric_cols] = df[numeric_cols].fillna(0)
    df["third_party_domains"] = df["third_party_domains"].fillna("")

    plot_top_domains_global(df, args.output_dir)
    plot_domain_presence_heatmap(df, args.output_dir)
    plot_tp_count_vs_resources_bubble(df, args.output_dir)
    plot_domain_ubiquity_histogram(df, args.output_dir)


if __name__ == "__main__":
    main()
