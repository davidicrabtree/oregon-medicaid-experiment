"""Where the evidence and the paper's descriptions diverge.

Checks of specific claims in Baicker et al. (2013) against the replicated estimates:
  1. Blood pressure definition. Table 2's footnote defines elevated blood pressure as systolic
     >= 140 AND diastolic >= 90. The published control rate (16.3%) is reproduced only with OR,
     which is also what the authors' replication code uses.
  2. Headline magnitudes. The paper describes catastrophic spending as "nearly eliminated" (a
     reduction of "more than 80%") and depression as reduced by 30%. Those are point estimates;
     the confidence intervals, expressed relative to the control-group rate, are much wider.
  3. Power at the authors' own benchmark. The paper notes its confidence interval includes a
     clinically significant 7.16-point reduction in hypertension. How likely was the study to
     detect a reduction of that size?
"""

import numpy as np
import pandas as pd
from scipy.stats import norm

from common import TABLES, iv, load_analysis, weighted_mean

ohie = load_analysis()
main = pd.read_csv(TABLES / "main_effects.csv").set_index("outcome")

# 1. Blood pressure definition -------------------------------------------------------------------

sys_bp, dia_bp = ohie["systolic_bp"], ohie["diastolic_bp"]
measured = sys_bp.notna() & dia_bp.notna()
ohie["hypertension_and"] = ((sys_bp >= 140) & (dia_bp >= 90)).astype(float).where(measured)

bp_controls = ["hh_size", "female", "age_decile"]
definitions = []
for column, rule in [("hypertension", "Systolic >= 140 OR diastolic >= 90 (replication code)"),
                     ("hypertension_and", "Systolic >= 140 AND diastolic >= 90 (Table 2 footnote)")]:
    d = ohie.dropna(subset=[column, *bp_controls])
    fit = iv(d, column, bp_controls)
    ctrl = d[d["treatment"] == 0]
    ci = fit.conf_int().loc["medicaid"]
    definitions.append({
        "definition": rule,
        "control_rate": weighted_mean(ctrl[column], ctrl["weight"]),
        "effect": fit.params["medicaid"], "effect_low": ci.iloc[0], "effect_high": ci.iloc[1],
    })
pd.DataFrame(definitions).to_csv(TABLES / "check_bp_definition.csv", index=False)

# 2. Headline magnitudes as relative reductions --------------------------------------------------

claims = {
    "depression": "Relative reduction of 30%",
    "catastrophic_spending": "Nearly eliminated; relative reduction of more than 80%",
}
relative = pd.DataFrame([{
    "outcome": outcome,
    "paper_claim": claim,
    "control_rate": main.loc[outcome, "control_mean"],
    "relative_reduction": -main.loc[outcome, "effect"] / main.loc[outcome, "control_mean"],
    # A reduction cannot exceed 100% of the control rate
    "relative_low": -main.loc[outcome, "effect_high"] / main.loc[outcome, "control_mean"],
    "relative_high": min(1.0, -main.loc[outcome, "effect_low"] / main.loc[outcome, "control_mean"]),
} for outcome, claim in claims.items()])
relative.to_csv(TABLES / "check_relative_effects.csv", index=False)

# 3. Power at the authors' clinical benchmark ----------------------------------------------------

CLINICAL = 0.0716  # Baicker et al. (2013), p. 1719
se = main.loc["hypertension", "effect_se"]
z = CLINICAL / se
pd.DataFrame([{
    "benchmark_reduction": CLINICAL,
    "relative_to_control": CLINICAL / main.loc["hypertension", "control_mean"],
    "power": norm.cdf(z - norm.ppf(0.975)) + norm.cdf(-z - norm.ppf(0.975)),
}]).to_csv(TABLES / "check_clinical_power.csv", index=False)
