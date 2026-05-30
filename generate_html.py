"""Render data/listings.csv as a single self-contained HTML page with sort/filter UI."""
from __future__ import annotations

import csv
import html
import re
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


def _int_from(text: str) -> int:
    """Pull the first integer from a free-text field (e.g. '1,234 TT' → 1234)."""
    if not text:
        return 0
    m = re.search(r"[\d,]+", text)
    if not m:
        return 0
    digits = m.group(0).replace(",", "")
    try:
        return int(digits)
    except ValueError:
        return 0


def render() -> Path:
    if not CSV_PATH.exists():
        raise SystemExit(f"{CSV_PATH} not found — run scrape.py first")
    rows = list(csv.DictReader(CSV_PATH.open(newline="", encoding="utf-8")))

    makes = sorted({r.get("make") or "Unknown" for r in rows})
    sources = sorted({r.get("source") or "" for r in rows if r.get("source")})

    # Default sort: make, then year desc, then price desc
    rows.sort(
        key=lambda r: (
            r.get("make") or "",
            -int(r.get("year") or 0),
            -_int_from(r.get("price") or ""),
        )
    )

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

        # Numeric data attributes for sort/filter
        year_n = int(r.get("year") or 0)
        price_n = _int_from(r.get("price") or "")
        hours_n = _int_from(r.get("total_time") or "")
        # Searchable text blob
        search_blob = html.escape(
            " ".join([
                r.get("title") or "",
                r.get("model") or "",
                r.get("location") or "",
                r.get("description") or "",
                r.get("engine") or "",
            ]).lower(),
            quote=True,
        )

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
            f"""<a class="card" href="{url}" target="_blank" rel="noopener"
   data-make="{make}" data-source="{source}"
   data-year="{year_n}" data-price="{price_n}" data-hours="{hours_n}"
   data-search="{search_blob}">
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

    make_buttons = "".join(
        f'<button class="chip make-chip" data-make="{html.escape(m, quote=True)}">{html.escape(m)}</button>'
        for m in makes
    )
    source_buttons = "".join(
        f'<button class="chip source-chip" data-source="{html.escape(s, quote=True)}">{html.escape(s)}</button>'
        for s in sources
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aircraft listings — {date.today().isoformat()}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#f5f5f7; --card:#fff; --fg:#222; --muted:#666;
           --border:#e2e2e6; --accent:#0366d6; --chip-bg:transparent; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#1a1a1c; --card:#26262a; --fg:#eee; --muted:#aaa; --border:#3a3a40;
             --accent:#58a6ff; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font: 14px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:var(--bg); color:var(--fg); }}
  header {{ padding:14px 20px; border-bottom:1px solid var(--border); background:var(--card);
            position:sticky; top:0; z-index:2; }}
  h1 {{ margin:0 0 4px 0; font-size:18px; font-weight:600; }}
  .subhead {{ color:var(--muted); font-size:12px; margin-bottom:10px; }}
  .controls {{ display:grid; gap:10px;
               grid-template-columns: 1fr; }}
  @media (min-width: 760px) {{
    .controls {{ grid-template-columns: 2fr 1fr 1fr 1fr; align-items:end; }}
  }}
  .control-group {{ display:flex; flex-direction:column; gap:4px; }}
  .control-group label {{ font-size:11px; color:var(--muted); text-transform:uppercase;
                          letter-spacing:0.5px; }}
  .control-group input, .control-group select {{
    padding:6px 10px; border:1px solid var(--border); border-radius:6px;
    background:var(--bg); color:var(--fg); font:inherit; }}
  .range-row {{ display:flex; gap:6px; }}
  .range-row input {{ width:0; flex:1; min-width:0; }}
  .chips {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:10px; }}
  .chip {{ padding:5px 12px; border-radius:999px; border:1px solid var(--border);
           background:var(--chip-bg); color:var(--fg); font:inherit; font-size:12px; cursor:pointer; }}
  .chip:hover {{ border-color:var(--accent); }}
  .chip.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
  .chip-row-label {{ font-size:11px; color:var(--muted); text-transform:uppercase;
                     letter-spacing:0.5px; align-self:center; margin-right:4px; }}
  #count {{ font-weight:600; }}
  main {{ padding:20px; display:grid; gap:16px;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
  .card {{ display:flex; flex-direction:column; background:var(--card); border:1px solid var(--border);
           border-radius:10px; overflow:hidden; text-decoration:none; color:inherit;
           transition: transform .1s, box-shadow .15s; }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }}
  .card.hidden {{ display:none; }}
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
  #empty {{ padding:40px 20px; text-align:center; color:var(--muted); display:none; }}
</style>
</head>
<body>
<header>
  <h1>Aircraft listings — <span id="count">{len(rows)}</span> shown</h1>
  <div class="subhead">Updated {date.today().isoformat()} · click any card to open the listing</div>
  <div class="controls">
    <div class="control-group">
      <label for="search">Search</label>
      <input id="search" type="search" placeholder="Title, model, location, description…">
    </div>
    <div class="control-group">
      <label for="sort">Sort by</label>
      <select id="sort">
        <option value="default">Default (make / newest / highest price)</option>
        <option value="year-desc">Year — newest first</option>
        <option value="year-asc">Year — oldest first</option>
        <option value="price-asc">Price — low to high</option>
        <option value="price-desc">Price — high to low</option>
        <option value="hours-asc">Airframe TT — low to high</option>
        <option value="hours-desc">Airframe TT — high to low</option>
      </select>
    </div>
    <div class="control-group">
      <label>Price range ($)</label>
      <div class="range-row">
        <input id="price-min" type="number" placeholder="Min" min="0">
        <input id="price-max" type="number" placeholder="Max" min="0">
      </div>
    </div>
    <div class="control-group">
      <label>Year range</label>
      <div class="range-row">
        <input id="year-min" type="number" placeholder="From" min="1900" max="2030">
        <input id="year-max" type="number" placeholder="To" min="1900" max="2030">
      </div>
    </div>
  </div>
  <div class="chips">
    <span class="chip-row-label">Make:</span>
    <button class="chip make-chip active" data-make="__all__">All</button>
    {make_buttons}
  </div>
  <div class="chips">
    <span class="chip-row-label">Source:</span>
    <button class="chip source-chip active" data-source="__all__">All</button>
    {source_buttons}
  </div>
</header>
<main id="grid">
  {''.join(cards_html)}
</main>
<div id="empty">No listings match the current filters.</div>
<script>
  const grid = document.getElementById('grid');
  const cards = Array.from(grid.querySelectorAll('.card'));
  const countEl = document.getElementById('count');
  const emptyEl = document.getElementById('empty');
  const searchEl = document.getElementById('search');
  const sortEl = document.getElementById('sort');
  const priceMinEl = document.getElementById('price-min');
  const priceMaxEl = document.getElementById('price-max');
  const yearMinEl = document.getElementById('year-min');
  const yearMaxEl = document.getElementById('year-max');

  let activeMake = '__all__';
  let activeSource = '__all__';

  function num(v) {{ const n = parseInt(v, 10); return Number.isFinite(n) ? n : null; }}

  function apply() {{
    const q = searchEl.value.trim().toLowerCase();
    const pMin = num(priceMinEl.value), pMax = num(priceMaxEl.value);
    const yMin = num(yearMinEl.value), yMax = num(yearMaxEl.value);

    let visible = [];
    for (const c of cards) {{
      const make = c.dataset.make;
      const source = c.dataset.source;
      const year = parseInt(c.dataset.year, 10) || 0;
      const price = parseInt(c.dataset.price, 10) || 0;
      const search = c.dataset.search;

      let show = true;
      if (activeMake !== '__all__' && make !== activeMake) show = false;
      if (activeSource !== '__all__' && source !== activeSource) show = false;
      if (q && !search.includes(q)) show = false;
      if (pMin !== null && (price === 0 || price < pMin)) show = false;
      if (pMax !== null && price > pMax) show = false;
      if (yMin !== null && (year === 0 || year < yMin)) show = false;
      if (yMax !== null && year > yMax) show = false;

      c.classList.toggle('hidden', !show);
      if (show) visible.push(c);
    }}

    // Sort
    const sortKey = sortEl.value;
    if (sortKey !== 'default') {{
      const cmp = {{
        'year-desc':  (a,b) => (+b.dataset.year) - (+a.dataset.year),
        'year-asc':   (a,b) => (+a.dataset.year) - (+b.dataset.year),
        'price-desc': (a,b) => (+b.dataset.price) - (+a.dataset.price),
        'price-asc':  (a,b) => ((+a.dataset.price || Infinity) - (+b.dataset.price || Infinity)),
        'hours-desc': (a,b) => (+b.dataset.hours) - (+a.dataset.hours),
        'hours-asc':  (a,b) => ((+a.dataset.hours || Infinity) - (+b.dataset.hours || Infinity)),
      }}[sortKey];
      visible.sort(cmp);
      // Re-attach in sorted order (DOM order = visual order)
      for (const c of visible) grid.appendChild(c);
    }}

    countEl.textContent = visible.length;
    emptyEl.style.display = visible.length === 0 ? 'block' : 'none';
  }}

  document.querySelectorAll('.make-chip').forEach(b => b.addEventListener('click', () => {{
    document.querySelectorAll('.make-chip').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    activeMake = b.dataset.make;
    apply();
  }}));
  document.querySelectorAll('.source-chip').forEach(b => b.addEventListener('click', () => {{
    document.querySelectorAll('.source-chip').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    activeSource = b.dataset.source;
    apply();
  }}));
  for (const el of [searchEl, priceMinEl, priceMaxEl, yearMinEl, yearMaxEl, sortEl]) {{
    el.addEventListener('input', apply);
    el.addEventListener('change', apply);
  }}
</script>
</body>
</html>
"""

    HTML_PATH.write_text(page, encoding="utf-8")
    DOCS_HTML_PATH.write_text(page, encoding="utf-8")
    return HTML_PATH


if __name__ == "__main__":
    p = render()
    print(f"Wrote {p}")
