"""WholesomeCo: product cards carry a JSON analytics payload; pages chain via ?after= cursors."""
import html
import json
import re

from common import fetch, make_product, normalize_category

BASE = "https://www.wholesome.co"
MAX_PAGES = 120  # safety stop (12 products per page)


def scrape(store):
    products = {}
    url = BASE + "/shop"
    for _ in range(MAX_PAGES):
        page = fetch(url)
        matches = list(re.finditer(r'data-analytics-rudderstack-payload-value="([^"]+)"', page))
        for i, m in enumerate(matches):
            p = json.loads(html.unescape(m.group(1)))
            if "product_id" not in p or "price" not in p:
                continue
            # The THC and strain badges sit after a card's payload and before the next card's.
            card = page[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(page)]
            thc = re.search(r'cannabinoidBadge-label">THC</span><span class="cannabinoidBadge-amount">([\d.]+)%', card)
            strain = re.search(r'aria-label="(Indica|Sativa|Hybrid)"', card)
            regular = float(p["price"])
            discount = float(p.get("discount") or 0)
            cats = p.get("categories") or []
            if p["product_id"] in products and not thc:
                continue
            products[p["product_id"]] = make_product(
                store["id"],
                name=p["name"],
                brand=p.get("brand"),
                category=normalize_category(" ".join(cats), p["name"]),
                price=regular - discount,
                regular_price=regular,
                size=p.get("variant"),
                url=p.get("url"),
                deal=f"{round(100 * discount / regular)}% off" if discount else "",
                image=p.get("image_url"),
                thc=float(thc.group(1)) if thc else None,
                strain_type=strain.group(1) if strain else None,
            )
        nxt = re.search(r'href="(/shop\?after=[^"]+)"', page)
        if not nxt:
            break
        url = BASE + html.unescape(nxt.group(1))
    return list(products.values())
