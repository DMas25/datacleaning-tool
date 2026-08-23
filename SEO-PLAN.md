# SEO Plan — coltradata.com
**Date:** 2026-08-21  
**Based on:** AUDIT.md findings + GSC data 18 Jul – 2 Aug 2026  
**Constraint:** No URL changes. British English. Match existing HTML/CSS conventions. One commit per logical change.

---

## Priority Key
- **H** = High — do first, material ranking or conversion impact
- **M** = Medium — do next, compounding benefit
- **L** = Low — housekeeping, marginal gain

---

## Action List

### 1. Fix sitemap.xml — add data-analysts.html
**Priority:** H | **Effort:** 5 minutes

Add the missing entry to sitemap.xml. This page has been indexed by internal links for ~2 weeks with no sitemap signal. Fixing this tells Google to crawl and prioritise it.

```xml
<url>
  <loc>https://coltradata.com/data-analysts.html</loc>
  <lastmod>2026-08-21</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.8</priority>
</url>
```

**Commit message:** `seo: add data-analysts.html to sitemap.xml`

---

### 2. Add canonical + OG/Twitter tags to 10 pages
**Priority:** H | **Effort:** 30-45 minutes

The 10 pages missing OG tags are invisible on LinkedIn — they render as a plain URL with no image, no title, no description. Since LinkedIn is the only active promotional channel, every post linking to these pages is underperforming.

Pages to update (in this order — most likely to be linked on LinkedIn first):
1. bookkeepers.html
2. smes.html
3. finance-teams.html
4. consultants.html
5. data-analysts.html
6. healthcare.html
7. importers-exporters.html
8. logistics.html
9. researchers.html
10. pricing.html

For each page, add immediately after `<link rel="icon" ...>`:

```html
<link rel="canonical" href="https://coltradata.com/[PAGE].html" />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://coltradata.com/[PAGE].html" />
<meta property="og:title" content="[SAME AS TITLE TAG]" />
<meta property="og:description" content="[SAME AS META DESCRIPTION]" />
<meta property="og:image" content="https://coltradata.com/assets/logo.png" />
<meta property="og:site_name" content="ColtraDataAi" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="[SAME AS TITLE TAG]" />
<meta name="twitter:description" content="[SAME AS META DESCRIPTION]" />
```

Also add canonical to index.html: `<link rel="canonical" href="https://coltradata.com/" />`

**Commit message:** `seo: add canonical and OG/Twitter meta tags to all use-case pages`

---

### 3. Fix pricing.html title tag
**Priority:** H | **Effort:** 2 minutes

Current: `Pricing: ColtraDataAi` (20 chars — no keyword, no value prop)  
Replace with: `ColtraDataAi Pricing | Data Cleaning Plans from £29/month`

Also add JSON-LD WebPage schema and OG tags (covered by action 2 above).

**Commit message:** `seo: improve pricing.html title tag`

---

### 4. Create /hospitality-reporting-tool.html
**Priority:** H | **Effort:** 2-3 hours

This is the single highest-ROI content action available. "hospitality reporting tool" sits at position 17.6 with 5 impressions and zero clicks — one good page away from a page-1 position.

**Page type:** Commercial/product page  
**Target query:** hospitality reporting tool  
**Supporting queries:** hotel reporting tool, hospitality kpi reporting, venue data reporting tool, restaurant reporting software  
**Minimum length:** 1,200 words of body copy  
**Structure:**
- H1: e.g. "The Hospitality Reporting Tool That Cleans Your Data First"
- H2: What it does / how it works / who it is for / pricing / FAQ (3-5 questions)
- Include a comparison table vs manual reporting process
- Add soft CTA to Free Health Check
- Full OG + canonical + JSON-LD WebPage + FAQPage
- Link back to /hospitality.html as parent hub
- Link to /how-to-report-hospitality-data.html as the companion informational guide

**Add to sitemap.xml after creation.**

**Commit message:** `content: add hospitality-reporting-tool.html commercial page`

---

### 5. Create /how-to-report-hospitality-data.html
**Priority:** H | **Effort:** 2-3 hours

"how to report hospitality data" sits at position 19.5 with 4 impressions and zero clicks. Informational intent — this reader does not yet know a tool exists.

**Page type:** How-to guide (informational)  
**Target query:** how to report hospitality data  
**Supporting queries:** hospitality data reporting guide, how to analyse hotel data, hospitality reporting best practices  
**Minimum length:** 1,200 words  
**Structure:**
- H1: e.g. "How to Report Hospitality Data: A Step-by-Step Guide"
- Intro: common problems (messy PMS exports, inconsistent booking channels, duplicate records)
- H2 sections: step 1 — clean your data / step 2 — standardise formats / step 3 — produce the report
- Naturally introduce ColtraDataAi as the tool that handles steps 1 and 2 automatically
- Soft CTA: Free Health Check, not hard sell
- Link to /hospitality-reporting-tool.html for readers who are ready to evaluate a tool
- Link to /hospitality.html as parent hub
- Full OG + canonical + JSON-LD WebPage + HowTo schema

**Add to sitemap.xml after creation.**

**Commit message:** `content: add how-to-report-hospitality-data.html informational guide`

---

### 6. Add Organization + WebSite JSON-LD to index.html
**Priority:** H | **Effort:** 15 minutes

The homepage currently has no JSON-LD at all. Add two blocks:

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": "https://coltradata.com/#organization",
  "name": "ColtraDataAi",
  "url": "https://coltradata.com",
  "logo": "https://coltradata.com/assets/logo.png",
  "sameAs": ["https://www.linkedin.com/company/coltradata"]
}
```

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": "https://coltradata.com/#website",
  "url": "https://coltradata.com",
  "name": "ColtraDataAi",
  "publisher": { "@id": "https://coltradata.com/#organization" }
}
```

These `@id` values are referenced by existing use-case page schemas via `"isPartOf"` and `"publisher"` — adding them to the homepage completes the graph.

**Commit message:** `seo: add Organization and WebSite JSON-LD to index.html`

---

### 7. Create /free-health-check.html on main domain
**Priority:** M | **Effort:** 1-2 hours

`app.coltradata.com/Free_Health_Check` earns 11 GSC impressions at position 82.7. App subdomains rarely rank and split link authority from the main domain.

**Page type:** Product landing page  
**Target queries:** free data health check, free online data quality check, health check online free, data quality score tool  
**Minimum length:** 800 words  
**Structure:**
- H1: "Free Data Health Check — Instant Quality Score for Any Spreadsheet"
- Explain what it checks (quality score, missing values, duplicates, formatting issues, 3 AI observations)
- Show the sample output preview (can reuse existing Health Check section visuals from index.html)
- Single CTA button: "Run My Free Health Check" → `https://app.coltradata.com/Free_Health_Check`
- Full OG + canonical + JSON-LD WebPage schema

**Add to sitemap.xml after creation.**

**Commit message:** `content: add free-health-check.html landing page on main domain`

---

### 8. Expand hospitality.html into topic hub
**Priority:** M | **Effort:** 1-2 hours

hospitality.html is the site's top-performing page by impressions (65% of all non-brand impressions). It should anchor a topic cluster. Currently it links outward to the nav dropdown only.

**Changes:**
- Expand body copy to 1,200-2,000 words, targeting the keyword cluster: "hospitality database", "hospitality data services", "hospitality industry database"
- Add an internal "In this series" or "Related guides" section linking to:
  - /hospitality-reporting-tool.html
  - /how-to-report-hospitality-data.html
- Tighten meta description to under 155 characters (currently 199)
- Verify existing FAQPage JSON-LD questions address the GSC queries

**Commit message:** `content: expand hospitality.html into topic hub, add child page links`

---

### 9. Add BreadcrumbList JSON-LD to remaining use-case pages
**Priority:** M | **Effort:** 30 minutes

Currently only hospitality.html and retail.html include BreadcrumbList in their JSON-LD. Add the same pattern to all 10 remaining use-case pages. The schema pattern to follow:

```json
"breadcrumb": {
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://coltradata.com/" },
    { "@type": "ListItem", "position": 2, "name": "[PAGE NAME]", "item": "https://coltradata.com/[page].html" }
  ]
}
```

**Commit message:** `seo: add BreadcrumbList JSON-LD to all remaining use-case pages`

---

### 10. Add noindex to 404.html
**Priority:** L | **Effort:** 2 minutes

Add `<meta name="robots" content="noindex, follow" />` to 404.html so Googlebot does not index it if it crawls a broken URL.

**Commit message:** `seo: add noindex meta to 404.html`

---

### 11. Add lazy loading to images
**Priority:** L | **Effort:** 10 minutes

Add `loading="lazy"` to all `<img>` tags that appear below the fold. The logo in the `<nav>` should remain eager (it is above the fold). Low impact on current traffic but good hygiene.

**Commit message:** `perf: add lazy loading to below-fold images`

---

## Measurement Checkpoints

After completing actions 1-6, wait 3-4 weeks before evaluating GSC changes. Check:
- Has "hospitality reporting tool" (pos 17.6) moved into top 10?
- Has "how to report hospitality data" (pos 19.5) moved into top 10?
- Has data-analysts.html begun appearing in GSC impressions?
- Has LinkedIn link-share engagement improved for pages that now have OG tags?

After completing actions 7-9, check:
- Has "free online health check" / "health check online free" started generating impressions on the main domain?
- Has the Structured Data report in GSC validated the new Organization/WebSite schema?

---

*Plan complete. Awaiting approval to begin implementation.*
