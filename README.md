# Did Medicaid Improve Health? Evidence from Oregon's Lottery

*Work in progress.*

In 2008, Oregon had funding to expand Medicaid to only a fraction of the low-income adults who wanted it, so it held a lottery. Because winners were chosen at random, comparing winners with non-winners gives an unusually clean estimate of what health insurance does. This project re-analyzes the experiment's public data, estimates the effect of actually having Medicaid (not just winning the lottery), and asks whether the study's well-known null result on blood pressure reflects a true absence of an effect or a study too small to detect one.

This analysis builds on Baicker et al. (2013), "The Oregon Experiment — Effects of Medicaid on Clinical Outcomes," *New England Journal of Medicine* 368: 1713–1722. The core estimates reproduce that paper; the power analysis and covariate-adjustment extension are my own.

## Data

The data are the Oregon Health Insurance Experiment public-use files, distributed by NBER under a data-use agreement and not included in this repository. To reproduce:

1. Create a free NBER account and download the public-use files from https://www.nber.org/research/data/oregon-health-insurance-experiment-data
2. Copy these three files into `data/raw/`:
   - `oregonhie_descriptive_vars.dta`
   - `oregonhie_inperson_vars.dta`
   - `oregonhie_stateprograms_vars.dta`
3. Run the scripts in `R/` in order.

Data citation: Oregon Health Insurance Experiment, public-use data. National Bureau of Economic Research. https://www.nber.org/research/data/oregon-health-insurance-experiment-data

## Replication check

Effect of Medicaid coverage (two-stage least squares, lottery as instrument), percentage points:

| Outcome | This analysis | Baicker et al. (2013) |
|---|---|---|
| Lottery's effect on Medicaid enrollment | 24.1 | *to confirm (Table 2)* |
| Elevated blood pressure | −1.35 (−7.17, 4.48) | not significant; *exact estimate to confirm* |
| Positive depression screen | −9.15 (−16.70, −1.60) | −9.15 (−16.70, −1.60) |
| Catastrophic medical spending | −4.48 (−8.26, −0.69) | −4.5; *CI to confirm* |

Control-group rates for depression (30.0%) and catastrophic spending (5.5%) match the published values.
