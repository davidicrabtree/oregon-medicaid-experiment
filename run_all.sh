#!/usr/bin/env bash
# Run the full Python analysis, check it against the R reference results, and render the report.
# Usage: ./run_all.sh          (Python pipeline + report)
#        ./run_all.sh --with-r (also rerun the R reference implementation first)
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "--with-r" ]]; then
  for script in R/0*.R; do Rscript "$script"; done
fi

PY=.venv/bin/python
for script in python/0*.py; do
  echo "Running $script"
  "$PY" "$script"
done

"$PY" python/verify_against_r.py

export PATH="$PWD/.venv/bin:$PATH" QUARTO_PYTHON="$PWD/$PY"
quarto render report.qmd
