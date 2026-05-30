"""Scrape AircraftForSale.com for a given make/model."""
from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .common import (
    UA,
    Listing,
    extract_engine,
    extract_engine_time,
    first_hours,
    first_price,
    first_year,
    save_raw,
)

BASE = "https://aircraftforsale.com"
SOURCE = "aircraftforsale"


def scrape(search: dict) -> list[Listing]:
    html = requests.get(search["url"], headers={"User-Agent": UA}, timeout=30).text
    save_raw(f"{SOURCE}_{search['slug']}", html)
    soup = BeautifulSoup(html, "lxml")

    href_substring = search["href_substring"].lower()
    listings: list[Listing] = []
    seen: set[str] = set()

    for a in soup.select(f"a[href*='/aircraft/']"):
        href = a.get("href", "").split("#")[0]
        # Skip pagination / view-mode links (query-string variants of the search page)
        if "?" in href or "/search" in href:
            continue
        if href_substring not in href.lower():
            continue
        url = urljoin(BASE, href)
        if url in seen:
            continue
        seen.add(url)

        card = a.find_parent(["article", "li", "div"])
        ctx = card.get_text(" ", strip=True) if card else a.get_text(" ", strip=True)

        loc_m = re.search(r"/(\d{5}-[a-z-]+?-united-states)/", href, re.I)
        location = (
            loc_m.group(1).replace("-united-states", "").replace("-", " ").title()
            if loc_m
            else None
        )

        img_el = (card or a).find("img") if card else a.find("img")
        img_url = None
        if img_el:
            img_url = (
                img_el.get("data-src")
                or img_el.get("data-original")
                or img_el.get("src")
            )
            # Skip site-chrome banners/icons; keep CDN listing photos
            if img_url and "cdn.aircraftforsale.com" not in img_url and "bundles/" in img_url:
                img_url = None

        model = search.get("default_model")
        listings.append(
            Listing(
                source=SOURCE,
                url=url,
                make=search["make"],
                year=first_year(ctx),
                model=model,
                price=first_price(ctx),
                total_time=first_hours(ctx),
                location=location,
                title=a.get_text(" ", strip=True)[:120] or None,
                description=ctx[:500],
                image_url=img_url,
                engine=extract_engine(ctx, model),
                engine_time=extract_engine_time(ctx),
            )
        )

    return listings
