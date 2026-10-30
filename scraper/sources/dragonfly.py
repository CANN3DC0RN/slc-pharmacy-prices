"""Dragonfly Wellness: the /products page embeds the full catalog as JSON."""
import json
import re

from common import fetch, make_product, normalize_category, parse_thc

BASE = "https://dragonflywellness.com"


def _rsc_text(html):
    # Next.js streams page data as self.__next_f.push([1,"..."]) string chunks.
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    return "".join(json.loads('"' + c + '"') for c in chunks)


def scrape(store):
    base = store.get("base", BASE)  # each Dragonfly location has its own site
    text = _rsc_text(fetch(base + "/products"))
    key = '"serverProducts":'
    i = text.find(key)
    if i < 0:
        raise RuntimeError("Dragonfly page layout changed: serverProducts not found")
    items, _ = json.JSONDecoder().raw_decode(text[i + len(key):])

    products = []
    for p in items:
        if not p.get("availableOnline", True) or not p.get("price"):
            continue
        regular = float(p["price"])
        discount = float(p.get("discount") or 0)
        potency = " ".join(p.get("potencyStrings") or [])
        products.append(make_product(
            store["id"],
            name=p["name"],
            brand=p.get("brandName"),
            category=normalize_category(p.get("category"), p.get("subcategory"), p["name"]),
            price=regular - discount,
            regular_price=regular,
            size=p.get("weight"),
            url=f"{base}/products/{p['urlName']}",
            thc=parse_thc(potency),
            deal=f"{round(100 * discount / regular)}% off" if discount else "",
            strain_type=p.get("dominance"),
            # imageURL is a signed link that expires in 3h; backupImages are permanent.
            image=(p.get("backupImages") or [None])[0],
        ))
    return products
