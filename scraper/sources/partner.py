"""Partner stores: prices come from partners/<store-id>.csv, supplied by the pharmacy."""
import csv
import datetime
import os

from common import make_product, normalize_category, parse_thc

PARTNER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "partners")


def _expired(row):
    exp = (row.get("expires") or "").strip()
    return bool(exp) and exp < datetime.date.today().isoformat()


def scrape(store):
    path = os.path.join(PARTNER_DIR, f"{store['id']}.csv")
    if not os.path.exists(path):
        return []
    products = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not (row.get("name") and row.get("price")) or _expired(row):
                continue
            regular = float(row["price"])
            sale = float(row["sale_price"]) if (row.get("sale_price") or "").strip() else regular
            products.append(make_product(
                store["id"],
                name=row["name"],
                brand=row.get("brand"),
                category=normalize_category(row.get("category"), row["name"]),
                price=sale,
                regular_price=regular,
                size=row.get("size"),
                url=row.get("url") or store["website"],
                thc=parse_thc("THC " + row["thc"] + "%") if (row.get("thc") or "").strip() else None,
                deal=row.get("deal"),
            ))
    return products


def store_deals():
    """Store-wide promos (e.g. '20% off flower Tuesdays') from partners/deals.csv."""
    path = os.path.join(PARTNER_DIR, "deals.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [
            {k: (row.get(k) or "").strip() for k in ("store", "title", "details", "expires")}
            for row in csv.DictReader(f)
            if row.get("store") and row.get("title") and not _expired(row)
        ]
