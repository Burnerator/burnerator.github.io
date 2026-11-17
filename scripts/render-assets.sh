#!/usr/bin/env bash
# Re-render the raster assets from their HTML sources in design/ with local headless Chrome.
# Only local files are loaded (file://); output is committed so the site has no build step.
set -euo pipefail
cd "$(dirname "$0")/.."
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
render() { # src out width height
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --default-background-color=00000000 \
    --window-size="$3,$4" --screenshot="$2" "file://$PWD/$1" 2>/dev/null
  echo "rendered $2"
}
render design/og-card.html assets/og.png 1200 630
render design/icon.html assets/apple-touch-icon.png 180 180
