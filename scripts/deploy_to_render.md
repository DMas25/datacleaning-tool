# Render Deployment Checklist — ColtraDataAI Webhook Server

This guide walks through deploying `services/webhook_server.py` (FastAPI + uvicorn)
to Render as a Web Service, wiring it to Supabase PostgreSQL, and registering the
live URL with LemonSqueezy.

---

## Step 1 — Supabase (database)

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard) and create
   a **new project** (choose the `eu-west-2` region to stay close to UK customers).

2. Once the project is ready, open the **SQL Editor** and paste the contents of
   `database/supabase_schema.sql`, then click **Run**.  
   This creates the `subscriptions` and `webhook_events` tables.

3. Copy the connection string:
   - Project Settings → **Database** → **Connection string**
   - Select the **URI** tab and the **Transaction mode** pooler (port **6543**)
   - It looks like:  
     `postgresql://postgres.<ref>:<password>@aws-0-eu-west-2.pooler.supabase.com:6543/postgres`
   - Save this — you'll need it in Step 2.

---

## Step 2 — Render (web service)

1. Log in to [https://dashboard.render.com](https://dashboard.render.com).

2. Click **New** → **Blueprint** → select **Connect a GitHub repository** →
   choose the `DataCleaningApp` repo.

3. Render will detect `render.yaml` at the repo root automatically.  
   Click **Apply** — Render creates the `coltradata-webhook` web service.

4. Once the service is created, open it and go to the **Environment** tab.  
   Add the two secret variables:

   | Key | Value |
   |-----|-------|
   | `LEMONSQUEEZY_WEBHOOK_SECRET` | (paste from Step 3 below — come back here after Step 3) |
   | `DATABASE_URL` | The Supabase connection string from Step 1 |

5. Click **Save Changes** and wait for the deploy to finish (watch the **Logs** tab).

6. Visit:  
   `https://coltradata-webhook.onrender.com/health`  
   Expected response:
   ```json
   {"service": "ColtraDataAI webhook", "status": "ok", ...}
   ```
   If you see a 502 or timeout, check the Render logs (see Troubleshooting below).

---

## Step 3 — LemonSqueezy webhook registration

1. In [LemonSqueezy](https://app.lemonsqueezy.com) go to **Settings** → **Webhooks**
   → **Add webhook**.

2. Set the **URL** to:  
   `https://coltradata-webhook.onrender.com/lemonsqueezy/webhook`

3. Tick the following events:
   - `order_created`
   - `subscription_created`
   - `subscription_updated`
   - `subscription_cancelled`

4. Click **Save**.

5. Copy the **Signing secret** that LemonSqueezy displays.

6. Go back to Render → `coltradata-webhook` → **Environment** and paste the signing
   secret as the value for `LEMONSQUEEZY_WEBHOOK_SECRET`. Save.

---

## Step 4 — Streamlit Cloud (connect to Supabase)

1. Open `.streamlit/secrets.toml` in your local repo and add a `[supabase]` section:

   ```toml
   [supabase]
   database_url = "postgresql://postgres.<ref>:<password>@aws-0-eu-west-2.pooler.supabase.com:6543/postgres"
   ```

2. Push the updated `secrets.toml` **or** (better for security) add the value
   directly in the **Streamlit Cloud** dashboard under **App settings → Secrets**.

3. Trigger a redeploy from the Streamlit Cloud dashboard (or push any commit).

---

## Step 5 — Verify end-to-end

1. In LemonSqueezy → Settings → Webhooks → click your webhook → **Send test**.

2. Open Render → `coltradata-webhook` → **Logs** and confirm you see lines like:
   ```
   Webhook signature verified
   upsert_subscription  email=...  plan=...
   ```

3. In Supabase → **Table Editor** → `subscriptions`, confirm a new row appeared
   with the test customer email.

---

## Step 6 — Make the Streamlit app publicly visible (IMPORTANT)

The Streamlit Cloud app is currently set to **"Only specific people can view this
app"** which will block paying customers from reaching the app after checkout.

Before going live:

1. Streamlit Cloud dashboard → select your app → **Settings** → **Sharing**.
2. Change to **"Anyone can view this app"**.
3. Save.

Confirm by opening the app URL in a private/incognito browser window — it should
load without asking for a Streamlit login.

---

## Troubleshooting

### 401 response from `/lemonsqueezy/webhook`
The HMAC signature check failed. This almost always means `LEMONSQUEEZY_WEBHOOK_SECRET`
in Render does not match the signing secret in LemonSqueezy. Re-copy the secret from
LemonSqueezy → Settings → Webhooks → (your webhook) → Signing secret, and paste it
into the Render environment variable. Save and redeploy if needed.

### 500 response from `/lemonsqueezy/webhook`
Look at **Render Logs** for a Python traceback. The most common cause is
`DATABASE_URL` not being set (or the Supabase schema not having been applied). Verify
both in Step 1 and Step 2 above.

### Health check fails / service marked unhealthy
Render sends `GET /health` every 30 seconds. If it fails:
- Confirm uvicorn started and bound to `$PORT` (check Render logs for
  `Uvicorn running on http://0.0.0.0:<port>`).
- The `startCommand` in `render.yaml` passes `--port $PORT` — ensure you have not
  accidentally hardcoded `8001` in a local override.

### Render service sleeping / slow cold start
Verify the service plan is **Starter**, not **Free**. Free-tier services sleep after
15 minutes of inactivity and would miss webhooks during the cold-start window.
Check: Render dashboard → `coltradata-webhook` → **Settings** → **Instance type**.
