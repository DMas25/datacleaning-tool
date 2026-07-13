# Render Deployment Checklist — ColtraDataAi

This guide deploys two services to Render:
- **`coltradata-app`** — the Streamlit app (replaces Streamlit Community Cloud)
- **`coltradata-webhook`** — the LemonSqueezy webhook receiver

Both are defined in `render.yaml` and deploy together via Render Blueprints.

---

## Step 1 — Supabase (database)

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard) and create
   a **new project** (choose the `eu-west-2` region to stay close to UK customers).

2. Once the project is ready, open the **SQL Editor** and paste the contents of
   `database/supabase_schema.sql`, then click **Run**.

3. Copy the connection string:
   - Project Settings → **Database** → **Connection string**
   - Select the **URI** tab and the **Transaction mode** pooler (port **6543**)
   - Format: `postgresql://postgres.<ref>:<password>@aws-0-eu-west-2.pooler.supabase.com:6543/postgres`
   - Save this — you'll need it in Step 2.

---

## Step 2 — Render Blueprint (both services)

1. Log in to [https://dashboard.render.com](https://dashboard.render.com).

2. Click **New** → **Blueprint** → **Connect a GitHub repository** →
   choose the `DataCleaningApp` repo.

3. Render detects `render.yaml` and creates **both** services: `coltradata-app` and
   `coltradata-webhook`. Click **Apply**.

4. Once both services are created, open **`coltradata-app`** → **Environment** tab
   and fill in all `sync: false` variables:

   | Key | Value |
   |-----|-------|
   | `CREDENTIALS_PASSWORD` | Your app login password (what users type to sign in) |
   | `ADMIN_PASSWORD` | Internal Coltrane staff bypass password |
   | `ADMIN_DASHBOARD_PASSWORD` | Admin analytics dashboard password |
   | `ADMIN_INSIGHTS_PASSWORD` | Internal insights dashboard password |
   | `ANTHROPIC_API_KEY` | Your Claude API key from console.anthropic.com |
   | `SMTP_USER` | support@coltradata.com (or your actual mailbox) |
   | `SMTP_PASSWORD` | Your Office 365 app password |
   | `SMTP_FROM` | noreply@coltradata.com |
   | `APP_URL` | The public URL once custom domain is set (e.g. `https://app.coltradataai.com`) |
   | `DATABASE_URL` | Supabase connection string from Step 1 |

   Leave `SMTP_ENABLED = false` until email is tested and ready.

5. Open **`coltradata-webhook`** → **Environment** tab and fill in:

   | Key | Value |
   |-----|-------|
   | `LEMONSQUEEZY_WEBHOOK_SECRET` | (paste from Step 3 below — come back here) |
   | `DATABASE_URL` | Same Supabase connection string as above |

6. Click **Save Changes** on both services and wait for deploys to finish (**Logs** tab).

7. Verify the webhook server is healthy:
   `https://coltradata-webhook.onrender.com/health`
   Expected: `{"service": "ColtraDataAI webhook", "status": "ok", ...}`

8. Verify the Streamlit app loads:
   `https://coltradata-app.onrender.com`
   Expected: ColtraDataAi login screen (no `dmas25` branding).

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

4. Click **Save** and copy the **Signing secret** displayed.

5. Go back to Render → `coltradata-webhook` → **Environment** and paste the signing
   secret as `LEMONSQUEEZY_WEBHOOK_SECRET`. Save.

---

## Step 4 — Custom domain (removes all Streamlit/dmas25 branding)

This step gives users a clean URL like `app.coltradataai.com` with no third-party
platform branding visible.

1. In Render → `coltradata-app` → **Settings** → **Custom domains** → **Add custom domain**.

2. Enter your domain (e.g. `app.coltradataai.com`) and click **Save**.

3. Render will show you a **CNAME target** (e.g. `coltradata-app.onrender.com`).

4. At your DNS provider (wherever `coltradataai.com` is registered), add a CNAME record:
   - **Host / Name**: `app`
   - **Points to / Value**: `coltradata-app.onrender.com`
   - **TTL**: 300 (or lowest available)

5. Wait for DNS propagation (usually 2–10 minutes). Render will automatically issue
   a free TLS certificate via Let's Encrypt once the CNAME resolves.

6. Once live, go back to Render → `coltradata-app` → **Environment** and update:
   `APP_URL = https://app.coltradataai.com`
   Then click **Save** (triggers a redeploy).

---

## Step 5 — Import swap (activate PostgreSQL licence manager)

Once Supabase is set up and the app is running on Render:

1. In your editor, do a project-wide find-and-replace:
   - Find:    `from services.licence_manager import`
   - Replace: `from services.licence_manager_pg import`

2. Commit and push — Render will auto-redeploy.

---

## Step 6 — Verify end-to-end

1. In LemonSqueezy → Settings → Webhooks → click your webhook → **Send test**.

2. Render → `coltradata-webhook` → **Logs**: confirm you see:
   ```
   Webhook signature verified
   upsert_subscription  email=...  plan=...
   ```

3. Supabase → **Table Editor** → `subscriptions`: confirm a new row appeared.

4. Open `https://app.coltradataai.com` in a private/incognito window: confirm the
   ColtraDataAi login screen loads with no Streamlit or `dmas25` branding.

---

## Step 7 — Retire Streamlit Community Cloud (optional)

Once the custom domain is live and tested:

1. Streamlit Cloud dashboard → select `ColtraDataAi` → **Settings** → **Delete app**.
2. This removes the `dmas25` profile exposure entirely.

---

## Troubleshooting

### App shows a blank page or 502
Check Render → `coltradata-app` → **Logs**. Common causes:
- `CREDENTIALS_PASSWORD` not set → startup script exits with error
- `run_render.sh` not executable → Render runs it via `bash run_render.sh` so this
  is not an issue (no execute bit needed)
- Missing package → check if `pip install -r requirements.txt` completed in the build log

### AI Advisor feature not working
Confirm `ANTHROPIC_API_KEY` is set in Render → `coltradata-app` → **Environment**.
The key must start with `sk-ant-`.

### 401 response from `/lemonsqueezy/webhook`
HMAC signature check failed. Re-copy the signing secret from LemonSqueezy →
Settings → Webhooks → (your webhook) → Signing secret, and paste it into
`LEMONSQUEEZY_WEBHOOK_SECRET` in the `coltradata-webhook` service. Save and redeploy.

### 500 from `/lemonsqueezy/webhook`
Check Render logs for a Python traceback. Most common cause: `DATABASE_URL` not set
or Supabase schema not applied. Verify Step 1.

### Health check fails / service marked unhealthy (webhook server)
Render sends `GET /health` every 30 seconds. Confirm uvicorn started on `$PORT`
(look for `Uvicorn running on http://0.0.0.0:<port>` in logs).

### Service sleeping / slow cold starts
Verify both services are on the **Starter** plan, not Free.
Render dashboard → service → **Settings** → **Instance type**.
