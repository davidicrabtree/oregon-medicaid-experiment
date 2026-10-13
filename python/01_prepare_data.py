"""Build the analysis files from the NBER public-use OHIE data.

Sample and variable definitions follow the published replication code for Baicker et al.
(2013, NEJM), reference/nejm_replication_code/Programs/prepare_data.do:
  - Medicaid = ever enrolled in OHP from lottery notification through the in-person interview
  - transgender respondents recoded to birth gender
  - hypertension = systolic >= 140 OR diastolic >= 90
  - depression = PHQ-8 score >= 10

Outputs (data/processed/):
  ohie_invited.parquet  - all 20,745 people invited to the in-person exam (response-rate checks)
  ohie_analysis.parquet - the 12,229 who completed it (the analysis sample)
"""

import numpy as np
import pandas as pd

from common import PROCESSED, RAW


def read(file: str, columns: list[str]) -> pd.DataFrame:
    return pd.read_stata(RAW / file, columns=columns, convert_categoricals=False)


# Recorded at lottery sign-up, before the drawing
lottery = read("oregonhie_descriptive_vars.dta",
               ["person_id", "household_id", "treatment", "numhh_list", "female_list",
                "birthyear_list", "english_list", "self_list", "first_day_list",
                "have_phone_list", "pobox_list", "zip_msa_list"])
lottery = pd.DataFrame({
    "person_id": lottery["person_id"],
    "household_id": lottery["household_id"],
    "treatment": lottery["treatment"],
    "hh_size": lottery["numhh_list"].astype(int).astype(str),
    "list_female": lottery["female_list"],
    "list_age": 2008 - lottery["birthyear_list"],
    "list_english": lottery["english_list"],
    "list_self_signup": lottery["self_list"],
    "list_first_day": lottery["first_day_list"],
    "list_phone": lottery["have_phone_list"],
    "list_po_box": lottery["pobox_list"],
    "list_urban": lottery["zip_msa_list"],
})

medicaid = (read("oregonhie_stateprograms_vars.dta", ["person_id", "ohp_all_ever_inperson"])
            .rename(columns={"ohp_all_ever_inperson": "medicaid"}))

invited = (
    read("oregonhie_inperson_vars.dta",
         ["person_id", "sample_resp_inp", "weight_total_inp", "gender_inp", "age_inp",
          "race_white_inp", "race_black_inp", "race_nwother_inp", "hispanic_inp",
          "language_inp", "interpreter_inp", "bp_sar_inp", "bp_dar_inp", "phqtot_inp",
          "catastrophic_exp_inp"])
    .rename(columns={"sample_resp_inp": "responded", "weight_total_inp": "weight"})
    .merge(lottery, on="person_id", how="left", validate="1:1")
    .merge(medicaid, on="person_id", how="left", validate="1:1")
)

assert len(invited) == 20745 and invited["person_id"].is_unique

invited[["person_id", "household_id", "treatment", "hh_size", "responded", "weight"]].to_parquet(
    PROCESSED / "ohie_invited.parquet", index=False)

ohie = invited[invited["responded"] == 1].copy()


def indicator(condition: pd.Series, known: pd.Series) -> pd.Series:
    """1/0 where `known` is True, missing otherwise."""
    return condition.astype(float).where(known)


age = ohie["age_inp"]
sys_bp, dia_bp, phq = ohie["bp_sar_inp"], ohie["bp_dar_inp"], ohie["phqtot_inp"]

# Age deciles, matching Stata's xtile (extra controls for blood pressure outcomes).
# R's quantile type 2 and Stata's default percentile both use the averaged inverse CDF.
cutpoints = np.quantile(age.dropna(), np.arange(1, 10) / 10, method="averaged_inverted_cdf")
ohie["age_decile"] = pd.cut(age, bins=[-np.inf, *cutpoints, np.inf], labels=False,
                            right=True).astype("Int64").astype(str).replace("<NA>", pd.NA)

ohie = ohie.assign(
    # Characteristics reported at the exam
    female=ohie["gender_inp"].map({1: 1.0, 4: 1.0, 0: 0.0, 3: 0.0}),  # 3/4 = transgender, by birth sex
    age=age,
    age_19_34=indicator(age < 35, age.notna()),
    age_35_49=indicator((age >= 35) & (age < 50), age.notna()),
    age_50_64=indicator(age >= 50, age.notna()),
    english=np.select(
        [ohie["interpreter_inp"] == 1, ohie["language_inp"] == 1, ohie["language_inp"] == 0],
        [0.0, 0.0, 1.0], default=np.nan),
    # Outcomes
    hypertension=np.select(
        [(sys_bp >= 140) | (dia_bp >= 90), (sys_bp < 140) & (dia_bp < 90)],
        [1.0, 0.0], default=np.nan),
    depression=indicator(phq >= 10, phq.notna()),
    catastrophic_spending=ohie["catastrophic_exp_inp"],
).rename(columns={
    "race_white_inp": "race_white", "race_black_inp": "race_black",
    "race_nwother_inp": "race_other", "hispanic_inp": "hispanic",
    "bp_sar_inp": "systolic_bp", "bp_dar_inp": "diastolic_bp", "phqtot_inp": "phq8",
})

columns = ["person_id", "household_id", "treatment", "medicaid", "weight", "hh_size",
           *[c for c in ohie.columns if c.startswith("list_")],
           "female", "age", "age_19_34", "age_35_49", "age_50_64", "age_decile",
           "race_white", "race_black", "race_other", "hispanic", "english",
           "systolic_bp", "diastolic_bp", "phq8",
           "hypertension", "depression", "catastrophic_spending"]
ohie = ohie[columns]

assert len(ohie) == 12229

ohie.to_parquet(PROCESSED / "ohie_analysis.parquet", index=False)
