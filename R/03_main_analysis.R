# 03_main_analysis.R
# What did Medicaid do?
#
# Two estimates for each outcome:
#   - Effect of winning the lottery (intent-to-treat): compare winners with non-winners.
#   - Effect of having Medicaid: winning raised enrollment by only ~24 points, so the lottery
#     effect understates what coverage itself does. Two-stage least squares uses winning as an
#     instrument for enrollment, estimating the effect among people who enrolled because they
#     won. This rests on two assumptions: winning affects health only through Medicaid, and no
#     one was made less likely to enroll by winning.
#
# Specification follows Baicker et al. (2013): household-size controls, survey weights,
# standard errors clustered by household; blood pressure also controls for sex and age decile.

library(tidyverse)
library(estimatr)
library(here)

ohie <- read_rds(here("data", "processed", "ohie_analysis.rds"))

outcomes <- c(
  hypertension          = "Elevated blood pressure",
  depression            = "Positive depression screen",
  catastrophic_spending = "Catastrophic medical spending"
)

controls_for <- function(outcome) {
  if (outcome == "hypertension") c("hh_size", "female", "age_decile") else "hh_size"
}

# First stage: how much did winning raise Medicaid enrollment? ----------------------------------

first_stage_fit <- lm_robust(medicaid ~ treatment + hh_size, data = ohie,
                             weights = weight, clusters = household_id, se_type = "stata")

enrollment <- ohie %>%
  group_by(treatment) %>%
  summarize(enrolled = weighted.mean(medicaid, weight))

# Effects on outcomes ---------------------------------------------------------------------------

estimate_effects <- function(outcome) {
  controls <- controls_for(outcome)
  d <- ohie %>% drop_na(all_of(c(outcome, controls)))

  itt_fit <- lm_robust(reformulate(c("treatment", controls), outcome), data = d,
                       weights = weight, clusters = household_id, se_type = "stata")
  iv_fit <- iv_robust(as.formula(paste(outcome, "~ medicaid +", paste(controls, collapse = " + "),
                                       "| treatment +", paste(controls, collapse = " + "))),
                      data = d, weights = weight, clusters = household_id, se_type = "stata")

  ctrl <- d %>% filter(treatment == 0)

  tibble(
    outcome      = outcome,
    label        = outcomes[[outcome]],
    n            = iv_fit$nobs,
    control_mean = weighted.mean(ctrl[[outcome]], ctrl$weight),
    itt          = coef(itt_fit)[["treatment"]],
    itt_low      = itt_fit$conf.low[["treatment"]],
    itt_high     = itt_fit$conf.high[["treatment"]],
    effect       = coef(iv_fit)[["medicaid"]],
    effect_se    = iv_fit$std.error[["medicaid"]],
    effect_low   = iv_fit$conf.low[["medicaid"]],
    effect_high  = iv_fit$conf.high[["medicaid"]],
    p_value      = iv_fit$p.value[["medicaid"]]
  )
}

results <- map_dfr(names(outcomes), estimate_effects)

# Output ----------------------------------------------------------------------------------------

write_csv(
  tibble(enrolled_control = enrollment$enrolled[enrollment$treatment == 0],
         enrolled_winners = enrollment$enrolled[enrollment$treatment == 1],
         first_stage      = coef(first_stage_fit)[["treatment"]],
         first_stage_se   = first_stage_fit$std.error[["treatment"]],
         f_stat           = (coef(first_stage_fit)[["treatment"]] /
                               first_stage_fit$std.error[["treatment"]])^2),
  here("output", "tables", "first_stage.csv")
)
write_csv(results, here("output", "tables", "main_effects.csv"))

plot_data <- results %>%
  mutate(across(c(control_mean, effect, effect_low, effect_high), ~ .x * 100),
         label = factor(label, levels = rev(outcomes)),
         significant = p_value < 0.05)

effects_plot <- ggplot(plot_data, aes(x = effect, y = label)) +
  geom_vline(xintercept = 0, color = "grey40") +
  geom_errorbarh(aes(xmin = effect_low, xmax = effect_high, color = significant),
                 height = 0.15, linewidth = 0.9) +
  geom_point(aes(color = significant), size = 3.2) +
  geom_text(aes(label = sprintf("%+.2f pts\n(from %.1f%%)", effect, control_mean)),
            nudge_y = 0.32, size = 3.3, lineheight = 0.9, color = "grey20") +
  scale_color_manual(values = c(`TRUE` = "#2A6F97", `FALSE` = "grey55"), guide = "none") +
  labs(
    title = "Medicaid reduced depression and financial catastrophe,\nbut not high blood pressure",
    subtitle = paste0("Effect of Medicaid coverage, percentage points, with 95% confidence intervals.\n",
                      "Labels show the effect and the rate among lottery non-winners."),
    x = "Change in percentage points", y = NULL
  ) +
  theme_minimal(base_size = 11) +
  theme(panel.grid.minor = element_blank(), panel.grid.major.y = element_blank(),
        plot.title.position = "plot")

ggsave(here("output", "figures", "main_effects.png"), effects_plot,
       width = 7, height = 4.5, dpi = 300, bg = "white")
