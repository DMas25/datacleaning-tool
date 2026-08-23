# SEO Audit — coltradata.com
**Date:** 2026-08-21  
**Scope:** All 16 HTML pages in docs/, robots.txt, sitemap.xml  
**GSC data period:** 18 Jul – 2 Aug 2026 (provided in brief)

---

## Summary of Critical Findings

| Priority | Issue | Pages Affected |
|---|---|---|
| CRITICAL | Two near-page-1 target pages do not exist | N/A — to create |
| CRITICAL | /free-health-check.html missing from main domain | N/A — to create |
| CRITICAL | data-analysts.html not in sitemap.xml | 1 page |
| HIGH | Canonical tag missing | 10 of 14 content pages |
| HIGH | OG/Twitter meta tags missing | 10 of 14 content pages |
| HIGH | JSON-LD Organization + WebSite schema missing from homepage | index.html |
| HIGH | pricing.html title carries no keyword | pricing.html |
| MEDIUM | hospitality.html needs topic-hub expansion + child page links | hospitality.html |
| MEDIUM | BreadcrumbList JSON-LD missing from most pages | 11 pages |
| LOW | 404.html has no robots noindex meta | 404.html |

---

## 1. Page Inventory

| File | Title (chars) | Meta Description (chars) | H1 | Canonical | JSON-LD | OG tags |
|---|---|---|---|---|---|---|
| index.html | ColtraDataAi: From Raw Data to Clear Decisions, Powered by AI (62) | Transform Excel and CSV data... (161) | Transform Raw Data into Business-Ready Insights in Minutes | NO | NO | YES |
| hospitality.html | Hospitality Data Cleaning Tool UK \| Clean Hotel, Restaurant & Venue Data \| ColtraDataAi (89) | Clean booking records, F&B inventory... (199) | Clean Booking, Inventory & Payroll Data Without a Data Team | YES | YES (x2) | YES |
| smes.html | Data Cleaning Tool for Small Businesses UK \| SME Data Quality \| ColtraDataAi (77) | Clean your business data without a data analyst... (154) | Professional Data Reporting Without the Data Team | NO | YES | NO |
| bookkeepers.html | Bookkeeper Data Cleaning Tool UK \| Clean Client Spreadsheets Fast \| ColtraDataAi (83) | Clean messy client data before it hits your accounting software... (156) | Stop Cleaning Client Data By Hand | NO | YES | NO |
| consultants.html | Consultant Data Cleaning Tool \| Clean Client Data & Generate PDF Reports \| ColtraDataAi (89) | Clean client data and produce boardroom-ready PDF reports... (154) | From Messy Client Data to Boardroom-Ready Reports, Same Day | NO | YES | NO |
| finance-teams.html | Financial Data Cleaning Tool UK \| Clean Finance Exports & Reports \| ColtraDataAi (83) | Clean finance data exports independently... (155) | Faster Reporting Without the IT Queue | NO | YES | NO |
| logistics.html | Logistics Data Cleaning Tool UK \| Clean Shipment & Supply Chain Records \| ColtraDataAi (89) | Clean shipment records, depot exports... (155) | Turn Operational Data Into Clean, Reliable Records | NO | YES | NO |
| healthcare.html | Healthcare Data Cleaning Tool UK \| Clean Clinical & Patient Records \| ColtraDataAi (85) | Clean patient records, clinical datasets... (191) | Clean Clinical Data. Reliable Healthcare Reporting. | NO | YES | NO |
| importers-exporters.html | Trade Data Cleaning Tool UK \| Import Export Data Quality \| ColtraDataAi (73) | Clean supplier records, customs data... (155) | Clean Trade Data. Confident Compliance. | NO | YES | NO |
| researchers.html | Research Data Cleaning Tool \| Clean Survey, Field & Dataset Files \| ColtraDataAi (83) | Clean survey data, field records... (157) | Start Your Analysis on Solid Ground | NO | YES | NO |
| retail.html | Retail Data Cleaning Tool UK \| Clean POS, Stock & Customer Data \| ColtraDataAi (80) | Clean retail data fast: POS exports... (155) | Clean Sales, Stock & Customer Data Without a Data Team | YES | YES (x2) | YES |
| clinical-trials.html | Clinical Trial Data Cleaning Tool \| NCT ID Validation & Trial Register \| ColtraDataAi (88) | Clean clinical trial registers... (195) | Clean Trial Register Data with Precision | YES | YES | YES |
| data-analysts.html | Data Cleaning Tool for Freelance Data Analysts \| ColtraDataAi (61) | Automate the data cleaning step... (148) | Stop Cleaning Data Manually. Start Delivering Insights Faster. | NO | YES | NO |
| pricing.html | Pricing: ColtraDataAi (20) | Simple, transparent pricing for ColtraDataAi... (73) | Simple, transparent pricing | NO | NO | NO |
| privacy.html | Privacy & Cookie Policy - ColtraDataAi (38) | (none found) | Privacy & Cookie Policy | NO | NO | NO |
| 404.html | Page Not Found: ColtraDataAi (30) | The page you're looking for couldn't be found... | Page Not Found | NO | NO | NO |

---

## 2. Missing Pages (Highest Priority)

### 2a. /hospitality-reporting-tool.html — does not exist
GSC shows "hospitality reporting tool" at **position 17.6** (5 impressions, 0 clicks). This is the closest query to page 1 on the entire site. There is no page targeting this query. Without a dedicated page, this query will stall on page 2.

**Intent:** Commercial/product. Someone evaluating tools, comparing options, looking for pricing.

### 2b. /how-to-report-hospitality-data.html — does not exist
GSC shows "how to report hospitality data" at **position 19.5** (4 impressions, 0 clicks). Second closest to page 1.

**Intent:** Informational. Someone who does not yet know a cleaning tool exists and is looking for a process.

### 2c. /free-health-check.html — does not exist on main domain
`app.coltradata.com/Free_Health_Check` earns 11 impressions at position 82.7. App subdomains rarely rank well and split link authority away from the main domain. A marketing landing page on `coltradata.com/free-health-check.html` targeting "free online health check", "health check online free", and "free data health check" would consolidate this authority. The app subdomain becomes the tool destination, reached by CTA.

---

## 3. Sitemap Issues

- **data-analysts.html is NOT in sitemap.xml.** It is linked from 14 pages (well-connected internally) but absent from the sitemap. Google will eventually crawl it via internal links, but the sitemap omission means it may be deprioritised. This page was added recently — the sitemap was not updated.
- All other content pages are present and correctly listed.
- 404.html is correctly excluded.
- Sitemap URL in robots.txt is correct: `https://coltradata.com/sitemap.xml`.

**Fix:** Add data-analysts.html to sitemap.xml with `<lastmod>` set to today's date.

---

## 4. Canonical Tags

Only 3 pages have canonical tags: `hospitality.html`, `retail.html`, `clinical-trials.html`.

The remaining 10 content pages — including `index.html`, `smes.html`, `bookkeepers.html`, and all other use-case pages — have no canonical declaration. This creates duplicate-content risk if GitHub Pages serves both `https://coltradata.com/smes.html` and `https://www.coltradata.com/smes.html`, or if query strings are appended by any UTM tracking links shared on LinkedIn.

**Fix:** Add `<link rel="canonical" href="https://coltradata.com/[page].html" />` to every content page. The pattern is already set correctly in the three pages that have it.

---

## 5. Open Graph / Twitter Meta Tags

Only 4 pages have OG/Twitter tags: `index.html`, `hospitality.html`, `retail.html`, `clinical-trials.html`.

**This is the most urgent gap given LinkedIn is the only promotional channel.** When a LinkedIn post links to `smes.html`, `bookkeepers.html`, or any other use-case page without OG tags, LinkedIn renders a plain URL with no image, no headline, and no description. This directly suppresses click-through rate on every post that links to those pages.

Pages missing OG tags (10):
- bookkeepers.html
- consultants.html
- data-analysts.html
- finance-teams.html
- healthcare.html
- importers-exporters.html
- logistics.html
- researchers.html
- smes.html
- pricing.html

---

## 6. JSON-LD Structured Data

### Missing from index.html (high impact)
The homepage has no JSON-LD at all. It is missing:
- `Organization` schema (name, url, logo, sameAs pointing to LinkedIn company page)
- `WebSite` schema with `SearchAction` (enables Google Sitelinks search box)

Both schemas belong on the homepage only and reference other pages. The brief specifically calls these out under Task 6.

### Missing from pricing.html
No schema at all. At minimum a `WebPage` schema and a `Product` or `Service` schema referencing the plans would be appropriate.

### Consistent across use-case pages
Every use-case page has a `WebPage` + `FAQPage` two-block pattern. hospitality.html and retail.html additionally include a `BreadcrumbList`. The breadcrumb schema should be added to all use-case pages for consistency.

---

## 7. Title and Description Issues

### pricing.html title is critically thin
`"Pricing: ColtraDataAi"` (20 characters) carries no keyword. No one searches "pricing coltradata". A searcher evaluating tools will compare pricing pages — this title will not win a SERP impression.

**Suggested replacement:** `ColtraDataAi Pricing | Data Cleaning Plans from £29/month`

### hospitality.html description is over-length
At 199 characters it may be truncated in SERPs (limit is typically ~155-160 characters).

**Suggested:** trim to 155 characters keeping the "Start free" CTA.

### H1 near-duplicate
`smes.html` H1: "Professional Data Reporting **Without the Data Team**"  
`retail.html` H1: "Clean Sales, Stock & Customer Data **Without a Data Team**"

Not identical, not a technical issue, but worth noting for differentiation.

---

## 8. Render-Blocking Scripts and Core Web Vitals

- **No external `<script src=` calls found** in any HTML page. All JavaScript is inline at the end of the body. No render-blocking third-party scripts.
- **All images have explicit width attributes.** No Cumulative Layout Shift risk from unsized images detected.
- Pages are self-contained static HTML/CSS — no framework overhead.
- No lazy loading (`loading="lazy"`) found on images, but given image volume is low this is not a material CWV risk.

---

## 9. Orphan Pages

No true orphans. Every content page is linked from the homepage nav dropdown and from within-domain use-case page nav menus.

`data-analysts.html` is linked from 14 pages internally — it is not an orphan by link structure. The risk is purely the sitemap omission.

---

## 10. robots.txt

```
User-agent: *
Allow: /

Sitemap: https://coltradata.com/sitemap.xml
```

Correct. No pages are blocked. Sitemap URL is valid.

---

## 11. 404.html

Has no `<meta name="robots" content="noindex">` tag. If Googlebot crawls it directly (e.g. via a broken inbound link), it will be indexed as content. Low priority, but worth adding noindex.

---

## Conflicts with the Brief

1. **Brief says "Orphan pages with no internal links pointing to them — likely the reason my new use-case pages are crawling slowly."** In reality, all pages including data-analysts.html are well-linked internally (14 inbound links). The crawl delay is more likely explained by the sitemap omission and the site being less than 2 weeks old.

2. **Brief implies hospitality.html is thin.** Word count (including inline CSS/JS) is ~3,737 raw tokens. Visible body text is likely 700-1,000 words, which is adequate for a use-case page but below the 1,200-2,000 the brief targets for the topic hub expansion. The expansion is still the right move.

3. **Brief says "no width/height attributes" as a CWV risk to check.** All images found have width attributes. No action needed there.

---

## Recommended Action Order

1. Add data-analysts.html to sitemap.xml (5-minute fix, high impact)
2. Add canonical + OG/Twitter tags to the 10 pages missing them (LinkedIn posting fix)
3. Create /hospitality-reporting-tool.html (near-page-1 opportunity, highest search upside)
4. Create /how-to-report-hospitality-data.html (second near-page-1 opportunity)
5. Add Organization + WebSite JSON-LD to index.html
6. Fix pricing.html title
7. Create /free-health-check.html on main domain
8. Expand hospitality.html into topic hub with links to the two new child pages
9. Add BreadcrumbList JSON-LD to remaining use-case pages
10. Add noindex to 404.html

---

*Audit complete. Awaiting review before any changes are made.*
