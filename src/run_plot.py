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

# English → Chinese label mappings
SITE_CAT_ZH: dict[str, str] = {
    "gambling":  "博彩",
    "gaming":    "游戏",
    "esports":   "电竞",
    "crypto":    "加密货币",
    "payment":   "支付",
    "ad-tech":   "广告技术",
    "social":    "社交媒体",
    "news":      "新闻",
    "ecommerce": "电商",
    "adult":     "成人",
    "cdn-infra": "CDN/基础设施",
    "streaming": "流媒体",
    "reference": "参考/教育",
    "unknown":   "未知",
}

DOMAIN_CAT_ZH: dict[str, str] = {
    "ad":        "广告",
    "analytics": "分析/监测",
    "social":    "社交",
    "cdn":       "CDN",
    "payment":   "支付",
    "gambling":  "博彩",
    "gaming":    "游戏",
    "other":     "其他",
}


CAT_COL_COLORS = [
    DOMAIN_CAT_COLORS.get("gambling"),   # cat_gambling
    DOMAIN_CAT_COLORS.get("gaming"),     # cat_gaming
    DOMAIN_CAT_COLORS.get("ad"),         # cat_ad
    DOMAIN_CAT_COLORS.get("analytics"),  # cat_analytics
    DOMAIN_CAT_COLORS.get("social"),     # cat_social
    DOMAIN_CAT_COLORS.get("payment"),    # cat_payment
    DOMAIN_CAT_COLORS.get("cdn"),        # cat_cdn
    DOMAIN_CAT_COLORS.get("other"),      # cat_other
]


def _zh(cat: str) -> str:
    return SITE_CAT_ZH.get(cat, cat)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _save(fig: plt.Figure, out_dir: str, name: str) -> None:
    fig.savefig(os.path.join(out_dir, name), bbox_inches="tight")
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
    colors = [CAT_COL_COLORS[CAT_COLS.index(c)] for c in totals.index]
    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        totals, labels=None, autopct="%1.1f%%", startangle=140,
        colors=colors, wedgeprops={"width": 0.5, "edgecolor": "white", "linewidth": 1.5},
        pctdistance=0.78,
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.text(0, 0, f"合计\n{int(totals.sum())}", ha="center", va="center",
            fontsize=12, fontweight="semibold")
    ax.legend(wedges, labels, loc="lower center", bbox_to_anchor=(0.5, -0.08),
              frameon=False, fontsize=9, ncol=4)
    ax.set_title("第三方域名行业类别占比（所有站点）", pad=12)
    _save(fig, out_dir, "01_resource_category_donut.png")


def plot_resource_bar(df: pd.DataFrame, out_dir: str) -> None:
    totals = df[RES_COLS].sum().sort_values(ascending=False)
    grand_total = totals.sum()
    labels = [RES_LABELS[RES_COLS.index(c)] for c in totals.index]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, totals.values, color=RES_COLORS[: len(labels)],
                  edgecolor="white", linewidth=0.8)
    offset = totals.max() * 0.015
    for bar, v in zip(bars, totals.values):
        pct = v / grand_total * 100 if grand_total else 0
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset,
                f"{pct:.1f}%", ha="center", va="bottom", fontsize=9, color="#444444")
    ax.set_xlabel("资源类型")
    ax.set_ylabel("资源总数")
    ax.set_title("各资源类型分布（所有站点汇总）")
    ax.set_ylim(0, totals.max() * 1.15)
    _save(fig, out_dir, "02_resource_bar.png")


def plot_heatmap(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" in df.columns:
        df = df.sort_values(["site_category", "url"])
    else:
        df = df.sort_values("url")
    if len(df) > 50:
        df = df.head(50)
    heat_df = df.set_index("url")[CAT_COLS].copy()
    heat_df.columns = CAT_LABELS
    # log1p scale so extreme outliers (poki CDN=28k) don't compress all other rows
    heat_log = np.log1p(heat_df.values)
    n_rows = len(heat_df)
    fig, ax = plt.subplots(figsize=(max(10, len(CAT_COLS) * 1.8), max(8, n_rows * 0.38 + 2)))
    im = ax.imshow(heat_log, aspect="auto", cmap="RdYlGn", vmin=0)
    ax.set_xticks(range(len(CAT_LABELS)))
    ax.set_xticklabels(CAT_LABELS, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([u.split("//")[-1].split("/")[0] for u in heat_df.index], fontsize=6)
    ax.set_title("各站点第三方域名类别数量热力图（颜色 = log(1+x) 变换）")
    fig.colorbar(im, ax=ax, label="log(1+域名数)", shrink=0.6, pad=0.02)
    _save(fig, out_dir, "03_url_heatmap.png")


# ── Industry charts ───────────────────────────────────────────────────────────

def plot_crawl_success_by_industry(df_raw: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df_raw.columns:
        return
    # "ok" means status==ok AND total_resources>=10; partial already applied upstream
    grouped = df_raw.groupby("site_category")["status"].apply(
        lambda s: (s == "ok").sum() / len(s) * 100
    ).sort_values(ascending=True)
    counts = df_raw.groupby("site_category")["status"].apply(
        lambda s: f"{(s == 'ok').sum()}/{len(s)}"
    )
    zh_labels = [f"{_zh(c)}  ({counts[c]})" for c in grouped.index]
    colors = ["#2a9d8f" if v >= 70 else "#f4a261" if v >= 40 else "#e63946"
              for v in grouped.values]
    fig, ax = plt.subplots(figsize=(10, max(5, len(grouped) * 0.6)))
    bars = ax.barh(zh_labels, grouped.values, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xlim(0, 115)
    ax.set_xlabel("爬取成功率 (%)")
    ax.set_title("各行业爬取成功率（括号内为 有效/总爬取 数）")
    for bar, v in zip(bars, grouped.values):
        ax.text(v + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{v:.0f}%", va="center", fontsize=9)
    patches = [mpatches.Patch(color="#2a9d8f", label="≥ 70%"),
               mpatches.Patch(color="#f4a261", label="40–70%"),
               mpatches.Patch(color="#e63946", label="< 40%")]
    ax.legend(handles=patches, frameon=False, fontsize=8, loc="lower right", title="成功率区间")
    _save(fig, out_dir, "04_crawl_success_rate.png")


def plot_resource_mix_by_industry(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df.columns:
        return
    group = df.groupby("site_category")[RES_COLS].mean()
    row_sums = group.sum(axis=1).replace(0, np.nan)
    pct = group.div(row_sums, axis=0).fillna(0) * 100
    pct = pct.loc[pct.index.isin(SITE_CATS + ["unknown"])]
    # n= per industry from df
    n_map = df.groupby("site_category").size()
    zh_labels = [f"{_zh(c)}  (n={n_map.get(c, 0)})" for c in pct.index]
    fig, ax = plt.subplots(figsize=(12, max(5, len(pct) * 0.65)))
    lefts = np.zeros(len(pct))
    for i, (col, label) in enumerate(zip(RES_COLS, RES_LABELS)):
        vals = pct[col].values
        ax.barh(zh_labels, vals, left=lefts, color=RES_COLORS[i], label=label,
                edgecolor="white", linewidth=0.5)
        for j, (v, l) in enumerate(zip(vals, lefts)):
            if v > 6:
                ax.text(l + v / 2, j, f"{v:.0f}%", ha="center", va="center",
                        fontsize=7, color="white", fontweight="medium")
        lefts += vals
    ax.set_xlim(0, 100)
    ax.set_xlabel("资源类型占比 (%)")
    ax.set_title("各行业资源类型构成（均值，括号内为样本量）")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22),
              frameon=False, fontsize=8, ncol=4)
    _save(fig, out_dir, "05_resource_mix_by_industry.png")


def plot_tp_load_by_industry(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df.columns:
        return
    # Use median + IQR to resist the heavy-tail skew of resource counts
    med = df.groupby("site_category")[CAT_COLS].median()
    q25 = df.groupby("site_category")[CAT_COLS].quantile(0.25)
    q75 = df.groupby("site_category")[CAT_COLS].quantile(0.75)
    med = med.loc[med.index.isin(SITE_CATS + ["unknown"])]
    q25 = q25.loc[med.index]
    q75 = q75.loc[med.index]
    n_map = df.groupby("site_category").size()
    n_cats, n_groups = len(med), len(CAT_COLS)
    # sort rows by total median third-party load
    row_total = med.sum(axis=1).sort_values(ascending=False)
    med = med.loc[row_total.index]
    q25 = q25.loc[row_total.index]
    q75 = q75.loc[row_total.index]
    zh_index = [f"{_zh(c)}\n(n={n_map.get(c, 0)})" for c in med.index]
    x = np.arange(n_cats)
    width = min(0.8 / n_groups, 0.10)
    fig, ax = plt.subplots(figsize=(max(14, n_cats * 1.2), 6))
    for i, (col, label) in enumerate(zip(CAT_COLS, CAT_LABELS)):
        color = CAT_COL_COLORS[i]
        offset = (i - n_groups / 2 + 0.5) * width
        vals = med[col].values
        err_lo = (med[col] - q25[col]).clip(lower=0).values
        err_hi = (q75[col] - med[col]).clip(lower=0).values
        ax.bar(x + offset, vals, width, label=label, color=color,
               edgecolor="white", linewidth=0.5)
        ax.errorbar(x + offset, vals, yerr=[err_lo, err_hi],
                    fmt="none", color="#333333", linewidth=0.6, capsize=1.5)
    ax.set_xticks(x)
    ax.set_xticklabels(zh_index, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("每站点域名数（中位数，误差棒=IQR）")
    ax.set_title("各行业第三方域名加载量——中位数对比（括号内为样本量）")
    ax.legend(loc="upper right", frameon=False, fontsize=8, ncol=4)
    _save(fig, out_dir, "06_tp_load_by_industry.png")


def plot_script_ratio_boxplot(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df.columns or "script_ratio" not in df.columns:
        return
    groups = {k: v.dropna().values for k, v in df.groupby("site_category")["script_ratio"]}
    order = sorted(groups, key=lambda k: float(np.median(groups[k])), reverse=True)
    data = [groups[k] for k in order]
    colors = [CATEGORY_COLORS.get(k, "#aaaaaa") for k in order]
    n_map = df.groupby("site_category").size()
    zh_labels = [f"{_zh(k)}\n(n={n_map.get(k, 0)})" for k in order]
    fig, ax = plt.subplots(figsize=(13, 6))
    bp = ax.boxplot(data, patch_artist=True,
                    medianprops={"color": "white", "linewidth": 2},
                    whiskerprops={"color": "#888888"}, capprops={"color": "#888888"},
                    flierprops={"marker": "o", "markersize": 3, "alpha": 0.5})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    ax.set_xticks(range(1, len(order) + 1))
    ax.set_xticklabels(zh_labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("脚本密度（脚本+XHR / 总资源）")
    ax.set_ylim(-0.05, 1.15)
    ax.set_title("各行业脚本/XHR 密度分布（括号内为样本量）")
    for i, d in enumerate(data):
        med = float(np.median(d))
        ax.text(i + 1, med + 0.05, f"{med:.2f}", ha="center", fontsize=7, color="#333333")
    _save(fig, out_dir, "07_script_ratio_boxplot.png")


def plot_resource_count_scatter(df: pd.DataFrame, out_dir: str) -> None:
    if "site_category" not in df.columns:
        return
    cats = sorted(df["site_category"].unique())
    cat_idx = {c: i for i, c in enumerate(cats)}
    n_map = df.groupby("site_category").size()
    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(14, 6))
    for cat in cats:
        sub = df[df["site_category"] == cat]
        jitter = rng.uniform(-0.3, 0.3, len(sub))
        log_vals = np.log10(sub["total_resources"].clip(lower=1))
        ax.scatter(cat_idx[cat] + jitter, log_vals,
                   color=CATEGORY_COLORS.get(cat, "#aaaaaa"), alpha=0.7, s=25, zorder=3)
        mean_val = log_vals.mean()
        med_val = log_vals.median()
        # mean: filled triangle ▲
        ax.scatter(cat_idx[cat], mean_val, marker="^", color="black", s=55, zorder=5)
        # median: filled diamond ◆
        ax.scatter(cat_idx[cat], med_val, marker="D", color="#e63946", s=45, zorder=6)
        # label outliers far above median
        threshold = med_val + 1.2
        for _, row in sub[log_vals > threshold].iterrows():
            lv = np.log10(max(row["total_resources"], 1))
            domain = row["url"].split("//")[-1].split("/")[0]
            ax.annotate(domain, (cat_idx[cat] + rng.uniform(-0.1, 0.1), lv),
                        fontsize=6, color="#333333", ha="center",
                        xytext=(0, 6), textcoords="offset points")
    zh_labels = [f"{_zh(c)}\n(n={n_map.get(c,0)})" for c in cats]
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(zh_labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("log₁₀(总资源数)")
    ax.set_title("各行业站点资源数分布（▲=均值，◆=中位数，两者差距反映分布偏态）")
    # legend: categories + mean/median markers
    cat_handles = [mpatches.Patch(color=CATEGORY_COLORS.get(c, "#aaaaaa"), label=_zh(c)) for c in cats]
    marker_handles = [
        ax.scatter([], [], marker="^", color="black", s=55, label="均值"),
        ax.scatter([], [], marker="D", color="#e63946", s=45, label="中位数"),
    ]
    leg1 = ax.legend(handles=cat_handles, frameon=False, fontsize=7, ncol=3,
                     loc="lower center", bbox_to_anchor=(0.5, -0.38), title="行业分类")
    ax.add_artist(leg1)
    ax.legend(handles=marker_handles, frameon=False, fontsize=8, loc="upper right")
    _save(fig, out_dir, "08_resource_count_scatter.png")


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
    cat_of = {d: classify_domain(d) for d in top.index}
    colors = [DOMAIN_CAT_COLORS.get(cat_of[d], "#aaaaaa") for d in top.index]
    fig, ax = plt.subplots(figsize=(11, max(7, n * 0.34)))
    ax.barh(range(len(top)), top.values[::-1], color=colors[::-1], edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top.index[::-1], fontsize=8)
    ax.set_xlabel("包含该域名的站点数量")
    ax.set_title(f"第三方域名站点覆盖数 Top {n}")
    legend_handles = [mpatches.Patch(color=c, label=DOMAIN_CAT_ZH.get(cat, cat))
                      for cat, c in DOMAIN_CAT_COLORS.items()]
    ax.legend(handles=legend_handles, frameon=False, fontsize=8,
              loc="lower right", title="域名类别")
    _save(fig, out_dir, "09_top_tp_domains.png")


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
    zh_cats = [_zh(c) for c in cats]
    fig, ax = plt.subplots(figsize=(max(12, len(cats) * 1.2), max(7, n * 0.48)))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(zh_cats, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(top_domains)))
    ax.set_yticklabels(top_domains, fontsize=8)
    ax.set_title(f"前 {n} 个第三方域名在各行业的覆盖率 (%)")
    for di in range(len(top_domains)):
        for ci in range(len(cats)):
            v = matrix[di, ci]
            if v > 15:
                ax.text(ci, di, f"{v:.0f}", ha="center", va="center",
                        fontsize=7, color="black" if v < 60 else "white")
    fig.colorbar(im, ax=ax, label="站点占比 (%)", shrink=0.6, pad=0.02)
    _save(fig, out_dir, "10_domain_presence_heatmap.png")


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
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.scatter(x, y, s=sizes, c=colors, alpha=0.75, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("log₁₀(总资源数)")
    ax.set_ylabel("第三方域名数量（去重）")
    ax.set_title("资源总数 vs 第三方域名数（气泡大小 = 脚本密度）")
    cat_list = sorted(set(cats))
    cat_handles = [mpatches.Patch(color=CATEGORY_COLORS.get(c, "#aaaaaa"), label=_zh(c))
                   for c in cat_list]
    size_handles = [
        ax.scatter([], [], s=sr * 300, color="#888888", alpha=0.6, label=f"脚本密度 {label}")
        for sr, label in [(0.1, "10%"), (0.5, "50%"), (1.0, "100%")]
    ]
    leg1 = ax.legend(handles=cat_handles, frameon=False, fontsize=7,
                     loc="upper left", title="行业分类", title_fontsize=8, ncol=2)
    ax.add_artist(leg1)
    ax.legend(handles=size_handles, frameon=False, fontsize=7,
              loc="lower right", title="脚本密度", title_fontsize=8)
    _save(fig, out_dir, "11_tp_bubble.png")


def plot_domain_ubiquity_histogram(df: pd.DataFrame, out_dir: str) -> None:
    counter = _explode_domains(df)
    if not counter:
        return
    scores = np.array(list(counter.values()))
    fig, ax = plt.subplots(figsize=(9, 5))
    max_val = int(scores.max())
    if max_val <= 60:
        bins = range(1, max_val + 2)
    else:
        bins = np.unique(np.concatenate([
            np.arange(1, min(20, max_val) + 1),
            np.linspace(20, max_val + 1, 40).astype(int),
        ]))
    ax.hist(scores, bins=bins,
            color="#457b9d", edgecolor="white", linewidth=0.5)
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
    _save(fig, out_dir, "12_domain_ubiquity_hist.png")


# ── Security & composition charts ─────────────────────────────────────────────

def plot_https_adoption(df: pd.DataFrame, out_dir: str) -> None:
    if "https_ratio" not in df.columns or "site_category" not in df.columns:
        return
    group = df.groupby("site_category")["https_ratio"].mean().sort_values(ascending=True)
    if group.empty:
        return
    n_map = df.groupby("site_category").size()
    zh_labels = [f"{_zh(c)}  (n={n_map.get(c, 0)})" for c in group.index]
    colors = ["#2a9d8f" if v >= 0.9 else "#f4a261" if v >= 0.7 else "#e63946"
              for v in group.values]
    fig, ax = plt.subplots(figsize=(10, max(5, len(group) * 0.6)))
    bars = ax.barh(zh_labels, group.values * 100, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xlim(0, 115)
    ax.set_xlabel("HTTPS 资源占比 (%)")
    ax.set_title("各行业 HTTPS 资源采用率（括号内为样本量）")
    for bar, v in zip(bars, group.values):
        ax.text(v * 100 + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{v * 100:.0f}%", va="center", fontsize=9)
    patches = [mpatches.Patch(color="#2a9d8f", label="≥ 90%"),
               mpatches.Patch(color="#f4a261", label="70–90%"),
               mpatches.Patch(color="#e63946", label="< 70%")]
    ax.legend(handles=patches, frameon=False, fontsize=8, loc="lower right", title="安全等级")
    _save(fig, out_dir, "13_https_adoption.png")


def plot_privacy_risk(df: pd.DataFrame, out_dir: str) -> None:
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
    zh_index = [_zh(c) for c in pct.index]
    colors_map = {"cat_ad": "#e63946", "cat_analytics": "#ff9f1c", "cat_social": "#a8dadc"}
    fig, ax = plt.subplots(figsize=(12, max(5, len(pct) * 0.65)))
    lefts = np.zeros(len(pct))
    for col in privacy_cats:
        vals = pct[col].values
        ax.barh(zh_index, vals, left=lefts,
                color=colors_map.get(col, "#aaaaaa"),
                label=privacy_labels.get(col, col),
                edgecolor="white", linewidth=0.5)
        for j, (v, l) in enumerate(zip(vals, lefts)):
            if v > 3:
                ax.text(l + v / 2, j, f"{v:.1f}%", ha="center", va="center",
                        fontsize=7, color="white" if col != "cat_social" else "#444444",
                        fontweight="medium")
        lefts += vals
    ax.set_xlabel("隐私相关资源占比 (%)")
    ax.set_title("各行业隐私风险资源构成（广告 + 分析 + 社交）")
    ax.legend(frameon=False, fontsize=8, loc="lower right", ncol=3)
    _save(fig, out_dir, "14_privacy_risk_by_industry.png")


def plot_resource_origin(df: pd.DataFrame, out_dir: str) -> None:
    if "self_hosted_ratio" not in df.columns or "site_category" not in df.columns:
        return
    group = df.groupby("site_category")[["self_hosted_ratio", "tp_ratio"]].mean()
    if group.empty:
        return
    group = group.sort_values("self_hosted_ratio", ascending=False)
    zh_index = [_zh(c) for c in group.index]
    x = np.arange(len(group))
    width = 0.38
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar(x - width / 2, group["self_hosted_ratio"] * 100, width,
           label="第一方（自托管）", color="#457b9d", edgecolor="white", linewidth=0.6)
    ax.bar(x + width / 2, group["tp_ratio"] * 100, width,
           label="第三方", color="#e63946", edgecolor="white", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(zh_index, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("资源占比 (%)")
    ax.set_title("各行业资源来源构成（第一方 vs 第三方）")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, out_dir, "15_resource_origin_by_industry.png")


# ── Vulnerability charts ──────────────────────────────────────────────────────

SEVERITY_COLORS = {
    "critical": "#7b2d8b",
    "high":     "#e63946",
    "medium":   "#f4a261",
    "low":      "#a8dadc",
}
SEVERITY_ZH = {"critical": "严重", "high": "高危", "medium": "中危", "low": "低危"}


def plot_vuln_by_library(df_vuln: pd.DataFrame, out_dir: str) -> None:
    """Bar chart: number of affected sites per library, coloured by worst severity."""
    if df_vuln.empty:
        return
    sev_order = ["critical", "high", "medium", "low"]
    # worst severity per (site, library) pair
    site_lib = df_vuln.groupby(["site_url", "library"])["severity"].apply(
        lambda s: min(s, key=lambda x: sev_order.index(x))
    ).reset_index()
    counts = site_lib.groupby(["library", "severity"]).size().unstack(fill_value=0)
    # reorder columns to severity order
    counts = counts.reindex(columns=[s for s in sev_order if s in counts.columns])
    counts["_total"] = counts.sum(axis=1)
    counts = counts.sort_values("_total", ascending=True).drop(columns="_total")

    fig, ax = plt.subplots(figsize=(10, max(4, len(counts) * 0.6)))
    lefts = np.zeros(len(counts))
    for sev in counts.columns:
        vals = counts[sev].values
        ax.barh(counts.index, vals, left=lefts,
                color=SEVERITY_COLORS.get(sev, "#aaaaaa"),
                label=SEVERITY_ZH.get(sev, sev),
                edgecolor="white", linewidth=0.5)
        for j, (v, l) in enumerate(zip(vals, lefts)):
            if v > 0:
                ax.text(l + v / 2, j, str(int(v)), ha="center", va="center",
                        fontsize=8, color="white", fontweight="medium")
        lefts += vals

    ax.set_xlabel("受影响的站点数量")
    ax.set_title("各前端库存在已知漏洞的站点数（按严重等级）")
    patches = [mpatches.Patch(color=SEVERITY_COLORS[s], label=SEVERITY_ZH[s])
               for s in sev_order if s in counts.columns]
    ax.legend(handles=patches, frameon=False, fontsize=8, loc="lower right", title="严重等级")
    _save(fig, out_dir, "16_vuln_by_library.png")


def plot_vuln_by_industry(df_vuln: pd.DataFrame, df_clean: pd.DataFrame, out_dir: str) -> None:
    """Bar chart: fraction of sites per industry with at least one known vulnerability."""
    if df_vuln.empty or "site_category" not in df_clean.columns:
        return
    vuln_sites = set(df_vuln["site_url"].unique())
    df = df_clean.copy()
    df["has_vuln"] = df["url"].isin(vuln_sites)
    group = df.groupby("site_category").agg(
        total=("url", "count"),
        vuln=("has_vuln", "sum"),
    )
    group["pct"] = group["vuln"] / group["total"] * 100
    group = group.sort_values("pct", ascending=True)
    zh_labels = [_zh(c) for c in group.index]

    fig, ax = plt.subplots(figsize=(10, max(4, len(group) * 0.6)))
    bars = ax.barh(zh_labels, group["pct"].values,
                   color="#7b2d8b", edgecolor="white", linewidth=0.8, alpha=0.85)
    ax.set_xlim(0, 110)
    ax.set_xlabel("含已知漏洞库的站点占比 (%)")
    ax.set_title("各行业前端库漏洞覆盖率")
    for bar, (_, row) in zip(bars, group.iterrows()):
        ax.text(row["pct"] + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{row['pct']:.0f}%  ({int(row['vuln'])}/{int(row['total'])})",
                va="center", fontsize=8)
    _save(fig, out_dir, "17_vuln_by_industry.png")


def plot_crawl_status_breakdown(df_raw: pd.DataFrame, out_dir: str) -> None:
    """Stacked bar: ok / partial / timeout / error counts per industry."""
    if "site_category" not in df_raw.columns:
        return
    status_order = ["ok", "partial", "timeout", "error"]
    status_zh    = {"ok": "成功", "partial": "部分加载", "timeout": "超时", "error": "错误"}
    status_colors = {"ok": "#2a9d8f", "partial": "#f4a261", "timeout": "#e9c46a", "error": "#e63946"}

    counts = (
        df_raw.groupby(["site_category", "status"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=[s for s in status_order if s in df_raw["status"].unique()], fill_value=0)
    )
    totals = counts.sum(axis=1)
    counts = counts.loc[counts.index.isin(SITE_CATS + ["unknown"])]
    totals = totals[counts.index]
    # sort by total descending
    counts = counts.loc[totals.sort_values(ascending=False).index]
    totals = totals[counts.index]

    zh_index = [f"{_zh(c)}  (n={int(totals[c])})" for c in counts.index]
    fig, ax = plt.subplots(figsize=(12, max(5, len(counts) * 0.6)))
    lefts = np.zeros(len(counts))
    for status in [s for s in status_order if s in counts.columns]:
        vals = counts[status].values
        ax.barh(zh_index, vals, left=lefts,
                color=status_colors[status], label=status_zh[status],
                edgecolor="white", linewidth=0.5)
        for j, (v, l) in enumerate(zip(vals, lefts)):
            if v > 0:
                ax.text(l + v / 2, j, str(int(v)), ha="center", va="center",
                        fontsize=7, color="white", fontweight="medium")
        lefts += vals
    ax.set_xlabel("站点数量")
    ax.set_title("各行业爬取结果状态分布（括号内为总爬取数）")
    ax.legend(frameon=False, fontsize=8, loc="lower right", title="爬取状态")
    _save(fig, out_dir, "18_crawl_status_breakdown.png")


def plot_mean_vs_median(df: pd.DataFrame, out_dir: str) -> None:
    """Paired bar: mean vs median total_resources per industry, to surface skew."""
    if "site_category" not in df.columns:
        return
    g = df.groupby("site_category")["total_resources"].agg(["mean", "median", "count"])
    g = g.loc[g.index.isin(SITE_CATS + ["unknown"])]
    g = g.sort_values("mean", ascending=False)
    if g.empty:
        return
    zh_index = [f"{_zh(c)}\n(n={int(g.loc[c,'count'])})" for c in g.index]
    x = np.arange(len(g))
    width = 0.38
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar(x - width / 2, g["mean"].values, width,
           label="均值", color="#457b9d", edgecolor="white", linewidth=0.6)
    ax.bar(x + width / 2, g["median"].values, width,
           label="中位数", color="#e63946", edgecolor="white", linewidth=0.6, alpha=0.85)
    # annotate ratio
    for i, (mean_v, med_v) in enumerate(zip(g["mean"].values, g["median"].values)):
        if med_v > 0:
            ratio = mean_v / med_v
            ax.text(i, max(mean_v, med_v) * 1.04, f"×{ratio:.0f}",
                    ha="center", fontsize=7, color="#555555")
    ax.set_xticks(x)
    ax.set_xticklabels(zh_index, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("资源总数")
    ax.set_title("各行业资源数均值 vs 中位数（标注倍数差距，反映分布偏态）")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, out_dir, "19_mean_vs_median.png")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate all analysis charts")
    parser.add_argument("--input",       default="data/results_clean.csv",
                        help="Cleaned results CSV (output of 'process')")
    parser.add_argument("--raw-results", default="data/results.csv",
                        help="Full results CSV (all statuses) for success-rate chart")
    parser.add_argument("--vuln-input",  default="data/vulns.csv",
                        help="Vulnerability scan CSV (output of 'process')")
    parser.add_argument("--urls-file",   default="urls.txt")
    parser.add_argument("--output-dir",  default="plot")
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
        # Mark ok-but-thin sites as partial so the status breakdown reflects reality
        thin_mask = (df_raw["status"] == "ok") & (df_raw["total_resources"] < 10)
        df_raw.loc[thin_mask, "status"] = "partial"
        plot_crawl_success_by_industry(df_raw, args.output_dir)
        plot_crawl_status_breakdown(df_raw, args.output_dir)
    plot_resource_mix_by_industry(df, args.output_dir)
    plot_tp_load_by_industry(df, args.output_dir)
    plot_script_ratio_boxplot(df, args.output_dir)
    plot_resource_count_scatter(df, args.output_dir)
    plot_mean_vs_median(df, args.output_dir)

    # Domains
    plot_top_domains_global(df, args.output_dir)
    plot_domain_presence_heatmap(df, args.output_dir)
    plot_tp_count_vs_resources_bubble(df, args.output_dir)
    plot_domain_ubiquity_histogram(df, args.output_dir)

    # Security & composition
    plot_https_adoption(df, args.output_dir)
    plot_privacy_risk(df, args.output_dir)
    plot_resource_origin(df, args.output_dir)

    # Vulnerability analysis
    if os.path.exists(args.vuln_input):
        df_vuln = pd.read_csv(args.vuln_input)
        plot_vuln_by_library(df_vuln, args.output_dir)
        plot_vuln_by_industry(df_vuln, df, args.output_dir)
    else:
        print(f"Skipping vulnerability charts (no {args.vuln_input}, run 'process' first)")


if __name__ == "__main__":
    main()
