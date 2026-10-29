"""Partner stores: prices come from partners/<store-id>.csv.

The file is either sent by the pharmacy or saved with the "Save prices" bookmark
(site/export.js). Bookmark files carry a `collected` date; once that's older than
STALE_DAYS the prices are dropped so the site never shows old prices as current.
"""
import csv
import datetime
import os

from common import make_product, normalize_category, parse_thc

PARTNER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "partners")
STALE_DAYS = 14


def _today():
    return datetime.date.today().isoformat()


def _expired(row):
    exp = (row.get("expires") or "").strip()
    return bool(exp) and exp < _today()


def _rows(store):
    path = os.path.join(PARTNER_DIR, f"{store['id']}.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def collected_on(store):
    """Date the newest prices in this store's file were saved, or None if undated."""
    dates = [(r.get("collected") or "").strip() for r in _rows(store)]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def is_stale(store):
    when = collected_on(store)
    if not when:
        return False
    cutoff = datetime.date.today() - datetime.timedelta(days=STALE_DAYS)
    return when < cutoff.isoformat()


def scrape(store):
    if is_stale(store):
        return []
    products = []
    for row in _rows(store):
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
            strain_type=row.get("strain_type"),
            image=row.get("image"),
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
