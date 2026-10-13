# 04_power_and_precision.R
# Extension: was the blood pressure null a true null, or a study too small to tell?
#
# Part 1 - Power. Only ~24% of lottery winners enrolled because they won, so the study's
#   precision for the effect of coverage is far lower than its 12,000-person sample suggests.
#   For each outcome: the minimum detectable effect (MDE) at 80% power, what the confidence
#   interval rules out, and how large the study would have needed to be to detect smaller effects.
#
# Part 2 - Precision. Can adjusting for characteristics recorded before the lottery tighten the
#   estimates? This is the same idea as variance reduction in A/B testing (e.g., CUPED): it helps
#   only to the extent the covariates predict the outcome.

library(tidyverse)
library(estimatr)
library(here)

ohie <- read_rds(here("data", "processed", "ohie_analysis.rds"))
main <- read_csv(here("output", "r", "tables", "main_effects.csv"), show_col_types = FALSE)

alpha <- 0.05
target_power <- 0.80
z_alpha <- qnorm(1 - alpha / 2)
z_power <- qnorm(target_power)

# Part 1: Power ---------------------------------------------------------------------------------

# Probability a two-sided test rejects zero when the true effect is `effect`
power_at <- function(effect, se) {
  pnorm(abs(effect) / se - z_alpha) + pnorm(-abs(effect) / se - z_alpha)
}

power_summary <- main %>%
  transmute(
    outcome, label, control_mean, effect, effect_se,
    mde = (z_alpha + z_power) * effect_se,
    mde_relative = mde / control_mean,
    # Largest reduction the 95% CI rules out
    rules_out_beyond = effect_low,
    rules_out_relative = effect_low / control_mean
  )

# Sample size needed to detect a given reduction in elevated blood pressure, scaling the
# realized standard error (SE shrinks with the square root of sample size)
bp <- power_summary %>% filter(outcome == "hypertension")
n_bp <- main$n[main$outcome == "hypertension"]

sample_size_needed <- tibble(relative_reduction = c(0.10, 0.20, 0.30, 0.40, 0.50)) %>%
  mutate(effect_pts = relative_reduction * bp$control_mean,
         n_needed = n_bp * ((z_alpha + z_power) * bp$effect_se / effect_pts)^2,
         times_actual = n_needed / n_bp)

power_curve <- tibble(effect = seq(0, 0.12, by = 0.001)) %>%
  mutate(power = power_at(effect, bp$effect_se))

# Part 2: Precision from covariate adjustment ---------------------------------------------------

baseline <- c("female", "age_decile", "race_black", "race_other", "hispanic",
              "list_english", "list_self_signup", "list_first_day", "list_phone",
              "list_po_box", "list_urban")

controls_for <- function(outcome) {
  if (outcome == "hypertension") c("hh_size", "female", "age_decile") else "hh_size"
}

iv_fit <- function(data, outcome, controls) {
  rhs <- paste(controls, collapse = " + ")
  iv_robust(as.formula(paste(outcome, "~ medicaid +", rhs, "| treatment +", rhs)),
            data = data, weights = weight, clusters = household_id, se_type = "stata")
}

compare_precision <- function(outcome) {
  base_controls <- controls_for(outcome)
  adj_controls <- union(base_controls, baseline)
  # Same people in both models, so differences reflect adjustment, not sample changes
  d <- ohie %>% drop_na(all_of(c(outcome, adj_controls)))

  original <- iv_fit(d, outcome, base_controls)
  adjusted <- iv_fit(d, outcome, adj_controls)

  # How much of the outcome do the baseline characteristics explain (among non-winners)?
  r2 <- lm_robust(reformulate(adj_controls, outcome), data = filter(d, treatment == 0),
                  weights = weight)$r.squared

  tibble(
    outcome = outcome,
    n = original$nobs,
    effect_original = coef(original)[["medicaid"]],
    se_original     = original$std.error[["medicaid"]],
    effect_adjusted = coef(adjusted)[["medicaid"]],
    se_adjusted     = adjusted$std.error[["medicaid"]],
    se_reduction    = 1 - se_adjusted / se_original,
    # Adjustment is worth as much as this many additional participants (in percent)
    equivalent_sample_gain = (se_original / se_adjusted)^2 - 1,
    covariate_r2 = r2
  )
}

precision <- map_dfr(main$outcome, compare_precision) %>%
  left_join(select(main, outcome, label), by = "outcome")

# Output ----------------------------------------------------------------------------------------

write_csv(power_summary, here("output", "r", "tables", "power_summary.csv"))
write_csv(sample_size_needed, here("output", "r", "tables", "sample_size_needed.csv"))
write_csv(precision, here("output", "r", "tables", "covariate_adjustment.csv"))

curve_plot <- ggplot(power_curve, aes(x = effect * 100, y = power)) +
  annotate("rect", xmin = abs(bp$rules_out_beyond) * 100, xmax = Inf, ymin = -Inf, ymax = Inf,
           fill = "grey92") +
  annotate("text", x = abs(bp$rules_out_beyond) * 100 + 0.2, y = 0.08, hjust = 0,
           size = 3.3, color = "grey30",
           label = sprintf("Reductions larger than %.1f pts\nare ruled out by the 95%% CI",
                           abs(bp$rules_out_beyond) * 100)) +
  geom_hline(yintercept = target_power, linetype = "dashed", color = "grey50") +
  geom_line(color = "#2A6F97", linewidth = 1.1) +
  geom_point(data = tibble(effect = bp$mde, power = target_power),
             color = "#2A6F97", size = 3) +
  annotate("text", x = bp$mde * 100 + 0.3, y = target_power - 0.17, hjust = 0, size = 3.3,
           label = sprintf("80%% power only for reductions\nof %.1f pts or more (%.0f%% of the\n%.1f%% baseline rate)",
                           bp$mde * 100, bp$mde_relative * 100, bp$control_mean * 100)) +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
  scale_x_continuous(breaks = seq(0, 12, by = 2)) +
  labs(
    title = "The study could only detect large effects on blood pressure",
    subtitle = paste0("Chance of a statistically significant result if Medicaid truly reduced elevated\n",
                      "blood pressure by a given amount, at the study's realized precision."),
    x = "True reduction in elevated blood pressure (percentage points)",
    y = "Statistical power"
  ) +
  theme_minimal(base_size = 11) +
  theme(panel.grid.minor = element_blank(), plot.title.position = "plot")

ggsave(here("output", "r", "figures", "power_curve.png"), curve_plot,
       width = 7, height = 4.5, dpi = 300, bg = "white")
