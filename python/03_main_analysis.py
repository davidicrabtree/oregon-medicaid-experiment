"""What did Medicaid do?

Two estimates for each outcome:
  - Effect of winning the lottery (intent-to-treat): compare winners with non-winners.
  - Effect of having Medicaid: winning raised enrollment by only ~24 points, so the lottery effect
    understates what coverage itself does. Two-stage least squares uses winning as an instrument
    for enrollment, estimating the effect among people who enrolled because they won. This rests
    on two assumptions: winning affects health only through Medicaid, and no one was made less
    likely to enroll by winning.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (FIGURES, OUTCOMES, TABLES, controls_for, iv, load_analysis, ols,
                    save_figure, set_plot_style, weighted_mean)

set_plot_style()
ohie = load_analysis()

# First stage: how much did winning raise Medicaid enrollment? -----------------------------------

first_stage = ols(ohie, "medicaid", ["treatment", "hh_size"])
enrolled = ohie.groupby("treatment").apply(lambda g: weighted_mean(g["medicaid"], g["weight"]))

pd.DataFrame([{
    "enrolled_control": enrolled[0],
    "enrolled_winners": enrolled[1],
    "first_stage": first_stage.params["treatment"],
    "first_stage_se": first_stage.bse["treatment"],
    "f_stat": (first_stage.params["treatment"] / first_stage.bse["treatment"]) ** 2,
}]).to_csv(TABLES / "first_stage.csv", index=False)

# Effects on outcomes ----------------------------------------------------------------------------


def estimate_effects(outcome: str) -> dict:
    controls = controls_for(outcome)
    d = ohie.dropna(subset=[outcome, *controls])
    itt_fit = ols(d, outcome, ["treatment", *controls])
    iv_fit = iv(d, outcome, controls)
    itt_ci = itt_fit.conf_int().loc["treatment"]
    iv_ci = iv_fit.conf_int().loc["medicaid"]
    ctrl = d[d["treatment"] == 0]
    return {
        "outcome": outcome,
        "label": OUTCOMES[outcome],
        "n": int(iv_fit.nobs),
        "control_mean": weighted_mean(ctrl[outcome], ctrl["weight"]),
        "itt": itt_fit.params["treatment"],
        "itt_low": itt_ci.iloc[0],
        "itt_high": itt_ci.iloc[1],
        "effect": iv_fit.params["medicaid"],
        "effect_se": iv_fit.std_errors["medicaid"],
        "effect_low": iv_ci.iloc[0],
        "effect_high": iv_ci.iloc[1],
        "p_value": iv_fit.pvalues["medicaid"],
    }


results = pd.DataFrame([estimate_effects(outcome) for outcome in OUTCOMES])
results.to_csv(TABLES / "main_effects.csv", index=False)

# Figure -----------------------------------------------------------------------------------------

plot = results.iloc[::-1].reset_index(drop=True)
pct = lambda col: plot[col] * 100
colors = np.where(plot["p_value"] < 0.05, "#2A6F97", "0.55")

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.axvline(0, color="0.4", linewidth=1)
for i, row in plot.iterrows():
    ax.plot([row["effect_low"] * 100, row["effect_high"] * 100], [i, i],
            color=colors[i], linewidth=2.2, solid_capstyle="butt")
    label = f"{row['effect'] * 100:+.2f} pts\n(from {row['control_mean'] * 100:.1f}%)"
    ax.annotate(label.replace("-", "\u2212"), (row["effect"] * 100, i), xytext=(0, 9), textcoords="offset points",
                ha="center", va="bottom", fontsize=9, color="0.2", linespacing=1.1)
ax.scatter(pct("effect"), plot.index, color=colors, s=60, zorder=3)
ax.set_yticks(plot.index, plot["label"])
ax.set_ylim(-0.6, len(plot) - 0.2)
ax.set_xlabel("Effect of Medicaid coverage (percentage points, 95% CI)")
save_figure(fig, FIGURES / "main_effects.png",
            title="Medicaid reduced depression and financial catastrophe,\n"
                  "with no detectable effect on high blood pressure")
