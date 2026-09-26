# ColtraDataAi - Business Plan
**Prepared by:** D. Maswodza, Founder and Director
**Company:** Coltrane Ltd
**Date:** September 2026
**Classification:** Confidential

---

## Executive Summary

ColtraDataAi is a proprietary AI-powered data cleaning and validation platform developed and owned by Coltrane Ltd. The platform addresses a documented, recurring pain point across UK small and medium enterprises, professional services firms, and public sector organisations: the cost in time, money, and compliance risk caused by poor-quality data arriving at the point where decisions, filings, and reports are produced.

ColtraDataAi is live at app.coltradata.com with a self-serve subscription model, a free tier for discovery, and a separate Enterprise API product. The business is currently at the revenue-generating stage, having shipped nine domain-specific data cleaners, a full billing pipeline, and a publicly accessible REST API.

---

## 1. Description of Product

### What ColtraDataAi Is

ColtraDataAi is a web-based, AI-assisted data cleaning, validation, and structured reporting platform. Users upload a dataset (CSV or Excel), select the relevant industry domain, and receive a cleaned output accompanied by a structured quality report highlighting errors, inconsistencies, and compliance gaps found in the original data.

The platform is a self-contained data preparation tool. It is positioned strictly as a cleaning and validation engine - not as advisory software, not as a replacement for accounting or ERP systems, and not as an analytical consultancy service.

### What the User Receives

- A cleaned and standardised version of their original dataset
- A domain-specific quality report identifying exactly what was wrong and what was corrected
- An AI-generated descriptive insights summary (Starter tier and above)
- Downloadable Excel and PDF reports (Professional tier and above)
- Interactive dashboard with KPI banners and charts (all tiers)

### Domain Coverage

The platform currently ships nine domain-specific cleaners, each encoding the validation rules and data standards of its respective industry:

| Domain | Key Standards Applied |
|---|---|
| Finance & Accounting | UK GAAP (FRS 102/105), HMRC VAT Notice 700/22 (MTD readiness), UK chart of accounts, double-entry validation, ISA 500 narrative checks |
| Import/Export & Trade | WCO Harmonized System (HS codes), ICC Incoterms 2020, ISO 3166-1 (countries), ISO 4217 (currencies, including 15 African currencies) |
| Logistics & Supply Chain | Carrier normalisation, shipment status standardisation, weight unit normalisation, transit time logic |
| Retail & Inventory | Product code consistency, stock quantity validation, pricing and margin logic |
| Consultants & Professional Services | Project reference normalisation, time and billing record validation |
| Healthcare (Operational) | NHS number validation (Modulus 11), ICD-10 code validation, NHS RTT 18-week standard, DNA rate benchmarking |
| SME & Small Business | General financial record cleaning adapted for non-specialist users |
| Hospitality & Accommodation | Booking record validation, occupancy and revenue line checks |
| Clinical Research | Patient ID validation, NCT ID normalisation (ClinicalTrials.gov format), adverse event classification, full audit trail |

### Pricing Structure

| Plan | Price | Key Limits |
|---|---|---|
| Free | £0 | 3 runs, 5,000 rows |
| Starter | £29/month | 50 runs, 50,000 rows, AI insights, Excel export |
| Professional | £99/month | 200 runs, 250,000 rows, AI-powered insights, full PDF/Excel reports, API access (1k rows/call, 100 calls/month) |
| Business | £299/month | 1,000 runs, 1 million rows, branded reports, unlimited API calls |
| Enterprise | £999/month | Unlimited, branded reports, contact-only - no public checkout |
| Enterprise API | £499/month | Standalone API product with unlimited calls, auto-provisioned key on purchase |

---

## 2. Description of Solution

### The Problem

Poor data quality is a well-documented, costly, and largely unsolved problem for small and medium-sized businesses. The problem manifests in predictable ways:

- **Pre-accounting data quality:** Bookkeepers and accountants routinely receive client data that contains inconsistent date formats, mismatched currency codes, blank or generic journal narratives, duplicate transactions, and nominal codes that do not conform to any recognisable chart of accounts. This creates hours of manual correction work before substantive accounting can begin.

- **Compliance exposure:** In the UK, HMRC's Making Tax Digital (MTD) for VAT programme requires businesses to maintain digital records with specific fields per transaction. Many businesses do not know whether their data meets these requirements until they are tested against them. The Finance cleaner's MTD VAT readiness check directly addresses this gap.

- **Trade documentation errors:** Exporters and importers using incorrect HS codes, outdated Incoterms, or non-ISO currency and country codes face customs delays, misdeclarations, and potential penalties. These errors are often invisible until they surface at the border.

- **Healthcare operational data:** NHS and private healthcare operations generate appointment, patient, and staffing records that are inconsistently formatted, affecting reporting, referral tracking, and RTT compliance.

- **Clinical research data integrity:** Research data requires full audit trails, consistent patient identifiers, and correctly formatted trial registry IDs to meet regulatory and publication standards.

### The Solution

ColtraDataAi encodes the domain knowledge needed to find and fix these problems automatically. A user does not need to know what an HS code is or what HMRC VAT Notice 700/22 requires. They upload their data, select their domain, and the platform applies the relevant rules and returns a structured report.

**This is different from generic data cleaning tools** such as OpenRefine, Trifacta, or Excel-based macros in a material way: those tools provide general-purpose transformation capabilities but carry no domain knowledge. The user still needs to know what "correct" looks like in their industry. ColtraDataAi encodes that knowledge directly into each cleaner.

**This is different from accounting or ERP software** because those systems require data to already be clean before entry. ColtraDataAi operates on the data before it reaches those systems - it is a preparation layer, not a replacement.

### International Bookkeeping and Accounting Logic

The Finance cleaner's core logic is internationally applicable:

- **Double-entry trial balance validation** (debits = credits within 1p tolerance) applies under any accounting standard - UK GAAP, IFRS, US GAAP, IPSAS
- **Journal narrative quality checks** align with ISA 500 (International Standards on Auditing) - applicable globally
- **Duplicate transaction detection, date logic, and cost centre coverage** are universal

UK-specific checks (HMRC MTD, UK nominal account ranges, UK VAT codes) are additive and keyword-triggered. Non-UK datasets skip them silently without error. This makes the Finance cleaner directly relevant to international bookkeeping practices, cross-border accounting operations, and African market clients - a gap most UK-built tools do not address.

### Founder Insight

The platform's domain coverage is not arbitrary. The founder's professional journey spans Zimbabwe tax practice, UK trade consulting under Coltrane Ltd's AfCFTA mandate, and direct experience with cross-border trade data in African and UK markets. This background directly informed the depth of the Finance, Trade, and Clinical cleaners, and explains the unusual breadth of African currency coverage in the Trade cleaner (15 African currencies, including KES, NGN, GHS, EGP, TZS, and others). The tool was built to solve problems the founder saw repeatedly, across two continents, before automated tooling existed to address them.

---

## 3. Technology Considerations - Present and Future

### Current Technology Stack

**Application Layer**
- **Streamlit (Python):** Front-end web application framework. Chosen for rapid iteration, Python-native data processing, and suitability for a single-developer delivery model. The application runs on Render (Frankfurt region) from the master branch and is accessible at app.coltradata.com.
- **FastAPI (Python):** Powers the Enterprise API product at coltradata-api.onrender.com. Accepts CSV (multipart) and JSON body inputs, performs Bearer token authentication, and routes requests to the same underlying domain cleaners used by the Streamlit app.

**Data and Authentication**
- **Supabase:** Provides PostgreSQL database, authentication (OTP-gated login), storage, and Edge Functions (serverless). Currently hosts user accounts, licence key tables (api_keys), usage logs (api_usage_log, api_usage_monthly view), and the LemonSqueezy webhook handler.
- **Pandas / xlsxwriter / ReportLab / Plotly:** Core data processing, Excel report generation, PDF report generation, and interactive charting respectively.

**Billing**
- **LemonSqueezy:** Subscription billing and payment processing. Webhooks trigger Supabase Edge Functions to auto-provision licence keys and, for Enterprise API purchases, API keys on checkout completion.

**Marketing and Content**
- **GitHub Pages:** Static marketing site at coltradata.com served from the docs/ folder on the master branch. Deliberately separate from the application server to eliminate coupling between marketing content changes and application deployments.
- **GoDaddy DNS:** Domain management for coltradata.com.

**AI Components**
- Claude Haiku (Anthropic): Powers AI descriptive insights for Starter and Professional tier users.
- Claude Sonnet (Anthropic): Powers AI descriptive insights for Business and Enterprise tier users.
- AI outputs are strictly descriptive/observational. The platform does not generate advice, recommendations, or interpretations - this is an explicit product scope boundary.

### Data Handling and Privacy

- User-uploaded datasets are processed **in-session only** - no permanent storage of file data.
- **Email addresses are stored** in Supabase as part of the authentication and licence provisioning flow (OTP login, webhook-triggered key delivery).
- Data retained per customer is limited to: email address, licence tier, and API usage logs (row counts and timestamps only - no file content).
- This is the GDPR baseline position: data processed = session only; data retained = account email and licence metadata only.

### Technology Strengths

- **Single-developer deployable:** The stack is deliberately chosen for low operational overhead. Render handles CI/CD from master push. Supabase handles authentication, database, and serverless functions without a separate backend team.
- **Domain cleaner architecture:** Each cleaner is a self-contained Python module. Adding a new domain requires no changes to the routing layer.
- **API-first secondary channel:** The Enterprise API was built on the same cleaner modules as the Streamlit app. There is no duplication of logic - the API is a new interface to the same processing engine.

### Technology Roadmap - Near Term (6-12 months)

- **Scheduled file export and auto-upload:** Rather than direct database connections (ruled out due to GDPR and credential management complexity), the near-term roadmap targets scheduled file export workflows - users export from their source system on a schedule and ColtraDataAi ingests those files automatically.
- **LemonSqueezy variant completion:** Business and Enterprise API LemonSqueezy webhook auto-delivery for API key provisioning is the most critical near-term billing pipeline completion item.
- **Affiliate programme:** A session-state based affiliate tracking system was built in August 2026 and is pending end-to-end testing. The LemonSqueezy affiliate programme (20% one-off, 30-day cookie, last-click attribution) is under manual approval review. Full activation is a near-term revenue distribution lever.
- **Localisation expansion for non-UK markets:** True localisation for US (NPI numbers, US chart of accounts) or EU (EORI codes) markets would require domain-equivalent rule sets - a deliberate future product decision.

### Technology Roadmap - Medium Term (12-36 months)

- **Mobile accessibility:** A mobile-accessible interface is identified as a core product competency for future development.
- **Direct integration connectors:** Native read-only connectors to accounting systems (Xero, QuickBooks, Sage) handling OAuth authentication and data extraction, moving ColtraDataAi from a file-upload tool to a persistent data quality layer.
- **Hybrid pricing model:** The api_usage_log table and api_usage_monthly view are already built to support a flat fee plus overage pricing model for the API product.
- **Domain expansion:** Tier 2 sectors identified for future cleaners: Freight and Logistics (AfCFTA corridor specific), Food and Beverage, Higher Education.
- **AI model evolution:** The platform's AI insight generation is model-agnostic at the application layer. Upgrades to underlying Claude models are transparent to users and require no architectural changes.

### Technology Risk Considerations

- **Single-developer dependency:** All platform delivery currently resides with the founder. Mitigation: modular architecture, documentation, and the medium-term staffing plan.
- **Render / Supabase platform dependency:** Both are third-party managed services. Comparable migration alternatives exist (Railway, Fly.io, Neon) and the application is not coupled to provider-specific APIs that would make migration prohibitive.
- **LemonSqueezy billing dependency:** Billing logic is isolated in services/billing.py and the Supabase Edge Function, limiting the blast radius of any provider change.

---

## 4. Market Fit

### Total Addressable Market

The UK alone has approximately 5.5 million small businesses (fewer than 50 employees, BEIS Business Population Estimates 2024). The majority generate operational data that requires periodic cleaning and validation before it can be used for reporting, filing, or decision-making.

Beyond SMEs, the professional services layer serving them - bookkeepers, accountants, management consultants, data analysts, and operations managers - represents a substantial secondary market. These professionals deal with client data in volume and are structurally incentivised to reduce data preparation time.

### Evidence of Market Fit

LinkedIn paid campaign data (September 2026) provides segment-level demand evidence:

| Segment | CTR | Notes |
|---|---|---|
| Higher Education | 2.57% | Highest quality engagement |
| Finance & Accounting | 1.93% | Confirmed by both industry and job-function reports |
| Consulting & Professional Services | 1.81% | Highest impression volume (4,755) |
| Technology & IT Services | ~1.65% | Combined audience; quality-informed clicks |
| Healthcare | 1.19-1.35% | Consistent across two report dimensions |

Standard B2B LinkedIn ad benchmark: 0.3-0.6%. All five campaigns are above benchmark.

### Problem-Solution Alignment by Segment

**Bookkeepers and Accountants:** MTD VAT readiness check, nominal account normalisation, and trial balance validation directly address the pre-accounting data quality problems this segment faces monthly. Positioned as time saved before accounting work begins - not as a replacement for accounting software.

**Management Consultants and Professional Services Firms:** Consultants frequently inherit client data in various states of quality. ColtraDataAi reduces data preparation time before analysis can begin.

**Importers, Exporters, and Freight Operations:** Post-Brexit customs compliance has increased the cost of incorrect trade documentation. The Trade cleaner's HS code validation, Incoterms 2020 check, and 15-currency African coverage directly address this. The AfCFTA dimension positions ColtraDataAi as one of very few tools with genuine African trade data capability built in from day one.

**Healthcare Operations:** The Healthcare cleaner's NHS number validation, RTT wait time benchmarking, and ICD-10 validation are directly relevant to NHS administrative teams and private healthcare operators.

**Data Analysts (Freelance and In-House):** Data analysts use ColtraDataAi as a productivity tool - cleaning and standardising source data faster so they can focus on higher-value analytical work. The positioning is explicitly inclusive: the tool supports analysts, it does not replace them.

**Clinical Research Organisations:** Clinical data integrity requirements are stringent. The Clinical cleaner's audit trail, run_id timestamping, patient ID validation, and corrected NCT ID handling address a compliance-sensitive use case.

### Competitive Landscape

| Category | Examples | ColtraDataAi Differentiator |
|---|---|---|
| Generic data cleaning tools | OpenRefine, Trifacta, Talend | ColtraDataAi carries domain knowledge - users do not need to know what "correct" looks like |
| Spreadsheet-based cleaning | Excel macros, Power Query | No programming required; structured quality report generated automatically |
| Accounting software | Xero, Sage, QuickBooks | These require clean data on entry; ColtraDataAi operates before those systems |
| Enterprise data quality platforms | Informatica, IBM DataStage | Six-figure contracts; inaccessible to SMEs and mid-market |
| AI-native data tools (emerging) | Various LLM-based tools | ColtraDataAi's domain-specific rule sets are deterministic; AI is additive for descriptive summaries |

The most direct competition is manual effort in Excel - the default approach for the majority of the SME and professional services target market.

---

## 5. Marketing Strategy

### Overall Positioning

ColtraDataAi is positioned as an **AI-powered business intelligence and decision support platform** in paid advertising. Business-value messaging (time saved, compliance risk reduced, decision-ready data) converts better than technical AI messaging for the target segments.

### Channel Strategy

**LinkedIn Paid Campaigns (Primary Acquisition Channel)**

Five sector-targeted campaigns, each crafted for a specific industry audience:

| Campaign | Audience | Tested CTR |
|---|---|---|
| Consulting & Professional Services | Management Consultants, Business Advisors, Transformation Consultants | 1.81% |
| Finance & Accounting | CFOs, Finance Directors, Accountants | 1.93% |
| Healthcare & Medical | NHS administrators, Medical Practices, Clinical Operations | 1.19-1.35% |
| Technology & IT Services | CTOs, Data Engineers, IT Directors | ~1.65% |
| Higher Education | University Administrators, Research Managers, Registrars | 2.57% |

Tier 2 sectors held for future campaigns: Freight and Logistics (2.55% CTR), Food and Beverage (1.54%), Hospitality (1.14%).

**Organic LinkedIn Content:** Structured 30-day content series covering AI insights, use cases, industry commentary, product features, and thought leadership. Supported by the founder's authentic cross-border narrative (Zimbabwe tax practice, AfCFTA trade consulting, UK SME market).

**Affiliate Programme:** LemonSqueezy affiliate programme - 20% one-off commission, 30-day cookie tracking window (last-click attribution). Session-state based affiliate parameter tracking built into the app. Partners (bookkeepers, accountants, consultants) promote to their own professional networks in exchange for commission on referred subscriptions. The 30-day cookie means: if a referred visitor clicks an affiliate link today but subscribes within the next 30 days, the affiliate still receives their commission - capturing the considered B2B purchase cycle without unlimited commission liability.

**Free Tier as Conversion Funnel:** Free plan (3 runs, 5,000 rows, no payment required) provides zero-commitment product discovery. Demo widget provides pre-built dataset experience for first-time visitors from paid or organic channels.

**Marketing Site (coltradata.com):** Static site on GitHub Pages carrying the full pricing comparison table, domain cleaner descriptions, and direct LemonSqueezy checkout links. Separated from the application server so content changes do not affect application stability.

### Pricing as a Marketing Tool

- At £29/month entry, the platform is affordable to a sole-practitioner bookkeeper or freelance consultant without budget approval
- At £999/month Enterprise (contact-only), the platform communicates credibility to larger organisations
- Enterprise API at £499/month is a distinct product for a distinct buyer (technical teams, data engineers)

---

## 6. Organisation and Staffing Plan

### Current Structure

**Coltrane Ltd** was incorporated in England and Wales in 2014. The company was dormant from incorporation through to 2025, during which time the founding director built academic credentials and professional expertise across two continents before returning to active trading through ColtraDataAi.

**Founder - D. Maswodza (Managing Director, 90% shareholder)**

Academic and professional qualifications:
- BA (Hons) International Business with Law - University of Greenwich
- Postgraduate Certificate in Business Administration - University of Roehampton
- Higher Diploma in Taxation
- AMCIEx - Chartered Institute of Export and International Trade

Career path: Zimbabwe tax practice - UK trade consulting (Coltrane Ltd, AfCFTA mandate) - ColtraDataAi. The combination of an international business and law degree, a postgraduate business qualification, and a professional taxation credential provides the academic foundation underpinning ColtraDataAi's compliance-focused product design. The AMCIEx credential directly informs the depth of the Trade cleaner's WCO, Incoterms 2020, and African currency coverage.

**Second Shareholder:** 10% shareholding. Non-operational.

**Current headcount:** 1 (founder only). The platform has been built, deployed, and is being actively marketed and operated by the founder - including product development, infrastructure management, domain cleaner design, billing pipeline configuration, marketing strategy, content production, and customer support.

### Immediate Period (Now - 6 months)

The business is in the revenue-building phase. The priority is to reach a sustainable monthly recurring revenue (MRR) level that covers infrastructure costs, advertising spend, and provides founder income.

- Covering basic operational costs requires approximately 5-8 Starter subscribers, or 2-3 Professional subscribers
- Target of 20 paying subscribers across Starter and Professional tiers within 6 months: approximately £700-£2,000 MRR depending on tier mix

The affiliate programme reduces the need for a dedicated sales function in the early stage.

### Near Term (6-18 months)

First hire: **Part-time Customer Success and Operations Associate** (flexible, likely freelance or part-time).

Responsibilities:
- Handling customer onboarding queries and support tickets
- Managing affiliate programme communications and approvals
- Supporting LinkedIn content scheduling and organic engagement
- Light quality assurance on report outputs for new domain or feature releases

Does not require technical skills. Requires strong written communication, comfort with SaaS tools, and ideally knowledge of one or more target domains (finance, healthcare, consulting).

### Medium Term (18-36 months)

- **Technical hire (part-time or contract):** Contract Python developer with data engineering experience to extend capacity for domain expansion or integration connector builds
- **Marketing and Growth hire:** Dedicated campaign execution, content production, and affiliate partner relationship management
- **Accounting and Compliance (outsourced):** Retained accountancy practice for statutory accounts, VAT filing, and HMRC compliance - not an in-house hire

### Governance and Operations

- **Legal entity:** Coltrane Ltd (England and Wales). All ColtraDataAi product assets, domain names, code, and customer contracts sit within Coltrane Ltd.
- **IP protection:** Domain-specific cleaning logic, compliance rule sets, and platform architecture are proprietary to Coltrane Ltd. No cleaner logic has been open-sourced.
- **Data handling:** User-uploaded data processed in-session only. Customer account data (email, licence tier) stored in Supabase under standard data processing agreements. GDPR compliance maintained as a baseline operational requirement.
- **Banking and payment infrastructure:** LemonSqueezy handles all card processing and subscription management. Coltrane Ltd receives net proceeds after LemonSqueezy fees.

---

## Summary - Key Milestones

| Milestone | Target Date |
|---|---|
| Affiliate programme fully live (end-to-end tested) | October 2026 |
| LemonSqueezy webhook auto-delivery for Enterprise API | October 2026 |
| 10 paying subscribers (any tier) | Q4 2026 |
| Break-even on infrastructure and ad costs | Q1 2027 |
| First part-time hire | Q2 2027 (revenue dependent) |
| 50 paying subscribers | Q2-Q3 2027 |
| Mobile-optimised interface | H2 2027 |
| Direct accounting system connectors (Xero, QuickBooks) | 2028 |

---

*Coltrane Ltd | Registered in England and Wales | ColtraDataAi is a trading product of Coltrane Ltd*
*Contact: support@coltradata.com | coltradata.com*
