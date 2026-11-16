# Citizen Brief — Auto-Poster

Daily Citizen Brief for **Shasta + Tehama counties** — elections, sheriff / police
oversight, courts, budgets, public safety. Sources named, no spin.
Professional Page only: no personal call-outs, no scrolling old crew.

## What this system does

This repo is the **delivery** side of the Brief. It does not write the Brief.

1. A brief row lands in Supabase (`briefs` table — see
   `supabase/migrations/001_briefs_sponsors.sql`).
2. A GitHub Action (`brief.yml`, Mon–Sat 6:00 AM PT) runs
   `scripts/post_brief.py`, which:
   - pulls today's brief rows for Shasta + Tehama from Supabase,
   - builds a sponsor footer from the `sponsors` table (Stripe-fed),
   - posts each county brief to Telegram (`@thecitizenbrief`) and to the
     Facebook Page **The United Citizen**,
   - writes the Telegram message id and Facebook post id back to the row.
3. A Stripe webhook (`supabase/functions/stripe-sponsors`) records $5
   supporters and $50 sponsors into the `sponsors` table, so the footer
   stays current with no hand edits.

## Architecture

```
brief row in Supabase ──► GitHub Action (cron, Mon–Sat 6am PT)
                              │  scripts/post_brief.py (urllib only)
                              ├──► Telegram @thecitizenbrief  (BRIEF_BOT_TOKEN)
                              ├──► Facebook Page feed          (FB_PAGE_TOKEN)
                              └──► PATCH tg_msg_id / fb_post_id back to Supabase
Stripe Checkout ──► webhook ──► Edge Function stripe-sponsors ──► sponsors table
```

Domains: `thecitizenmovement.org` = home + Brief,
`thecitizenmovement.com` redirects to `.org`,
`thecitizenmovement.online` = Private Eye investigations,
`thecitizenmovement.store` = Stripe Checkout ($5 supporter / $50 sponsor).

## Secrets (GitHub → Settings → Secrets and variables → Actions)

| Secret | Used by |
|---|---|
| `SUPABASE_URL` | `post_brief.py` |
| `SUPABASE_SERVICE_KEY` | `post_brief.py` |
| `BRIEF_BOT_TOKEN` | `post_brief.py` (Telegram) |
| `FB_PAGE_TOKEN` | `post_brief.py` (Facebook) |
| `FB_PAGE_ID` | `post_brief.py` (Facebook) |
| `STRIPE_WEBHOOK_SECRET` | Edge Function `stripe-sponsors` (Supabase env) |

Full detail — where each one comes from and its status — is in
[`docs/SECRETS.md`](docs/SECRETS.md). **No secret value ever goes in this
repo.** Names only.

## Enabling the live cron (Josh's go required)

The cron schedule in `.github/workflows/brief.yml` is **commented out** on
purpose — nothing auto-posts until all of these are true:

1. Secrets above are set in the repo.
2. Supabase tables exist (run `supabase/migrations/001_briefs_sponsors.sql`
   in the citizen-members project, SQL Editor).
3. The Telegram bot is an admin of the `@thecitizenbrief` channel.
4. Josh gives the go — then uncomment the `schedule:` block in `brief.yml`
   and push.

Until then the workflow runs only on manual dispatch (`workflow_dispatch`),
and `post_brief.py` skips any destination whose token is missing instead of
failing.

## Open integration point — TODO

**How brief rows get into Supabase is not decided yet.** This system only
delivers rows that are already there. Options on the table:

- The **Mail Bot** (which already auto-posts the daily Brief) writes the row
  when it generates the Brief, or
- rows are entered manually in the Supabase dashboard / a small form.

Do not invent a writer here — that decision is Josh's, and the writer is a
separate piece of work.

## Sponsor footer

- Active sponsor present: `Today's Brief is supported by [Name] — thank
  you. Want your business here? $50/mo: thecitizenmovement.store`
- No active sponsor: `Today's Brief has no sponsor yet — put your business
  here $50/mo`

## Local test

```bash
cp .env.example .env   # fill in values locally only — never commit .env
python3 scripts/post_brief.py
```
