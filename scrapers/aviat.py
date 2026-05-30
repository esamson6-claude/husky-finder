"""Scrape Aviat Aircraft's used Husky inventory page (Husky-only specialty).

Ignores the `search` arg — Aviat doesn't sell Maules.
"""
from __future__ import annotations

import re

import requests

from .common import UA, Listing, extract_engine, extract_engine_time, save_raw

URL = "https://aviataircraft.com/husky-aircraft-used-inventory/"
SOURCE = "aviat"

_LISTING_RE = re.compile(
    r"((?:19|20)\d{2})\s+(Husky\s+[A-Z0-9\-]+)\s+(N\w{3,6})</h\d>", re.I
)
_PRICE_RE = re.compile(r"\$[\d,]{4,}")
_TT_RE = re.compile(r"Preowned\s+(\d[\d,]*)\s*TT", re.I)
_LOC_RE = re.compile(r"\|\s*([A-Z0-9]{3,4})\s*\|")
_SOLD_RE = re.compile(r"\bSOLD\b", re.I)
# Images are stored under wp-content/uploads/... with N-number in the filename
_IMG_RE = re.compile(
    r'(?:src|data-src|data-lazy-src)="(https?://aviataircraft\.com/wp-content/uploads/[^"]+\.(?:jpg|jpeg|png|webp))"',
    re.I,
)


def scrape(search: dict) -> list[Listing]:
    html = requests.get(URL, headers={"User-Agent": UA}, timeout=30).text
    save_raw(SOURCE, html)

    listings: list[Listing] = []
    seen: set[str] = set()

    for m in _LISTING_RE.finditer(html):
        year, model, nnum = m.group(1), m.group(2).strip(), m.group(3).upper()
        if nnum in seen:
            continue
        seen.add(nnum)

        chunk = html[m.end() : m.end() + 2500]
        if _SOLD_RE.search(chunk):
            continue

        price_m = _PRICE_RE.search(chunk)
        tt_m = _TT_RE.search(chunk)
        loc_m = _LOC_RE.search(chunk)

        # First image whose filename references this aircraft's N-number
        img_url = None
        for img in _IMG_RE.findall(chunk):
            if nnum.lower() in img.lower():
                img_url = img
                break

        listings.append(
            Listing(
                source=SOURCE,
                url=f"{URL}#{nnum}",
                make="Aviat Husky",
                year=int(year),
                model=model,
                price=price_m.group(0) if price_m else None,
                total_time=f"{tt_m.group(1)} TT" if tt_m else None,
                location=loc_m.group(1) if loc_m else None,
                title=f"{year} {model} {nnum}",
                description=chunk[:800],
                image_url=img_url,
                engine=extract_engine(chunk, model),
                engine_time=extract_engine_time(chunk),
            )
        )

    return listings
