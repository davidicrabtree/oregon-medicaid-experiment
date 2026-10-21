#!/usr/bin/env bash
# Run the full Python analysis, check it against the R reference results, and render the report.
# Usage: ./run_all.sh          (Python pipeline + report)
#        ./run_all.sh --with-r (also rerun the R reference implementation first)
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "--with-r" ]]; then
  for script in R/0*.R; do Rscript "$script"; done
fi

# The virtual environment keeps its programs in bin/ on Mac and Linux, Scripts/ on Windows.
if [[ -d .venv/bin ]]; then VENV_BIN=.venv/bin; PY=$VENV_BIN/python
else VENV_BIN=.venv/Scripts; PY=$VENV_BIN/python.exe; fi

for script in python/0*.py; do
  echo "Running $script"
  "$PY" "$script"
done

"$PY" python/verify_against_r.py

export PATH="$PWD/$VENV_BIN:$PATH" QUARTO_PYTHON="$PWD/$PY"
quarto render report.qmd
