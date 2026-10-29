# SLC Pharmacy Prices

Compares medical cannabis prices and deals across Salt Lake area pharmacies.
Every 4 hours, a free GitHub job collects the latest prices and republishes the site. Nothing needs to stay running on your computer.

## How prices get in

| Pharmacy | How |
|---|---|
| Dragonfly Wellness (SLC) | Automatic, read from their public product page |
| WholesomeCo (West Bountiful) | Automatic, read from their public shop pages |
| Beehive Farmacy (SLC), The Forest (Murray), Bloc (South Jordan) | Partner: the pharmacy sends a spreadsheet, see below |

If an automatic store's website changes and the read fails, the site keeps showing that store's last good prices and labels them "last good …".

## Saving prices by hand (the "Save prices" bookmark)

Dutchie blocks automatic reading, so for Beehive, The Forest and Bloc you save their prices while you browse:
open `save-prices.html` on the live site and follow the three steps (add bookmark → click it on the menu → upload the file).
Hand-saved prices show "checked X days ago", and they're hidden once they're more than 14 days old.

## Adding a partner pharmacy's prices

1. Copy `partners/TEMPLATE.csv` to `partners/<store-id>.csv` (ids are in `stores.json`, e.g. `beehive-slc.csv`).
2. Fill in one row per product. `sale_price`, `deal`, `thc`, `url` and `expires` (YYYY-MM-DD) are optional.
3. For store-wide promos like "20% off flower Tuesdays", add a row to `partners/deals.csv`.

Edit the file on github.com and save it. The site rebuilds within a few minutes.

## Going live for free (GitHub Pages)

1. Create a free account at github.com.
2. Create a new **public** repository and upload everything in this folder, including the hidden `.github` folder.
3. In the repository, open **Settings → Pages** and set **Source** to **GitHub Actions**.
4. Open **Actions → Update prices → Run workflow**.
5. When it finishes, the site is at `https://<your-username>.github.io/<repo-name>/`.

After that it updates itself every 4 hours. Check **Actions** for the run history: a red ✗ means every automatic store failed.

Later, to use your own domain, go to **Settings → Pages → Custom domain**. Hosting stays free.

## Running it on your computer

```bash
python3 scraper/run.py
python3 -m http.server 8787 --directory site
```

Then open http://localhost:8787.

## Adding another pharmacy later

Add it to `stores.json`. Use `"source": "partner"` unless someone writes a reader for that store in `scraper/sources/`.
