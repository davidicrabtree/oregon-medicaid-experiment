"""Confirm the Python analysis reproduces the R reference implementation.

Compares every numeric column of each table in output/tables/ with its counterpart in
output/r/tables/. Point estimates should agree to floating-point precision; p-values and
confidence limits can differ slightly because R's estimatr uses t-distribution critical values
where statsmodels uses the normal distribution.
"""

import sys

import pandas as pd

from common import ROOT, TABLES

R_TABLES = ROOT / "output" / "r" / "tables"
TOLERANCE = 1e-4

failures = []
for r_path in sorted(R_TABLES.glob("*.csv")):
    py = pd.read_csv(TABLES / r_path.name)
    r = pd.read_csv(r_path)
    shared = [c for c in py.select_dtypes("number").columns if c in r.columns]
    max_diff = (py[shared] - r[shared]).abs().max().max()
    status = "ok" if max_diff < TOLERANCE else "MISMATCH"
    print(f"{status:9} {r_path.name:28} max difference {max_diff:.1e}")
    if status != "ok":
        failures.append(r_path.name)

sys.exit(1 if failures else 0)
