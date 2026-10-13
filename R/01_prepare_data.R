# 01_prepare_data.R
# Build the analysis files from the NBER public-use OHIE data.
#
# Sample and variable definitions follow the published replication code for
# Baicker et al. (2013, NEJM), reference/nejm_replication_code/Programs/prepare_data.do:
#   - Medicaid = ever enrolled in OHP from lottery notification through the in-person interview
#   - transgender respondents recoded to birth gender
#   - hypertension = systolic >= 140 OR diastolic >= 90
#   - depression = PHQ-8 score >= 10
#
# Outputs (data/processed/):
#   ohie_invited.rds  - all 20,745 people invited to the in-person exam (for response-rate checks)
#   ohie_analysis.rds - the 12,229 who completed it (the analysis sample)

library(tidyverse)
library(haven)
library(here)

raw <- function(file) read_dta(here("data", "raw", file)) %>% zap_labels()

# Recorded at lottery sign-up, before the drawing
lottery <- raw("oregonhie_descriptive_vars.dta") %>%
  transmute(person_id, household_id, treatment,
            hh_size = factor(numhh_list),
            list_female = female_list,
            list_age = 2008 - birthyear_list,
            list_english = english_list,
            list_self_signup = self_list,
            list_first_day = first_day_list,
            list_phone = have_phone_list,
            list_po_box = pobox_list,
            list_urban = zip_msa_list)

medicaid <- raw("oregonhie_stateprograms_vars.dta") %>%
  select(person_id, medicaid = ohp_all_ever_inperson)

invited <- raw("oregonhie_inperson_vars.dta") %>%
  select(person_id, responded = sample_resp_inp, weight = weight_total_inp,
         gender_inp, age_inp, race_white_inp, race_black_inp, race_nwother_inp,
         hispanic_inp, language_inp, interpreter_inp,
         bp_sar_inp, bp_dar_inp, phqtot_inp, catastrophic_exp_inp) %>%
  left_join(lottery, by = "person_id") %>%
  left_join(medicaid, by = "person_id")

stopifnot(nrow(invited) == 20745, !anyDuplicated(invited$person_id))

write_rds(invited %>% select(person_id, household_id, treatment, hh_size, responded, weight),
          here("data", "processed", "ohie_invited.rds"))

ohie <- invited %>%
  filter(responded == 1) %>%
  mutate(
    # Characteristics reported at the exam
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
    catastrophic_spending = catastrophic_exp_inp
  ) %>%
  select(person_id, household_id, treatment, medicaid, weight, hh_size,
         starts_with("list_"),
         female, age = age_inp, age_19_34, age_35_49, age_50_64, age_decile,
         race_white = race_white_inp, race_black = race_black_inp,
         race_other = race_nwother_inp, hispanic = hispanic_inp, english,
         systolic_bp = bp_sar_inp, diastolic_bp = bp_dar_inp, phq8 = phqtot_inp,
         hypertension, depression, catastrophic_spending)

stopifnot(nrow(ohie) == 12229)

write_rds(ohie, here("data", "processed", "ohie_analysis.rds"))
