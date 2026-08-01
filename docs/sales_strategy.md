# ColtraDataAi — Sales Strategy

**Version:** 1.0  
**Effective:** 01 August 2026  
**Owner:** Coltrane Ltd · support@coltradata.com

---

## 1. Ideal Customer Profile (ICP)

### Primary ICP — Professional Services & Finance

| Attribute | Description |
|---|---|
| Role | Bookkeeper, accountant, finance manager, practice manager |
| Company size | 1–50 employees (SME, practice, or departmental buyer) |
| Pain point | Manually cleaning client data from Xero/QuickBooks/Sage exports before reporting; spending hours on validation that should take minutes |
| Tech comfort | Moderate — comfortable with Excel and accounting software; does not need to code |
| Budget authority | Direct budget owner for software subscriptions (£20–£300/month range) |
| Decision speed | Fast — 1–2 weeks from awareness to purchase |
| Preferred tier | Starter (£29) → Professional (£99) |

### Secondary ICP — Operations & Logistics

| Attribute | Description |
|---|---|
| Role | Operations manager, supply chain analyst, logistics coordinator |
| Company size | 10–200 employees |
| Pain point | Inconsistent supplier/carrier data, shipment date errors, duplicate records from ERP exports |
| Tech comfort | Moderate |
| Preferred tier | Professional (£99) → Business (£299) |

### Tertiary ICP — Enterprise & Mid-Market

| Attribute | Description |
|---|---|
| Role | Finance Director, Head of Operations, Head of Data |
| Company size | 50–500 employees |
| Pain point | Multiple departments producing inconsistent data; no automated validation before board reports |
| Tech comfort | Decision-maker: low-moderate; team: high |
| Budget authority | Departmental budget, may require procurement sign-off |
| Decision speed | 4–8 weeks (procurement cycle) |
| Preferred tier | Business (£299), Enterprise API (£499), Enterprise £999 |

### ICP — Developer / Technical Integrator (Enterprise API)

| Attribute | Description |
|---|---|
| Role | Developer, data engineer, product manager |
| Company size | Any (startup to enterprise) |
| Pain point | No clean, domain-aware data cleaning library available as an API; building in-house takes weeks |
| Tech comfort | High — can integrate an HTTP API |
| Decision speed | Fast once approved — 1–5 days |
| Preferred tier | Enterprise API (£499) |

---

## 2. Value Proposition

### Core message

> "Clean your business data in seconds — not hours. ColtraDataAi is the only domain-aware data cleaning platform built specifically for how UK businesses actually work."

### By segment

**For bookkeepers & accountants:**
> "Stop spending Friday afternoons fixing client CSV files. ColtraDataAi validates and cleans Xero, QuickBooks, and Sage exports automatically — so you can deliver cleaner reports, faster."

**For operations & logistics:**
> "From shipment date mismatches to duplicate supplier codes — ColtraDataAi flags the data quality issues that cause costly errors, before they reach your board report."

**For developers (Enterprise API):**
> "Add domain-aware data cleaning to your product in a single API call. Eight industry cleaners, REST JSON/CSV, live in under 15 minutes."

**For Enterprise buyers:**
> "A data cleaning layer purpose-built for your industry, with the SLA and onboarding you need — without the six-month implementation cycle."

---

## 3. Competitive Positioning

| Competitor | Their positioning | Our advantage |
|---|---|---|
| OpenRefine | Free, open-source, general-purpose | We are domain-aware (finance vs logistics vs healthcare rules differ); no installation; cloud-native; AI insights |
| Excel Power Query | Built into Excel, familiar | We produce standardised reports; handle all 8 domain types; no VBA; AI insights; API available |
| Talend / Informatica | Enterprise ETL platforms | We are 1/100th of the cost; no consultant required; deploys in minutes; purpose-built for SME data quality |
| ChatGPT / Copilot | AI for data tasks | We are deterministic (rules-based cleaner + AI layer), auditable, and produce structured reports — not chat responses |
| Manual cleaning (status quo) | Free | We save 3–5 hours per dataset; reduce errors; produce audit-ready reports |

**Our moat:** Domain-specific cleaning rules (8 industries), structured PDF/Excel audit reports, UK-focused (GDPR-compliant, UK GAAP-aware), and a live REST API — all in one platform.

---

## 4. Pricing Strategy

### Anchoring

Lead with Professional (£99) as the "most popular" in sales conversations. It solves the core problem for most ICPs and positions Starter (£29) as an easy step up from free, and Business (£299) as the obvious growth path.

Enterprise £999 is always presented as a premium — mention it to anchor high even when the prospect is actually a Business buyer.

### Tier Summary for Sales Use

| Tier | Price | Best for | Headline feature |
|---|---|---|---|
| Free | £0 | Evaluation | 3 free cleans, 5k rows |
| Starter | £29 | Individuals, sole traders | 50 cleans, Excel reports |
| Professional | £99 | Growing practices, teams | 200 cleans, AI insights, API access (100 calls/month) |
| Business | £299 | Multi-client practices, ops teams | 1M rows, branded reports, 10k rows/API call |
| Enterprise API | £499 | Developers, technical integrators | Unlimited API, REST + JSON/CSV |
| Enterprise | £999 | Finance directors, operations heads | Full SLA, onboarding, dedicated support |

### Annual Discount (Enterprise £999 only — on request)

Offer 10% annual discount: £10,788/year vs £11,988 monthly. Only mention this when a prospect is clearly committed — do not lead with it.

---

## 5. Sales Funnel

```
Awareness
  └─ Content marketing (LinkedIn, industry blogs)
  └─ SEO landing pages (bookkeepers.html, finance-teams.html, logistics.html, etc.)
  └─ Word of mouth / referral

Interest
  └─ Landing page visit → Free sign-up
  └─ Demo video (embedded on homepage)
  └─ Feature comparison table

Evaluation (Trial)
  └─ Free tier: 3 cleans → experience the quality of output
  └─ Upgrade prompt at clean #3 or row limit

Conversion
  └─ LemonSqueezy checkout (Starter, Professional, Business, Enterprise API)
  └─ "Book a Demo" flow (Enterprise £999)

Expansion
  └─ Starter → Professional: triggered when user hits 50-run limit
  └─ Professional → Business: triggered when they want higher row limits or branded reports
  └─ Business → Enterprise: triggered when they need SLA or custom setup
  └─ Any tier → Enterprise API: triggered when they ask "can we automate this?"

Retention
  └─ Review calls (Enterprise)
  └─ Product updates / new domain cleaners
  └─ Customer case studies
```

---

## 6. Channel Strategy

### Organic / Content (Primary for Starter/Professional)

- **LinkedIn:** Post content targeting bookkeepers, accountants, operations managers
  - "5 data errors that accountants miss every month" (pain-led)
  - "How we built a logistics data cleaner" (technical credibility)
  - Customer success stories (anonymised if needed)
- **SEO landing pages:** Already live — `bookkeepers.html`, `finance-teams.html`, `logistics.html`, `consultants.html`, `retail.html`, `researchers.html`, `importers-exporters.html`, `smes.html`, `healthcare.html`
  - Optimise titles, descriptions, and H1s for long-tail search
  - Target: "clean xero export csv", "fix quickbooks data errors", "logistics data cleaning tool"
- **Blog / Help content:** How-to guides linked from landing pages (can live in `docs/` or a Notion public page)

### Outreach (Primary for Business / Enterprise)

- **LinkedIn Sales Navigator:** Target Finance Directors and Operations Managers at 50–500 employee UK businesses
- **Accounting practice network:** Target bookkeepers at AAT, ICAEW practice member firms
- **Cold email:** Short, pain-led emails; 3-touch sequence max
  - Email 1: Pain point (3–4 sentences) + one-line product mention + soft CTA
  - Email 2: Social proof or use case + link to relevant landing page
  - Email 3: Direct ask for 15-minute call or "happy to help if the timing is ever right"

### Partnerships (Medium-term)

- **Accounting software ecosystems:** Explore listing in Xero App Marketplace or QuickBooks App Store as a data cleaning / reporting tool
- **Bookkeeping networks:** Partner with bookkeeping franchises or practice groups to offer group rates
- **ERP / system integrators:** Offer Enterprise API referral commissions to system integrators who embed ColtraDataAi into their client solutions

---

## 7. Enterprise Sales Process (£999 tier)

The Enterprise £999 sale requires a consultative approach. The buyer is a senior decision-maker (Finance Director, Head of Operations) who needs to justify the spend internally.

### Qualification Criteria (BANT-light)

| Criterion | Qualify-in signal | Qualify-out signal |
|---|---|---|
| **Budget** | Has discretionary software budget; £999/month is < 0.5% of problem cost | Needs extensive procurement; "we'd need to go to tender" for <£1k/month |
| **Authority** | Speaking directly to the decision-maker | Gatekeeper with no budget visibility |
| **Need** | Specific, recurring data quality pain; multiple datasets per month | One-off data cleaning task; better served by a freelancer |
| **Timeline** | Wants to start within 30 days | "Maybe next year" with no concrete trigger |

### Sales stages

| Stage | Owner | Action |
|---|---|---|
| 1. Enquiry | Support | Respond within 4 h; book discovery call |
| 2. Discovery call | Platform Owner | Qualify; understand use case; present fit |
| 3. Proposal | Platform Owner | Send tailored proposal within 2 days of call |
| 4. Follow-up | Platform Owner | One follow-up call or email after 5 days |
| 5. Close | Platform Owner | Send order confirmation / DPA if requested |
| 6. Onboard | Developer + Support | Provision account; run onboarding session |

---

## 8. Objection Handling

### "We already use Excel for this"

> "Excel is great for viewing data — but it doesn't know the difference between a logistics shipment date and a finance transaction date, and it won't flag industry-specific issues automatically. ColtraDataAi does both in seconds and produces an audit report. Most of our customers use both."

### "Is our data safe?"

> "Your data never leaves your session. Files are processed in memory and not stored on our servers. We're UK GDPR compliant, hosted in the EU, and you retain full ownership of everything you upload. We're happy to sign a Data Processing Agreement."

### "We use Xero / QuickBooks / Sage — do you integrate?"

> "You don't need a direct integration — you just export your CSV from Xero/QuickBooks/Sage and upload it. ColtraDataAi's finance cleaner recognises those export formats automatically. If you need a direct API connection in future, that's something we can explore under our Enterprise plan."

### "We have a developer — can they automate this?"

> "Absolutely — that's exactly what the Enterprise API is for. One HTTP call with a CSV or JSON body, and you get cleaned data back. Your developer can have it integrated in under an hour."

### "£999/month feels expensive"

> "Consider what a single data error in a client report costs — in time, credibility, and corrections. Our customers typically recover that £999 in the first week. And compared to hiring someone to clean data manually, it's a fraction of the cost. We also offer a 30-day satisfaction guarantee."

### "We need a trial before committing to Enterprise"

> "Absolutely. Sign up for Professional (£99) for a month — it gives you access to the same cleaners and AI insights. If you need higher volume or dedicated support, we can upgrade you to Enterprise and credit the first month. No lock-in."

---

## 9. Partnerships & Referrals

### Referral Programme (to be formalised)

- Offer existing Business and Enterprise customers a 1-month credit for every paying referral
- Offer developers who integrate the API and refer Enterprise clients a 10% revenue share for 3 months

### Integration Listing Targets

1. **Xero App Marketplace** — "Data Quality & Cleaning" category
2. **QuickBooks App Store** — "Data Management" category
3. **Sage Marketplace** — "Reporting & Analytics" category
4. **AccountingWEB Software Listings** — UK-specific directory used by bookkeepers

### Affiliate & Agency Channel

- Target bookkeeping practice management software vendors (Karbon, Senta, TaxCalc) for co-marketing or referral agreements
- Offer white-label branding under Business/Enterprise for agencies serving multiple clients

---

## 10. KPIs & Metrics

Track these monthly:

| Metric | Target (Month 6) | Source |
|---|---|---|
| Free sign-ups | 50/month | Supabase `subscriptions` table |
| Free → Paid conversion | ≥ 15% | LemonSqueezy dashboard |
| MRR | £5,000 | LemonSqueezy |
| Churn rate | < 5%/month | LemonSqueezy |
| Enterprise pipeline (enquiries) | ≥ 3/month | CRM / email |
| Enterprise close rate | ≥ 33% | CRM |
| API customer calls/month | ≥ 500/customer | Supabase `api_usage_monthly` |
| NPS / satisfaction | ≥ 8/10 | Post-onboarding email survey |

---

*End of Sales Strategy v1.0 — Review date: 01 November 2026*
