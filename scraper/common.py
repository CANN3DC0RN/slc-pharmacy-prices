"""Shared helpers: polite HTTP fetching and product normalization."""
import os
import re
import ssl
import time
import urllib.request

USER_AGENT = (
    "UtahPharmacyPriceCheck/0.1 (price comparison for Utah medical cannabis patients)"
)

# macOS python.org builds ship without a CA bundle; fall back to the system one.
_ctx = ssl.create_default_context()
if not _ctx.get_ca_certs() and os.path.exists("/etc/ssl/cert.pem"):
    _ctx = ssl.create_default_context(cafile="/etc/ssl/cert.pem")

REQUEST_DELAY = 1.5  # seconds between requests to the same site


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45, context=_ctx) as r:
        body = r.read().decode("utf-8", "replace")
    time.sleep(REQUEST_DELAY)
    return body


CATEGORIES = ["Flower", "Vapes", "Concentrates", "Edibles", "Tinctures", "Topicals", "Accessories"]

# Checked in order, so the product form ("gummy", "tincture", "cart") wins over
# the extraction words ("rosin", "resin", "diamond") that show up in every category.
_CATEGORY_WORDS = [
    ("Accessories", ["unmedicated", "accessor", "grinder", "battery", "batteries", "glassware"]),
    ("Topicals", ["topical", "lotion", "balm", "cream", "transdermal", "non-edible", "patch", "roll-on"]),
    ("Vapes", ["vape", "vaporizer", "cartridge", "cartpen", "cart ", "aio", "all-in-one", "disposable", "pod"]),
    ("Edibles", ["edible", "gummy", "gummies", "chew", "chocolate", "beverage", "drink", "tablet", "capsule", "lozenge", "mint "]),
    ("Tinctures", ["tincture", "oral", "syringe", "rso", "spray"]),
    ("Concentrates", ["concentrate", "badder", "budder", "rosin", "resin", "shatter", "wax", "diamond", "sauce", "sugar", "crumble", "hash", "distillate"]),
    ("Flower", ["flower", "pre-roll", "preroll", "shake", "smalls", "popcorn"]),
]


def _match(text):
    text = f" {text.lower()} "
    for cat, words in _CATEGORY_WORDS:
        if any(w in text for w in words):
            return cat
    return None


# Stores file infused products loosely (Dragonfly puts tinctures under "Infused
# Edible"), so for those catch-all categories an explicit form in the name wins.
# Never applied to Flower/Vapes, where strain names like "Gummy Bears" would mislead.
_NAME_OVERRIDES = [
    ("Topicals", ["transdermal", "patch", "balm", "salve", "lotion"]),
    ("Tinctures", ["tincture"]),
    ("Vapes", ["vape", "cartridge", "all-in-one", "aio", "disposable"]),
]


def normalize_category(store_category, *other_hints):
    """Map a store's category (and, failing that, product name etc.) to ours."""
    cat = _match(store_category or "")
    names = " ".join(h for h in other_hints if h)
    if cat in ("Edibles", "Concentrates"):
        text = f" {names.lower()} "
        for override, words in _NAME_OVERRIDES:
            if any(w in text for w in words):
                return override
    return cat or _match(names) or "Accessories"


def parse_grams(*texts):
    """Find a size like '3.5g', '1 g', '1/8 oz' and return grams (or None)."""
    for t in texts:
        if not t:
            continue
        t = t.lower()
        m = re.search(r"(\d+(?:\.\d+)?)\s*(mg|g|gram|grams)\b", t)
        if m and m.group(2) != "mg":
            return float(m.group(1))
        m = re.search(r"(\d+)\s*/\s*(\d+)\s*oz", t)
        if m:
            return round(28.35 * int(m.group(1)) / int(m.group(2)), 2)
        m = re.search(r"(\d+(?:\.\d+)?)\s*oz\b", t)
        if m:
            return round(28.35 * float(m.group(1)), 2)
    return None


def parse_thc(*texts):
    for t in texts:
        if not t:
            continue
        m = re.search(r"THC[^0-9]{0,6}(\d+(?:\.\d+)?)\s*%", t, re.I)
        if m:
            return float(m.group(1))
    return None


def make_product(store_id, name, brand, category, price, regular_price=None,
                 size=None, url=None, thc=None, deal=None, strain_type=None, image=None):
    price = round(float(price), 2)
    regular = round(float(regular_price), 2) if regular_price else price
    # Per-gram pricing only means something for smokable/vapeable product.
    grams = parse_grams(size, name) if category in ("Flower", "Vapes", "Concentrates") else None
    return {
        "store": store_id,
        "name": name.strip(),
        "brand": (brand or "").strip(),
        "category": category,
        "size": size or "",
        "grams": grams,
        "price": price,
        "regular_price": regular,
        "on_sale": regular - price >= 0.01,
        "deal": deal or "",
        "price_per_gram": round(price / grams, 2) if grams else None,
        "thc": thc,
        "strain_type": (strain_type or "").title(),
        "url": url or "",
        "image": image or "",
    }
