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
        for raw in re.findall(r'data-analytics-rudderstack-payload-value="([^"]+)"', page):
            p = json.loads(html.unescape(raw))
            if "product_id" not in p or "price" not in p:
                continue
            regular = float(p["price"])
            discount = float(p.get("discount") or 0)
            cats = p.get("categories") or []
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
            )
        nxt = re.search(r'href="(/shop\?after=[^"]+)"', page)
        if not nxt:
            break
        url = BASE + html.unescape(nxt.group(1))
    return list(products.values())
