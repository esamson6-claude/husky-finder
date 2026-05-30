"""Run all source scrapers, dedupe, write CSV, and emit a diff of new listings."""
from __future__ import annotations

import csv
import importlib
import re
import sys
import traceback
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "listings.csv"
NEW_PATH = DATA_DIR / "new_listings.md"

# Per-listing post-filters. Returns True to keep.
def _keep_husky_180_or_c(l: dict) -> bool:
    """Keep only Aviat Husky A-1B (180) and A-1C variants (180 and 200)."""
    blob = " ".join(
        [(l.get(k) or "").upper() for k in ("model", "description", "title")]
    )
    return bool(re.search(r"\bA-1B\b|\bA-1C\b", blob))


def _keep_maule_m5(l: dict) -> bool:
    """Keep only Maule M-5 variants (any M-5-XXX)."""
    blob = " ".join(
        [(l.get(k) or "").upper() for k in ("model", "description", "title")]
    )
    return bool(re.search(r"\bM[-\s]?5\b", blob))


# Each search is one (source, make, url) combination.
SEARCHES: list[dict] = [
    # ---- Aviat Husky ----
    {
        "make": "Aviat Husky",
        "module": "scrapers.aviat",
        "slug": "aviat-husky",
        "url": None,  # ignored; aviat.py hardcodes its own URL
        "default_model": "Husky",
        "post_filter": _keep_husky_180_or_c,
    },
    {
        "make": "Aviat Husky",
        "module": "scrapers.aircraftforsale",
        "slug": "aviat-husky",
        "url": "https://aircraftforsale.com/aircraft/search?manufacturer=Aviat&model=A-1",
        "href_substring": "husky",
        "default_model": "Husky",
        "post_filter": _keep_husky_180_or_c,
    },
    {
        "make": "Aviat Husky",
        "module": "scrapers.barnstormers",
        "slug": "aviat-husky",
        "url": "https://www.barnstormers.com/category-24045-Aviat-Aircraft.html",
        "ad_keyword": "husky",
        "default_model": "Husky",
        "post_filter": _keep_husky_180_or_c,
    },
    {
        "make": "Aviat Husky",
        "module": "scrapers.trade_a_plane",
        "slug": "aviat-husky",
        "url": (
            "https://www.trade-a-plane.com/filtered/search?make=AVIAT"
            "&model_group=AVIAT+HUSKY+SERIES&s-type=aircraft"
        ),
        "default_model": "Husky",
        "post_filter": _keep_husky_180_or_c,
    },
    {
        "make": "Aviat Husky",
        "module": "scrapers.controller",
        "slug": "aviat-husky",
        "url": "https://www.controller.com/listings/for-sale/aviat/husky/aircraft",
        "title_make_pattern": "AVIAT\\s+HUSKY",
        "default_model": "Husky",
        "post_filter": _keep_husky_180_or_c,
    },
    # ---- Maule M-5 ----
    {
        "make": "Maule M-5",
        "module": "scrapers.aircraftforsale",
        "slug": "maule-m5",
        "url": "https://aircraftforsale.com/aircraft/search?manufacturer=Maule&model=M-5",
        "href_substring": "m-5",
        "default_model": "M-5",
    },
    {
        "make": "Maule M-5",
        "module": "scrapers.trade_a_plane",
        "slug": "maule-m5",
        "url": (
            "https://www.trade-a-plane.com/filtered/search?make=MAULE"
            "&model_group=MAULE+M5+SERIES&s-type=aircraft"
        ),
        "default_model": "M-5",
    },
    {
        "make": "Maule M-5",
        "module": "scrapers.controller",
        "slug": "maule-m5",
        # Controller has no /maule/m-5/ subpath; use parent and filter to M-5.
        "url": "https://www.controller.com/listings/for-sale/maule/aircraft",
        "title_make_pattern": "MAULE",
        "default_model": "M-5",
        "post_filter": _keep_maule_m5,
    },
]

FIELDS = [
    "source",
    "make",
    "year",
    "model",
    "price",
    "engine",
    "total_time",
    "engine_time",
    "location",
    "title",
    "url",
    "image_url",
    "description",
    "first_seen",
    "last_seen",
]


def load_previous() -> dict[str, dict]:
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return {row["url"]: row for row in csv.DictReader(f)}


def run_all() -> list[dict]:
    rows: list[dict] = []
    for search in SEARCHES:
        label = f"{search['module'].split('.')[-1]} ({search['make']})"
        try:
            mod = importlib.import_module(search["module"])
            scraped = mod.scrape(search)
        except Exception as e:
            print(f"  {label}: FAILED — {e}", file=sys.stderr)
            traceback.print_exc()
            continue

        filt = search.get("post_filter")
        kept = [l.as_row() for l in scraped if (filt is None or filt(l.as_row()))]
        dropped = len(scraped) - len(kept)
        suffix = f" ({dropped} filtered out)" if dropped else ""
        print(f"  {label}: {len(kept)} listings{suffix}", file=sys.stderr)
        rows.extend(kept)
    return rows


def dedupe(rows: list[dict]) -> dict[str, dict]:
    by_url: dict[str, dict] = {}
    for r in rows:
        url = r["url"]
        if url not in by_url:
            by_url[url] = r
    return by_url


def main() -> int:
    print("Scraping sources…", file=sys.stderr)
    previous = load_previous()
    current = dedupe(run_all())
    today = date.today().isoformat()

    new_urls = [u for u in current if u not in previous]

    merged: list[dict] = []
    for url, row in current.items():
        prev = previous.get(url)
        merged.append(
            {
                **{k: row.get(k, "") for k in FIELDS if k not in ("first_seen", "last_seen")},
                "first_seen": prev["first_seen"] if prev else today,
                "last_seen": today,
            }
        )

    merged.sort(
        key=lambda r: (r.get("make") or "", r["source"], str(r.get("year") or ""), r["url"])
    )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in merged:
            w.writerow(row)

    lines = [f"# New listings — {today}", ""]
    if not new_urls:
        lines.append("_No new listings since last run._")
    else:
        lines.append(f"{len(new_urls)} new listings:")
        lines.append("")
        for url in new_urls:
            r = current[url]
            lines.append(
                f"- **{r.get('year') or '?'} {r.get('make') or ''} "
                f"{r.get('model') or ''}** — {r.get('price') or 'price n/a'} "
                f"— {r.get('total_time') or ''} "
                f"— {r.get('location') or ''} "
                f"— _{r['source']}_  \n  {url}"
            )
    NEW_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    gone = [u for u in previous if u not in current]
    print(
        f"Done. {len(current)} total, {len(new_urls)} new, {len(gone)} removed. "
        f"-> {CSV_PATH.name}, {NEW_PATH.name}",
        file=sys.stderr,
    )

    # Render the HTML view
    try:
        from generate_html import render
        html_path = render()
        print(f"  HTML -> {html_path.name}", file=sys.stderr)
    except Exception as e:
        print(f"  HTML generation failed: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
