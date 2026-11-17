#!/usr/bin/env bash
# Quality gate for the static site (stdlib only, no dependencies). Used by pre-push and CI.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "==> site tests"
python3 -m unittest discover -s tests -t . -v 2>&1 | tail -n +1
echo "==> OK: site checks passed"
