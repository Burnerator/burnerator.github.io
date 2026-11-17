#!/usr/bin/env bash
# Local preview of the site INCLUDING unpublished drafts. Never touches the repo.
#   scripts/preview.sh [DRAFTS_DIR] [PORT]     (default ~/wks/burnerator-drafts, 8770)
# Copies only the publishable site files (allowlist) plus the drafts into a throwaway
# directory, builds there and serves it on 127.0.0.1. Fails loudly on any copy problem.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
drafts="${1:-$HOME/wks/burnerator-drafts}"
port="${2:-8770}"
py="$repo/.venv/bin/python"

[[ -x "$py" ]] || { echo "preview: missing $py (see README: build deps)" >&2; exit 1; }
[[ -d "$drafts" ]] || { echo "preview: drafts directory not found: $drafts" >&2; exit 1; }
shopt -s nullglob
posts=("$drafts"/*/)
(( ${#posts[@]} )) || echo "preview: note: no drafts in $drafts (previewing the published site)"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/burnerator-preview.XXXXXX")"
# allowlist of site inputs, and within it ONLY git-tracked files (ignored files never copied)
allow=(index.html 404.html CNAME robots.txt .nojekyll assets .well-known design scripts)
while IFS= read -r -d '' f; do
  mkdir -p "$tmp/$(dirname "$f")"
  cp "$repo/$f" "$tmp/$f"
done < <(git -C "$repo" ls-files -z -- "${allow[@]}")
mkdir -p "$tmp/content/posts"
for p in "${posts[@]}"; do cp -R "${p%/}" "$tmp/content/posts/"; done  # no trailing slash: copy the folder itself

"$py" "$tmp/scripts/build.py"
rm -rf "$tmp/scripts" "$tmp/content"   # serve only publishable output
echo "preview: http://127.0.0.1:$port/blog/   (Ctrl+C to stop; files in $tmp)"
cd "$tmp" && exec "$py" -m http.server "$port" --bind 127.0.0.1
