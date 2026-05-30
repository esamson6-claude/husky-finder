"""Render data/listings.csv as a single self-contained HTML page with thumbnails."""
from __future__ import annotations

import csv
import html
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "listings.csv"
HTML_PATH = DATA_DIR / "listings.html"
DOCS_HTML_PATH = DOCS_DIR / "index.html"


PLACEHOLDER_IMG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 250'>"
    "<rect width='400' height='250' fill='%23e0e0e0'/>"
    "<text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle'"
    " font-family='sans-serif' font-size='18' fill='%23888'>No image</text>"
    "</svg>"
)


def _price_int(price: str) -> int:
    try:
        return int("".join(c for c in (price or "") if c.isdigit()))
    except ValueError:
        return 0


def render() -> Path:
    if not CSV_PATH.exists():
        raise SystemExit(f"{CSV_PATH} not found — run scrape.py first")
    rows = list(csv.DictReader(CSV_PATH.open(newline="", encoding="utf-8")))
    # Sort by make, then year desc, then price desc
    rows.sort(
        key=lambda r: (
            r.get("make") or "",
            -int(r.get("year") or 0),
            -_price_int(r.get("price") or ""),
        )
    )

    makes = sorted({r.get("make") or "Unknown" for r in rows})

    cards_html: list[str] = []
    for r in rows:
        title = html.escape(
            f"{r.get('year') or '?'} {r.get('make') or ''} {r.get('model') or ''}".strip()
        )
        price = html.escape(r.get("price") or "Price n/a")
        airframe = html.escape(r.get("total_time") or "")
        eng_time = html.escape(r.get("engine_time") or "")
        engine = html.escape(r.get("engine") or "")
        model = html.escape(r.get("model") or "")
        loc = html.escape(r.get("location") or "")
        source = html.escape(r.get("source") or "")
        make = html.escape(r.get("make") or "Unknown")
        url = html.escape(r.get("url") or "#", quote=True)
        img = html.escape(r.get("image_url") or "", quote=True) or PLACEHOLDER_IMG
        first_seen = html.escape(r.get("first_seen") or "")

        spec_rows = []
        if model:
            spec_rows.append(f'<div class="spec"><span>Model</span><span>{model}</span></div>')
        if engine:
            spec_rows.append(f'<div class="spec"><span>Engine</span><span>{engine}</span></div>')
        if airframe:
            spec_rows.append(f'<div class="spec"><span>Airframe TT</span><span>{airframe}</span></div>')
        if eng_time:
            spec_rows.append(f'<div class="spec"><span>Engine TT</span><span>{eng_time}</span></div>')

        cards_html.append(
            f"""<a class="card" href="{url}" target="_blank" rel="noopener" data-make="{make}" data-source="{source}">
  <div class="thumb"><img loading="lazy" src="{img}" alt="{title}" onerror="this.src='{PLACEHOLDER_IMG}'"></div>
  <div class="body">
    <div class="title">{title}</div>
    <div class="price">{price}</div>
    <div class="specs">{''.join(spec_rows)}</div>
    <div class="meta">
      <span class="loc">{loc}</span>
    </div>
    <div class="footer">
      <span class="source">{source}</span>
      <span class="seen">first seen {first_seen}</span>
    </div>
  </div>
</a>"""
        )

    filter_buttons = "".join(
        f'<button class="filter" data-filter="{html.escape(m, quote=True)}">{html.escape(m)}</button>'
        for m in makes
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aircraft listings — {date.today().isoformat()}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#f5f5f7; --card:#fff; --fg:#222; --muted:#666;
           --border:#e2e2e6; --accent:#0366d6; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#1a1a1c; --card:#26262a; --fg:#eee; --muted:#aaa; --border:#3a3a40;
             --accent:#58a6ff; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font: 14px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:var(--bg); color:var(--fg); }}
  header {{ padding:18px 24px; border-bottom:1px solid var(--border); background:var(--card);
            position:sticky; top:0; z-index:2; }}
  h1 {{ margin:0 0 8px 0; font-size:20px; font-weight:600; }}
  .subhead {{ color:var(--muted); font-size:13px; margin-bottom:12px; }}
  .filters {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .filter {{ padding:6px 14px; border-radius:999px; border:1px solid var(--border); background:transparent;
             color:var(--fg); font:inherit; cursor:pointer; }}
  .filter.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
  main {{ padding:20px; display:grid; gap:16px;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
  .card {{ display:flex; flex-direction:column; background:var(--card); border:1px solid var(--border);
           border-radius:10px; overflow:hidden; text-decoration:none; color:inherit;
           transition: transform .1s, box-shadow .15s; }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }}
  .thumb {{ aspect-ratio: 16/10; background:#0001; overflow:hidden; }}
  .thumb img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .body {{ padding:12px 14px; display:flex; flex-direction:column; gap:6px; }}
  .title {{ font-weight:600; font-size:15px; }}
  .price {{ color:var(--accent); font-weight:600; font-size:16px; }}
  .specs {{ display:grid; grid-template-columns: auto 1fr; gap:2px 10px; font-size:12px;
            color:var(--muted); margin-top:2px; }}
  .spec {{ display:contents; }}
  .spec > span:first-child {{ text-transform:uppercase; letter-spacing:0.4px; font-size:10px;
                              opacity:0.7; align-self:center; }}
  .spec > span:last-child {{ color:var(--fg); font-size:12.5px; }}
  .meta {{ color:var(--muted); font-size:12px; display:flex; gap:10px; flex-wrap:wrap; }}
  .footer {{ display:flex; justify-content:space-between; font-size:11px; color:var(--muted);
             margin-top:auto; padding-top:6px; border-top:1px solid var(--border); }}
  .source {{ text-transform:uppercase; letter-spacing:0.5px; }}
</style>
</head>
<body>
<header>
  <h1>Aircraft listings — {len(rows)} total</h1>
  <div class="subhead">Updated {date.today().isoformat()} · click any card to open the listing</div>
  <div class="filters">
    <button class="filter active" data-filter="__all__">All ({len(rows)})</button>
    {filter_buttons}
  </div>
</header>
<main id="grid">
  {''.join(cards_html)}
</main>
<script>
  const filters = document.querySelectorAll('.filter');
  const cards = document.querySelectorAll('.card');
  filters.forEach(b => b.addEventListener('click', () => {{
    filters.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    const f = b.dataset.filter;
    cards.forEach(c => {{
      c.style.display = (f === '__all__' || c.dataset.make === f) ? '' : 'none';
    }});
  }}));
</script>
</body>
</html>
"""

    HTML_PATH.write_text(page, encoding="utf-8")
    # Mirror to docs/index.html for GitHub Pages (Pages reads from /docs on main).
    DOCS_HTML_PATH.write_text(page, encoding="utf-8")
    return HTML_PATH


if __name__ == "__main__":
    p = render()
    print(f"Wrote {p}")
