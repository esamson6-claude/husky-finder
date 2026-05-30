# husky-finder

Scrapes US aircraft marketplaces for **Aviat Husky** (A-1B / A-1C variants only) and **Maule M-5** listings and writes a deduped CSV plus a diff of new listings since the previous run.

Searches are defined in `scrape.py` (`SEARCHES` list). To add a new (make, source) combination, append a search dict — most scrapers take `url`, `make`, `slug`, and optional `post_filter`.

## Sources

- Aviat factory used inventory (aviataircraft.com) — ~2 listings
- AircraftForSale.com — ~1 listing
- Barnstormers.com — ~1 listing
- Trade-A-Plane.com (curl_cffi w/ Chrome TLS impersonation) — ~24 listings
- Controller.com — Imperva-protected, scraped via [ScrapingBee](https://www.scrapingbee.com).
  Set `SCRAPINGBEE_API_KEY` in `.env` to enable; free trial gives 1000 credits
  (~330 Controller scrapes since each call costs ~3 credits w/ premium proxy + JS rendering).

## Setup

```bash
cd /mnt/c/Users/edward.samson/Projects/husky-finder
~/.local/bin/uv venv
~/.local/bin/uv pip install -r requirements.txt
.venv/bin/playwright install chromium
```

### Chromium system libs (one-time, no-sudo workaround)

Playwright needs `libnspr4 libnss3 libasound2t64 libxss1`. If sudo is
available, install via apt. If not, extract them into a user dir:

```bash
mkdir -p /tmp/chromium-libs ~/.local/lib/chromium-deps
cd /tmp/chromium-libs
apt download libnspr4 libnss3 libasound2t64 libxss1
for d in *.deb; do dpkg-deb -x "$d" ~/.local/lib/chromium-deps/; done
```

The scrapers auto-detect `~/.local/lib/chromium-deps` and add it to
`LD_LIBRARY_PATH`.

## Run

```bash
source .venv/bin/activate
python scrape.py
```

Outputs:
- `data/listings.csv` — current full snapshot
- `data/new_listings.md` — listings that weren't in the previous snapshot
- `data/raw/<source>.html` — saved raw pages for debugging (gitignored)

## Schema

`year, model, price, total_time, location, url, source, first_seen, last_seen`
