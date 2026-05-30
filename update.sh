#!/usr/bin/env bash
# Re-scrape, regenerate the HTML, commit any changes, and push.
# Usage: ./update.sh
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

.venv/bin/python scrape.py

git add data/ docs/
if git diff --staged --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "Update listings: $(date -u +%Y-%m-%d)"
git push
echo "Pushed. Pages will rebuild in ~1 minute → https://esamson6-claude.github.io/husky-finder/"
