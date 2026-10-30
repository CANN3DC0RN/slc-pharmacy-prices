# Utah Cannabis Prices

Compares medical cannabis prices and deals across Utah pharmacies, starting with the Salt Lake area, so cardholders can see where to shop before they go.

**Live site:** https://cann3dc0rn.github.io/slc-pharmacy-prices/

Every 4 hours, a free GitHub job collects the latest prices, rebuilds every page and republishes the site. Nothing needs to stay running on your computer.

## What's on the site

- **Home page:** search, category tiles, today's best deals, the latest news, and a full price comparison with filters (area, category, size, strain type, THC range, max price, brand, pharmacy, on sale, saved) and sorting (price either way, price per gram, biggest discount, THC either way). Visitors start on the Salt Lake area, and the site remembers the area they pick.
- **Saved items:** the heart on any product saves it in that visitor's browser. Saved items show "↓ $5 since you saved it" when the price drops. Nothing is sent anywhere.
- **Weekly price reports** (`/reports/`): published automatically every Monday. They cover the cheapest eighths, ounces, vapes and concentrates, how the pharmacies compare, the biggest sales, and, from the second week on, what changed since last week.
- **Price guides** (`/prices/flower.html`, vapes, concentrates, edibles, tinctures, topicals): the cheapest options by size, prices by pharmacy, best value per gram, current sales, and a short Q&A. Rebuilt every run.
- **Pharmacy pages** (`/pharmacy/<id>.html`): each pharmacy's prices compared with the Salt Lake typical price in every category, plus its sales and directions.
- **News** (`/news/`): Utah medical cannabis headlines from KSL, The Salt Lake Tribune, Deseret News, FOX 13, ABC4, KUER, Utah Public Radio and KPCW, checked every 4 hours. Only the headline, source and date are shown, linking to the newsroom.

Weekly reports and price guides cover the Salt Lake area. Pharmacy pages and the comparison cover all of Utah.
- **Sitemap and search tags** so Google and AI search tools can find and understand every page.

## Where prices come from

| Pharmacy | Area | How | How fresh |
|---|---|---|---|
| Dragonfly Wellness (Salt Lake City) | Salt Lake area | Automatic | Every 4 hours |
| WholesomeCo (West Bountiful) | Salt Lake area | Automatic | Every 4 hours |
| Beehive Farmacy (Salt Lake City) | Salt Lake area | "Save prices" bookmark | When you save it |
| The Forest (Murray) | Salt Lake area | "Save prices" bookmark | When you save it |
| Bloc Pharmacy (South Jordan) | Salt Lake area | "Save prices" bookmark | When you save it |
| Beehive Farmacy (Brigham City) | Northern Utah | "Save prices" bookmark | When you save it |
| Dragonfly Wellness (Price) | Central & Eastern Utah | Automatic | Every 4 hours |
| Bloc Pharmacy (St. George) | Southern Utah | "Save prices" bookmark | When you save it |
| Zion Medicinal (Cedar City) | Southern Utah | "Save prices" bookmark | When you save it |
| The Flower Shop (South Ogden, North Logan) | Northern Utah | Not yet: Jane menu, which blocks automatic reading and the bookmark doesn't support yet | Prices coming soon |
| Curaleaf (Lehi, Provo, Springville, Park City) | Utah County, Park City | Not yet: the menu requires accepting Curaleaf's terms first | Prices coming soon |

Beehive, The Forest, Bloc and Zion use Dutchie menus, which block automatic reading, so their prices are saved by hand.

If an automatic store's website changes and reading it fails, the site keeps showing that store's last good prices and labels them with their age.

## Your weekly routine: the "Save prices" bookmark

About once a week, which takes about 10 minutes for all six bookmark pharmacies (do just the Salt Lake four if you're short on time):

1. Open https://cann3dc0rn.github.io/slc-pharmacy-prices/save-prices.html (this page is hidden from search engines).
2. The first time only, drag the **Save prices** button onto your bookmarks bar.
3. Open each pharmacy's menu from the links on that page, wait for products to appear, and click **Save prices**. A file like `beehive-slc.csv` downloads.
4. Click **Open the upload page**, drag in the downloaded files, and click **Commit changes**. The site updates in about 3 minutes.

Each of these pharmacies shows "prices checked X days ago" on the site. Prices more than 14 days old are hidden automatically, so the site never shows old prices as current.

## Store-wide promos

For promos like "20% off flower Tuesdays", add a row to `partners/deals.csv` (columns: `store`, `title`, `details`, `expires` as YYYY-MM-DD). They appear on that pharmacy's card on the home page and drop off after they expire.

A pharmacy can also send its own price list: copy `partners/TEMPLATE.csv` to `partners/<store-id>.csv` (ids are in `stores.json`).

## When you buy a domain

1. Change `site_url` in `config.json` to the new address, for example `https://utahcannabisprices.com`. All links, the sitemap and the search tags follow it.
2. In the repository, go to **Settings → Pages → Custom domain**, enter the domain, and follow GitHub's instructions for your domain registrar. Hosting on GitHub Pages stays free; you can also move to another host later, since the whole site is the `site/` folder.
3. Submit `https://<your domain>/sitemap.xml` in Google Search Console and Bing Webmaster Tools.

## Counting visitors

The site is ready for [GoatCounter](https://www.goatcounter.com), a free, privacy-friendly visit counter that uses no cookies (so no cookie banner). Sign up, pick a code (for example `utahcannabisprices`), then put that code in two places: `goatcounter` in `config.json` and `GOATCOUNTER` near the top of the script in `site/index.html`. Visits show up on your GoatCounter dashboard.

## Contact button

To show the "Get listed free" button for pharmacies, set `CONTACT_EMAIL` near the top of the script in `site/index.html` to a dedicated email address.

## Checking that it's working

Open the **Actions** tab. Each "Update prices" run should have a green ✓. A red ✗ means every automatic store failed; the site keeps the last good prices until the next successful run. **Run workflow** on that page forces an update right away.

## What's in this repository

| Path | What it is |
|---|---|
| `stores.json` | The pharmacies on the site |
| `config.json` | Site name and address |
| `scraper/run.py` | Collects prices from every store into `site/data.json` |
| `scraper/build.py` | Builds reports, guides, pharmacy pages, the news page, history snapshots and the sitemap |
| `scraper/news.py` | Collects Utah cannabis headlines into `site/news/news.json` |
| `scraper/sources/` | One reader per price source |
| `partners/` | Hand-saved price files and store-wide promos |
| `history/` | One small price snapshot per day, for trends |
| `site/` | The website itself (`index.html`, `style.css`, `save-prices.html`, generated pages) |
| `.github/workflows/update-prices.yml` | The 4-hour schedule |

## Running it on your computer

```bash
python3 scraper/run.py
python3 scraper/build.py
python3 -m http.server 8787 --directory site
```

Then open http://localhost:8787.

## Adding another pharmacy later

Add it to `stores.json` with its `area`. If it uses a Dutchie menu, use `"source": "partner"` and add its Dutchie ID to the `STORES` list in `site/export.js` so the bookmark names the file correctly. Otherwise, a reader for its website can be added in `scraper/sources/`.
