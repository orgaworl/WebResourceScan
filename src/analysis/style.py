import matplotlib as mpl

CATEGORY_COLORS: dict[str, str] = {
    "gambling":  "#e63946",
    "gaming":    "#457b9d",
    "esports":   "#1d3557",
    "crypto":    "#f4a261",
    "payment":   "#2a9d8f",
    "ad-tech":   "#e9c46a",
    "social":    "#264653",
    "news":      "#6d6875",
    "ecommerce": "#b5838d",
    "adult":     "#e07a5f",
    "cdn-infra": "#81b29a",
    "streaming": "#f2cc8f",
    "reference": "#3d405b",
    "unknown":   "#aaaaaa",
}

DOMAIN_CAT_COLORS: dict[str, str] = {
    "ad":        "#e63946",
    "analytics": "#ff9f1c",
    "social":    "#a8dadc",
    "cdn":       "#457b9d",
    "payment":   "#2a9d8f",
    "gambling":  "#f4a261",
    "gaming":    "#1d3557",
    "other":     "#aaaaaa",
}

RES_COLORS: list[str] = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
    "#59a14f", "#edc948", "#b07aa1",
]


def apply_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor":   "white",
        "axes.facecolor":     "white",
        "axes.edgecolor":     "#cccccc",
        "axes.grid":          False,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.labelcolor":    "#333333",
        "axes.titlecolor":    "#1a1a1a",
        "axes.titlesize":     15,
        "axes.titleweight":   "semibold",
        "axes.labelsize":     13,
        "xtick.labelsize":    11,
        "ytick.labelsize":    11,
        "xtick.color":        "#555555",
        "ytick.color":        "#555555",
        "font.family":        "PingFang SC",
        "figure.dpi":         150,
        "savefig.dpi":        150,
        "savefig.bbox":       "tight",
        "savefig.facecolor":  "white",
    })
