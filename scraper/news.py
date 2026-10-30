"""Collect Utah cannabis news headlines into site/news/news.json.

Usage: python3 scraper/news.py
Reads the public RSS feeds of Utah newsrooms, keeps stories about cannabis,
and adds them to a running archive. Only the headline, source, date and link
are kept; readers click through to the newsroom for the story.
"""
import datetime
import email.utils
import html
import json
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fetch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "news", "news.json")
KEEP = 300  # stories in the archive

FEEDS = [
    ("The Salt Lake Tribune", "https://www.sltrib.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("KSL", "https://www.ksl.com/rss/news"),
    ("Deseret News", "https://www.deseret.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("FOX 13", "https://www.fox13now.com/news/local-news.rss"),
    ("ABC4", "https://www.abc4.com/feed/"),
    ("KUER", "https://www.kuer.org/news.rss"),
    ("KUER", "https://www.kuer.org/tags/medical-cannabis.rss"),  # topic feeds reach back further
    ("Utah Public Radio", "https://www.upr.org/news.rss"),
    ("Utah Public Radio", "https://www.upr.org/tags/medical-cannabis.rss"),
    ("KPCW", "https://www.kpcw.org/news.rss"),
    # Runs Utah's medical cannabis program since 2026
    ("Utah Department of Agriculture and Food", "https://ag.utah.gov/news/feed/"),
]

# Whole words only, so "THC" doesn't match inside other words.
TOPIC = re.compile(r"\b(cannabis|marijuana|medical pot|thc|cbd|hemp|dispensar(y|ies)|cannabis pharmac(y|ies))\b", re.I)


def _text(item, tag):
    el = item.find(tag)
    return html.unescape(re.sub(r"<[^>]+>", " ", el.text or "")).strip() if el is not None and el.text else ""


def _date(item):
    raw = _text(item, "pubDate")
    try:
        return email.utils.parsedate_to_datetime(raw).astimezone(datetime.timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def _clean_url(url):
    u = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(u.query) if not k.startswith("utm_")]
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(query), ""))


def _title_key(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def collect():
    found = []
    for source, url in FEEDS:
        try:
            root = ET.fromstring(fetch(url).encode())
        except Exception as e:  # one newsroom being down shouldn't stop the rest
            print(f"{source}: skipped ({e.__class__.__name__})")
            continue
        n = 0
        for item in root.iter("item"):
            title, link = _text(item, "title"), _text(item, "link")
            if not (title and link) or not TOPIC.search(title + " " + _text(item, "description")):
                continue
            found.append({"title": title, "url": _clean_url(link), "source": source, "published": _date(item)})
            n += 1
        print(f"{source}: {n} cannabis stories")
    return found


def main():
    archive = []
    if os.path.exists(OUT):
        with open(OUT) as f:
            archive = json.load(f)
    seen_urls = {a["url"] for a in archive}
    seen_titles = {_title_key(a["title"]) for a in archive}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    added = 0
    for story in collect():
        if story["url"] in seen_urls or _title_key(story["title"]) in seen_titles:
            continue
        story["published"] = story["published"] or now
        archive.append(story)
        seen_urls.add(story["url"])
        seen_titles.add(_title_key(story["title"]))
        added += 1
    archive.sort(key=lambda a: a["published"], reverse=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(archive[:KEEP], f, indent=1)
    print(f"News: {added} new, {min(len(archive), KEEP)} in archive")


if __name__ == "__main__":
    main()
