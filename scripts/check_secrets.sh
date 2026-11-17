#!/usr/bin/env bash
# Secrets gate. Used by pre-push and CI. Scope (what it does and does NOT guarantee):
#   1) no .env file in ANY commit of the history (only .env.example allowed)
#   2) gitleaks finds no secrets in the full history (pattern-based: known key formats)
#   3) every author/committer email is a GitHub noreply address
# It cannot detect arbitrary personal data in file contents or commit messages; that
# still requires human review of every diff before publishing (see docs/SDLC.md).
set -euo pipefail

cd "$(dirname "$0")/.."
fail=0

# Run git separately from filtering: a git failure must abort, never look like "no matches".
all_paths=$(git log --all -m --name-only --format=) || { echo "ERROR: git log failed" >&2; exit 1; }
identities=$(git log --all --format='%ae%n%ce') || { echo "ERROR: git log failed" >&2; exit 1; }

echo "==> .env files in history (incl. merge commits)"
env_files=$(printf '%s\n' "$all_paths" | sort -u \
  | grep -E '(^|/)\.env($|\.)' | grep -vE '(^|/)\.env\.example$' || true)
if [[ -n "$env_files" ]]; then
  echo "ERROR: .env file(s) present in git history: $(echo "$env_files" | wc -l | tr -d ' ') path(s)." >&2
  echo "Fix: remove from history before publishing, and revoke any key it contained." >&2
  fail=1
fi

echo "==> gitleaks (full history)"
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "ERROR: gitleaks not installed (macOS: brew install gitleaks). Refusing to continue." >&2
  exit 1
fi
if ! gitleaks git --redact --no-banner .; then
  echo "ERROR: gitleaks found secrets. Revoke the key at the provider, then clean history." >&2
  fail=1
fi

echo "==> commit identities"
bad=$(printf '%s\n' "$identities" | sort -u \
  | grep -vE '^([0-9]+\+)?[A-Za-z0-9-]+(\[bot\])?@users\.noreply\.github\.com$|^noreply@github\.com$' || true)
if [[ -n "$bad" ]]; then
  # Do not print the addresses: CI logs of this repo are public.
  echo "ERROR: $(echo "$bad" | wc -l | tr -d ' ') non-noreply email(s) in commit metadata (not shown)." >&2
  echo "Inspect locally: git log --all --format='%h %ae %ce'" >&2
  echo "Fix: git config user.email '<id>+<login>@users.noreply.github.com' and rewrite." >&2
  fail=1
fi

if [[ $fail -ne 0 ]]; then
  exit 1
fi
echo "==> OK: no .env in history, no gitleaks findings, only noreply identities"
