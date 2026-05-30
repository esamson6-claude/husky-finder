"""Geocode listing locations via OpenStreetMap Nominatim, cached on disk.

Reads `data/listings.csv` for unique location strings, looks up any not
already in `data/geocache.json`, and saves the cache back. Rate-limits at
~1 req/sec per Nominatim's usage policy. Run idempotently — only new
locations hit the network.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent
CSV_PATH = PROJECT_ROOT / "data" / "listings.csv"
CACHE_PATH = PROJECT_ROOT / "data" / "geocache.json"

NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = "husky-finder/1.0 (github.com/esamson6-claude/husky-finder)"


def load_cache() -> dict[str, list[float] | None]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict[str, list[float] | None]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, sort_keys=True, indent=2))


def looks_like_airport_code(loc: str) -> bool:
    """E.g. 'C29', 'KBMC' — short alphanumeric strings Nominatim won't resolve."""
    s = loc.strip()
    return 2 <= len(s) <= 5 and s.replace(" ", "").isalnum() and any(c.isdigit() for c in s)


def geocode_one(location: str) -> list[float] | None:
    if looks_like_airport_code(location):
        return None
    try:
        r = requests.get(
            NOMINATIM,
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": UA},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return None
    if not data:
        return None
    try:
        return [float(data[0]["lat"]), float(data[0]["lon"])]
    except (KeyError, ValueError, TypeError):
        return None


def main() -> int:
    if not CSV_PATH.exists():
        print(f"{CSV_PATH} not found — run scrape.py first", file=sys.stderr)
        return 1

    cache = load_cache()
    rows = list(csv.DictReader(CSV_PATH.open(newline="", encoding="utf-8")))
    locations = {r.get("location", "").strip() for r in rows}
    locations.discard("")

    new_locations = [l for l in locations if l not in cache]
    if not new_locations:
        print(f"  geocode: cache complete ({len(cache)} entries, 0 new)", file=sys.stderr)
        return 0

    print(f"  geocode: {len(new_locations)} new locations to geocode…", file=sys.stderr)
    hits, misses = 0, 0
    for i, loc in enumerate(new_locations):
        coords = geocode_one(loc)
        cache[loc] = coords
        if coords:
            hits += 1
        else:
            misses += 1
        # Nominatim rate limit: max 1 req/sec
        if i < len(new_locations) - 1:
            time.sleep(1.1)
        if (i + 1) % 25 == 0:
            save_cache(cache)
            print(f"    progress: {i+1}/{len(new_locations)}", file=sys.stderr)

    save_cache(cache)
    print(f"  geocode: done — {hits} hit, {misses} miss (cache now {len(cache)} entries)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
