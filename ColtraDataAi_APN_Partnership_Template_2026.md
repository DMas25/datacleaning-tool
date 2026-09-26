# ColtraDataAi - AWS APN Joint Business Plan Template
**Prepared by:** D. Maswodza, Managing Director - Coltrane Ltd
**Date:** September 2026
**Classification:** Confidential

---

# Partnership Overview

## Partner 1

| Field | Entry |
|---|---|
| **Partner 1 Name** | Coltrane Ltd (trading as ColtraDataAi) |
| **SFDC Link** | [To be provided - Salesforce CRM account record URL] |
| **APN SFDC Link** | [To be provided - AWS Partner Central / APN Salesforce record URL] |
| **Partner Tier** | [To be confirmed upon APN enrollment - likely Select tier at entry] |
| **Partner Since** | [To be confirmed - insert APN enrollment date] |
| **Business Plan Owners** | D. Maswodza, Managing Director - Coltrane Ltd |
| **Current APN Programs** | [To be confirmed - e.g. ISV Accelerate, AWS Marketplace, SaaS Competency Program] |
| **Office Locations** | United Kingdom (England and Wales) |
| **Key Focus Verticals** | Finance & Accounting, Healthcare (Operational and Clinical), Import/Export and Trade, Logistics and Supply Chain, Professional Services and Consulting, SME and Small Business, Higher Education |
| **EXISTING Competencies & Service Delivery Programs** | AI/ML-powered data quality tooling; domain-specific compliance rule engine (HMRC MTD VAT, WCO HS codes, ICC Incoterms 2020, NHS RTT, WHO ICD-10); REST API delivery via FastAPI; PostgreSQL-backed licence and usage management; automated subscription fulfilment via webhook |

---

## Partner 2

| Field | Entry |
|---|---|
| **Partner 2 Name** | [To be identified - potential systems integrator, reseller, or consulting partner] |
| **SFDC Link** | [To be provided] |
| **APN SFDC Link** | [To be provided] |
| **Partner Tier** | [To be confirmed] |
| **Partner Since** | [To be confirmed] |
| **Business Plan Owners** | [To be confirmed] |
| **Current APN Programs** | [To be confirmed] |
| **Office Locations** | [To be confirmed] |
| **Key Focus Verticals** | [To be confirmed] |
| **EXISTING Competencies & Service Delivery Programs** | [To be confirmed] |

---

## Partner 3

| Field | Entry |
|---|---|
| **Partner 3 Name** | [To be identified if applicable] |
| **SFDC Link** | [To be provided] |
| **APN SFDC Link** | [To be provided] |
| **Partner Tier** | [To be confirmed] |
| **Partner Since** | [To be confirmed] |
| **Business Plan Owners** | [To be confirmed] |
| **Current APN Programs** | [To be confirmed] |
| **Key Focus Verticals** | [To be confirmed] |
| **EXISTING Competencies & Service Delivery Programs** | [To be confirmed] |

---

# Solution Overview

## Executive Summary

ColtraDataAi is a proprietary AI-powered data cleaning, validation, and structured reporting platform developed by Coltrane Ltd (England and Wales). The platform addresses a documented and costly problem across UK SMEs, professional services firms, healthcare operations, and trade-facing businesses: poor-quality data that creates compliance risk, delays reporting, and increases the manual burden on accountants, bookkeepers, operations managers, and data professionals before any substantive analytical or filing work can begin.

The solution is live at app.coltradata.com, built on a Python/Streamlit front end, a FastAPI REST API layer, and Supabase (PostgreSQL) for authentication, licence management, and usage tracking, hosted on Render (Frankfurt). A self-serve subscription model handles customer acquisition, billing, and licence fulfilment automatically via LemonSqueezy webhooks.

The platform ships nine domain-specific cleaners (Finance, Trade, Logistics, Healthcare, Clinical, Retail, SME, Hospitality, and Consulting), each encoding the validation and standardisation rules of its respective industry. AI-powered descriptive insights are generated using Anthropic Claude (Haiku for Starter and Professional tiers, Sonnet for Business and Enterprise tiers). The Enterprise API product provides a standalone REST interface at coltradata-api.onrender.com, making the cleaning engine programmable for technical teams and data pipelines.

The solution is designed to be cloud-native, modular, and incrementally extensible. AWS infrastructure and services represent the logical next platform layer as the business scales beyond the current single-server Render deployment, particularly for higher-availability API delivery, data pipeline integration, and potential AWS Marketplace listing.

---

## Description of Solution

ColtraDataAi delivers a domain-intelligent data cleaning and quality reporting service. The final product a customer receives is:

1. A **cleaned and standardised dataset** - correcting formatting inconsistencies, normalising codes (currency, country, HS, VAT, ICD-10, etc.), removing duplicates, and flagging unfixable issues for human review
2. A **structured quality report** (Excel and PDF at Professional tier and above) documenting every issue found, every correction applied, and a quality score across dimensions including completeness, consistency, format compliance, and domain-specific compliance readiness
3. **AI-generated descriptive insights** (Starter and above) summarising the data quality profile in plain language - strictly observational, never advisory
4. An **interactive dashboard** with KPI banners and Plotly charts showing data quality metrics at a glance

The product is desirable because it removes the pre-accounting, pre-reporting, and pre-filing data preparation burden that currently falls on accountants, bookkeepers, consultants, and operations staff - work that is manual, repetitive, time-consuming, and error-prone. It does not replace accounting software or advisory services. It operates in the gap before those systems receive data.

Demand is evidenced by LinkedIn paid campaign performance consistently exceeding standard B2B SaaS benchmarks (typical CTR: 0.3-0.6%; ColtraDataAi campaigns: 1.81% Consulting, 1.93% Finance and Accounting, 2.57% Higher Education). The addressable population in the UK alone includes approximately 5.5 million SMEs and the professional services layer serving them.

---

## Technology Considerations

**Current delivery architecture:**

| Layer | Technology | Notes |
|---|---|---|
| Web application | Python / Streamlit | Hosted on Render (Frankfurt); auto-deploys from GitHub master branch |
| REST API | Python / FastAPI | coltradata-api.onrender.com; Bearer token auth; CSV and JSON inputs |
| Database / Auth | Supabase (PostgreSQL) | OTP-gated login; licence key and API key management; usage logging |
| Serverless functions | Supabase Edge Functions | LemonSqueezy webhook handler; auto-provisions licence and API keys on purchase |
| AI insights | Anthropic Claude (Haiku: Starter/Professional; Sonnet: Business/Enterprise) | Descriptive insights only - no advisory outputs |
| Report generation | xlsxwriter (Excel), ReportLab (PDF), Plotly (charts) | Multi-sheet Excel reports; branded PDF executive summary |
| Billing | LemonSqueezy | Subscription management; webhook-triggered auto-fulfilment |
| Marketing site | GitHub Pages (docs/ folder) | Static HTML/CSS/JS; separate from app server |
| DNS | GoDaddy | coltradata.com |

**Data handling note:**
- User-uploaded datasets are processed in-session only - no permanent storage of file data
- Email addresses are stored in Supabase as part of authentication and licence provisioning (OTP login, webhook-triggered key delivery)
- Data retained per customer: email address, licence tier, and API usage logs (row counts and timestamps only - no file content)
- GDPR baseline position: data processed = session only; data retained = account email and licence metadata only

**Technology needed to scale with AWS:**
- **AWS Lambda or ECS:** Higher-availability, auto-scaling API compute as Enterprise API call volumes grow beyond single-instance Render capacity
- **Amazon S3:** Scheduled file export and auto-upload workflows (near-term roadmap alternative to direct database connectors)
- **Amazon RDS (PostgreSQL) or Aurora Serverless:** Production-grade database availability and read replicas as subscriber volumes grow
- **Amazon CloudFront:** CDN layer for marketing site and report download delivery
- **AWS Marketplace:** Self-serve listing to reach enterprise buyers already operating in AWS environments with existing AWS spend commitments

**Labour:** Currently single-developer. First technical hire (contract Python / data engineering) targeted for 2027 when revenue supports it.

---

## Market Fit

**Target market:**

| Segment | Relevant Cleaner(s) | Evidence |
|---|---|---|
| Bookkeepers and accountants (UK SME) | Finance & Accounting | Founder firsthand domain expertise; MTD VAT compliance driver |
| Management consultants and professional services firms | Consulting, Finance | Highest impression volume in LinkedIn campaigns; 1.81% CTR |
| Import/export operators and freight forwarders | Trade, Logistics | Post-Brexit HS code and Incoterms compliance demand; AfCFTA corridor relevance |
| Healthcare operations (NHS and private) | Healthcare (Operational) | 1.19-1.35% CTR across two LinkedIn campaign report dimensions |
| Clinical research organisations | Clinical Research | Regulatory-grade audit trail requirement; NCT ID and patient ID compliance |
| Freelance data analysts | All domains | API product; speed-to-analysis productivity tool |
| Higher education administrators | SME, Consulting, Clinical | Highest quality engagement: 2.57% CTR |
| African market and diaspora-linked businesses | Trade (15 African currencies) | Unique differentiator; no comparable UK-built tool covers this |

**International bookkeeping and accounting logic:** The Finance cleaner's core logic (double-entry trial balance validation, ISA 500 narrative quality checks, duplicate detection, date logic) is internationally applicable under UK GAAP, IFRS, and IPSAS. UK-specific checks are additive and keyword-triggered - non-UK datasets skip them silently. This positions the product for international bookkeeping practices and cross-border accounting operations, not only UK-only clients.

**Key competitors:**

| Competitor | Type | ColtraDataAi Advantage |
|---|---|---|
| OpenRefine / Trifacta | Generic data cleaning | No domain knowledge - user must know what correct looks like |
| Excel macros / Power Query | Spreadsheet-based | No structured quality report; no compliance rule encoding |
| Xero / Sage / QuickBooks | Accounting software | Requires clean data on entry; ColtraDataAi operates before these systems |
| Informatica / IBM DataStage | Enterprise data quality | Six-figure contracts; inaccessible to SMEs and mid-market |
| Emerging LLM-based tools | AI-native data tools | ColtraDataAi's rule engine is deterministic; AI is additive, not the core logic |

The primary competition is manual effort in Excel - the default approach for the majority of the SME and professional services target market.

---

## Marketing Strategy

**Primary channel - LinkedIn paid campaigns (5 sector-targeted campaigns):**

| Campaign | Audience | Tested CTR |
|---|---|---|
| Consulting & Professional Services | Management Consultants, Business Advisors | 1.81% |
| Finance & Accounting | CFOs, Finance Directors, Accountants | 1.93% |
| Healthcare & Medical | NHS administrators, Medical Practices, Clinical Operations | 1.19-1.35% |
| Technology & IT Services | CTOs, Data Engineers, IT Directors | ~1.65% |
| Higher Education | University Administrators, Research Managers, Registrars | 2.57% |

Tier 2 sectors held for future campaigns: Freight and Logistics (2.55% CTR), Food and Beverage (1.54%), Hospitality (1.14%).

**Organic LinkedIn content:** 30-day content series covering AI insights, use cases, industry commentary, product features, and thought leadership.

**Affiliate programme:** LemonSqueezy affiliate programme - 20% one-off commission, 30-day cookie tracking window (last-click attribution). Session-state based affiliate parameter tracking built into the app.

**Free tier as conversion funnel:** Free plan (3 runs, 5,000 rows) provides zero-commitment product discovery. Demo widget provides pre-built dataset experience.

**AWS Marketplace (planned):** Listing creates a procurement-friendly channel for enterprise buyers with existing AWS spend commitments, removing procurement friction for the Enterprise and Enterprise API tiers.

**Positioning:** AI-powered business intelligence and decision support platform. Business-value messaging (time saved, compliance risk reduced, decision-ready data) rather than technical AI messaging.

---

## Organisation and Teaming Structure

**Current state:**

- **Coltrane Ltd** (England and Wales, incorporated 2014, operationally active from late 2025)
- Shareholding: D. Maswodza 90%, second shareholder 10%
- Current headcount: 1 (founder and managing director)
- Founder manages: product development, infrastructure, domain cleaner design, billing pipeline, marketing strategy, content, and customer support

**Founder credentials:**
- BA (Hons) International Business with Law - University of Greenwich
- Postgraduate Certificate in Business Administration - University of Roehampton
- Higher Diploma in Taxation
- AMCIEx - Chartered Institute of Export and International Trade

**Planned hires to fulfil solution demands:**

| Role | Timing | Trigger |
|---|---|---|
| Part-time Customer Success and Operations Associate | Q2 2027 | Revenue supports part-time cost; support ticket volume grows |
| Contract Python / Data Engineering Developer | 2027 | Domain expansion or integration connector build required |
| Marketing and Growth hire | 2027-2028 | Paid campaign model proven at scale |
| Retained accountancy practice (outsourced) | Ongoing | Statutory accounts, VAT filing, HMRC compliance |

---

## Schedule

| Milestone | Target Date | Constraints |
|---|---|---|
| Affiliate programme end-to-end activation | Oct 2026 | LemonSqueezy manual approval pending |
| Enterprise API auto-delivery webhook complete | Oct 2026 | LemonSqueezy variant ID configuration |
| 10 paying subscribers | Q4 2026 | Advertising spend and organic reach |
| Break-even on infrastructure and ad costs | Q1 2027 | ~5-8 Starter or 2-3 Professional subscribers covers costs |
| First part-time hire | Q2 2027 | Revenue dependent |
| 50 paying subscribers | Q2-Q3 2027 | Affiliate programme contribution assumed |
| AWS Marketplace listing | H1 2027 | APN enrollment and listing validation |
| Mobile-optimised interface | H2 2027 | Development time; currently single-developer |
| Direct accounting system connectors (Xero, QuickBooks, Sage) | 2028 | OAuth integration complexity; requires technical hire |

---

## Initial Financial Projections

Conservative scenario - 15 subscribers per tier as baseline:

| Tier | Price | Subscribers (Yr 1) | Monthly Revenue | Annual Revenue |
|---|---|---|---|---|
| Starter | £29/month | 15 | £435 | £5,220 |
| Professional | £99/month | 15 | £1,485 | £17,820 |
| Business | £299/month | 15 | £4,485 | £53,820 |
| Enterprise API | £499/month | 5 | £2,495 | £29,940 |
| **Total** | | **50** | **£8,900** | **£106,800** |

Year 2 projection (20% subscriber growth per tier): approximately £128,160 ARR.
Year 3 projection (further 30% growth, Enterprise tier activation): approximately £180,000+ ARR.

Full detailed three-year financial model with balance sheet available as a companion document (ColtraDataAi_Financial_Projections_2026).

---

## Draft Reference Architecture

```
                    +------------------------------------------+
                    |           coltradata.com                 |
                    |    (GitHub Pages - Static Marketing)     |
                    +-------------------+----------------------+
                                        | Traffic
                    +-------------------v----------------------+
                    |         app.coltradata.com               |
                    |    (Render - Python / Streamlit App)     |
                    |  +--------------------------------------+ |
                    |  |  9 Domain Cleaners (Python)          | |
                    |  |  Report Builder (xlsxwriter)         | |
                    |  |  PDF Engine (ReportLab)              | |
                    |  |  Chart Gallery (Plotly)              | |
                    |  |  AI Insights (Anthropic Claude)      | |
                    |  +--------------------------------------+ |
                    +-------------------+----------------------+
                                        |
          +-----------------+-----------+-----------+
          |                 |                       |
+---------v----------+ +----v-------------------+ +-v-----------+
|  Supabase          | | coltradata-api.         | | LemonSqueezy|
|  - PostgreSQL DB   | | onrender.com            | | - Subscript.|
|  - OTP Auth        | | (FastAPI - Enterprise   | | - Webhooks  |
|  - api_keys table  | |  API)                  | | - Affiliates|
|  - api_usage_log   | |  Bearer Token Auth      | +------+------+
|  - Edge Functions  |<+  POST /v1/clean/{domain}|        |
|    (Webhook)       | +-------------------------+        |
+--------------------+                                    |
          ^                                               |
          +-----------------------------------------------+
                   Webhook triggers key provisioning

AWS Evolution Layer (planned):
Lambda/ECS (API compute) | S3 (file ingestion) | RDS/Aurora (database)
CloudFront (CDN) | Marketplace (enterprise procurement)
```

---

## First Customer Targets

| Target Profile | Sector | Relevant Cleaner | Route to Market |
|---|---|---|---|
| UK sole-practitioner bookkeeper or small accountancy practice | Finance | Finance & Accounting | LinkedIn Finance campaign; affiliate programme |
| Management consulting firm (1-10 consultants) | Professional Services | Consulting, Finance | LinkedIn Consulting campaign |
| NHS administrative team or private healthcare operator | Healthcare | Healthcare (Operational) | LinkedIn Healthcare campaign (run independently) |
| University department or research administrator | Higher Education | Clinical, SME | LinkedIn Higher Education campaign |
| UK importer/exporter or freight forwarder | Trade / Logistics | Trade, Logistics | LinkedIn Technology campaign; AfCFTA network |
| Freelance data analyst | Cross-sector | All via API | LinkedIn Technology campaign; affiliate programme |

*ACE opportunity links to be inserted when ColtraDataAi is registered in AWS ACE (APN Customer Engagements) pipeline.*

---

## Findings and Recommendations

**Findings:**

1. ColtraDataAi addresses a real, recurring, and underserved problem. The data quality gap between raw business data and decision-ready or filing-ready data is manually absorbed by the professional services layer today - at significant time cost and with no systematic validation.

2. The product is live, revenue-generating, and technically coherent. Nine domain cleaners, a billing pipeline, and a publicly accessible API represent a meaningful proof of execution for a single-founder company.

3. Early paid campaign data provides objective evidence of above-benchmark engagement across five industry segments, with Finance, Consulting, and Higher Education as the strongest-signal verticals.

4. The technology architecture is cloud-native and modular. AWS infrastructure is the natural next layer for scaling the API product, enabling scheduled data ingestion, and reaching enterprise buyers via Marketplace.

5. The founder's credentials (international business law, postgraduate business administration, taxation, export and trade) directly underpin the compliance depth of the product - a genuine differentiator over generic data tools.

**Recommendations:**

- Proceed with APN enrollment and pursue ISV Accelerate program eligibility to access co-sell support and AWS Marketplace listing
- Prioritise Enterprise API auto-delivery webhook completion as the highest-value near-term revenue action
- Use AWS Marketplace as the enterprise procurement channel alongside the direct LemonSqueezy self-serve model
- Target the Consulting and Finance and Accounting verticals first with any co-sell activity - these show the strongest combination of volume and intent
- Plan the AWS architecture migration for the API product in H1 2027, timed with the first technical hire

---

# Solution Team Structure

## Support Model

| Question | Answer |
|---|---|
| **Which Partner is the first line of support?** | Coltrane Ltd / ColtraDataAi is the sole first line of support at this stage. Support is handled directly by the founder via support@coltradata.com. |
| **How does the support model work?** | Email-based support for all tiers. Enterprise and Enterprise API customers receive prioritised response. As subscriber volume grows and a Customer Success Associate is hired (Q2 2027), support will be handled by that role with technical escalation to the founder. A knowledge base and FAQ are planned to reduce inbound support load. |

---

## Sales Model

| Question | Answer |
|---|---|
| **Who generates opportunities?** | Opportunities are currently generated by the founder through LinkedIn paid campaigns, organic content, and the affiliate programme. There are no co-selling partners at this stage. |
| **If multiple partners, how do they work together?** | Not applicable at present - single-partner model. When a systems integrator or reseller partner is added, the model will be: partner identifies and qualifies the opportunity, registers it in AWS ACE, and ColtraDataAi handles product delivery and technical support. Revenue share to be agreed on a per-partner basis. |

---

## Commercial Agreements

| Question | Answer |
|---|---|
| **Have the partners determined if they can work commercially together?** | Not applicable at present - single-partner model. For any future partner, a standard reseller or referral agreement will be required before opportunities are worked jointly. Revenue allocation model: referral fee or reseller margin to be negotiated (indicative: 15-20% of first-year subscription value for qualified referrals). All commercial agreements must be reviewed and signed before any joint customer engagement. |

---

*Coltrane Ltd | Registered in England and Wales | ColtraDataAi is a trading product of Coltrane Ltd*
*Contact: support@coltradata.com | coltradata.com*

---

**Fields still requiring completion before submission:**
- All SFDC Link and APN SFDC Link fields (require AWS Partner Central account and Salesforce CRM record IDs)
- Partner Tier (confirm upon APN enrollment)
- Partner Since date (confirm APN enrollment date)
- Current APN Programs (confirm which programs enrolled in)
- Partners 2 and 3 details (if applicable)
- ACE opportunity links for First Customer Targets section
