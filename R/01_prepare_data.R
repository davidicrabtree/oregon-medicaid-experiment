# 01_prepare_data.R
# Build the analysis file from the NBER public-use OHIE data.
#
# Sample and variable definitions follow the published replication code for
# Baicker et al. (2013, NEJM), reference/nejm_replication_code/Programs/prepare_data.do:
#   - in-person interview respondents (sample_resp_inp == 1)
#   - Medicaid = ever enrolled in OHP from lottery notification through the in-person interview
#   - transgender respondents recoded to birth gender
#   - hypertension = systolic >= 140 OR diastolic >= 90
#   - depression = PHQ-8 score >= 10

library(tidyverse)
library(haven)
library(here)

raw <- function(file) read_dta(here("data", "raw", file))

lottery <- raw("oregonhie_descriptive_vars.dta") %>%
  select(person_id, household_id, treatment, numhh_list)

medicaid <- raw("oregonhie_stateprograms_vars.dta") %>%
  select(person_id, medicaid = ohp_all_ever_inperson)

inperson <- raw("oregonhie_inperson_vars.dta") %>%
  filter(sample_resp_inp == 1) %>%
  select(person_id, weight = weight_total_inp,
         gender_inp, age_inp, race_white_inp, race_black_inp, race_nwother_inp,
         hispanic_inp, language_inp, interpreter_inp,
         bp_sar_inp, bp_dar_inp, phqtot_inp, catastrophic_exp_inp)

ohie <- inperson %>%
  left_join(lottery, by = "person_id") %>%
  left_join(medicaid, by = "person_id") %>%
  mutate(
    across(where(is.labelled), zap_labels),

    # Covariates (pre-lottery characteristics)
    female = case_when(gender_inp %in% c(1, 4) ~ 1,   # 4 = transgender, female at birth
                       gender_inp %in% c(0, 3) ~ 0),  # 3 = transgender, male at birth
    age_19_34 = as.numeric(age_inp < 35),
    age_35_49 = as.numeric(age_inp >= 35 & age_inp < 50),
    age_50_64 = as.numeric(age_inp >= 50),
    # Age deciles, matching Stata's xtile (extra controls for blood pressure outcomes)
    age_decile = cut(age_inp,
                     breaks = c(-Inf, quantile(age_inp, 1:9 / 10, type = 2, na.rm = TRUE), Inf),
                     labels = FALSE, right = TRUE) %>% factor(),
    english = case_when(interpreter_inp == 1 ~ 0,
                        language_inp == 1 ~ 0,
                        language_inp == 0 ~ 1),

    # Outcomes
    hypertension = case_when(bp_sar_inp >= 140 | bp_dar_inp >= 90 ~ 1,
                             bp_sar_inp < 140 & bp_dar_inp < 90 ~ 0),
    depression = case_when(phqtot_inp >= 10 ~ 1,
                           phqtot_inp < 10 ~ 0),
    catastrophic_spending = catastrophic_exp_inp,

    hh_size = factor(numhh_list)
  ) %>%
  select(person_id, household_id, treatment, medicaid, weight, hh_size,
         female, age = age_inp, age_19_34, age_35_49, age_50_64, age_decile,
         race_white = race_white_inp,
         race_black = race_black_inp, race_other = race_nwother_inp,
         hispanic = hispanic_inp, english,
         systolic_bp = bp_sar_inp, diastolic_bp = bp_dar_inp, phq8 = phqtot_inp,
         hypertension, depression, catastrophic_spending)

stopifnot(nrow(ohie) == 12229, !anyDuplicated(ohie$person_id))

write_rds(ohie, here("data", "processed", "ohie_analysis.rds"))
