"""Shared paths, data loading, and estimators for the OHIE analysis.

Every estimate in this project uses the same design, following Baicker et al. (2013):
survey weights, standard errors clustered by household, and indicators for the number of
household members on the lottery list (the lottery drew households, so selection was random
only conditional on household size). Clustered standard errors use the Stata small-sample
correction so results match the published tables.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.iv import IV2SLS

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"

OUTCOMES = {
    "hypertension": "Elevated blood pressure",
    "depression": "Positive depression screen",
    "catastrophic_spending": "Catastrophic medical spending",
}

# Characteristics fixed before the lottery (sign-up data) or unaffected by it (demographics)
BASELINE = ["female", "age_decile", "race_black", "race_other", "hispanic",
            "list_english", "list_self_signup", "list_first_day", "list_phone",
            "list_po_box", "list_urban"]

CATEGORICAL = {"hh_size", "age_decile"}


def set_plot_style() -> None:
    """Minimal style shared by all figures."""
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "Helvetica",
        "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.spines.bottom": False,
        "axes.grid": True, "axes.grid.axis": "x", "grid.color": "0.92",
        "axes.axisbelow": True,
        "xtick.color": "0.3", "ytick.color": "0.3",
        "xtick.major.size": 0, "ytick.major.size": 0,
    })


def save_figure(fig, path: Path, title: str, subtitle: str | None = None,
                legend_space: float = 0.0) -> None:
    """Lay out a left-aligned title and subtitle above the plot, then save.

    `legend_space` reserves room (inches) between the subtitle and the plot for a legend
    anchored to the top of the axes.
    """
    height = fig.get_figheight()
    line = lambda size: size * 1.25 / 72  # line height in inches
    fig.tight_layout()

    top_pad, gap = 0.15, 0.08
    fig.text(0.02, 1 - top_pad / height, title, ha="left", va="top", fontsize=13)
    header = top_pad + line(13) * (title.count("\n") + 1)
    if subtitle:
        fig.text(0.02, 1 - (header + gap) / height, subtitle, ha="left", va="top",
                 fontsize=10, color="0.25")
        header += gap + line(10) * (subtitle.count("\n") + 1)
    fig.subplots_adjust(top=1 - (header + 0.12 + legend_space) / height)
    fig.savefig(path, dpi=300, facecolor="white")


def load_analysis() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "ohie_analysis.parquet")


def load_invited() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "ohie_invited.parquet")


def controls_for(outcome: str) -> list[str]:
    """Household size for every outcome; blood pressure also adjusts for sex and age decile."""
    return ["hh_size", "female", "age_decile"] if outcome == "hypertension" else ["hh_size"]


def design_matrix(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Columns as regressors, expanding categorical variables into indicators."""
    parts = []
    for col in columns:
        if col in CATEGORICAL:
            parts.append(pd.get_dummies(df[col], prefix=col, drop_first=True, dtype=float))
        else:
            parts.append(df[[col]].astype(float))
    return pd.concat(parts, axis=1)


def weighted_mean(x: pd.Series, w: pd.Series) -> float:
    keep = x.notna()
    return float(np.average(x[keep], weights=w[keep]))


def ols(df: pd.DataFrame, outcome: str, regressors: list[str]):
    """Weighted least squares with household-clustered standard errors."""
    d = df.dropna(subset=[outcome, *regressors])
    X = sm.add_constant(design_matrix(d, regressors))
    return sm.WLS(d[outcome].astype(float), X, weights=d["weight"]).fit(
        cov_type="cluster", cov_kwds={"groups": d["household_id"]}
    )


def iv(df: pd.DataFrame, outcome: str, controls: list[str]):
    """Two-stage least squares: lottery win (treatment) instruments for Medicaid coverage."""
    d = df.dropna(subset=[outcome, *controls])
    exog = sm.add_constant(design_matrix(d, controls))
    return IV2SLS(d[outcome].astype(float), exog, d[["medicaid"]].astype(float),
                  d[["treatment"]].astype(float), weights=d["weight"]).fit(
        cov_type="clustered", clusters=d["household_id"], debiased=True
    )
