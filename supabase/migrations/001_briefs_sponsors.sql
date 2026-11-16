-- Citizen Brief tables — run in the Supabase SQL Editor
-- Project: citizen-members (jesrbqrwbacuirwxbkis)

CREATE TABLE IF NOT EXISTS briefs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  date date NOT NULL,
  county text NOT NULL,
  headline text,
  body text,
  sources text,
  fb_post_id text,
  tg_msg_id text,
  created_at timestamptz DEFAULT now(),
  UNIQUE (date, county)
);

CREATE TABLE IF NOT EXISTS sponsors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  tier text CHECK (tier IN ('supporter', 'sponsor')),
  active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);
