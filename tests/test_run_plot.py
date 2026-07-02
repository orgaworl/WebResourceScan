import matplotlib.pyplot as plt
import pandas as pd

from src.run_plot import _save, select_top_industries


def test_select_top_industries_uses_analyzable_site_rate():
    raw = pd.DataFrame(
        {
            "site_category": [
                "gaming",
                "gaming",
                "gaming",
                "ad-tech",
                "ad-tech",
                "reference",
                "reference",
                "cdn-infra",
                "gambling",
                "esports",
            ],
            "status": [
                "ok",
                "ok",
                "timeout",
                "ok",
                "timeout",
                "ok",
                "timeout",
                "ok",
                "ok",
                "ok",
            ],
            "total_resources": [100, 5, 0, 40, 0, 30, 0, 20, 15, 5],
        }
    )

    assert select_top_industries(raw, top_n=3, min_resources=10) == [
        "cdn-infra",
        "gambling",
        "ad-tech",
    ]


def test_save_clears_axes_titles(tmp_path):
    fig, ax = plt.subplots()
    ax.set_title("title should be removed")

    _save(fig, str(tmp_path), "sample.png")

    assert ax.get_title() == ""
