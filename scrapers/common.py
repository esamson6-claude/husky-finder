"""Shared types and helpers for all scrapers."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Load .env from project root into os.environ (zero-dep).
_env_path = PROJECT_ROOT / ".env"
if _env_path.is_file():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        os.environ.setdefault(key, val)

# Chromium needs libnspr4/libnss3/libasound2t64/libxss1 from the system. On Ubuntu
# 24.04 WSL without sudo these were extracted by hand to ~/.local/lib/chromium-deps.
# Add that to LD_LIBRARY_PATH so Playwright can find them.
_CHROMIUM_LIB_DIR = Path.home() / ".local/lib/chromium-deps/usr/lib/x86_64-linux-gnu"
if _CHROMIUM_LIB_DIR.is_dir():
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    parts = [p for p in existing.split(":") if p]
    if str(_CHROMIUM_LIB_DIR) not in parts:
        parts.insert(0, str(_CHROMIUM_LIB_DIR))
        os.environ["LD_LIBRARY_PATH"] = ":".join(parts)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class Listing:
    source: str
    url: str
    make: Optional[str] = None  # e.g. "Aviat Husky", "Maule M-5"
    year: Optional[int] = None
    model: Optional[str] = None
    price: Optional[str] = None
    total_time: Optional[str] = None
    location: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None  # used for text filtering (e.g. paint scheme)
    image_url: Optional[str] = None  # primary thumbnail for the HTML view
    engine: Optional[str] = None  # e.g. "Lycoming O-360 180hp"
    engine_time: Optional[str] = None  # e.g. "275 SMOH"

    def as_row(self) -> dict:
        return asdict(self)


def hp_from_model(model: Optional[str]) -> Optional[int]:
    """Extract the horsepower suffix from a model name (e.g. 'A-1C-180' → 180)."""
    if not model:
        return None
    m = re.search(r"-(\d{3})[A-Z]?\b", model)
    if not m:
        return None
    hp = int(m.group(1))
    return hp if 100 <= hp <= 400 else None


_ENGINE_MAKE_RE = re.compile(
    r"\b(LYCOMING|CONTINENTAL|FRANKLIN|ROTAX)\b(?:\s+([A-Z0-9\-]{2,15}))?",
    re.I,
)


def extract_engine(text: Optional[str], model: Optional[str]) -> Optional[str]:
    """Build an engine string from free text + the model's HP suffix."""
    hp = hp_from_model(model)
    if not text:
        return f"{hp} hp" if hp else None
    m = _ENGINE_MAKE_RE.search(text)
    if not m:
        return f"{hp} hp" if hp else None
    make = m.group(1).title()
    sub = (m.group(2) or "").upper().strip("-").strip()
    parts = [make]
    if sub and not sub.isdigit():
        parts.append(sub)
    if hp:
        parts.append(f"{hp} hp")
    return " ".join(parts)


_ENG_TIME_RES = [
    # "Engine 1 Time : 1,645 SNEW" or "Engine Time : 275 SMOH"
    re.compile(
        r"Engine(?:\s*1)?\s*Time\s*:\s*([\d,]+(?:\.\d+)?)\s*(SNEW|SMOH|SOH|TBO|TTSN|TT)?",
        re.I,
    ),
    # "275 SMOH" or "1234 SOH" patterns in free text
    re.compile(r"\b([\d,]+(?:\.\d+)?)\s+(SMOH|SNEW|SOH|TTSN)\b", re.I),
]


def extract_engine_time(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for pat in _ENG_TIME_RES:
        m = pat.search(text)
        if m:
            suffix = (m.group(2) or "hrs").upper()
            return f"{m.group(1)} {suffix}"
    return None


_PRICE_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")
# Require a non-digit boundary before the number so "N49349" isn't read as "49349 TT".
# Cap at 5 digits + optional comma group; a Husky realistically never exceeds ~15k hours.
_HOURS_RE = re.compile(
    r"(?:^|[^\d])(\d{1,2}(?:,\d{3})?|\d{1,4})\s*(?:hrs?|hours?|TT|TTAF|SMOH)\b",
    re.I,
)


def first_price(text: str) -> Optional[str]:
    m = _PRICE_RE.search(text or "")
    return m.group(0) if m else None


def first_year(text: str) -> Optional[int]:
    m = _YEAR_RE.search(text or "")
    return int(m.group(0)) if m else None


def first_hours(text: str) -> Optional[str]:
    m = _HOURS_RE.search(text or "")
    if not m:
        return None
    digits = int(m.group(1).replace(",", ""))
    if digits > 15000:  # implausible for a Husky
        return None
    return f"{m.group(1)} {m.group(0).rsplit(m.group(1), 1)[-1].strip()}"


def save_raw(name: str, html: str) -> None:
    (RAW_DIR / f"{name}.html").write_text(html, encoding="utf-8")
