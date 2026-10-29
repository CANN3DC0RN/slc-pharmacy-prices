"""Collect prices from every store and write site/data.json.

Usage: python3 scraper/run.py
If a store fails, its last good prices are kept and it is marked stale.
"""
import datetime
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "sources"))

import dragonfly  # noqa: E402
import partner  # noqa: E402
import wholesome  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "site", "data.json")
SOURCES = {"dragonfly": dragonfly.scrape, "wholesome": wholesome.scrape, "partner": partner.scrape}


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(ROOT, "stores.json")) as f:
        stores = json.load(f)

    previous = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            previous = json.load(f)
    prev_products = previous.get("products", [])
    prev_stores = {s["id"]: s for s in previous.get("stores", [])}

    products, failures = [], 0
    for store in stores:
        info = dict(store)
        try:
            items = SOURCES[store["source"]](store)
            if not items and store["source"] != "partner":
                raise RuntimeError("no products found")
            info.update(updated=now if items else None, ok=True, count=len(items))
            print(f"{store['name']}: {len(items)} products")
        except Exception:
            failures += 1
            traceback.print_exc()
            items = [p for p in prev_products if p["store"] == store["id"]]
            old = prev_stores.get(store["id"], {})
            info.update(updated=old.get("updated"), ok=False, count=len(items))
            print(f"{store['name']}: FAILED, keeping {len(items)} older products")
        products.extend(items)
        info.pop("source")
        info["automatic"] = store["source"] != "partner"
        prev_stores[store["id"]] = info

    data = {
        "generated": now,
        "stores": [prev_stores[s["id"]] for s in stores],
        "deals": partner.store_deals(),
        "products": products,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Wrote {len(products)} products to {OUT}")
    # Fail the run only if every automatic source broke, so the schedule flags it.
    if failures and failures == sum(1 for s in stores if s["source"] != "partner"):
        sys.exit(1)


if __name__ == "__main__":
    main()
