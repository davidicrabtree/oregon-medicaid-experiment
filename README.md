# What Did Medicaid Do? Re-examining the Oregon Health Insurance Experiment

In 2008, Oregon expanded Medicaid by lottery, creating one of the few randomized tests of the effect of health insurance. This project rebuilds the experiment's best-known clinical analysis (Baicker et al. 2013, *New England Journal of Medicine*) from the public-use data, reproduces its headline estimates, and examines how well the evidence supports the way those results are described.

**Read the write-up:** [report.html](report.html) · [report.pdf](report.pdf)

## Findings

**Some of the paper's summary claims go further than its evidence.** The physical-health null comes from a study too small to detect moderate effects, while the positive findings for depression and financial strain are described by their point estimates rather than their much wider confidence intervals, a more lenient standard than the paper applies to its null results.

1. The blood pressure "null" cannot distinguish no effect from a meaningful one. The study had a 67% chance of detecting a reduction the authors themselves call clinically significant, and 80% power only for reductions of at least 8.3 points, about half the baseline rate. Its 95% confidence interval runs from a 44% reduction to a 27% increase.
2. The positive findings are stated more precisely than the data allow. "Nearly eliminated" catastrophic medical spending describes a point estimate whose 95% confidence interval is consistent with a reduction as small as 13%. The "30% reduction" in depression has an interval running from 5% to 56%.
3. The paper's definition of elevated blood pressure is misstated. Table 2's footnote requires systolic pressure of at least 140 *and* diastolic of at least 90 mm Hg; the published results use *or*. Under the stated definition, 7.0% of the control group would have elevated blood pressure, not the reported 16.3%.
4. Covariate adjustment cannot recover the lost precision. Pre-lottery characteristics explain 1–8% of outcome variation and shrink standard errors by about 1%.

## Replication

Percentage points, with 95% confidence intervals. Published values are from the paper's text and Tables 2 and 4.

| Estimate | This analysis | Baicker et al. (2013) |
|---|---|---|
| Lottery's effect on Medicaid enrollment | 24.1 (22.4, 25.9) | 24.1 (22.3, 25.9) |
| Lottery's effect on exam response | 0.28 (p = 0.86) | 0.28 (p = 0.86) |
| Effect of Medicaid on elevated blood pressure | −1.35 (−7.17, 4.48) | −1.33 (−7.16, 4.49) |
| Effect of Medicaid on positive depression screen | −9.15 (−16.70, −1.60) | −9.15 (−16.70, −1.60) |
| Effect of Medicaid on catastrophic medical spending | −4.48 (−8.26, −0.69) | −4.48 (−8.26, −0.69) |

The blood pressure estimate differs from the published value by 0.02 points; the source of the gap is not identified.

## Project structure

```
python/                 Main analysis (pandas, statsmodels, linearmodels)
  01_prepare_data.py      Build analysis files from the raw NBER data
  02_balance.py           Exam response, covariate balance, joint test
  03_main_analysis.py     Lottery effects and two-stage least squares effects of Medicaid
  04_power_and_precision.py  Minimum detectable effects, required sample sizes, covariate adjustment
  05_paper_checks.py      Checks of specific claims in the original paper
  verify_against_r.py     Confirms Python and R results agree
R/                      Reference implementation in R (estimatr), same analysis
output/                 Tables and figures from Python; output/r/ holds the R results
report.qmd              Write-up (Quarto)
```

## Reproducing the analysis

The data are the Oregon Health Insurance Experiment public-use files, distributed by NBER under a data-use agreement and not included in this repository.

1. Create a free NBER account and download the public-use files from <https://www.nber.org/research/data/oregon-health-insurance-experiment-data>.
2. Copy these three files into `data/raw/`: `oregonhie_descriptive_vars.dta`, `oregonhie_inperson_vars.dta`, `oregonhie_stateprograms_vars.dta`.
3. Create the Python environment and run everything:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run_all.sh
```

`./run_all.sh --with-r` also reruns the R reference implementation (requires R with tidyverse, haven, here, and estimatr).

## References

Baicker, K., Taubman, S. L., Allen, H. L., et al. (2013). The Oregon Experiment — Effects of Medicaid on Clinical Outcomes. *New England Journal of Medicine*, 368(18), 1713–1722.

Oregon Health Insurance Experiment, public-use data. National Bureau of Economic Research. <https://www.nber.org/research/data/oregon-health-insurance-experiment-data>
