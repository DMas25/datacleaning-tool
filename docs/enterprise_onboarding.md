# ColtraDataAi — Enterprise Onboarding Playbook

**Version:** 1.0  
**Effective:** 01 August 2026  
**Owner:** Coltrane Ltd · support@coltradata.com

---

## Overview

ColtraDataAi has two distinct enterprise products requiring different onboarding approaches:

| Product | Price | Delivery | Audience |
|---|---|---|---|
| **Enterprise API** | £499/month (self-serve) | Automated key delivery | Developers, technical teams embedding data cleaning into their systems |
| **Enterprise £999** | £999/month (contact-only) | High-touch, dedicated | Finance directors, operations leaders, large organisations needing custom SLA + onboarding |

---

## Part A: Enterprise API (£499/month) Onboarding

### Overview

Enterprise API is designed for self-serve activation. The purchase-to-first-call journey should take under 15 minutes. Our role is to ensure the automated flow works and provide fast technical support if it does not.

---

### Phase 1: Purchase & Fulfilment (Automated — Day 0)

**Trigger:** Customer completes checkout on LemonSqueezy.

**Automated steps (no manual action required):**
1. LemonSqueezy fires `order_created` → `subscription_created` to Supabase Edge Function
2. Edge Function generates API key (`cdai_…`) and inserts hashed version into `api_keys` table
3. Resend delivers welcome email with API key and quick-start instructions

**Manual fallback (if automation fails within 30 minutes of purchase):**
1. Confirm payment in LemonSqueezy dashboard
2. Run `python scripts/create_api_key.py --email "customer@company.com" --label "Company — API Key"`
3. Send the key using the API Welcome Email Template (see Section: Email Templates)
4. Log the manual provision in the customer's Supabase record

---

### Phase 2: Technical Onboarding (Day 0–3)

**Day 0 — Welcome email includes:**
- API key (`cdai_…`) — one-time display, advise secure storage
- Link to API documentation (`coltradata-api.onrender.com/docs`)
- Sample `curl` request for finance domain
- Rate limits and fair-use notice
- Support contact for technical queries

**Day 1 — Follow-up check (automated or manual):**
- If `api_usage_log` shows ≥ 1 successful call within 24 h → no action needed
- If no calls after 24 h → send Technical Support Offer email (see templates)

**Day 3 — If still no usage:**
- Reach out directly to confirm they received the key and offer a 15-minute setup call

---

### Phase 3: 30-Day Check-In

- Review `api_usage_monthly` view for customer's call volume and row counts
- If usage is high and no support tickets → send a brief "How is it going?" email
- If usage is unexpectedly low → offer a call to understand barriers
- Offer a case study / testimonial if the customer is satisfied

---

### Enterprise API — Key Technical Details to Share with Customer

| Detail | Value |
|---|---|
| Base URL | `https://coltradata-api.onrender.com` |
| Auth header | `Authorization: Bearer cdai_YOUR_KEY` |
| Endpoint | `POST /v1/clean/{domain}` |
| Supported domains | `finance`, `logistics`, `retail`, `trade`, `healthcare`, `consultant`, `sme`, `hospitality` |
| Input formats | CSV (multipart/form-data) or JSON body |
| Max rows/call | Unlimited (Enterprise API) |
| Health check | `GET /health` |
| Swagger docs | `GET /docs` |
| Usage tracking | Logged per-call (domain, rows, format, timestamp) in Supabase |

**Sample curl (finance domain, CSV):**
```bash
curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \
  -H "Authorization: Bearer cdai_YOUR_KEY" \
  -F "file=@transactions.csv"
```

**Sample curl (JSON body):**
```bash
curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \
  -H "Authorization: Bearer cdai_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": [{"date": "01/01/2026", "amount": "1000", "type": "DR"}]}'
```

---

### Enterprise API — Acceptable Use Policy (communicate on purchase)

- API key is tied to the purchasing email and organisation
- Keys must not be shared across organisations or resold
- Automated pipelines must include reasonable delays between calls
- Data submitted is processed in memory and not retained by ColtraDataAi
- Usage is logged (metadata only) for billing and capacity planning

---

## Part B: Enterprise £999/month Onboarding

### Overview

Enterprise £999 is contact-only — no public checkout. It covers organisations requiring:
- Unlimited data volume
- Dedicated onboarding session
- Service Level Agreement (SLA)
- Branded report templates (client-ready)
- Custom domain cleaner scope (on request)
- Quarterly review calls
- Priority support (1-hour response SLA)

---

### Phase 1: Sales & Discovery (Days 1–5)

**Trigger:** Prospect submits enquiry via "Book a Demo" or "Contact Us" on the website.

**Respond within 4 business hours:**
- Acknowledge the enquiry
- Book a 30-minute discovery call (Calendly or direct)

**Discovery call agenda (30 min):**
1. Introduction (5 min) — who we are, what ColtraDataAi does
2. Their situation (15 min):
   - What data problems are they experiencing?
   - What software are they using? (Xero, QuickBooks, Sage, bespoke ERP, databases)
   - How do they currently clean/validate data?
   - Team size and technical capability
   - How many rows / files / domains are involved?
3. Fit assessment (5 min) — confirm Enterprise is the right tier
4. Next steps (5 min) — proposal timeline, questions

**After the call:**
- Send a brief summary of what was discussed and agreed
- Begin drafting the proposal

---

### Phase 2: Proposal & Contract (Days 5–10)

**Proposal should include:**
- Tailored description of how ColtraDataAi addresses their specific use case
- Which domain cleaners are relevant to them
- SLA commitments (1-hour response, 4-hour resolution for P1)
- Onboarding schedule
- Pricing (£999/month, annual discount available on request)
- Data processing agreement (DPA) confirmation — Coltrane Ltd as data processor
- Any custom scope items (additional domain cleaner, branded outputs, database connection support)

**Contracting:**
- Standard: month-to-month at £999
- Annual: offer 10% discount (£10,788/year vs £11,988 monthly)
- Enterprise customers get a Data Processing Agreement on request
- Use a signed order confirmation email as the contract for month-to-month; use a formal MSA for annual or large-volume deals

---

### Phase 3: Technical Setup (Days 10–14)

**Provision in Supabase:**
```bash
python scripts/create_api_key.py \
  --email "finance-director@company.com" \
  --label "Company Name — Enterprise"
```

**Configure their account:**
- Set plan to `enterprise` in `subscriptions` table
- Note any custom branding requirements in the customer record
- If database connection required: arrange a separate technical session with the developer

**Confirm with customer:**
- App URL: `app.coltradata.com`
- Login method: email OTP (they will receive a 6-digit code via Resend)
- What to expect on first login

---

### Phase 4: Onboarding Session (Day 14 — 60 min)

Schedule a live session (video call). Cover:

**Agenda:**
1. Platform walkthrough (15 min):
   - Login flow (OTP)
   - File upload (CSV, XLSX, XLS)
   - Selecting the correct domain cleaner
   - Running a clean
2. Reading the results (15 min):
   - KPI banner (Issues, Cleaned Rows, Risk Level)
   - Findings table — what each flag means
   - Charts and dashboards
3. Reports (10 min):
   - Downloading Excel (multi-sheet) and PDF
   - Branded outputs (client-ready)
   - AI insights section (Enterprise uses Opus model)
4. Enterprise API (if applicable) (10 min):
   - Quick-start with their API key
   - Live demo call
5. Q&A (10 min)

**After the session:**
- Send a written summary of what was covered
- Attach relevant API documentation
- Confirm their dedicated support contact

---

### Phase 5: Go-Live (Day 14+)

- Customer is now independently using the platform
- First invoice raised via LemonSqueezy (manual invoice if annual contract)
- Confirm all team members who need access have been given login guidance

---

### Phase 6: Review Cadence

| Milestone | Format | Agenda |
|---|---|---|
| 30-day review | 30-min call | Is the platform meeting expectations? Any friction points? |
| 60-day review | Email or call | Usage stats, any new use cases, expansion opportunities |
| 90-day review | 45-min call | Full review: ROI, time saved, quality improvement. Begin renewal / upsell conversation. |
| Quarterly thereafter | 30-min call | Roadmap preview, new features, case study opportunity |

---

## Escalation & Support (Both Enterprise Tiers)

| Situation | Action | SLA |
|---|---|---|
| API key not working | Check `api_keys` table; re-provision if needed | Enterprise API: 2 h; Enterprise £999: 1 h |
| Cleaner producing incorrect results | Escalate to Developer; provide sample dataset | Enterprise API: 4 h; Enterprise £999: 2 h |
| App unavailable | P1 incident response (see SOP Section 10) | Acknowledge 15 min; resolve 4 h |
| Data security / GDPR concern | Escalate to Platform Owner immediately | 1 h |
| Contract / billing query | Platform Owner; resolve or escalate to finance | 4 h |

---

## Email Templates

### A: API Welcome Email (Enterprise API)

```
Subject: Your ColtraDataAi API Key — Welcome to Enterprise API

Hi [Name],

Thank you for subscribing to ColtraDataAi Enterprise API.

Your API key is:

  cdai_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

Keep this key secure — it will not be shown again. If it is ever compromised,
contact us immediately at support@coltradata.com and we will revoke and replace it.

Getting started:

curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \
  -H "Authorization: Bearer cdai_YOUR_KEY" \
  -F "file=@your_data.csv"

Supported domains: finance, logistics, retail, trade, healthcare,
                   consultant, sme, hospitality

Full documentation: https://coltradata-api.onrender.com/docs

If you have any questions or need help integrating, reply to this email or
reach out at support@coltradata.com — we aim to respond within 2 business hours.

Welcome aboard.

— The ColtraDataAi Team
Coltrane Ltd · support@coltradata.com
```

### B: Technical Support Offer (no API calls after 24 h)

```
Subject: ColtraDataAi API — Need any help getting started?

Hi [Name],

We noticed you haven't made your first API call yet — that's completely fine,
it can take a day or two to integrate.

If you have any questions about the request format, authentication, or which
domain cleaner to use, we're happy to help. Just reply to this email.

Alternatively, our documentation is available at:
https://coltradata-api.onrender.com/docs

— ColtraDataAi Support
```

### C: Enterprise Discovery Call Confirmation

```
Subject: ColtraDataAi Enterprise — Confirmed: [Date/Time] Discovery Call

Hi [Name],

Thank you for your interest in ColtraDataAi Enterprise.

I've confirmed our 30-minute discovery call for:

  [Date], [Time] [Timezone]
  [Video call link]

On the call, we'll cover your current data challenges, how ColtraDataAi
can fit into your workflow, and next steps.

If you need to reschedule, please reply to this email or use the link below:
[Reschedule link]

Looking forward to speaking with you.

— [Name], Coltrane Ltd
```

### D: Enterprise Onboarding Confirmation

```
Subject: Your ColtraDataAi Enterprise Account is Ready

Hi [Name],

Your ColtraDataAi Enterprise account is now active.

App URL: https://app.coltradata.com
Login: Enter your email address and we'll send a 6-digit code to sign in.

Your dedicated support contact is [Name] at support@coltradata.com.
For urgent issues, use the subject line URGENT: [Company Name].

Our onboarding session is scheduled for:
  [Date], [Time] [Timezone]
  [Video call link]

We look forward to working with you.

— The ColtraDataAi Team
```

---

*End of Enterprise Onboarding Playbook v1.0 — Review date: 01 February 2027*
