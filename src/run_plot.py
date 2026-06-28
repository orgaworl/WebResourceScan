import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from .analysis.style import apply_style, CATEGORY_COLORS, DOMAIN_CAT_COLORS, RES_COLORS
from .analysis.categories import build_site_category_map, get_site_category

try:
    from .classifier import classify_domain
except ImportError:
    def classify_domain(d: str) -> str:  # type: ignore[misc]
        return "other"

CAT_COLS   = ["cat_gambling", "cat_gaming", "cat_ad", "cat_analytics",
              "cat_social", "cat_payment", "cat_cdn", "cat_other"]
RES_COLS   = ["res_script", "res_stylesheet", "res_image", "res_media", "res_font", "res_xhr", "res_other"]
CAT_LABELS = ["博彩", "游戏", "广告", "分析/监测", "社交", "支付", "CDN", "其他"]
RES_LABELS = ["脚本", "样式表", "图片", "媒体", "字体", "XHR", "其他"]
SITE_CATS  = ["gambling", "gaming", "esports", "crypto", "payment", "ad-tech",
               "social", "news", "ecommerce", "adult", "cdn-infra", "streaming", "reference"]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _save(fig: plt.Figure, out_dir: str, name: str) -> None:
    fig.savefig(os.path.join(out_dir, name))
    plt.close(fig)
    print(f"Saved {name}")


def _add_site_category(df: pd.DataFrame, urls_file: str) -> pd.DataFrame:
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


def _explode_domains(df: pd.DataFrame) -> "Counter":
    from collections import Counter
    counter: Counter = Counter()
    for s in df["third_party_domains"].fillna(""):
        for d in s.split(","):
            d = d.strip()
            if d:
                counter[d] += 1
    return counter


# ── Overview charts ───────────────────────────────────────────────────────────

def plot_resource_category_donut(df: pd.DataFrame, out_dir: str) -> None:
    totals = df[CAT_COLS].sum()
    totals = totals[totals > 0]
    if totals.empty:
        return
    labels = [CAT_LABELS[CAT_COLS.index(c)] for c in totals.index]
    colors = [list(DOMAIN_CAT_COLORS.values())[i % len(DOMAIN_CAT_COLORS)] for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(7, 7))
    _, _, autotexts = ax.pie(
        totals, labels=labels, autopct="%1.1f%%", startangle=140,
        colors=colors, wedgeprops={"width": 0.5, "edgecolor": "white", "linewidth": 1.5},
        pctdistance=0.75,
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax.text(0, 0, f"Total\n{int(totals.sum())}", ha="center", va="center", fontsize=11, fontweight="semibold")
    ax.set_title("第三方域名行业类别占比（所有站点）")
    _save(fig, out_dir, "resource_category_donut.png")


def plot_resource_bar(df: pd.DataFrame, out_dir: str) -> None:
    totals = df[RES_COLS].sum().sort_values(ascending=False)
    grand_total = totals.sum()
    labels = [RES_LABELS[RES_COLS.index(c)] for c in totals.index]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, totals.values, color=RES_COLORS[: len(labels)], edgecolor="white", linewidth=0.8)
    for bar, v in zip(bars, totals.values):
        pct = v / grand_total * 100 if grand_total else 0
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + grand_total * 0.005,
                f"{pct:.1f}%", ha="center", va="bottom", fontsize=8, color="#444444")
    ax.set_xlabel("资源类型")
    ax.set_ylabel("资源总数")
    ax.set_title("各资源类型分布（所有站点汇总）")
    _save(fig, out_dir, "resource_bar.png")


def plot_heatmap(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" in df.columns:
        df = df.sort_values(["site_category", "url"])
    else:
        df = df.sort_values("url")
    if len(df) > 50:
        df = df.head(50)
    heat_df = df.set_index("url")[CAT_COLS].copy()
    heat_df.columns = CAT_LABELS
    n_rows = len(heat_df)
    fig, ax = plt.subplots(figsize=(max(8, len(CAT_COLS) * 1.8), max(6, n_rows * 0.35 + 2)))
    im = ax.imshow(heat_df.values, aspect="auto", cmap="RdYlGn", vmin=0)
    ax.set_xticks(range(len(CAT_LABELS)))
    ax.set_xticklabels(CAT_LABELS, rotation=30, ha="right")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([u.split("//")[-1].split("/")[0] for u in heat_df.index], fontsize=6)
    ax.set_title("各站点第三方域名类别数量热力图")
    fig.colorbar(im, ax=ax, label="域名数量", shrink=0.6)
    _save(fig, out_dir, "url_heatmap.png")


# ── Industry charts ───────────────────────────────────────────────────────────

def plot_crawl_success_by_industry(df_raw: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df_raw.columns:
        return
    grouped = df_raw.groupby("site_category")["status"].apply(
        lambda s: (s == "ok").sum() / len(s) * 100
    ).sort_values(ascending=True)
    colors = ["#2a9d8f" if v >= 70 else "#f4a261" if v >= 40 else "#e63946" for v in grouped.values]
    fig, ax = plt.subplots(figsize=(9, max(4, len(grouped) * 0.55)))
    bars = ax.barh(grouped.index, grouped.values, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xlim(0, 105)
    ax.set_xlabel("爬取成功率 (%)")
    ax.set_title("各行业爬取成功率")
    for bar, v in zip(bars, grouped.values):
        ax.text(v + 1, bar.get_y() + bar.get_height() / 2, f"{v:.0f}%", va="center", fontsize=8)
    patches = [mpatches.Patch(color="#2a9d8f", label="≥ 70%"),
               mpatches.Patch(color="#f4a261", label="40–70%"),
               mpatches.Patch(color="#e63946", label="< 40%")]
    ax.legend(handles=patches, frameon=False, fontsize=8, loc="lower right", title="成功率区间")
    _save(fig, out_dir, "crawl_success_rate.png")


def plot_resource_mix_by_industry(df: pd.DataFrame, out_dir: str) -> None:
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
        ax.barh(pct.index, vals, left=lefts, color=RES_COLORS[i], label=label,
                edgecolor="white", linewidth=0.5)
        for j, (v, l) in enumerate(zip(vals, lefts)):
            if v > 5:
                ax.text(l + v / 2, j, f"{v:.0f}%", ha="center", va="center",
                        fontsize=7, color="white", fontweight="medium")
        lefts += vals
    ax.set_xlim(0, 100)
    ax.set_xlabel("资源类型占比 (%)")
    ax.set_title("各行业资源类型构成")
    ax.legend(loc="lower right", frameon=False, fontsize=8, ncol=4)
    _save(fig, out_dir, "resource_mix_by_industry.png")


def plot_tp_load_by_industry(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df.columns:
        return
    group = df.groupby("site_category")[CAT_COLS].mean()
    group = group.loc[group.index.isin(SITE_CATS + ["unknown"])]
    n_cats, n_groups = len(group), len(CAT_COLS)
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
    ax.set_ylabel("每站点平均域名数量")
    ax.set_title("各行业第三方域名加载量")
    ax.legend(frameon=False, fontsize=8, ncol=3)
    _save(fig, out_dir, "tp_load_by_industry.png")


def plot_script_ratio_boxplot(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df.columns or "script_ratio" not in df.columns:
        return
    groups = {k: v.dropna().values for k, v in df.groupby("site_category")["script_ratio"]}
    order = sorted(groups, key=lambda k: float(np.median(groups[k])), reverse=True)
    data = [groups[k] for k in order]
    colors = [CATEGORY_COLORS.get(k, "#aaaaaa") for k in order]
    fig, ax = plt.subplots(figsize=(12, 5))
    bp = ax.boxplot(data, patch_artist=True,
                    medianprops={"color": "white", "linewidth": 2},
                    whiskerprops={"color": "#888888"}, capprops={"color": "#888888"},
                    flierprops={"marker": "o", "markersize": 3, "alpha": 0.5})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    ax.set_xticks(range(1, len(order) + 1))
    ax.set_xticklabels(order, rotation=30, ha="right")
    ax.set_ylabel("脚本密度（脚本+XHR / 总资源）")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("各行业脚本/XHR 密度分布")
    for i, d in enumerate(data):
        med = float(np.median(d))
        ax.text(i + 1, med + 0.03, f"{med:.2f}", ha="center", fontsize=7, color="#333333")
    _save(fig, out_dir, "script_ratio_boxplot.png")


def plot_resource_count_scatter(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df.columns:
        return
    cats = sorted(df["site_category"].unique())
    cat_idx = {c: i for i, c in enumerate(cats)}
    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(13, 5))
    for cat in cats:
        sub = df[df["site_category"] == cat]
        jitter = rng.uniform(-0.3, 0.3, len(sub))
        ax.scatter(cat_idx[cat] + jitter, np.log10(sub["total_resources"].clip(lower=1)),
                   color=CATEGORY_COLORS.get(cat, "#aaaaaa"), alpha=0.7, s=25, zorder=3)
        mean_val = np.log10(sub["total_resources"].clip(lower=1)).mean()
        ax.scatter(cat_idx[cat], mean_val, marker="D", color="black", s=60, zorder=5)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=35, ha="right")
    ax.set_ylabel("log₁₀(总资源数)")
    ax.set_title("各行业站点资源数分布  (◆ = 均值)")
    handles = [mpatches.Patch(color=CATEGORY_COLORS.get(c, "#aaaaaa"), label=c) for c in cats]
    ax.legend(handles=handles, frameon=False, fontsize=7, ncol=3, loc="upper right", title="行业分类")
    _save(fig, out_dir, "resource_count_scatter.png")


# ── Domain charts ─────────────────────────────────────────────────────────────

def plot_top_domains_global(df: pd.DataFrame, out_dir: str, n: int = 25) -> None:
    site_sets = df["third_party_domains"].fillna("").apply(
        lambda s: {x.strip() for x in s.split(",") if x.strip()}
    )
    from collections import Counter
    site_counter: Counter = Counter()
    for s in site_sets:
        site_counter.update(s)
    top = pd.Series(site_counter).sort_values(ascending=False).head(n)
    if top.empty:
        return
    colors = [DOMAIN_CAT_COLORS.get(classify_domain(d), "#aaaaaa") for d in top.index]
    fig, ax = plt.subplots(figsize=(10, max(6, n * 0.32)))
    ax.barh(range(len(top)), top.values[::-1], color=colors[::-1], edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top.index[::-1], fontsize=8)
    ax.set_xlabel("包含该域名的站点数量")
    ax.set_title(f"第三方域名站点覆盖数 Top {n}")
    legend_handles = [mpatches.Patch(color=c, label=cat) for cat, c in DOMAIN_CAT_COLORS.items()]
    ax.legend(handles=legend_handles, frameon=False, fontsize=8, loc="lower right", title="域名类别")
    _save(fig, out_dir, "top_tp_domains.png")


def plot_domain_presence_heatmap(df: pd.DataFrame, out_dir: str, n: int = 20) -> None:
    if "site_category" not in df.columns:
        return
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
    ax.set_xticklabels(cats, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(top_domains)))
    ax.set_yticklabels(top_domains, fontsize=8)
    ax.set_title(f"前 {n} 个第三方域名在各行业的覆盖率 (%)")
    for di in range(len(top_domains)):
        for ci in range(len(cats)):
            v = matrix[di, ci]
            if v > 15:
                ax.text(ci, di, f"{v:.0f}", ha="center", va="center",
                        fontsize=7, color="black" if v < 60 else "white")
    fig.colorbar(im, ax=ax, label="站点占比 (%)", shrink=0.6)
    _save(fig, out_dir, "domain_presence_heatmap.png")


def plot_tp_count_vs_resources_bubble(df: pd.DataFrame, out_dir: str) -> None:
    if "tp_domain_count" not in df.columns:
        df = df.copy()
        df["tp_domain_count"] = df["third_party_domains"].fillna("").apply(
            lambda s: len([x for x in s.split(",") if x.strip()])
        )
    if "script_ratio" not in df.columns:
        total = df["total_resources"].replace(0, float("nan"))
        df = df.copy()
        df["script_ratio"] = ((df["res_script"] + df["res_xhr"]) / total).fillna(0)
    valid = df[df["total_resources"] > 0].copy()
    if valid.empty:
        return
    x = np.log10(valid["total_resources"].clip(lower=1))
    y = valid["tp_domain_count"]
    sizes = (valid["script_ratio"] * 300).clip(lower=20)
    cats = valid["site_category"] if "site_category" in valid.columns else pd.Series(["unknown"] * len(valid))
    colors = [CATEGORY_COLORS.get(c, "#aaaaaa") for c in cats]
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(x, y, s=sizes, c=colors, alpha=0.75, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("log₁₀(总资源数)")
    ax.set_ylabel("第三方域名数量（去重）")
    ax.set_title("资源总数 vs 第三方域名数\n（气泡大小 = 脚本密度）")
    cat_list = sorted(set(cats))
    cat_handles = [mpatches.Patch(color=CATEGORY_COLORS.get(c, "#aaaaaa"), label=c) for c in cat_list]
    leg1 = ax.legend(handles=cat_handles, frameon=False, fontsize=7, loc="upper left",
                     title="行业分类", title_fontsize=8, ncol=2)
    ax.add_artist(leg1)
    for sr, label in [(0.1, "10%"), (0.5, "50%"), (1.0, "100%")]:
        ax.scatter([], [], s=sr * 300, color="#888888", alpha=0.6, label=f"脚本密度 {label}")
    ax.legend(frameon=False, fontsize=7, loc="lower right", title="脚本密度", title_fontsize=8)
    _save(fig, out_dir, "tp_bubble.png")


def plot_domain_ubiquity_histogram(df: pd.DataFrame, out_dir: str) -> None:
    counter = _explode_domains(df)
    if not counter:
        return
    scores = np.array(list(counter.values()))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(scores, bins=range(1, scores.max() + 2), color="#457b9d", edgecolor="white", linewidth=0.5)
    ax.set_yscale("log")
    ax.set_xlabel("包含该域名的站点数量")
    ax.set_ylabel("域名数量（对数坐标）")
    ax.set_title("第三方域名普遍性分布")
    for pct, label, color in [(25, "p25", "#f4a261"), (50, "p50", "#e63946"), (75, "p75", "#2a9d8f")]:
        val = float(np.percentile(scores, pct))
        ax.axvline(val, color=color, linestyle="--", linewidth=1.2, label=f"{label}={val:.0f}")
    single_site = (scores == 1).sum()
    ax.text(0.98, 0.95, f"{single_site / len(scores) * 100:.0f}% 的域名\n仅出现在 1 个站点",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color="#555555")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, out_dir, "domain_ubiquity_hist.png")


# ── New: HTTPS adoption, privacy risk, resource origin ───────────────────────

def plot_https_adoption(df: pd.DataFrame, out_dir: str) -> None:
    """Horizontal bar showing HTTPS ratio per industry (sorted by ratio)."""
    if "https_ratio" not in df.columns or "site_category" not in df.columns:
        return
    group = df.groupby("site_category")["https_ratio"].mean().sort_values(ascending=True)
    if group.empty:
        return
    colors = ["#2a9d8f" if v >= 0.9 else "#f4a261" if v >= 0.7 else "#e63946"
              for v in group.values]
    fig, ax = plt.subplots(figsize=(9, max(4, len(group) * 0.55)))
    bars = ax.barh(group.index, group.values * 100, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xlim(0, 110)
    ax.set_xlabel("HTTPS 资源占比 (%)")
    ax.set_title("各行业 HTTPS 资源采用率")
    for bar, v in zip(bars, group.values):
        ax.text(v * 100 + 1, bar.get_y() + bar.get_height() / 2,
                f"{v * 100:.0f}%", va="center", fontsize=8)
    patches = [mpatches.Patch(color="#2a9d8f", label="≥ 90%"),
               mpatches.Patch(color="#f4a261", label="70–90%"),
               mpatches.Patch(color="#e63946", label="< 70%")]
    ax.legend(handles=patches, frameon=False, fontsize=8, loc="lower right", title="安全等级")
    _save(fig, out_dir, "https_adoption.png")


def plot_privacy_risk(df: pd.DataFrame, out_dir: str) -> None:
    """Stacked bar: ad + analytics + social fraction per industry."""
    privacy_cats = [c for c in ["cat_ad", "cat_analytics", "cat_social"] if c in df.columns]
    privacy_labels = {"cat_ad": "广告", "cat_analytics": "分析/监测", "cat_social": "社交"}
    if not privacy_cats or "site_category" not in df.columns:
        return
    group = df.groupby("site_category")[privacy_cats + ["total_resources"]].mean()
    total = group["total_resources"].replace(0, float("nan"))
    pct = group[privacy_cats].div(total, axis=0).fillna(0) * 100
    if pct.empty:
        return
    pct = pct.sort_values(privacy_cats[0], ascending=False)
    colors_map = {"cat_ad": "#e63946", "cat_analytics": "#ff9f1c", "cat_social": "#a8dadc"}
    fig, ax = plt.subplots(figsize=(12, max(4, len(pct) * 0.6)))
    lefts = np.zeros(len(pct))
    for col in privacy_cats:
        vals = pct[col].values
        ax.barh(pct.index, vals, left=lefts,
                color=colors_map.get(col, "#aaaaaa"),
                label=privacy_labels.get(col, col),
                edgecolor="white", linewidth=0.5)
        for j, (v, l) in enumerate(zip(vals, lefts)):
            if v > 3:
                ax.text(l + v / 2, j, f"{v:.1f}%", ha="center", va="center",
                        fontsize=7, color="white", fontweight="medium")
        lefts += vals
    ax.set_xlabel("隐私相关资源占比 (%)")
    ax.set_title("各行业隐私风险资源构成（广告 + 分析 + 社交）")
    ax.legend(frameon=False, fontsize=8, loc="lower right", ncol=3)
    _save(fig, out_dir, "privacy_risk_by_industry.png")


def plot_resource_origin(df: pd.DataFrame, out_dir: str) -> None:
    """Grouped bar: first-party vs third-party resource fraction per industry."""
    if "self_hosted_ratio" not in df.columns or "site_category" not in df.columns:
        return
    group = df.groupby("site_category")[["self_hosted_ratio", "tp_ratio"]].mean()
    if group.empty:
        return
    group = group.sort_values("self_hosted_ratio", ascending=False)
    x = np.arange(len(group))
    width = 0.38
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width / 2, group["self_hosted_ratio"] * 100, width,
           label="第一方（自托管）", color="#457b9d", edgecolor="white", linewidth=0.6)
    ax.bar(x + width / 2, group["tp_ratio"] * 100, width,
           label="第三方", color="#e63946", edgecolor="white", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(group.index, rotation=30, ha="right")
    ax.set_ylabel("资源占比 (%)")
    ax.set_title("各行业资源来源构成（第一方 vs 第三方）")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, out_dir, "resource_origin_by_industry.png")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate all analysis charts")
    parser.add_argument("--input",       default="data/results_clean.csv",
                        help="Cleaned results CSV (output of 'process')")
    parser.add_argument("--raw-results", default="data/results.csv",
                        help="Full results CSV (all statuses) for success-rate chart")
    parser.add_argument("--urls-file",   default="urls.txt")
    parser.add_argument("--output-dir",  default="data/charts")
    args = parser.parse_args()

    apply_style()
    os.makedirs(args.output_dir, exist_ok=True)

    df = pd.read_csv(args.input)
    if df.empty:
        print("No data to plot.")
        return

    df = _add_site_category(df, args.urls_file)

    numeric_cols = [c for c in df.columns if c.startswith("res_") or c.startswith("cat_")
                    or c in ("total_resources", "https_resources", "error_resources",
                              "iframe_resources", "first_party_resources", "unique_domains")]
    df[numeric_cols] = df[numeric_cols].fillna(0)
    df["third_party_domains"] = df["third_party_domains"].fillna("")
    if "script_ratio" not in df.columns:
        total = df["total_resources"].replace(0, float("nan"))
        df["script_ratio"] = ((df["res_script"] + df["res_xhr"]) / total).fillna(0)
    if "tp_ratio" not in df.columns:
        total = df["total_resources"].replace(0, float("nan"))
        df["tp_ratio"] = (df[[c for c in CAT_COLS if c in df.columns]].sum(axis=1) / total).fillna(0)
    if "tp_domain_count" not in df.columns:
        df["tp_domain_count"] = df["third_party_domains"].apply(
            lambda s: len([x for x in s.split(",") if x.strip()])
        )
    if "https_ratio" not in df.columns and "https_resources" in df.columns:
        total = df["total_resources"].replace(0, float("nan"))
        df["https_ratio"] = (df["https_resources"] / total).fillna(0)
    if "self_hosted_ratio" not in df.columns and "first_party_resources" in df.columns:
        total = df["total_resources"].replace(0, float("nan"))
        df["self_hosted_ratio"] = (df["first_party_resources"] / total).fillna(0)
    if "privacy_score" not in df.columns:
        privacy_cols = [c for c in ["cat_ad", "cat_analytics", "cat_social"] if c in df.columns]
        if privacy_cols:
            total = df["total_resources"].replace(0, float("nan"))
            df["privacy_score"] = (df[privacy_cols].sum(axis=1) / total).fillna(0)

    # Overview
    plot_resource_category_donut(df, args.output_dir)
    plot_resource_bar(df, args.output_dir)
    plot_heatmap(df, args.output_dir)

    # Industry
    if os.path.exists(args.raw_results):
        df_raw = pd.read_csv(args.raw_results)
        df_raw = _add_site_category(df_raw, args.urls_file)
        plot_crawl_success_by_industry(df_raw, args.output_dir)
    plot_resource_mix_by_industry(df, args.output_dir)
    plot_tp_load_by_industry(df, args.output_dir)
    plot_script_ratio_boxplot(df, args.output_dir)
    plot_resource_count_scatter(df, args.output_dir)

    # Domains
    plot_top_domains_global(df, args.output_dir)
    plot_domain_presence_heatmap(df, args.output_dir)
    plot_tp_count_vs_resources_bubble(df, args.output_dir)
    plot_domain_ubiquity_histogram(df, args.output_dir)

    # Security & composition
    plot_https_adoption(df, args.output_dir)
    plot_privacy_risk(df, args.output_dir)
    plot_resource_origin(df, args.output_dir)


if __name__ == "__main__":
    main()
