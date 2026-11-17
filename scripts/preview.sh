#!/usr/bin/env bash
# Local preview of the site INCLUDING unpublished drafts. Never touches the repo.
#   scripts/preview.sh [DRAFTS_DIR] [PORT]     (default ~/wks/burnerator-drafts, 8770)
# Builds into a throwaway copy and serves it on 127.0.0.1 only.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
drafts="${1:-$HOME/wks/burnerator-drafts}"
port="${2:-8770}"
py="$repo/.venv/bin/python"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/burnerator-preview.XXXXXX")"
rsync -a --exclude .git --exclude .venv "$repo/" "$tmp/"
mkdir -p "$tmp/content/posts"
cp -R "$drafts"/*/ "$tmp/content/posts/" 2>/dev/null || true
"$py" "$tmp/scripts/build.py"
echo "preview: http://127.0.0.1:$port/blog/   (Ctrl+C to stop; files in $tmp)"
cd "$tmp" && exec "$py" -m http.server "$port" --bind 127.0.0.1
