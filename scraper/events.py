"""Collect Utah cannabis events into site/events/events.json.

Usage: python3 scraper/events.py
Sources:
  - events/events.csv: festivals, card clinics and other events added by hand
  - the state Medical Cannabis Policy Advisory Board's public meeting notices
  - TownLift's community events calendar (searched for cannabis events)
Upcoming events are kept, plus recent past ones so the page isn't empty between events.
"""
import csv
import datetime
import html
import json
import os
import re
import sys
import urllib.parse
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fetch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "events", "events.csv")
OUT = os.path.join(ROOT, "site", "events", "events.json")
TZ = zoneinfo.ZoneInfo("America/Denver")
KEEP_PAST_DAYS = 120

PMN = "https://www.utah.gov"
BOARD_PAGE = PMN + "/pmn/sitemap/publicbody/8241.html"  # Medical Cannabis Policy Advisory Board
TOWNLIFT = "https://townlift.com/wp-json/tribe/events/v1/events"
TOPIC = re.compile(r"\b(cannabis|marijuana|medical card|med card|thc|cbd|420|4/20)\b", re.I)


def _text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "\n", fragment))


def _lines(page):
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    return [l.strip() for l in _text(page).splitlines() if l.strip()]


def _after(lines, label):
    """The line after a label on a public notice page."""
    try:
        return lines[lines.index(label) + 1]
    except (ValueError, IndexError):
        return ""


def _when(raw):
    return datetime.datetime.strptime(raw, "%B %d, %Y %I:%M %p")


def _clock(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


def from_csv():
    if not os.path.exists(CSV):
        return []
    with open(CSV, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    keys = ("title", "start", "end", "time", "location", "city", "url", "type", "details")
    return [{k: (r.get(k) or "").strip() for k in keys} for r in rows if r.get("title") and r.get("start")]


def from_board(today):
    """Upcoming board meetings. Each has its own notice page with the time and place."""
    page = fetch(BOARD_PAGE)
    events = []
    for path, title in re.findall(r'href="(/pmn/sitemap/notice/\d+\.html)">([^<]+)</a>', page):
        title = html.unescape(title).strip()
        m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", title)
        if not m or datetime.datetime.strptime(m.group(1), "%B %d, %Y").date() < today:
            continue
        lines = _lines(fetch(PMN + path))
        start, end = _after(lines, "Event Start Date & Time"), _after(lines, "Event End Date & Time")
        try:
            s, e = _when(start), _when(end) if end else None
        except ValueError:
            continue
        i = lines.index("Meeting Location") if "Meeting Location" in lines else -1
        place = lines[i + 1:i + 4] if i >= 0 else []
        place = [p for p in place if not p.startswith("Show in")]
        events.append({
            "title": "Medical Cannabis Policy Advisory Board meeting",
            "start": s.date().isoformat(),
            "end": "",
            "time": f"{_clock(s)} – {_clock(e)}" if e else _clock(s),
            "location": ", ".join(place[:2]),
            "city": re.sub(r",? UT.*", "", place[2]) if len(place) > 2 else "",
            "url": PMN + path,
            "type": "Public meeting",
            "details": "The state board that advises on Utah's medical cannabis rules. Open to the public, in person or online; "
                       "the agenda and online link are on the notice.",
        })
    return events


def from_townlift():
    events = {}
    for term in ("cannabis", "marijuana", "medical card"):
        url = TOWNLIFT + "?" + urllib.parse.urlencode({"search": term, "per_page": 50})
        for e in json.loads(fetch(url)).get("events", []):
            desc = _text(e.get("description") or "")
            if not TOPIC.search(e["title"] + " " + desc):
                continue
            s = datetime.datetime.fromisoformat(e["start_date"])
            venue = e.get("venue") if isinstance(e.get("venue"), dict) else {}
            events[e["url"]] = {
                "title": html.unescape(e["title"]),
                "start": s.date().isoformat(),
                "end": e["end_date"][:10] if e.get("end_date", "")[:10] != s.date().isoformat() else "",
                "time": "" if e.get("all_day") else _clock(s),
                "location": html.unescape(venue.get("venue", "")),
                "city": venue.get("city", ""),
                "url": e["url"],
                "type": "Event",
                "details": re.sub(r"\s+", " ", desc).strip()[:220],
            }
    return list(events.values())


def main():
    today = datetime.datetime.now(TZ).date()
    events = from_csv()
    for name, source in (("Board meetings", lambda: from_board(today)), ("TownLift", from_townlift)):
        try:
            found = source()
            print(f"{name}: {len(found)} events")
            events += found
        except Exception as e:  # one source being down shouldn't stop the rest
            print(f"{name}: skipped ({e.__class__.__name__}: {e})")

    cutoff = (today - datetime.timedelta(days=KEEP_PAST_DAYS)).isoformat()
    seen, kept = set(), []
    for e in sorted(events, key=lambda e: e["start"]):
        k = (e["title"].lower(), e["start"])
        if k in seen or (e["end"] or e["start"]) < cutoff:
            continue
        seen.add(k)
        kept.append(e)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(kept, f, indent=1)
    upcoming = sum(1 for e in kept if (e["end"] or e["start"]) >= today.isoformat())
    print(f"Events: {upcoming} upcoming, {len(kept) - upcoming} recent")


if __name__ == "__main__":
    main()
