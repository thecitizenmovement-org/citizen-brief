// Stripe → Supabase sponsors webhook (Supabase Edge Function, Deno).
//
// Deploy:
//   supabase functions deploy stripe-sponsors --project-ref jesrbqrwbacuirwxbkis
//   supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... --project-ref jesrbqrwbacuirwxbkis
//
// Then in the Stripe Dashboard, point a webhook at
//   https://jesrbqrwbacuirwxbkis.supabase.co/functions/v1/stripe-sponsors
// listening for checkout.session.completed.
//
// Amount map: $5.00 (500¢) → tier 'supporter'; $50.00 (5000¢) → tier 'sponsor'.
// The sponsors table has no email column, so the customer name is stored;
// if email storage is wanted later, add an `email text` column and extend
// the insert below. No unique constraint exists on name, so this does a
// select-then-insert/update instead of a true upsert.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const WEBHOOK_SECRET = Deno.env.get("STRIPE_WEBHOOK_SECRET") ?? "";

function hex(buf: ArrayBuffer): string {
  return [...new Uint8Array(buf)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// Constant-time-ish string compare for the signature check.
function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function verifyStripeSignature(
  payload: string,
  header: string,
  secret: string,
): Promise<boolean> {
  // header: t=<timestamp>,v1=<sig>[,v1=<sig>...]
  const parts = Object.fromEntries(
    header.split(",").map((p) => {
      const [k, ...rest] = p.split("=");
      return [k, rest.join("=")];
    }),
  );
  const t = parts["t"];
  const sigs = header
    .split(",")
    .filter((p) => p.startsWith("v1="))
    .map((p) => p.slice(3));
  if (!t || sigs.length === 0) return false;

  // Reject stale signatures (Stripe tolerance: 5 minutes).
  if (Math.abs(Date.now() / 1000 - Number(t)) > 300) return false;

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signed = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(`${t}.${payload}`),
  );
  const expected = hex(signed);
  return sigs.some((s) => safeEqual(s, expected));
}

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }
  const payload = await req.text();
  const sigHeader = req.headers.get("stripe-signature") ?? "";
  if (!WEBHOOK_SECRET) {
    console.error("STRIPE_WEBHOOK_SECRET not set");
    return new Response("Server misconfigured", { status: 500 });
  }
  if (!(await verifyStripeSignature(payload, sigHeader, WEBHOOK_SECRET))) {
    console.error("Stripe signature verification failed");
    return new Response("Bad signature", { status: 400 });
  }

  const event = JSON.parse(payload);
  if (event.type !== "checkout.session.completed") {
    return new Response(JSON.stringify({ received: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  const session = event.data.object;
  const amount = session.amount_total as number | undefined;
  const tier = amount === 500
    ? "supporter"
    : amount === 5000
    ? "sponsor"
    : null;
  if (!tier) {
    console.log(`Ignoring checkout amount ${amount} (not $5 / $50)`);
    return new Response(JSON.stringify({ received: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  const name = session.customer_details?.name
    || session.customer_details?.email
    || "Supporter";
  const email = session.customer_details?.email as string | undefined;

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL") ?? "",
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
  );

  // Select-then-write (no unique key on sponsors to upsert against).
  const { data: existing } = await supabase
    .from("sponsors")
    .select("id")
    .eq("name", name)
    .eq("tier", tier)
    .maybeSingle();

  if (existing) {
    await supabase.from("sponsors").update({ active: true }).eq("id", existing.id);
    console.log(`Reactivated ${tier} ${name}${email ? ` <${email}>` : ""}`);
  } else {
    const { error } = await supabase
      .from("sponsors")
      .insert({ name, tier, active: true });
    if (error) {
      console.error("sponsors insert failed:", error.message);
      return new Response("DB error", { status: 500 });
    }
    console.log(`Added ${tier} ${name}${email ? ` <${email}>` : ""}`);
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { "Content-Type": "application/json" },
  });
});
