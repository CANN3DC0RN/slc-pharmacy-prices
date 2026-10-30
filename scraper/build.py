"""Build everything that comes from site/data.json: price history, weekly
reports, pharmacy pages, category guides, sitemap and robots.txt.

Usage: python3 scraper/build.py   (after scraper/run.py)

Reports are written once per week and then left alone, so they read like a
dated article. Pharmacy and category pages are rebuilt on every run.
"""
import datetime
import gzip
import html
import json
import os
import statistics
import urllib.parse
import zoneinfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
HISTORY = os.path.join(ROOT, "history")
REPORTS = os.path.join(SITE, "reports")
TZ = zoneinfo.ZoneInfo("America/Denver")

with open(os.path.join(ROOT, "config.json")) as f:
    CONFIG = json.load(f)
SITE_URL = CONFIG["site_url"].rstrip("/")
SITE_NAME = CONFIG["site_name"]
GOATCOUNTER = CONFIG.get("goatcounter", "")

HOME_AREA = "Salt Lake area"
GUIDES = ["Flower", "Vapes", "Concentrates", "Edibles", "Tinctures", "Topicals"]
SIZES = {"Flower": [1, 3.5, 7, 14, 28], "Vapes": [0.5, 1, 2], "Concentrates": [0.5, 1]}
ICONS = {
    "Flower": '<path d="M12 21v-8M12 13c-4.5 0-7-3-7-7.5 4.5 0 7 2.8 7 7.5zm0 0c4.5 0 7-3 7-7.5-4.5 0-7 2.8-7 7.5z"/>',
    "Vapes": '<rect x="9" y="3" width="6" height="18" rx="2"/><path d="M9 8h6M12 17v1"/>',
    "Concentrates": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "Edibles": '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M9 9h.01M15 15h.01M15 9h.01M9 15h.01"/>',
    "Tinctures": '<path d="M10 2h4v4h-4zM8 6h8l1 3v11a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V9z"/><path d="M7 13h10"/>',
    "Topicals": '<rect x="5" y="9" width="14" height="12" rx="2"/><path d="M7 9V6h10v3"/>',
    "Accessories": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
}
LOGO = ('<svg width="{s}" height="{s}" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#17603f"/>'
        '<path d="M16 25V14M16 14c-5 0-8-3.5-8-8.5 5 0 8 3 8 8.5zm0 0c5 0 8-3.5 8-8.5-5 0-8 3-8 8.5z" stroke="#7ee2a8" '
        'stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' "
           "fill='%230f3d2a'/%3E%3Cpath d='M16 25V14M16 14c-5 0-8-3.5-8-8.5 5 0 8 3 8 8.5zm0 0c5 0 8-3.5 8-8.5-5 0-8 3-8 8.5z' "
           "stroke='%237ee2a8' stroke-width='2.2' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")

esc = html.escape


# ---------- small helpers ----------

def money(n):
    return f"${n:.0f}" if float(n).is_integer() else f"${n:.2f}"


def pct_off(p):
    return round(100 * (1 - p["price"] / p["regular_price"])) if p["regular_price"] > p["price"] else 0


def fmt_g(g):
    return "½g" if g == 0.5 else f"{g:g}g"


def long_date(d):
    return f"{d:%B} {d.day}, {d.year}"


def median(values):
    return statistics.median(values) if values else None


def slug(cat):
    return cat.lower()


def icon(cat, size=22):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(cat, ICONS["Accessories"])}</svg>')


def write(rel, text):
    path = os.path.join(SITE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


# ---------- page shell (matches site/index.html) ----------

def page(rel, title, description, body, json_ld=None):
    """Wrap body in the site's nav and footer. Every generated page sits one folder deep."""
    up = "../"
    ld = f'<script type="application/ld+json">{json.dumps(json_ld).replace("</", "<\\/")}</script>\n' if json_ld else ""
    if GOATCOUNTER:
        ld += f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>\n'
    guides = "".join(f'<a href="{up}prices/{slug(c)}.html">Cheapest {c.lower()}</a>' for c in GUIDES)
    stores = "".join(f'<a href="{up}pharmacy/{esc(s["id"])}.html">{esc(s["name"])} · {esc(s["city"])}</a>' for s in STORES if s.get("count"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{SITE_URL}/{rel}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}/{rel}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta name="theme-color" content="#0f3d2a">
<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}style.css">
{ld}</head>
<body>
<header class="nav">
  <div class="wrap">
    <a class="logo" href="{up}" aria-label="{SITE_NAME} home">{LOGO.format(s=30)} {SITE_NAME}</a>
    <nav aria-label="Main">
      <a href="{up}#deals">Deals</a>
      <a href="{up}#pharmacies">Pharmacies</a>
      <a href="{up}reports/">Price reports</a>
      <a href="{up}events/">Events</a>
      <a href="{up}news/">News</a>
      <a class="primary" href="{up}#compare">Compare prices</a>
    </nav>
  </div>
</header>
<main>
{body}
</main>
<footer>
  <div class="wrap">
    <div>
      <div class="logo">{LOGO.format(s=26)} {SITE_NAME}</div>
      <p>© {NOW.year} {SITE_NAME}</p>
    </div>
    <div class="flinks"><h4>Price guides</h4>{guides}</div>
    <div class="flinks"><h4>Pharmacies</h4>{stores}</div>
    <div class="flinks"><h4>More</h4><a href="{up}reports/">Weekly price reports</a><a href="{up}events/">Cannabis events</a><a href="{up}news/">Utah cannabis news</a><a href="{up}#compare">Compare prices</a><a href="{up}#deals">Today's deals</a></div>
    <div class="about">
      <p>Prices come from each pharmacy's online menu. Prices and availability can change, so always confirm with the pharmacy before you go.</p>
      <p>For Utah medical cannabis cardholders. We don't sell anything and aren't affiliated with any pharmacy listed. Nothing here is medical advice.</p>
    </div>
  </div>
</footer>
</body>
</html>
"""


def hero(crumbs, h1, intro, buttons=""):
    trail = " / ".join(f'<a href="{href}">{esc(label)}</a>' if href else esc(label) for label, href in crumbs)
    return f"""<div class="phero"><div class="wrap">
  <div class="crumbs">{trail}</div>
  <h1>{h1}</h1>
  <p>{intro}</p>
  {f'<div class="btn-row">{buttons}</div>' if buttons else ""}
</div></div>"""


def section(h2, sub, inner, link=""):
    return f"""<section><div class="head"><div><h2>{h2}</h2>{f"<p>{sub}</p>" if sub else ""}</div>{link}</div>
{inner}</section>"""


def card(p):
    s = STORES_BY_ID.get(p["store"], {})
    off = pct_off(p)
    chips = [c for c in (p["size"], p["strain_type"], f'{p["thc"]:g}% THC' if p["thc"] is not None else "") if c]
    ph = icon(p["category"], 44)
    img = (f'<img src="{esc(p["image"])}" alt="" loading="lazy" decoding="async" '
           f'onerror="this.replaceWith(Object.assign(document.createElement(\'span\'),{{className:\'ph\',innerHTML:this.dataset.ph}}))" '
           f"data-ph='{ph}'>" if p["image"] else f'<span class="ph">{ph}</span>')
    return f"""<a class="card" href="{esc(p["url"] or s.get("website", ""))}" target="_blank" rel="noopener">
  <div class="thumb">{img}{f'<span class="tag">{off}% off</span>' if off else ""}</div>
  <div class="body">
    <span class="brand">{esc(p["brand"] or p["category"])}</span>
    <span class="name">{esc(p["name"])}</span>
    {f'<span class="chips">{"".join(f"<span class=chip-s>{esc(c)}</span>" for c in chips)}</span>' if chips else ""}
    <span class="price"><strong>{money(p["price"])}</strong>{f"<s>{money(p['regular_price'])}</s>" if off else ""}
      {f'<span class="ppg">{money(p["price_per_gram"])}/g</span>' if p["price_per_gram"] else ""}</span>
    <span class="store-line"><span class="dot"></span><span>{esc(s.get("name", ""))} · {esc(s.get("city", ""))}</span></span>
  </div>
</a>"""


def grid(products):
    return f'<div class="grid">{"".join(card(p) for p in products)}</div>'


def table(headers, rows):
    """headers: list of (label, is_numeric); rows: lists of already-escaped cell HTML."""
    head = "".join(f'<th class="num">{h}</th>' if num else f"<th>{h}</th>" for h, num in headers)
    body = "".join("<tr>" + "".join(f'<td class="num">{c}</td>' if headers[i][1] else f"<td>{c}</td>"
                                    for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tbl"><table class="t"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def product_cell(p):
    brand = f'<span class="sub">{esc(p["brand"])}</span>' if p["brand"] else ""
    return f'<a href="{esc(p["url"])}" target="_blank" rel="noopener">{esc(p["name"])}</a>{brand}'


def store_cell(store_id):
    s = STORES_BY_ID.get(store_id, {})
    return f'<a href="../pharmacy/{esc(store_id)}.html">{esc(s.get("name", store_id))}</a><span class="sub">{esc(s.get("city", ""))}</span>'


def price_cell(p):
    was = f'<span class="sub"><s>{money(p["regular_price"])}</s></span>' if p["on_sale"] else ""
    return money(p["price"]) + was


def faq(pairs):
    items = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in pairs)
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]}
    return f'<div class="faq">{items}</div>', ld


def checked(store):
    """When a pharmacy's prices were last checked, as text."""
    when = store.get("updated")
    if not when:
        return "not yet"
    if len(when) == 10:
        return long_date(datetime.date.fromisoformat(when))
    return long_date(datetime.datetime.fromisoformat(when).astimezone(TZ).date())


# ---------- price queries ----------

def of(cat, grams=None, products=None):
    items = [p for p in (products if products is not None else PRODUCTS) if p["category"] == cat]
    if grams is not None:
        items = [p for p in items if p["grams"] == grams]
    return items


def cheapest(items, n, key="price"):
    return sorted(items, key=lambda p: (p[key] if p[key] is not None else 1e9, p["price"]))[:n]


def biggest_deals(items, n):
    # $1 accessories would top every list with "90% off".
    return sorted((p for p in items if pct_off(p) >= 5 and p["category"] != "Accessories"), key=lambda p: (-pct_off(p), p["price"]))[:n]


def median_price(items):
    m = median([p["price"] for p in items])
    return money(round(m, 2)) if m is not None else "–"


# ---------- history ----------

def save_snapshot(today):
    """One compact snapshot per day (the first run of the day), for week-over-week trends."""
    path = os.path.join(HISTORY, f"{today.isoformat()}.json.gz")
    if os.path.exists(path):
        return
    os.makedirs(HISTORY, exist_ok=True)
    rows = [[p["store"], p["category"], p["name"], p["size"], p["grams"], p["price"], p["regular_price"]] for p in ALL_PRODUCTS]
    with open(path, "wb") as f:
        f.write(gzip.compress(json.dumps(rows, separators=(",", ":")).encode(), mtime=0))


def load_snapshot(target):
    """The snapshot closest to `target`, within a few days either way, or None."""
    for delta in (0, -1, 1, -2, 2, -3, 3):
        path = os.path.join(HISTORY, f"{(target + datetime.timedelta(days=delta)).isoformat()}.json.gz")
        if os.path.exists(path):
            with open(path, "rb") as f:
                rows = json.loads(gzip.decompress(f.read()))
            keys = ("store", "category", "name", "size", "grams", "price", "regular_price")
            return [dict(zip(keys, r)) for r in rows]
    return None


def key(p):
    return (p["store"], p["name"], p["size"])


# ---------- weekly report ----------

def build_report(today):
    monday = today - datetime.timedelta(days=today.weekday())
    slug_ = monday.isoformat()
    index_path = os.path.join(REPORTS, "index.json")
    reports = []
    if os.path.exists(index_path):
        with open(index_path) as f:
            reports = json.load(f)
    if any(r["slug"] == slug_ for r in reports) or not PRODUCTS:
        return reports

    live = [s for s in LOCAL_STORES if s.get("count")]
    eighth = of("Flower", 3.5)
    vape = of("Vapes", 1)
    sale = [p for p in PRODUCTS if p["on_sale"]]
    best_eighth = cheapest(eighth, 1)
    title = f"Salt Lake medical cannabis prices: week of {monday:%B} {monday.day}"
    summary_bits = []
    if best_eighth:
        b = best_eighth[0]
        summary_bits.append(f"The cheapest 3.5g of flower is {money(b['price'])} at {STORES_BY_ID[b['store']]['name']}")
    summary_bits.append(f"{len(sale):,} items are on sale across {len(live)} pharmacies")
    summary = ". ".join(summary_bits) + "."

    # The short version
    bullets = []
    if best_eighth:
        b = best_eighth[0]
        bullets.append(f"<b>Cheapest 3.5g flower:</b> {esc(b['name'])} for {money(b['price'])} at {esc(STORES_BY_ID[b['store']]['name'])}. "
                       f"The typical (median) 3.5g across Salt Lake is {median_price(eighth)}.")
    if vape:
        v = cheapest(vape, 1)[0]
        bullets.append(f"<b>Cheapest 1g vape:</b> {esc(v['name'])} for {money(v['price'])} at {esc(STORES_BY_ID[v['store']]['name'])}. "
                       f"Median 1g vape: {median_price(vape)}.")
    by_store_eighth = {s["id"]: median([p["price"] for p in eighth if p["store"] == s["id"]]) for s in live}
    ranked = sorted(((m, sid) for sid, m in by_store_eighth.items() if m is not None))
    if len(ranked) >= 2:
        bullets.append(f"<b>Lowest typical 3.5g price:</b> {esc(STORES_BY_ID[ranked[0][1]]['name'])} at a median of {money(round(ranked[0][0], 2))}, "
                       f"compared with {money(round(ranked[-1][0], 2))} at {esc(STORES_BY_ID[ranked[-1][1]]['name'])}.")
    deals = biggest_deals(PRODUCTS, 10)
    if deals:
        d = deals[0]
        bullets.append(f"<b>Biggest discount:</b> {pct_off(d)}% off {esc(d['name'])} at {esc(STORES_BY_ID[d['store']]['name'])} "
                       f"({money(d['regular_price'])} → {money(d['price'])}). {len(sale):,} items are on sale in total.")

    parts = [section("The short version", "", f'<div class="prose"><ul>{"".join(f"<li>{b}</li>" for b in bullets)}</ul></div>')]

    def top_table(items, n, ppg=True):
        rows = [[product_cell(p), store_cell(p["store"]), price_cell(p),
                 money(p["price_per_gram"]) if p["price_per_gram"] else "–", f'{p["thc"]:g}%' if p["thc"] is not None else "–"]
                for p in cheapest(items, n)]
        return table([("Product", False), ("Pharmacy", False), ("Price", True), ("Per gram", True), ("THC", True)], rows)

    if eighth:
        parts.append(section("Cheapest 3.5g flower", "The ten lowest prices on an eighth this week.", top_table(eighth, 10),
                             '<a class="link" href="../prices/flower.html">All flower prices →</a>'))
    ounce = of("Flower", 28)
    if ounce:
        parts.append(section("Best price on an ounce (28g)", "", top_table(ounce, 5)))
    if vape:
        parts.append(section("Cheapest 1g vapes", "", top_table(vape, 10),
                             '<a class="link" href="../prices/vapes.html">All vape prices →</a>'))
    conc = of("Concentrates", 1)
    if conc:
        parts.append(section("Cheapest 1g concentrates", "", top_table(conc, 5),
                             '<a class="link" href="../prices/concentrates.html">All concentrate prices →</a>'))

    rows = []
    for s in live:
        mine = [p for p in PRODUCTS if p["store"] == s["id"]]
        rows.append([store_cell(s["id"]), f"{len(mine):,}", median_price(of("Flower", 3.5, mine)),
                     median_price(of("Vapes", 1, mine)), f'{sum(p["on_sale"] for p in mine):,}', esc(checked(s))])
    parts.append(section("How the pharmacies compare", "Median price means half the products cost less and half cost more.",
                         table([("Pharmacy", False), ("Products", True), ("Median 3.5g flower", True), ("Median 1g vape", True),
                                ("On sale", True), ("Prices checked", False)], rows)))

    if deals:
        rows = [[product_cell(p), store_cell(p["store"]), money(p["regular_price"]), money(p["price"]), f"{pct_off(p)}%"] for p in deals]
        parts.append(section("Biggest discounts", "", table(
            [("Product", False), ("Pharmacy", False), ("Was", True), ("Now", True), ("Off", True)], rows),
            '<a class="link" href="../#deals">Today\'s deals →</a>'))

    prior = load_snapshot(today - datetime.timedelta(days=7))
    if prior:
        before = {key(p): p for p in prior}
        rows = []
        for s in live:
            old = median([p["price"] for p in prior if p["store"] == s["id"] and p["category"] == "Flower" and p["grams"] == 3.5])
            new = by_store_eighth.get(s["id"])
            if old is None or new is None:
                continue
            diff = round(new - old, 2)
            change = "no change" if abs(diff) < 0.01 else (f'<span class="down">−{money(-diff)}</span>' if diff < 0 else f'<span class="up">+{money(diff)}</span>')
            rows.append([store_cell(s["id"]), money(round(old, 2)), money(round(new, 2)), change])
        inner = ""
        if rows:
            inner += table([("Pharmacy", False), ("Median 3.5g last week", True), ("This week", True), ("Change", True)], rows)
        drops = sorted(((before[key(p)]["price"] - p["price"], p) for p in PRODUCTS
                        if key(p) in before and before[key(p)]["price"] - p["price"] >= 1), key=lambda t: -t[0])[:10]
        if drops:
            inner += "<h3>Biggest price drops</h3>" + table(
                [("Product", False), ("Pharmacy", False), ("Last week", True), ("Now", True)],
                [[product_cell(p), store_cell(p["store"]), money(before[key(p)]["price"]), money(p["price"])] for _, p in drops])
        new_items = sum(1 for p in PRODUCTS if key(p) not in before)
        inner += f'<p class="note">{new_items:,} products are new on menus since last week.</p>'
        parts.append(section("What changed since last week", "", inner))
    else:
        parts.append(section("What changed since last week", "",
                             '<p class="note">We started keeping price history this week, so week-over-week changes begin with next week\'s report.</p>'))

    parts.append(section("How we collect these prices", "", f"""<div class="prose">
<p>Prices come from each pharmacy's own online menu, at the medical (cardholder) price. Some menus are checked automatically
several times a day; others are saved by hand about once a week, and the "Prices checked" column above shows when.
Prices change often, so confirm with the pharmacy before you go.</p>
<p>This report covers {len(live)} Salt Lake area pharmacies and {len(PRODUCTS):,} products, as of {esc(long_date(today))}.</p>
</div>"""))

    body = hero([("Home", "../"), ("Price reports", "./"), (f"Week of {monday:%b} {monday.day}", None)],
                esc(title), esc(summary),
                '<a class="btn light" href="../#compare">Compare all prices</a>')
    body += '<div class="wrap">' + "".join(parts) + "</div>"
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": summary,
          "datePublished": today.isoformat(), "author": {"@type": "Organization", "name": SITE_NAME},
          "publisher": {"@type": "Organization", "name": SITE_NAME}}
    write(f"reports/{slug_}.html", page(f"reports/{slug_}.html", f"{title} · {SITE_NAME}", summary, body, ld))

    reports.insert(0, {"slug": slug_, "title": title, "summary": summary, "published": today.isoformat()})
    with open(index_path, "w") as f:
        json.dump(reports, f, indent=1)
    print(f"New weekly report: reports/{slug_}.html")
    return reports


def build_report_index(reports):
    items = "".join(f"""<a class="latest" href="{r['slug']}.html"><span class="eyebrow">Published {esc(long_date(datetime.date.fromisoformat(r['published'])))}</span>
<h3>{esc(r['title'])}</h3><p>{esc(r['summary'])}</p></a>""" for r in reports)
    body = hero([("Home", "../"), ("Price reports", None)], "Weekly price reports",
                "Every Monday: the cheapest flower, vapes and concentrates in Salt Lake, the biggest sales, and what changed since last week.")
    body += f'<div class="wrap"><section><div class="rlist">{items or "<p class=note>The first report is on its way.</p>"}</div></section></div>'
    write("reports/index.html", page("reports/", f"Weekly Salt Lake Medical Cannabis Price Reports · {SITE_NAME}",
                                     "Weekly reports on medical cannabis prices and deals at Salt Lake area pharmacies.", body))


# ---------- category guides ----------

NOUNS = {"Flower": "flower", "Vapes": "vape cartridges and disposables", "Concentrates": "concentrates",
         "Edibles": "edibles", "Tinctures": "tinctures", "Topicals": "topicals"}


def build_guide(cat):
    items = of(cat)
    noun = NOUNS[cat]
    rel = f"prices/{slug(cat)}.html"
    title = f"Cheapest Medical Cannabis {cat} in Salt Lake City · {SITE_NAME}"
    if not items:
        body = hero([("Home", "../"), (f"{cat} prices", None)], f"Cheapest {noun} in Salt Lake", "No prices right now. Check back soon.")
        write(rel, page(rel, title, f"Compare {noun} prices at Salt Lake area pharmacies.", body))
        return

    low = cheapest(items, 1)[0]
    sale = [p for p in items if p["on_sale"]]
    stores_with = sorted({p["store"] for p in items}, key=lambda i: [s["id"] for s in STORES].index(i))
    gram_cat = cat in SIZES
    desc = (f"Compare {len(items):,} medical cannabis {noun} prices at {len(stores_with)} Salt Lake area pharmacies. "
            f"Lowest right now: {money(low['price'])} at {STORES_BY_ID[low['store']]['name']}. Updated several times a day.")
    intro = (f"We're tracking {len(items):,} {noun} at {len(stores_with)} Salt Lake area pharmacies. "
             f"{len(sale):,} are on sale right now. Updated {esc(long_date(NOW.date()))}.")
    body = hero([("Home", "../"), (f"{cat} prices", None)], f"Cheapest {esc(noun)} in Salt Lake", intro,
                f'<a class="btn light" href="../?cat={cat}#compare">Compare all {len(items):,} {esc(noun)}</a>')
    parts = []
    qa = []

    if gram_cat:
        rows = []
        for g in SIZES[cat]:
            sized = of(cat, g)
            if not sized:
                continue
            c = cheapest(sized, 1)[0]
            rows.append([f"<b>{fmt_g(g)}</b>", product_cell(c), store_cell(c["store"]), money(c["price"]), median_price(sized), f"{len(sized):,}"])
            qa.append((f"Where is the cheapest {fmt_g(g)} of {cat.lower()} in Salt Lake?",
                       f"Right now it's {c['name']} for {money(c['price'])} at {STORES_BY_ID[c['store']]['name']} in {STORES_BY_ID[c['store']]['city']}. "
                       f"The median {fmt_g(g)} price across {len(stores_with)} pharmacies is {median_price(sized)}."))
        if rows:
            parts.append(section("Lowest price by size", "The cheapest option at each common size, and the typical (median) price.",
                                 table([("Size", False), ("Cheapest", False), ("Pharmacy", False), ("Price", True), ("Median", True), ("Options", True)], rows)))

    rows = []
    for sid in stores_with:
        mine = [p for p in items if p["store"] == sid]
        ppg = median([p["price_per_gram"] for p in mine if p["price_per_gram"]])
        rows.append([store_cell(sid), f"{len(mine):,}", money(cheapest(mine, 1)[0]["price"]),
                     median_price(mine)] + ([money(round(ppg, 2)) if ppg else "–"] if gram_cat else []) + [f'{sum(p["on_sale"] for p in mine):,}'])
    headers = [("Pharmacy", False), ("Products", True), ("From", True), ("Median price", True)] + \
              ([("Median per gram", True)] if gram_cat else []) + [("On sale", True)]
    parts.append(section(f"{cat} prices by pharmacy", "", table(headers, rows)))

    if gram_cat:
        value = cheapest([p for p in items if p["price_per_gram"] and (p["grams"] or 0) >= 1], 12, "price_per_gram")
        parts.append(section("Best value per gram", "Lowest price per gram on 1g and larger.", grid(value)))
    else:
        parts.append(section(f"Lowest-priced {noun}", "", grid(cheapest(items, 12))))
    deals = biggest_deals(items, 8)
    if deals:
        parts.append(section(f"{cat} on sale", "The biggest discounts right now.", grid(deals)))

    qa.append((f"How many {noun} are on sale in Salt Lake right now?",
               f"{len(sale):,} of the {len(items):,} {noun} we track are on sale today."))
    qa.append(("How often are these prices updated?",
               "Most menus are checked automatically several times a day. A few are saved by hand about once a week; "
               "each pharmacy's page shows when its prices were last checked."))
    faq_html, faq_ld = faq(qa)
    parts.append(section("Questions", "", faq_html))
    body += '<div class="wrap">' + "".join(parts) + "</div>"
    write(rel, page(rel, title, desc, body, faq_ld))


# ---------- pharmacy pages ----------

def build_pharmacy(s):
    rel = f"pharmacy/{s['id']}.html"
    mine = [p for p in ALL_PRODUCTS if p["store"] == s["id"]]
    maps = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{s['name']} {s['address']}")
    buttons = (f'<a class="btn light" href="../?cat=&amp;store={esc(s["id"])}#compare">See all prices</a>' if mine else "") + \
              f'<a class="btn ghost" href="{esc(s["website"])}" target="_blank" rel="noopener">Website</a>' \
              f'<a class="btn ghost" href="{maps}" target="_blank" rel="noopener">Directions</a>'
    if mine:
        sale = sum(p["on_sale"] for p in mine)
        intro = (f"{esc(s['address'])}. {len(mine):,} products with prices, {sale:,} on sale. "
                 f"Prices checked {esc(checked(s))}.")
    else:
        intro = f"{esc(s['address'])}. Prices coming soon."
    body = hero([("Home", "../"), ("Pharmacies", "../#pharmacies"), (f"{s['name']} · {s['city']}", None)],
                f"{esc(s['name'])} {esc(s['city'])}: prices &amp; deals", intro, buttons)
    parts = []
    desc = f"Medical cannabis prices and deals at {s['name']} in {s['city']}, Utah, compared with other Utah pharmacies."
    if mine:
        rows = []
        for cat in GUIDES:
            here = of(cat, products=mine)
            if not here:
                continue
            area = of(cat)
            rows.append([f'<a href="../prices/{slug(cat)}.html">{cat}</a>', f"{len(here):,}", money(cheapest(here, 1)[0]["price"]),
                         median_price(here), median_price(area), f'{sum(p["on_sale"] for p in here):,}'])
        parts.append(section("Prices by category", f"How {esc(s['name'])} compares with the Salt Lake area median.",
                             table([("Category", False), ("Products", True), ("From", True), ("Median here", True),
                                    ("Salt Lake median", True), ("On sale", True)], rows)))
        eighth = of("Flower", 3.5, mine)
        if eighth:
            here_m, area_m = median([p["price"] for p in eighth]), median([p["price"] for p in of("Flower", 3.5)])
            diff = here_m - area_m
            compare = "about the same as" if abs(diff) < 1 else (f"{money(round(abs(diff), 2))} {'below' if diff < 0 else 'above'}")
            parts.append(section("Cheapest 3.5g flower here",
                                 f"The median eighth at {esc(s['name'])} is {money(round(here_m, 2))}, {compare} the Salt Lake median of {money(round(area_m, 2))}.",
                                 grid(cheapest(eighth, 8))))
        deals = biggest_deals(mine, 12)
        if deals:
            parts.append(section(f"On sale at {esc(s['name'])}", "The biggest discounts right now.", grid(deals)))
    parts.append(section("Visit", "", f"""<div class="prose"><p><b>{esc(s['name'])}</b><br>{esc(s['address'])}</p>
<p>A Utah medical cannabis card is required to shop. Hours, stock and prices change, so check the
<a class="link" href="{esc(s['website'])}" target="_blank" rel="noopener">pharmacy's website</a> before you go.</p></div>"""))
    body += '<div class="wrap">' + "".join(parts) + "</div>"
    write(rel, page(rel, f"{s['name']} Prices & Deals ({s['city']}, UT) · {SITE_NAME}", desc, body))


# ---------- news ----------

def news_item(a):
    when = datetime.datetime.fromisoformat(a["published"]).astimezone(TZ).date()
    return (f'<li><a href="{esc(a["url"])}" target="_blank" rel="noopener">{esc(a["title"])}</a>'
            f'<span>{esc(a["source"])} · {esc(long_date(when))}</span></li>')


def build_news():
    path = os.path.join(SITE, "news", "news.json")
    stories = []
    if os.path.exists(path):
        with open(path) as f:
            stories = json.load(f)
    inner = (f'<ul class="newslist">{"".join(news_item(a) for a in stories)}</ul>' if stories
             else '<p class="note">No stories yet. Check back soon.</p>')
    body = hero([("Home", "../"), ("News", None)], "Utah medical cannabis news",
                "Headlines about medical cannabis in Utah from local newsrooms, checked several times a day. "
                "Each headline links to the full story at the newsroom.")
    body += f'<div class="wrap"><section>{inner}</section></div>'
    write("news/index.html", page("news/", f"Utah Medical Cannabis News · {SITE_NAME}",
                                  "The latest Utah medical cannabis headlines from KSL, The Salt Lake Tribune, Deseret News, KUER and other local newsrooms.",
                                  body))
    return stories


# ---------- events ----------

def event_date(e):
    start = datetime.date.fromisoformat(e["start"])
    text = f"{start:%a}, {start:%b} {start.day}"
    if e["end"]:
        end = datetime.date.fromisoformat(e["end"])
        text += f" – {end:%b} {end.day}" if end.month != start.month else f"–{end.day}"
    return text + (f" · {e['time']}" if e["time"] else "")


def event_item(e):
    start = datetime.date.fromisoformat(e["start"])
    where = ", ".join(x for x in (e["location"], e["city"]) if x)
    return f"""<li class="event">
  <div class="cal"><span>{start:%b}</span><b>{start.day}</b></div>
  <div class="what">
    <span class="eyebrow">{esc(e["type"])}</span>
    <a href="{esc(e["url"])}" target="_blank" rel="noopener">{esc(e["title"])}</a>
    <span class="when">{esc(event_date(e))}</span>
    {f'<span class="where">{esc(where)}</span>' if where else ""}
    {f'<p>{esc(e["details"])}</p>' if e["details"] else ""}
  </div>
</li>"""


def build_events():
    path = os.path.join(SITE, "events", "events.json")
    events = []
    if os.path.exists(path):
        with open(path) as f:
            events = json.load(f)
    today = NOW.date().isoformat()
    upcoming = [e for e in events if (e["end"] or e["start"]) >= today]
    past = [e for e in events if (e["end"] or e["start"]) < today][::-1]
    inner = (f'<ul class="events">{"".join(event_item(e) for e in upcoming)}</ul>' if upcoming
             else '<p class="note">No upcoming events right now. Check back soon.</p>')
    body = hero([("Home", "../"), ("Events", None)], "Utah cannabis events",
                "Festivals, medical card clinics, pharmacy events and public meetings about medical cannabis in Utah. "
                "Details change, so confirm with the organizer before you go.")
    body += f'<div class="wrap"><section><div class="head"><div><h2>Upcoming</h2></div></div>{inner}</section>'
    if past:
        body += section("Recent", "", f'<ul class="events past">{"".join(event_item(e) for e in past)}</ul>')
    body += section("Know of an event?", "", """<div class="prose"><p>Festivals, card clinics, pharmacy parties, classes and
patient meetups in Utah all belong here. Events are added to <code>events/events.csv</code> in the site's GitHub repository.</p></div>""")
    body += "</div>"
    ld = [{"@context": "https://schema.org", "@type": "Event", "name": e["title"], "startDate": e["start"],
           **({"endDate": e["end"]} if e["end"] else {}), "description": e["details"], "url": e["url"],
           "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
           "location": {"@type": "Place", "name": e["location"] or e["city"],
                        "address": {"@type": "PostalAddress", "addressLocality": e["city"], "addressRegion": "UT"}}}
          for e in upcoming]
    write("events/index.html", page("events/", f"Utah Cannabis Events · {SITE_NAME}",
                                    "Upcoming medical cannabis events in Utah: festivals, medical card clinics, pharmacy events and public meetings.",
                                    body, ld or None))
    return upcoming


# ---------- sitemap ----------

def build_sitemap(reports, stories):
    today = NOW.date().isoformat()
    urls = [("", today), ("reports/", reports[0]["published"] if reports else today),
            ("news/", stories[0]["published"][:10] if stories else today), ("events/", today)]
    urls += [(f"prices/{slug(c)}.html", today) for c in GUIDES]
    urls += [(f"pharmacy/{s['id']}.html", today) for s in STORES if s.get("count")]
    urls += [(f"reports/{r['slug']}.html", r["published"]) for r in reports]
    entries = "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}</urlset>\n')
    write("robots.txt", f"User-agent: *\nDisallow: /save-prices.html\nSitemap: {SITE_URL}/sitemap.xml\n")


def main():
    global DATA, ALL_PRODUCTS, PRODUCTS, STORES, LOCAL_STORES, STORES_BY_ID, NOW
    with open(os.path.join(SITE, "data.json")) as f:
        DATA = json.load(f)
    ALL_PRODUCTS, STORES = DATA["products"], DATA["stores"]
    STORES_BY_ID = {s["id"]: s for s in STORES}
    # Reports and price guides are about Salt Lake; pharmacy pages and history cover every store.
    LOCAL_STORES = [s for s in STORES if s.get("area", HOME_AREA) == HOME_AREA]
    local_ids = {s["id"] for s in LOCAL_STORES}
    PRODUCTS = [p for p in ALL_PRODUCTS if p["store"] in local_ids]
    NOW = datetime.datetime.now(TZ)
    today = NOW.date()

    save_snapshot(today)
    reports = build_report(today)
    build_report_index(reports)
    for cat in GUIDES:
        build_guide(cat)
    for s in STORES:
        build_pharmacy(s)
    stories = build_news()
    build_events()
    build_sitemap(reports, stories)
    print(f"Built {len(GUIDES)} guides, {len(STORES)} pharmacy pages, {len(reports)} reports")


if __name__ == "__main__":
    main()
