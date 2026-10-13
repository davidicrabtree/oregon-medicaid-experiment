"""Extension: was the blood pressure null a true null, or a study too small to tell?

Part 1 - Power. Only ~24% of lottery winners enrolled because they won, so the study's precision
  for the effect of coverage is far lower than its 12,000-person sample suggests. For each outcome:
  the minimum detectable effect (MDE) at 80% power, what the confidence interval rules out, and how
  large the study would have needed to be to detect smaller effects.

Part 2 - Precision. Can adjusting for characteristics recorded before the lottery tighten the
  estimates? This is the same idea as variance reduction in A/B testing (e.g., CUPED): it helps
  only to the extent the covariates predict the outcome.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

from common import (BASELINE, FIGURES, TABLES, controls_for, iv, load_analysis, ols,
                    save_figure, set_plot_style)

set_plot_style()
ohie = load_analysis()
main = pd.read_csv(TABLES / "main_effects.csv")

ALPHA, TARGET_POWER = 0.05, 0.80
Z_ALPHA, Z_POWER = norm.ppf(1 - ALPHA / 2), norm.ppf(TARGET_POWER)


def power_at(effect, se):
    """Probability a two-sided test rejects zero when the true effect is `effect`."""
    z = np.abs(effect) / se
    return norm.cdf(z - Z_ALPHA) + norm.cdf(-z - Z_ALPHA)


# Part 1: Power ----------------------------------------------------------------------------------

power = main[["outcome", "label", "control_mean", "effect", "effect_se"]].assign(
    mde=(Z_ALPHA + Z_POWER) * main["effect_se"],
    rules_out_beyond=main["effect_low"],  # largest reduction the 95% CI rules out
)
power["mde_relative"] = power["mde"] / power["control_mean"]
power["rules_out_relative"] = power["rules_out_beyond"] / power["control_mean"]
power.to_csv(TABLES / "power_summary.csv", index=False)

# Sample size needed to detect a given reduction in elevated blood pressure, scaling the realized
# standard error (SE shrinks with the square root of sample size)
bp = power.set_index("outcome").loc["hypertension"]
n_bp = main.set_index("outcome").loc["hypertension", "n"]

needed = pd.DataFrame({"relative_reduction": [0.10, 0.20, 0.30, 0.40, 0.50]})
needed["effect_pts"] = needed["relative_reduction"] * bp["control_mean"]
needed["n_needed"] = n_bp * ((Z_ALPHA + Z_POWER) * bp["effect_se"] / needed["effect_pts"]) ** 2
needed["times_actual"] = needed["n_needed"] / n_bp
needed.to_csv(TABLES / "sample_size_needed.csv", index=False)

# Part 2: Precision from covariate adjustment ----------------------------------------------------


def compare_precision(outcome: str) -> dict:
    base_controls = controls_for(outcome)
    adj_controls = base_controls + [c for c in BASELINE if c not in base_controls]
    # Same people in both models, so differences reflect adjustment, not sample changes
    d = ohie.dropna(subset=[outcome, *adj_controls])
    original = iv(d, outcome, base_controls)
    adjusted = iv(d, outcome, adj_controls)
    # How much of the outcome do the baseline characteristics explain (among non-winners)?
    r2 = ols(d[d["treatment"] == 0], outcome, adj_controls).rsquared
    se_o, se_a = original.std_errors["medicaid"], adjusted.std_errors["medicaid"]
    return {
        "outcome": outcome,
        "n": int(original.nobs),
        "effect_original": original.params["medicaid"],
        "se_original": se_o,
        "effect_adjusted": adjusted.params["medicaid"],
        "se_adjusted": se_a,
        "se_reduction": 1 - se_a / se_o,
        # Adjustment is worth as much as this many additional participants (proportion)
        "equivalent_sample_gain": (se_o / se_a) ** 2 - 1,
        "covariate_r2": r2,
    }


precision = pd.DataFrame([compare_precision(o) for o in main["outcome"]]).merge(
    main[["outcome", "label"]], on="outcome")
precision.to_csv(TABLES / "covariate_adjustment.csv", index=False)

# Figure -----------------------------------------------------------------------------------------

effects = np.arange(0, 0.1205, 0.001)
# Baicker et al. (2013, p. 1719) cite a 7.16-point reduction in hypertension as an example of a
# clinically significant change that their confidence interval could not exclude.
CLINICAL = 0.0716
clinical_power = power_at(CLINICAL, bp["effect_se"])

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.axvline(CLINICAL * 100, color="#C8553D", linestyle=":", linewidth=1.5)
ax.scatter([CLINICAL * 100], [clinical_power], color="#C8553D", s=50, zorder=3)
ax.text(CLINICAL * 100 - 0.3, 0.97,
        f"A reduction the original authors\ncall clinically significant\n"
        f"({CLINICAL * 100:.2f} pts): {clinical_power:.0%} power",
        ha="right", va="top", fontsize=9, color="#C8553D")
ax.axhline(TARGET_POWER, color="0.5", linestyle="--", linewidth=1)
ax.plot(effects * 100, power_at(effects, bp["effect_se"]), color="#2A6F97", linewidth=2.2)
ax.scatter([bp["mde"] * 100], [TARGET_POWER], color="#2A6F97", s=50, zorder=3)
ax.text(bp["mde"] * 100 + 0.3, TARGET_POWER - 0.17,
        f"80% power only for reductions\nof {bp['mde'] * 100:.1f} pts or more "
        f"({bp['mde_relative'] * 100:.0f}% of the\n{bp['control_mean'] * 100:.1f}% baseline rate)",
        fontsize=9)
ax.set_xlim(-0.3, 12.5)
ax.set_ylim(0, 1.02)
ax.set_xticks(range(0, 13, 2))
ax.yaxis.set_major_formatter(plt.matplotlib.ticker.PercentFormatter(1.0))
ax.grid(axis="y", color="0.92")
ax.set_xlabel("True reduction in elevated blood pressure (percentage points)")
ax.set_ylabel("Statistical power")
save_figure(fig, FIGURES / "power_curve.png",
            title="The study could only detect large effects on blood pressure",
            subtitle="Chance of a statistically significant result if Medicaid truly reduced "
                     "elevated\nblood pressure by a given amount, at the study's realized precision.")
