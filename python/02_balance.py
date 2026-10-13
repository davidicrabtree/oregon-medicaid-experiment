"""Did the lottery produce comparable groups?

Three checks:
  1. Exam response: did winners and non-winners complete the in-person exam at similar rates?
  2. Covariate balance: do winners and non-winners look alike on characteristics recorded before
     the drawing (lottery sign-up data) and demographics reported at the exam?
  3. Joint test: can these characteristics predict who won?

The lottery drew households, so people who signed up with another household member had more
chances to win. Every comparison is therefore shown with and without adjustment for household
size on the lottery list, as in the original study.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from common import (FIGURES, TABLES, load_analysis, load_invited, ols, save_figure,
                    set_plot_style, weighted_mean)

set_plot_style()

ohie = load_analysis()
invited = load_invited()

# 1. Exam response -------------------------------------------------------------------------------

sampled = invited[invited["weight"] > 0]
response = ols(sampled, "responded", ["treatment", "hh_size"])
rates = sampled.groupby("treatment").apply(lambda g: weighted_mean(g["responded"], g["weight"]))

pd.DataFrame([{
    "rate_control": rates[0],
    "rate_winners": rates[1],
    "diff_adjusted": response.params["treatment"],
    "p_value": response.pvalues["treatment"],
}]).to_csv(TABLES / "response_rates.csv", index=False)

# 2. Covariate balance ---------------------------------------------------------------------------

COVARIATES = {
    "list_female": "Female",
    "list_age": "Age in 2008",
    "list_english": "Requested English-language materials",
    "list_self_signup": "Signed self up for the lottery",
    "list_first_day": "Signed up on the first day",
    "list_phone": "Gave a phone number",
    "list_po_box": "Gave a PO box address",
    "list_urban": "Lives in a metropolitan area",
    "race_white": "White",
    "race_black": "Black",
    "race_other": "Other non-white race",
    "hispanic": "Hispanic or Latino",
    "english": "Interviewed in English",
}

ohie["multi_person_hh"] = (ohie["hh_size"] != "1").astype(float)


def weighted_sd(x: pd.Series, w: pd.Series) -> float:
    keep = x.notna()
    x, w = x[keep], w[keep]
    return float(np.sqrt(np.average((x - np.average(x, weights=w)) ** 2, weights=w)))


def balance_row(var: str) -> dict:
    d = ohie.dropna(subset=[var])
    treat, ctrl = d[d["treatment"] == 1], d[d["treatment"] == 0]
    pooled_sd = np.sqrt((weighted_sd(treat[var], treat["weight"]) ** 2 +
                         weighted_sd(ctrl[var], ctrl["weight"]) ** 2) / 2)
    unadjusted = ols(d, var, ["treatment"])
    adjusted = ols(d, var, ["treatment", "hh_size"])
    return {
        "variable": var,
        "mean_control": weighted_mean(ctrl[var], ctrl["weight"]),
        "mean_winners": weighted_mean(treat[var], treat["weight"]),
        "std_diff_unadjusted": unadjusted.params["treatment"] / pooled_sd,
        "std_diff_adjusted": adjusted.params["treatment"] / pooled_sd,
        "p_adjusted": adjusted.pvalues["treatment"],
    }


# Household size itself: the one characteristic the lottery design made unequal by construction
hh_row = balance_row("multi_person_hh") | {
    "std_diff_adjusted": np.nan, "p_adjusted": np.nan,
    "label": "Signed up with another household member"}
balance = pd.DataFrame([hh_row] + [balance_row(v) | {"label": label}
                                   for v, label in COVARIATES.items()])
balance.to_csv(TABLES / "balance.csv", index=False)

# 3. Joint test ----------------------------------------------------------------------------------
# Regress winning on all characteristics (plus household size) and test whether the
# characteristics jointly predict it. A large p-value is what a fair lottery should produce.

joint_model = ols(ohie, "treatment", [*COVARIATES, "hh_size"])
b = joint_model.params[list(COVARIATES)].to_numpy()
V = joint_model.cov_params().loc[list(COVARIATES), list(COVARIATES)].to_numpy()
chi_sq = float(b @ np.linalg.solve(V, b))
pd.DataFrame([{"chi_sq": chi_sq, "df": len(COVARIATES),
               "p_value": stats.chi2.sf(chi_sq, len(COVARIATES)),
               "n": int(joint_model.nobs)}]).to_csv(TABLES / "balance_joint_test.csv", index=False)

# Figure -----------------------------------------------------------------------------------------

RAW_COLOR, ADJ_COLOR = "#C8553D", "#2A6F97"
y = np.arange(len(balance))[::-1]

fig, ax = plt.subplots(figsize=(7, 5.5))
ax.axvline(0, color="0.4", linewidth=1)
ax.scatter(balance["std_diff_unadjusted"], y, color=RAW_COLOR, s=40, zorder=3,
           label="Raw comparison")
ax.scatter(balance["std_diff_adjusted"], y, color=ADJ_COLOR, s=40, zorder=3,
           label="Adjusted for household size")
ax.set_yticks(y, balance["label"])
ax.set_xlim(-0.25, 0.25)
ax.set_xlabel("Standardized difference")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False,
          handletextpad=0.3, borderaxespad=0)
save_figure(fig, FIGURES / "balance.png",
            title="After accounting for household size,\nlottery winners and non-winners look alike",
            subtitle="Standardized difference, winners minus non-winners. Households with more "
                     "members\non the lottery list had more chances to win.",
            legend_space=0.22)
