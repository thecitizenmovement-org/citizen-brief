# Secrets — Citizen Brief auto-poster

No secret **value** ever goes in this repo. Names only. Values live in
GitHub Secrets (repo → Settings → Secrets and variables → Actions) or in
Supabase function secrets.

## SUPABASE_URL + SUPABASE_SERVICE_KEY

- **Where:** Supabase project **citizen-members**
  (ref `jesrbqrwbacuirwxbkis`) → Project Settings → API.
  `SUPABASE_URL` is the project URL; `SUPABASE_SERVICE_KEY` is the
  `service_role` key (NOT the anon key — the poster reads and PATCHes rows).
- **Status:** TO BE FILLED after Supabase login. The CLI token on this VM
  does not hold, so this is a login step, not a copy step.

## BRIEF_BOT_TOKEN

- **Where:** A dedicated Telegram bot for the Brief, made via **BotFather**
  (`/newbot`), or the Mail Bot token supplied by Josh.
- **Status:** NEEDS JOSH. Either he creates a new Brief bot in BotFather
  and hands over the token through secure entry, or he supplies the Mail
  Bot token the same way. **Never extract an existing token out of the
  vault or a connector.**
- **Note:** whichever bot this is must be an **admin of the
  `@thecitizenbrief` channel**, or Telegram delivery fails.

## FB_PAGE_TOKEN

- **Where:** Meta developer app with `pages_manage_posts` on the Facebook
  Page **The United Citizen** (`1020020267871985`), exchanged for a
  long-lived Page access token.
- **Status:** PENDING — this is the separate token step, after the rest of
  the build. Until it is set, the poster logs `SKIPPING Facebook` and
  still delivers to Telegram.

## FB_PAGE_ID

- **Value:** `1020020267871985` (The United Citizen Page).
- **Status:** public ID, already in `.env.example` and the workflow. Not
  a secret.

## STRIPE_WEBHOOK_SECRET

- **Where:** Stripe Dashboard → Developers → Webhooks, when the webhook
  is created pointing at the deployed `stripe-sponsors` function
  (`https://jesrbqrwbacuirwxbkis.supabase.co/functions/v1/stripe-sponsors`).
  The secret starts `whsec_...`.
- **Status:** TO BE CREATED with the webhook. Set it as a Supabase
  function secret (`supabase secrets set STRIPE_WEBHOOK_SECRET=...`),
  never in this repo.
