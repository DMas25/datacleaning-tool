# ColtraDataAi — API Reference

**Version:** v1  
**Base URL:** `https://coltradata-api.onrender.com`  
**Interactive docs:** `https://coltradata-api.onrender.com/docs`  
**Owner:** Coltrane Ltd - support@coltradata.com

---

## Table of Contents

1. [Overview](#overview)
2. [Versioning](#versioning)
3. [Authentication](#authentication)
4. [Test Mode](#test-mode)
5. [Endpoints](#endpoints)
   - [GET /health](#get-health)
   - [GET /v1/domains](#get-v1domains)
   - [POST /v1/clean/{domain}](#post-v1cleandomain)
6. [Request Formats](#request-formats)
7. [Response Schema](#response-schema)
8. [Error Reference](#error-reference)
9. [Rate Limits and Fair Use](#rate-limits-and-fair-use)
10. [Usage Tracking](#usage-tracking)
11. [Onboarding Checklist](#onboarding-checklist)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The ColtraDataAi Enterprise API gives developers programmatic access to ColtraDataAi's domain-specific data cleaners. You send a file or JSON payload, specify a domain (e.g. `finance`, `logistics`), and receive cleaned records with quality metrics and a structured issues report.

The API is designed for:

- Embedding data cleaning into internal tools and ETL pipelines
- Automating pre-upload validation before accounting or ERP imports
- Batch-processing datasets without using the web application

The API is available on the **Enterprise API** plan (£199/month). Each call logs metadata (domain, row count, timestamp) but the submitted data itself is never stored.

---

## Versioning

All cleaning endpoints are prefixed with `/v1`. The version is stable and backwards-compatible within `v1`. Breaking changes will be introduced under a new prefix (e.g. `/v2`) with advance notice by email.

The current API version is `1.0.0`.

---

## Authentication

Every request to a `/v1/` endpoint must include a Bearer token in the `Authorization` header.

```
Authorization: Bearer cdai_YOUR_API_KEY
```

API keys are issued in the format `cdai_` followed by a 43-character URL-safe random string. Keys are hashed (SHA-256) before storage; the raw key is shown only once at the time of provisioning.

**Security guidance:**

- Store the key in an environment variable or secrets manager, never in source code
- If a key is compromised, contact support@coltradata.com immediately for revocation and replacement
- Keys are tied to the purchasing email address and must not be shared across organisations or resold

---

## Test Mode

The API does not have a separate sandbox environment. For integration testing:

**1. Swagger UI (recommended for initial testing)**

Open `https://coltradata-api.onrender.com/docs` in a browser. Paste your key into the Authorize dialog (top right) and call any endpoint interactively without writing code. The response is shown inline.

**2. Health check (no authentication required)**

```bash
curl https://coltradata-api.onrender.com/health
```

Expected response:
```json
{"status": "ok", "service": "ColtraDataAi Enterprise API"}
```

**3. First real call with a small sample**

Use 3-5 rows in a CSV or JSON body to verify your key, domain selection, and output parsing before running production volume. This is the recommended first step before integrating into a pipeline.

---

## Endpoints

### GET /health

Returns the operational status of the API. No authentication required.

**Request**
```
GET /health
```

**Response (200)**
```json
{
  "status": "ok",
  "service": "ColtraDataAi Enterprise API"
}
```

---

### GET /v1/domains

Returns the list of supported cleaning domains. No authentication required.

**Request**
```
GET /v1/domains
```

**Response (200)**
```json
{
  "domains": [
    "finance",
    "logistics",
    "retail",
    "trade",
    "healthcare",
    "consultant",
    "sme",
    "hospitality"
  ]
}
```

---

### POST /v1/clean/{domain}

Cleans a dataset using the domain-specific cleaner. Accepts CSV (multipart) or JSON.

**Path parameter**

| Parameter | Type   | Required | Description                             |
|-----------|--------|----------|-----------------------------------------|
| `domain`  | string | Yes      | One of the supported domain identifiers |

**Supported domains**

| Domain        | Use case                                                  |
|---------------|-----------------------------------------------------------|
| `finance`     | Transaction records, ledger data, bank exports            |
| `logistics`   | Shipment, delivery, and freight records                   |
| `retail`      | Sales, inventory, and product data                        |
| `trade`       | Import/export, customs, and cross-border records          |
| `healthcare`  | Patient, appointment, and clinical records                |
| `consultant`  | Time entries, project records, and client billing data    |
| `sme`         | General small business records across mixed domains       |
| `hospitality` | Bookings, reservations, and guest records                 |

---

## Request Formats

The `/v1/clean/{domain}` endpoint accepts two content types. Use whichever fits your pipeline.

### CSV upload (multipart/form-data)

Send the file as a `file` field in a multipart form. The CSV must have a header row.

```bash
curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \
  -H "Authorization: Bearer cdai_YOUR_KEY" \
  -F "file=@transactions.csv"
```

### JSON body (application/json)

Send an array of record objects. Two formats are accepted:

**Array format:**
```bash
curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \
  -H "Authorization: Bearer cdai_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '[{"date": "01/01/2026", "amount": "1000", "type": "DR"}]'
```

**Object with rows key:**
```bash
curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \
  -H "Authorization: Bearer cdai_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rows": [{"date": "01/01/2026", "amount": "1000", "type": "DR"}]}'
```

**Python example:**
```python
import requests

API_KEY = "cdai_YOUR_KEY"
BASE_URL = "https://coltradata-api.onrender.com"

# CSV upload
with open("transactions.csv", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/v1/clean/finance",
        headers={"Authorization": f"Bearer {API_KEY}"},
        files={"file": ("transactions.csv", f, "text/csv")},
    )

result = response.json()
print(result["rows_processed"])
```

**Node.js example:**
```javascript
const FormData = require("form-data");
const fs = require("fs");
const fetch = require("node-fetch");

const form = new FormData();
form.append("file", fs.createReadStream("transactions.csv"));

const response = await fetch("https://coltradata-api.onrender.com/v1/clean/finance", {
  method: "POST",
  headers: {
    Authorization: "Bearer cdai_YOUR_KEY",
    ...form.getHeaders(),
  },
  body: form,
});

const result = await response.json();
console.log(result.rows_processed);
```

---

## Response Schema

A successful `POST /v1/clean/{domain}` call returns HTTP 200 with this body:

```json
{
  "domain": "finance",
  "rows_processed": 150,
  "cleaned_data": [
    {
      "date": "2026-01-01",
      "amount": 1000.0,
      "type": "DR"
    }
  ],
  "metrics": {
    "issues_found": 12,
    "rows_with_issues": 8,
    "risk_level": "Medium"
  },
  "issues": [
    {
      "row": 3,
      "column": "date",
      "issue": "Non-standard date format",
      "original_value": "1 Jan 26",
      "corrected_value": "2026-01-01"
    }
  ]
}
```

**Field descriptions**

| Field           | Type             | Description                                                     |
|-----------------|------------------|-----------------------------------------------------------------|
| `domain`        | string           | The domain used for cleaning                                    |
| `rows_processed`| integer          | Number of rows in the cleaned output                            |
| `cleaned_data`  | array of objects | The cleaned records; null values are represented as JSON `null` |
| `metrics`       | object           | Summary statistics from the cleaner (varies by domain)          |
| `issues`        | array of objects | Structured log of each detected and corrected issue             |

The shape of `metrics` and `issues` entries varies by domain. Each domain's cleaner documents the fields it emits; use the Swagger UI at `/docs` to inspect live examples.

---

## Error Reference

All errors return a JSON body with a `detail` field.

```json
{"detail": "Human-readable error description"}
```

| HTTP Status | Meaning                                                                              |
|-------------|--------------------------------------------------------------------------------------|
| `400`       | Bad request - malformed headers or missing required fields                           |
| `401`       | Invalid or inactive API key - check the key value; contact support if recently issued|
| `403`       | Forbidden - key is valid but access is denied (contact support)                      |
| `404`       | Unknown domain - check the domain path parameter against `/v1/domains`               |
| `422`       | Unprocessable content - empty file, unparseable CSV, or invalid JSON structure       |
| `500`       | Cleaning failed - the cleaner encountered an unexpected error; include sample data in support report |
| `503`       | Auth service unavailable - Supabase connectivity issue; retry after 30 seconds       |

**Common 422 causes:**

- CSV file has no header row
- CSV file is empty
- JSON body is not a list or does not have a `rows` key
- File field is missing from multipart form (use `file` exactly)

---

## Rate Limits and Fair Use

There are no hard rate limits enforced on the Enterprise API plan. The following fair-use guidelines apply:

- Automated pipelines must include a delay between calls (recommended: at least 500ms)
- Extremely large datasets (tens of thousands of rows) should be batched into files of 5,000-10,000 rows to avoid long processing times per request
- Sustained high-frequency usage (hundreds of calls per minute) is outside the intended use and may result in account review

If your integration requires defined throughput guarantees or SLA-backed limits, contact support@coltradata.com to discuss an Enterprise £999 arrangement.

---

## Usage Tracking

Every successful `/v1/clean/{domain}` call is logged with:

- API key ID (not the raw key)
- Domain used
- Number of rows processed
- Input format (`csv` or `json`)
- Timestamp (UTC)

The submitted data is processed in memory and is never written to storage. Usage logs are used for billing verification and capacity planning only.

You can request a usage report for your account by emailing support@coltradata.com.

---

## Onboarding Checklist

Follow these steps to go from key to first production call:

- [ ] **Receive API key** - check welcome email for `cdai_...` key; store securely
- [ ] **Verify connectivity** - `curl https://coltradata-api.onrender.com/health` should return `{"status": "ok", ...}`
- [ ] **Test authentication** - call `/v1/domains` with your Bearer token; `401` means an incorrect key
- [ ] **Run a sample clean** - upload 3-5 rows to `/v1/clean/{domain}` using the Swagger UI or curl
- [ ] **Parse the response** - confirm your code reads `cleaned_data`, `metrics`, and `issues` correctly
- [ ] **Handle errors** - add handling for `401`, `422`, `500`, and `503` before going to production
- [ ] **Integrate into pipeline** - wire up your chosen input format (CSV or JSON) in your application
- [ ] **Go live** - run against production data; monitor response times and error rates

---

## Troubleshooting

**API key is rejected (401)**

- Check that the full key is included: it starts with `cdai_` and is 48 characters total
- Ensure there is no trailing whitespace in the key string
- Confirm the `Authorization` header is exactly `Bearer cdai_YOUR_KEY` (space between `Bearer` and the key)
- If the key was issued more than 24 hours ago and has never worked, contact support - provisioning may have failed

**File not parsed (422: "Multipart request must include a 'file' field")**

- The form field name must be `file` (lowercase, no quotes in the field name)
- The file must be UTF-8 encoded CSV with a header row as the first line
- Files with BOM encoding may need to be re-saved as plain UTF-8

**Unexpected cleaning results**

- Confirm you are using the correct domain for your data type
- Use the `issues` array to understand what was detected and corrected
- If the cleaner produces incorrect output for a specific dataset, email support@coltradata.com with a sanitised sample (remove any personally identifiable information)

**Timeout or slow response**

- The Render service cold-starts after inactivity (typically 30-60 seconds on first request)
- For production pipelines, call `GET /health` on startup to wake the service before your first cleaning call
- Very large files (over 10,000 rows) will have longer processing times; consider batching

**503: Auth service unavailable**

- This indicates a temporary connectivity issue between the API and Supabase
- Retry the request after 30 seconds; sustained 503 errors should be reported to support

**Need help?**

Email support@coltradata.com with:
- Your account email address
- The domain and input format you were using
- The full error response body
- A sanitised sample of the data (first 5-10 rows, PII removed)

Target response time: 2 business hours for Enterprise API subscribers.

---

*End of API Reference v1 - Review date: 01 February 2027*  
*Coltrane Ltd - support@coltradata.com*
