# ColtraDataAi — Standard Operating Procedure (SOP)

**Version:** 1.1  
**Effective:** 01 August 2026  
**Owner:** Coltrane Ltd · support@coltradata.com

---

## 1. Purpose & Scope

This SOP defines the operational procedures for running the ColtraDataAi platform across three surfaces:

| Surface | URL | Hosting |
|---|---|---|
| Web application | `https://app.coltradata.com` | Render (Frankfurt) |
| Enterprise API | `https://coltradata-api.onrender.com` | Render (Frankfurt) |
| Marketing website | `https://coltradata.com` | GitHub Pages |

It covers daily and weekly operations, customer support, billing, enterprise onboarding, deployment, incident response, GDPR compliance, and website management. All team members with operational access must follow this document.

---

## 2. System Architecture Overview

```
Customer browser
    │
    ▼
app.coltradata.com   (Render — coltradata-app service)
    │
    ├── Supabase Auth (OTP via Resend)
    ├── Supabase PostgreSQL (subscriptions, API keys, usage logs)
    ├── Supabase Storage (reports bucket — signed URLs)
    ├── Anthropic API (AI insights — Business: Sonnet, Enterprise: Opus)
    └── LemonSqueezy (subscription billing)
          │
          └── Supabase Edge Function (lemonsqueezy-webhook)
                    → upsert subscription
                    → generate licence key
                    → email via Resend

Enterprise API:
coltradata-api.onrender.com  (Render — coltradata-api service)
    │
    ├── Bearer token auth → Supabase api_keys table
    └── Usage logging → Supabase api_usage_log table
```

**Key environment (Render — coltradata-app):**
`ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `RESEND_API_KEY`, `DATABASE_URL`, `APP_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`

---

## 3. Roles & Responsibilities

| Role | Responsibility |
|---|---|
| Platform Owner | Deployment approvals, billing config, enterprise contracting |
| Support | Customer tickets, licence issues, billing queries |
| Developer | Code changes, API key provisioning (manual), incident response |

---

## 4. Daily Operations Checklist

Run each working day (takes < 5 minutes):

- [ ] Open Render dashboard — confirm `coltradata-app` and `coltradata-api` are **Live** (green)
- [ ] Check Supabase dashboard — confirm project is active (West EU / Ireland)
- [ ] Check LemonSqueezy dashboard — review any new orders or subscription events from the past 24 h
- [ ] Check `support@coltradata.com` inbox — acknowledge any customer tickets (SLA: 4 hours for Business/Enterprise, 24 h for others)
- [ ] Check Supabase Edge Function logs (`lemonsqueezy-webhook`) — verify no failed webhook deliveries
- [ ] Spot-check `api_usage_log` for anomalous API usage (unusually high row counts, unknown key IDs)

---

## 5. Weekly Operations Checklist

Run every Monday:

- [ ] Review Supabase `api_usage_monthly` view — confirm all active API customers have used service
- [ ] Review LemonSqueezy MRR and churn report — flag any unexpected cancellations
- [ ] Run full functional smoke test (see `docs/qa_checklist.md`)
- [ ] Review Render resource usage — CPU, memory, bandwidth for both services
- [ ] Review any outstanding support tickets from the prior week
- [ ] Rotate any secrets flagged for rotation (see Section 8)
- [ ] Check `docs/qa_checklist.md` for any items marked pending from the last deploy

---

## 6. Customer Support SOP

### 6.1 Support Tiers & SLA

| Plan | Channels | Response SLA | Resolution SLA |
|---|---|---|---|
| Free | Email only | 5 business days | Best effort |
| Starter | Email | 3 business days | 5 business days |
| Professional | Email | 2 business days | 3 business days |
| Business | Email, priority queue | 4 business hours | 1 business day |
| Enterprise API | Email, priority queue | 2 business hours | 4 business hours |
| Enterprise £999 | Dedicated contact, email | 1 business hour | 2 business hours |

### 6.2 Common Issues & Resolutions

| Issue | Likely Cause | Action |
|---|---|---|
| "My plan shows as Free" | Subscription not linked to email | Ask for email used at checkout; look up in Supabase `subscriptions` table; re-send licence key via Resend |
| "I didn't receive my licence key" | Email went to spam / Resend delivery failure | Check Resend logs; manually send key via `scripts/send_licence.py` |
| "My API key returns 401" | Key deactivated or wrong format | Look up key hash in `api_keys` table; check `is_active = true`; verify Bearer token format `cdai_…` |
| "File upload failing" | File too large or format unsupported | Confirm CSV/XLSX/XLS; check row limit for tier; advise splitting large files |
| "AI insights not appearing" | AI feature not available on their tier | Confirm tier is Business or above; check Anthropic API key in Render env |
| "Report download fails" | Supabase Storage signed URL expired | Advise re-running clean to regenerate; signed URLs expire after 3600 s |
| "OTP code not received" | Resend delivery failure or wrong email | Check Resend dashboard; confirm email address; re-send OTP |

### 6.3 Escalation Path

1. **Tier 1** — Support (this document)
2. **Tier 2** — Developer (billing pipeline, API auth, data processing bugs)
3. **Tier 3** — Platform Owner (enterprise contracts, legal queries, data breach)

---

## 7. Subscription & Billing SOP

### 7.1 New Subscriptions (Automated)

The standard flow requires no manual action:

1. Customer pays on LemonSqueezy (`coltradataai.lemonsqueezy.com`)
2. LemonSqueezy fires `order_created` / `subscription_created` webhook to Supabase Edge Function
3. Edge Function upserts subscription in Supabase PostgreSQL, generates licence key, emails key via Resend
4. Customer signs in at `app.coltradata.com` → OTP → plan activates

**If webhook fails:** Check Supabase Edge Function logs. Re-trigger via LemonSqueezy webhook resend. If LemonSqueezy resend unavailable, manually provision (see 7.5).

### 7.2 Plan Upgrades

LemonSqueezy handles prorated upgrades automatically. Verify the `subscription_updated` event is received in Edge Function logs. Customer's plan should update on next sign-in.

### 7.3 Cancellations

LemonSqueezy fires `subscription_cancelled`. Edge Function sets `status = 'cancelled'` in Supabase. Customer retains access until end of billing period. No manual action needed.

### 7.4 Refunds

Refunds are processed in LemonSqueezy (30-day satisfaction guarantee, handled case by case for other requests). After issuing a refund, set `status = 'cancelled'` in Supabase manually if webhook has not fired.

### 7.5 Manual Subscription Provision

Only use when automated flow fails after confirming payment:

```sql
-- In Supabase SQL editor
INSERT INTO subscriptions (email, plan, status, licence_key, created_at)
VALUES ('customer@example.com', 'professional', 'active', 'CDAI-XXXX-XXXX-XXXX', now());
```

Then send the key via email manually referencing the licence email template.

---

## 8. Enterprise API Key Management SOP

### 8.1 Auto-Provisioning (Standard)

Triggered automatically via the LemonSqueezy → Supabase Edge Function flow when a customer purchases the Enterprise API plan. No manual action required.

### 8.2 Manual Key Provisioning

Used for: Enterprise £999 customers, pilots, replacements.

```bash
# From the DataCleaningApp directory
python scripts/create_api_key.py \
  --email "customer@company.com" \
  --label "Company Name — API Key"
```

The script outputs the raw key (begins `cdai_`). Store the key in the email to the customer — **it cannot be recovered after creation** (only the SHA-256 hash is stored in Supabase).

### 8.3 Key Rotation

If a customer suspects their key is compromised:

1. Deactivate old key in Supabase:
   ```sql
   UPDATE api_keys SET is_active = false WHERE email = 'customer@company.com';
   ```
2. Run `create_api_key.py` to generate and send a new key.
3. Log the rotation with date and reason in the customer's support record.

### 8.4 Key Revocation (Subscription Cancelled)

```sql
UPDATE api_keys SET is_active = false WHERE email = 'customer@company.com';
```

Confirm with a notification to the customer.

---

## 9. Deployment SOP

### 9.1 Web Application (Render — coltradata-app)

Deploys automatically when code is pushed to `master` on GitHub.

**Pre-push checklist (always run):**
1. [ ] `docs/qa_checklist.md` — all smoke test items passed locally
2. [ ] No secrets or `.env` files staged (`git status` clean of secrets)
3. [ ] `requirements.txt` updated if packages changed
4. [ ] No advisory language in any new copy

**Post-deploy:**
1. [ ] Render dashboard shows deploy succeeded (green)
2. [ ] Navigate to `app.coltradata.com` — app loads, login works
3. [ ] Run QA smoke test steps 1–7

### 9.2 Enterprise API (Render — coltradata-api)

Uses the same GitHub repo, deployed via `render.yaml` Blueprint. Changes to `api/` trigger a redeploy.

**Post-deploy:**
1. [ ] `GET https://coltradata-api.onrender.com/health` returns `{"status": "ok"}`
2. [ ] `POST /v1/clean/finance` with test key and sample CSV returns cleaned data

### 9.3 Marketing Website (GitHub Pages)

Deployed from `docs/` folder on the `master` branch.

**Update process:**
1. Edit the relevant HTML file in `docs/`
2. Test locally (open file in browser)
3. Commit and push to `master`
4. GitHub Pages redeploys automatically (< 2 minutes)
5. Verify change is live at `coltradata.com`

---

## 10. Incident Response

### 10.1 Severity Classification

| Severity | Definition | Example |
|---|---|---|
| P1 — Critical | Platform completely unavailable; data breach | App down, API down, security incident |
| P2 — High | Core feature broken for paying customers | File upload failing, report generation failing |
| P3 — Medium | Non-core feature degraded; intermittent issues | Chart not rendering, analytics cookies broken |
| P4 — Low | Minor visual/copy issue | Typo on website, misaligned UI element |

### 10.2 Response Procedures

**P1:**
1. Confirm the incident (attempt to reproduce)
2. Post a status message to the status page / social if available
3. Escalate immediately to Developer + Platform Owner
4. Investigate Render logs and Supabase logs in parallel
5. Implement fix or rollback (Render: redeploy previous release from dashboard)
6. Confirm resolution and notify affected Enterprise customers directly

**P2:**
1. Reproduce and log the issue
2. Assign to Developer
3. Notify affected customers via support ticket with ETA
4. Deploy fix following standard deployment SOP

**P3/P4:**
1. Log in GitHub Issues
2. Schedule for next sprint
3. No customer notification required unless directly reported by customer

### 10.3 Rollback Procedure

In Render: Render dashboard → Service → Deploys → select a previous successful deploy → Manual Deploy.

For Supabase schema changes: write a compensating SQL migration and apply via Supabase SQL editor. Never run destructive migrations without a backup.

### 10.4 Incident Communication Template (P1)

```
Subject: ColtraDataAi Service Incident — [Date/Time]

We are aware of an issue affecting [describe affected service].
We are investigating and will provide an update within [time].

Services affected: [list]
Services not affected: [list]

We apologise for the inconvenience.

— ColtraDataAi Support Team
```

---

## 11. GDPR & Data Compliance SOP

### 11.1 Data Subject Requests

All requests must be acknowledged within **72 hours** and fulfilled within **one calendar month**.

| Request Type | Action |
|---|---|
| Access (SAR) | Export customer record from Supabase (subscriptions, api_keys, api_usage_log, webhook_log). Exclude hashed keys. |
| Erasure | Delete records from all Supabase tables for that email. Remove from LemonSqueezy if subscription active. |
| Rectification | Update relevant fields in Supabase. |
| Portability | Export as JSON/CSV from Supabase. |

Log all requests and outcomes. Retain the log for 3 years.

### 11.2 Data Breach Response

1. **Identify and contain** — disable affected services or API keys immediately
2. **Assess** — determine what data was exposed, how many individuals affected
3. **Notify the ICO** within **72 hours** if the breach is likely to result in a risk to individuals' rights and freedoms
4. **Notify affected individuals** without undue delay if high risk
5. **Document** the breach, response actions, and outcome in a breach register

Contact: ICO self-reporting portal at `ico.org.uk/report`

---

## 12. Website & Content Management

### 12.1 Content Update Process

All website content lives in `docs/*.html` and is deployed via GitHub Pages.

When updating copy, pricing, or legal pages:
1. Edit the relevant HTML file
2. Update the `Last updated` date on legal pages (privacy.html)
3. If pricing changes: update `docs/pricing.html` AND `docs/index.html` (pricing section)
4. Push to `master` — GitHub Pages auto-deploys
5. Verify live within 2 minutes

### 12.2 Legal Page Update Triggers

| Event | Pages to Update |
|---|---|
| New third-party service added | `docs/privacy.html` — Section 6 |
| New data type collected | `docs/privacy.html` — Sections 2 and 5 |
| Pricing change | `docs/pricing.html`, `docs/index.html` |
| New integration (Xero, QB, Sage, database) | `docs/privacy.html` — Section 5 |
| New domain cleaner | Industry-specific landing page in `docs/` |

---

## 13. Offboarding (Customer or Team Member)

### 13.1 Customer Offboarding

On cancellation (automated via LemonSqueezy webhook):
- Subscription marked cancelled in Supabase
- Access ends at billing period end
- Data retained per privacy policy retention schedule

On erasure request:
- Delete all personal data from Supabase tables
- Confirm deletion to customer in writing

### 13.2 Team Member Offboarding

1. Remove access to Render dashboard
2. Remove access to Supabase project
3. Remove access to LemonSqueezy
4. Rotate any shared secrets the team member had access to (see Section 8.3)
5. Remove from GitHub repository collaborators
6. Document the removal date and reason

---

*End of SOP v1.1 — Review date: 01 February 2027*
