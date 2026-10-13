# 02_balance.R
# Did the lottery produce comparable groups?
#
# Three checks:
#   1. Exam response: did winners and non-winners complete the in-person exam at similar rates?
#   2. Covariate balance: do winners and non-winners look alike on characteristics recorded
#      before the drawing (lottery sign-up data) and demographics reported at the exam?
#   3. Joint test: can these characteristics predict who won?
#
# The lottery drew households, so people who signed up with another household member had more
# chances to win. Every comparison is therefore shown with and without adjustment for household
# size on the lottery list, as in the original study. All estimates use the survey weights and
# cluster standard errors by household.

library(tidyverse)
library(estimatr)
library(here)

invited <- read_rds(here("data", "processed", "ohie_invited.rds"))
ohie <- read_rds(here("data", "processed", "ohie_analysis.rds"))

# 1. Exam response ------------------------------------------------------------------------------

response <- lm_robust(responded ~ treatment + hh_size, data = invited %>% filter(weight > 0),
                      weights = weight, clusters = household_id, se_type = "stata")

response_rates <- invited %>%
  filter(weight > 0) %>%
  group_by(treatment) %>%
  summarize(response_rate = weighted.mean(responded, weight), n_invited = n())

# 2. Covariate balance --------------------------------------------------------------------------

covariates <- c(
  list_female       = "Female",
  list_age          = "Age in 2008",
  list_english      = "Requested English-language materials",
  list_self_signup  = "Signed self up for the lottery",
  list_first_day    = "Signed up on the first day",
  list_phone        = "Gave a phone number",
  list_po_box       = "Gave a PO box address",
  list_urban        = "Lives in a metropolitan area",
  race_white        = "White",
  race_black        = "Black",
  race_other        = "Other non-white race",
  hispanic          = "Hispanic or Latino",
  english           = "Interviewed in English"
)

ohie <- ohie %>% mutate(multi_person_hh = as.numeric(hh_size != "1"))

weighted_sd <- function(x, w) {
  ok <- !is.na(x)
  sqrt(sum(w[ok] * (x[ok] - weighted.mean(x[ok], w[ok]))^2) / sum(w[ok]))
}

balance_row <- function(var) {
  d <- ohie %>% filter(!is.na(.data[[var]]))
  treat <- d %>% filter(treatment == 1)
  ctrl  <- d %>% filter(treatment == 0)

  pooled_sd <- sqrt((weighted_sd(treat[[var]], treat$weight)^2 +
                     weighted_sd(ctrl[[var]], ctrl$weight)^2) / 2)

  unadjusted <- lm_robust(reformulate("treatment", var), data = d,
                          weights = weight, clusters = household_id, se_type = "stata")
  adjusted <- lm_robust(reformulate(c("treatment", "hh_size"), var), data = d,
                        weights = weight, clusters = household_id, se_type = "stata")

  tibble(
    variable     = var,
    mean_control = weighted.mean(ctrl[[var]], ctrl$weight),
    mean_winners = weighted.mean(treat[[var]], treat$weight),
    std_diff_unadjusted = coef(unadjusted)[["treatment"]] / pooled_sd,
    std_diff_adjusted   = coef(adjusted)[["treatment"]] / pooled_sd,
    p_adjusted   = adjusted$p.value[["treatment"]]
  )
}

balance <- map_dfr(names(covariates), balance_row) %>%
  mutate(label = covariates[variable])

# Household size itself: the one characteristic the lottery design made unequal by construction
hh_row <- balance_row("multi_person_hh") %>%
  mutate(std_diff_adjusted = NA, p_adjusted = NA,
         label = "Signed up with another household member")

balance_table <- bind_rows(hh_row, balance)

# 3. Joint test ---------------------------------------------------------------------------------
# Regress winning on all characteristics (plus household size) and test whether the
# characteristics jointly predict it. A large p-value is what a fair lottery should produce.

joint_test <- function(model, terms) {
  b <- coef(model)[terms]
  V <- vcov(model)[terms, terms]
  stat <- as.numeric(t(b) %*% solve(V) %*% b)
  tibble(chi_sq = stat, df = length(terms),
         p_value = pchisq(stat, df = length(terms), lower.tail = FALSE))
}

joint_model <- lm_robust(reformulate(c(names(covariates), "hh_size"), "treatment"),
                         data = ohie, weights = weight, clusters = household_id, se_type = "stata")
joint <- joint_test(joint_model, names(covariates)) %>%
  mutate(n = joint_model$nobs)

# Output ----------------------------------------------------------------------------------------

write_csv(balance_table, here("output", "tables", "balance.csv"))
write_csv(
  tibble(
    rate_control  = response_rates$response_rate[response_rates$treatment == 0],
    rate_winners  = response_rates$response_rate[response_rates$treatment == 1],
    diff_adjusted = coef(response)[["treatment"]],
    p_value       = response$p.value[["treatment"]]
  ),
  here("output", "tables", "response_rates.csv")
)
write_csv(joint, here("output", "tables", "balance_joint_test.csv"))

plot_data <- balance_table %>%
  select(label, unadjusted = std_diff_unadjusted, adjusted = std_diff_adjusted) %>%
  pivot_longer(-label, names_to = "comparison", values_to = "std_diff") %>%
  filter(!is.na(std_diff)) %>%
  mutate(label = factor(label, levels = rev(balance_table$label)),
         comparison = factor(comparison, levels = c("unadjusted", "adjusted"),
                             labels = c("Raw comparison",
                                        "Adjusted for household size")))

balance_plot <- ggplot(plot_data, aes(x = std_diff, y = label, color = comparison)) +
  annotate("rect", xmin = -0.1, xmax = 0.1, ymin = -Inf, ymax = Inf,
           fill = "grey92") +
  geom_vline(xintercept = 0, color = "grey40") +
  geom_point(size = 2.6) +
  scale_color_manual(values = c("Raw comparison" = "#C8553D",
                                "Adjusted for household size" = "#2A6F97")) +
  scale_x_continuous(limits = c(-0.25, 0.25)) +
  labs(
    title = "After accounting for household size,\nlottery winners and non-winners look alike",
    subtitle = paste0("Standardized difference, winners minus non-winners. Households with more members on\n",
                      "the lottery list had more chances to win; values inside the shaded band (-0.1 to 0.1)\n",
                      "are conventionally considered negligible."),
    x = "Standardized difference", y = NULL, color = NULL
  ) +
  theme_minimal(base_size = 11) +
  theme(legend.position = "top", legend.justification = "left",
        panel.grid.minor = element_blank(), panel.grid.major.y = element_blank(),
        plot.title.position = "plot")

ggsave(here("output", "figures", "balance.png"), balance_plot,
       width = 7, height = 5.5, dpi = 300, bg = "white")
