#!/usr/bin/env bash
# Quality gate for the static site. Used by pre-push and CI.
# Uses .venv (markdown-it-py, hash-pinned in requirements-build.txt) when present.
set -euo pipefail
cd "$(dirname "$0")/.."
# SITE_PY lets the pre-push hook (clean temp worktree, no .venv) reuse the repo's venv
py="${SITE_PY:-python3}"
[[ -z "${SITE_PY:-}" && -x .venv/bin/python ]] && py=.venv/bin/python
"$py" -c "import markdown_it" 2>/dev/null || {
  echo "build deps missing: python3 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements-build.txt" >&2
  exit 1
}
echo "==> blog build is up to date"
"$py" scripts/build.py --check
echo "==> site tests"
"$py" -m unittest discover -s tests -t . -v 2>&1 | tail -n +1
echo "==> OK: site checks passed"
