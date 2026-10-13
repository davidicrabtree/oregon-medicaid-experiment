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

Percentage points, with 95% confidence intervals. Published values are from the paper's text and Tables 2 and 4.

| Estimate | This analysis | Baicker et al. (2013) |
|---|---|---|
| Lottery's effect on Medicaid enrollment | 24.1 (22.4, 25.9) | 24.1 (22.3, 25.9) |
| Lottery's effect on exam response | 0.28 (p = 0.86) | 0.28 (p = 0.86) |
| Effect of Medicaid on elevated blood pressure | −1.35 (−7.17, 4.48) | −1.33 (−7.16, 4.49) |
| Effect of Medicaid on positive depression screen | −9.15 (−16.70, −1.60) | −9.15 (−16.70, −1.60) |
| Effect of Medicaid on catastrophic medical spending | −4.48 (−8.26, −0.69) | −4.48 (−8.26, −0.69) |

Control-group rates (16.3% elevated blood pressure, 30.0% depression, 5.5% catastrophic spending) also match. The blood pressure estimate differs from the published value by 0.02 points; the source of the gap is not identified.
