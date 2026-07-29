/**
 * ColtraDataAi — LemonSqueezy Webhook Edge Function
 *
 * Replaces services/webhook_server.py (Render service) with a Supabase
 * Edge Function so no separate Render service is needed for the webhook.
 *
 * Deploy:
 *   supabase functions deploy lemonsqueezy-webhook --no-verify-jwt
 *
 * Required Supabase secrets (set via CLI before deploying):
 *   supabase secrets set LEMONSQUEEZY_WEBHOOK_SECRET=<your-secret>
 *   supabase secrets set RESEND_API_KEY=<your-key>
 *   supabase secrets set APP_URL=https://app.coltradata.com
 *
 * SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are injected automatically.
 *
 * After deploying, update the LemonSqueezy webhook URL to:
 *   https://<project-ref>.supabase.co/functions/v1/lemonsqueezy-webhook
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// ── Types ─────────────────────────────────────────────────────────────────────

interface LemonSqueezyPayload {
  meta: { event_name: string; custom_data?: Record<string, string> };
  data: {
    id: string;
    attributes: {
      user_email?: string;
      customer_email?: string;
      order_id?: string;
      status?: string;
      product_name?: string;
      variant_name?: string;
      first_order_item?: { product_name?: string; variant_name?: string };
    };
  };
}

// ── Plan map ──────────────────────────────────────────────────────────────────

const PLAN_MAP: Record<string, string> = {
  Starter: "starter",
  starter: "starter",
  Professional: "professional",
  Pro: "professional",
  professional: "professional",
  Premium: "premium",
  premium: "premium",
  Enterprise: "enterprise",
  enterprise: "enterprise",
};

// ── HMAC signature verification ───────────────────────────────────────────────

async function verifySignature(
  rawBody: Uint8Array,
  signatureHeader: string,
  secret: string
): Promise<boolean> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, rawBody);
  const expected = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return expected === (signatureHeader ?? "").trim();
}

// ── Licence key generation ────────────────────────────────────────────────────

function generateLicenceKey(): string {
  const hex = () =>
    [...crypto.getRandomValues(new Uint8Array(2))]
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
      .toUpperCase();
  return `${hex()}-${hex()}-${hex()}-${hex()}`;
}

// ── Resend email ──────────────────────────────────────────────────────────────

async function sendLicenceEmail(
  to: string,
  key: string,
  plan: string,
  appUrl: string,
  resendKey: string
): Promise<void> {
  const planLabel =
    plan.charAt(0).toUpperCase() + plan.slice(1);
  const body = `Thank you for subscribing to ColtraDataAi ${planLabel}.

Your licence key is:

    ${key}

Sign in at ${appUrl} using the email address you used at checkout.
Your plan will activate automatically — no manual key entry needed.

If you have any questions, contact us at support@coltradata.com

ColtraDataAi by Coltrane Ltd`;

  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${resendKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: "ColtraDataAi <support@coltradata.com>",
      to: [to],
      subject: `Your ColtraDataAi ${planLabel} licence key`,
      text: body,
    }),
  });
}

// ── DB helpers (uses service role — bypasses RLS) ─────────────────────────────

async function upsertSubscription(
  supabase: ReturnType<typeof createClient>,
  email: string,
  plan: string,
  subscriptionId: string,
  orderId: string,
  status: string
): Promise<string> {
  // Reuse existing key if present; generate one if not.
  const { data: existing } = await supabase
    .from("subscriptions")
    .select("licence_key")
    .eq("email", email)
    .maybeSingle();

  const key: string =
    (existing as { licence_key?: string } | null)?.licence_key ??
    generateLicenceKey();

  await supabase.from("subscriptions").upsert(
    {
      email,
      plan,
      licence_key: key,
      subscription_id: subscriptionId || null,
      order_id: orderId || null,
      status,
      updated_at: new Date().toISOString(),
    },
    {
      onConflict: "email",
      ignoreDuplicates: false,
    }
  );

  return key;
}

async function cancelSubscription(
  supabase: ReturnType<typeof createClient>,
  subscriptionId: string
): Promise<boolean> {
  const { count } = await supabase
    .from("subscriptions")
    .update({ plan: "free", status: "inactive", updated_at: new Date().toISOString() })
    .eq("subscription_id", subscriptionId)
    .select("*", { count: "exact", head: true });
  return (count ?? 0) > 0;
}

async function logWebhookEvent(
  supabase: ReturnType<typeof createClient>,
  eventType: string,
  payload: string
): Promise<void> {
  await supabase
    .from("webhook_log")
    .insert({ event_type: eventType, payload, received_at: new Date().toISOString() });
}

// ── Payload extraction ────────────────────────────────────────────────────────

function extractFields(payload: LemonSqueezyPayload) {
  const attrs = payload.data.attributes;
  const meta = payload.meta;

  const email = (
    attrs.user_email ||
    attrs.customer_email ||
    meta.custom_data?.email ||
    ""
  ).toLowerCase().trim();

  const subscriptionId = String(payload.data.id ?? "");
  const orderId = String(attrs.order_id ?? "");

  const firstItem = attrs.first_order_item ?? {};
  const productName = firstItem.product_name || attrs.product_name || "";
  const variantName = firstItem.variant_name || attrs.variant_name || "";

  const planKey =
    PLAN_MAP[variantName] ?? PLAN_MAP[productName] ?? "free";

  return { email, planKey, subscriptionId, orderId, lsStatus: attrs.status ?? "active" };
}

// ── Main handler ──────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ status: "ok", service: "coltradata-webhook" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  const webhookSecret = Deno.env.get("LEMONSQUEEZY_WEBHOOK_SECRET") ?? "";
  const resendKey = Deno.env.get("RESEND_API_KEY") ?? "";
  const appUrl = Deno.env.get("APP_URL") ?? "https://app.coltradata.com";

  const rawBody = new Uint8Array(await req.arrayBuffer());
  const signatureHeader = req.headers.get("X-Signature") ?? "";

  if (webhookSecret) {
    const valid = await verifySignature(rawBody, signatureHeader, webhookSecret);
    if (!valid) {
      return new Response(JSON.stringify({ error: "Invalid signature" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  let payload: LemonSqueezyPayload;
  try {
    payload = JSON.parse(new TextDecoder().decode(rawBody));
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
  );

  const eventType = payload.meta?.event_name ?? "unknown";
  await logWebhookEvent(supabase, eventType, new TextDecoder().decode(rawBody));

  const f = extractFields(payload);
  let detail = "";

  try {
    if (eventType === "order_created" || eventType === "subscription_created") {
      if (!f.email) {
        detail = "skipped — no email in payload";
      } else {
        const key = await upsertSubscription(
          supabase, f.email, f.planKey, f.subscriptionId, f.orderId, "active"
        );
        if (resendKey) {
          await sendLicenceEmail(f.email, key, f.planKey, appUrl, resendKey);
        }
        detail = `activated ${f.planKey} for ${f.email} (key=${key})`;
      }
    } else if (eventType === "subscription_updated") {
      if (!f.email) {
        detail = "skipped — no email in payload";
      } else {
        const internal = ["active", "on_trial"].includes(f.lsStatus) ? "active" : "inactive";
        const plan = internal === "active" ? f.planKey : "free";
        await upsertSubscription(
          supabase, f.email, plan, f.subscriptionId, f.orderId, internal
        );
        detail = `updated to ${plan} (${internal}) for ${f.email}`;
      }
    } else if (eventType === "subscription_cancelled") {
      const found = await cancelSubscription(supabase, f.subscriptionId);
      detail = `cancelled sub_id=${f.subscriptionId} found=${found}`;
    } else {
      detail = "ignored";
    }
  } catch (err) {
    console.error("Handler error:", err);
    return new Response(JSON.stringify({ error: "Internal processing error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(
    JSON.stringify({ status: "ok", event: eventType, detail }),
    { headers: { "Content-Type": "application/json" } }
  );
});
