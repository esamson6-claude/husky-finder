"""Scrape Barnstormers.com — Aviat category (Maule has no clean category here)."""
from __future__ import annotations

import re

import requests

from .common import (
    UA,
    Listing,
    extract_engine,
    extract_engine_time,
    first_price,
    first_year,
    save_raw,
)

SOURCE = "barnstormers"

_AD_RE = re.compile(
    r"adclick\.php\?type=[a-z_]+&id=(\d+)&adtitle=([^'\"&]+)",
    re.I,
)


def scrape(search: dict) -> list[Listing]:
    html = requests.get(search["url"], headers={"User-Agent": UA}, timeout=30).text
    save_raw(f"{SOURCE}_{search['slug']}", html)

    match_keyword = search["ad_keyword"].lower()
    listings: list[Listing] = []
    seen: set[str] = set()

    for ad_id, adtitle in _AD_RE.findall(html):
        if match_keyword not in adtitle.lower():
            continue
        if ad_id in seen:
            continue
        seen.add(ad_id)

        title = adtitle.replace("-", " ").strip()
        ctx_window = html[max(0, html.find(ad_id) - 200) : html.find(ad_id) + 800]
        model = search.get("default_model")
        listings.append(
            Listing(
                source=SOURCE,
                url=(
                    f"https://www.barnstormers.com/adclick.php?type="
                    f"featured_category_clicks&id={ad_id}&adtitle={adtitle}"
                ),
                make=search["make"],
                year=first_year(title) or first_year(ctx_window),
                model=model,
                price=first_price(ctx_window),
                title=title,
                description=ctx_window[:500],
                engine=extract_engine(ctx_window, model),
                engine_time=extract_engine_time(ctx_window),
            )
        )

    return listings
