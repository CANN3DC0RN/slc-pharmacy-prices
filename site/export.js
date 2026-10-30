// "Save prices" bookmark: run on a Dutchie menu page while you're viewing it.
// Asks the menu for every product (the same request the page makes when you
// browse a category) and downloads a CSV for the site's partners/ folder.
(async () => {
  const STORES = {
    "5ea72292b6c1d3012f5eb694": "beehive-slc",
    "69cd22a84028784c6f7ecf8a": "the-forest-murray",
    "6035916f516b4e34776f4dc5": "bloc-south-jordan",
    "603fbfd8751ff0189db9b778": "beehive-brigham-city",
    "60359153c590f500e234ba43": "bloc-st-george",
    "60b0455896ed3f00b4e88396": "zion-cedar-city",
  };
  const KNOWN_HASH = "cfbda410fd502c77b467a174a666b809bec1e61c70ee7f75de1aff7440b59bf4";

  const calls = performance.getEntriesByType("resource").map((e) => e.name).filter((n) => n.includes("graphql"));
  let dispensaryId = null;
  for (const c of calls) {
    const m = decodeURIComponent(c).match(/"(?:dispensaryId|cNameOrID)":"([a-f0-9]{24})"/);
    if (m) { dispensaryId = m[1]; break; }
  }
  if (!dispensaryId) {
    const m = location.pathname.match(/\/embedded-menu\/([a-f0-9]{24})/);
    if (m) dispensaryId = m[1];
  }
  if (!calls.length) {
    // On a pharmacy's own website the Dutchie menu sits in a frame the bookmark can't read,
    // so send them to the same menu on its own page.
    const embed = [...performance.getEntriesByType("resource").map((e) => e.name), ...[...document.querySelectorAll("iframe")].map((f) => f.src)]
      .map((u) => u.match(/embedded-menu\/([a-f0-9]{24})/)).find(Boolean);
    if (embed) {
      alert("Save prices: this menu is inside the pharmacy's website, where it can't be read. Opening the full menu now. When products show, click Save prices again.");
      location.href = "https://dutchie.com/embedded-menu/" + embed[1];
      return;
    }
  }
  if (!dispensaryId || !calls.length) {
    alert("Save prices: open the pharmacy's online menu (the page with products on it) first, then click this again.");
    return;
  }
  const endpoint = new URL(calls[0]);
  const api = endpoint.origin + endpoint.pathname;
  const fp = calls.find((c) => c.includes("operationName=FilteredProducts"));
  const hash = fp ? JSON.parse(new URL(fp).searchParams.get("extensions")).persistedQuery.sha256Hash : KNOWN_HASH;
  const base = location.origin + location.pathname.split("/").slice(0, 3).join("/");

  const banner = document.createElement("div");
  banner.style.cssText = "position:fixed;z-index:2147483647;top:16px;right:16px;background:#0f3d2a;color:#fff;font:600 15px system-ui;padding:14px 18px;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.3)";
  banner.textContent = "Saving prices…";
  document.body.appendChild(banner);

  async function page(n, pricingType) {
    const variables = {
      includeEnterpriseSpecials: false,
      productsFilter: {
        productIds: [], dispensaryId, pricingType, strainTypes: [], subcategories: [], Status: "Active", types: [],
        useCache: false, isDefaultSort: true, sortBy: "featuredProducts", sortDirection: 1, bypassOnlineThresholds: false,
        ignoreQuantityThresholds: false, isKioskMenu: false, removeProductsBelowOptionThresholds: true,
        platformType: "ONLINE_MENU", preOrderType: null,
      },
      page: n,
      perPage: 100,
    };
    const url = api + "?" + new URLSearchParams({
      operationName: "FilteredProducts",
      variables: JSON.stringify(variables),
      extensions: JSON.stringify({ persistedQuery: { version: 1, sha256Hash: hash } }),
    });
    const r = await fetch(url, { headers: { "content-type": "application/json", "apollographql-client-name": "Marketplace (production)" }, credentials: "include" });
    const d = await r.json();
    if (!d.data) throw new Error(JSON.stringify(d.errors || d).slice(0, 200));
    return d.data.filteredProducts;
  }

  try {
    const products = [];
    let first = await page(0, "med");
    const pricingType = first.products.length ? "med" : "rec";
    if (!first.products.length) first = await page(0, "rec");
    products.push(...first.products);
    for (let n = 1; n < (first.queryInfo?.totalPages || 1); n++) {
      banner.textContent = `Saving prices… ${products.length}`;
      await new Promise((r) => setTimeout(r, 400)); // go easy on their menu
      products.push(...(await page(n, pricingType)).products);
    }

    const today = new Date().toISOString().slice(0, 10);
    const rows = [];
    for (const p of products) {
      const opts = p.Options || [];
      const reg = (pricingType === "med" ? p.medicalPrices : p.recPrices) || p.Prices || [];
      const sale = (pricingType === "med" ? p.medicalSpecialPrices : p.recSpecialPrices) || [];
      const thc = p.THCContent?.unit === "PERCENTAGE" && p.THCContent.range?.length ? Math.max(...p.THCContent.range) : "";
      const deal = p.specialData?.saleSpecials?.[0]?.specialName || "";
      opts.forEach((opt, i) => {
        const price = reg[i] ?? p.Prices?.[i];
        if (price == null) return;
        const s = sale[i] && sale[i] < price ? sale[i] : "";
        rows.push({
          name: opts.length > 1 ? `${p.Name} (${opt})` : p.Name,
          brand: p.brandName || "",
          category: [p.type, p.subcategory].filter(Boolean).join(" "),
          size: opt,
          price,
          sale_price: s,
          deal: s ? deal : "",
          thc,
          url: `${base}/product/${p.cName}`,
          expires: "",
          image: p.Image || "",
          strain_type: p.strainType && p.strainType !== "N/A" ? p.strainType : "",
          collected: today,
        });
      });
    }

    const cols = ["name", "brand", "category", "size", "price", "sale_price", "deal", "thc", "url", "expires", "image", "strain_type", "collected"];
    const cell = (v) => (/[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
    const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => cell(r[c])).join(","))].join("\n");
    const storeId = STORES[dispensaryId] || `dutchie-${dispensaryId}`;
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
      download: `${storeId}.csv`,
    });
    document.body.appendChild(a);
    a.click();
    a.remove();
    banner.textContent = `Saved ${rows.length} prices to ${storeId}.csv`;
    if (!STORES[dispensaryId]) banner.textContent += " (new store: ask Claude to add it)";
    setTimeout(() => banner.remove(), 6000);
  } catch (e) {
    banner.style.background = "#9a3412";
    banner.textContent = "Couldn't save prices: " + e.message;
    setTimeout(() => banner.remove(), 10000);
  }
})();
