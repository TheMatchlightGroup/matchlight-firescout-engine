[README.md](https://github.com/user-attachments/files/27531268/README.md)
# Matchlight Audit Engine (FireScout + SCRLaudit)

The Matchlight Group's internal audit generator — one engine, two products:

- **FireScout** (`/firescout`) — sales fills a brief, **Claude writes** the
  comprehensive storefront audit, the engine publishes a scrolling web audit
  with a shareable link + QR (PDF on demand for print).
- **SCRLaudit Studio** (`/scrlaudit`) — **Caleb writes** the focused
  mobile-first audit directly in a form; the engine publishes it through the
  same pipeline: Edition 01 web audit, link + QR, same `/a/{slug}` links.

Both audit types live in the same Supabase table (`kind` column tells them
apart) and are served by the same routes. The root URL (`/`) is a small
landing page linking both tools.

## What's in this folder

| File | What it does | Who touches it |
|------|--------------|----------------|
| `firescout.html` | The intake form your sales team uses | Designer/dev for tweaks |
| `server.py` | FastAPI backend — orchestrates everything | Developer |
| `firescout_web.py` | FireScout web renderer — Edition 01 scrolling HTML | Designer/dev |
| `scrlaudit_web.py` | SCRLaudit web renderer — same design system | Designer/dev |
| `scrlaudit.html` | Caleb's SCRLaudit form (manual audits) | Designer/dev |
| `firescout_renderer.py` | The locked PDF renderer (the print layer) | **Treat as read-only** |
| `firescout_prompt.md` | Claude's instructions — voice, rubric, schema | **Edit this to refine the audit's voice** |
| `assets/Matchlight_isotype.svg` | Your isotype | Designer |
| `requirements.txt` | Python dependencies | pip install |

## How it works (v3 — web-first)

```
Sales team
   │
   ▼
[ /firescout intake form ]  ──────► Brief composed
                                       │
                                       ▼
                            [ Claude API + master prompt ]
                                       │
                                       ▼
                              Structured audit JSON
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
        [ firescout_web.render_web_audit() ]   (stored JSON)
                          │                         │
                          ▼                         ▼
                 HTML stored in Supabase     /a/{slug}.pdf renders
                          │                  the print version
                          ▼                  on demand
              /a/{slug} — live audit link
                          │
                          ▼
          Success screen: link + QR + internal note
          (sit with the client, scan, scroll together)
```

One Claude call produces both versions. The web audit is the deliverable; the
PDF is the fallback for print.

## Supabase setup (one-time, ~2 minutes)

Audits are stored in a Supabase table so links survive restarts and redeploys.

1. In your Supabase project, run this SQL (SQL Editor → New query):

```sql
create table if not exists firescout_audits (
  slug          text primary key,
  client_name   text not null,
  audit_json    jsonb not null,
  html          text not null,
  internal_note text,
  created_at    timestamptz not null default now(),
  kind          text not null default 'firescout'
);

-- Lock it down: the engine uses the service key, which bypasses RLS.
-- No public policies means no public access except through the engine.
alter table firescout_audits enable row level security;
```

2. Grab two values from Project Settings → API:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** → `SUPABASE_SERVICE_KEY` (keep this secret; it's
     server-side only and never appears in any page)

3. Set both as env vars on Render (see below).

Audit links are unguessable (`client-name-a1b2c3`) and pages are served with
`noindex` — private to whoever holds the link.

## Local setup (dev)

```bash
# 1. Get the code into a folder, then:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. System dependency for PDF flattening (one-time)
#    Mac:    brew install poppler
#    Ubuntu: sudo apt-get install poppler-utils

# 3. Put your isotype here:
mkdir -p assets
cp /path/to/Matchlight_isotype.svg assets/

# 4. Set env vars:
export ANTHROPIC_API_KEY="sk-ant-..."
export FIRESCOUT_PASSWORD="something-only-the-team-knows"
export MATCHLIGHT_LOGO_SVG="$(pwd)/assets/Matchlight_isotype.svg"
export SUPABASE_URL="https://YOUR-PROJECT.supabase.co"
export SUPABASE_SERVICE_KEY="eyJ..."          # service_role key
# Optional:
export FIRESCOUT_PUBLIC_BASE=""               # e.g. https://firescout.thematchlightgroup.com
export FIRESCOUT_CTA_URL="https://www.thematchlightgroup.com"

# 5. Run it:
uvicorn server:app --reload --port 8000

# 6. Visit:
open http://localhost:8000/firescout
# Username: anything. Password: whatever you set above.
```

## Deploying to production

Easiest paths, in order:

### Option A — Render.com (~$7/mo, 5 minutes)
1. Push this folder to a private GitHub repo.
2. Sign in at render.com, "New Web Service," connect the repo.
3. Build command: `pip install -r requirements.txt && apt-get update && apt-get install -y poppler-utils`
4. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Set env vars in Render's dashboard (API key, password, logo path).
6. Once deployed, you'll get a `*.onrender.com` URL.

### Option B — Railway.app (~$5/mo)
Similar to Render. Railway autodetects Python and runs `uvicorn` if specified
in a `Procfile`. Add a `Procfile` with: `web: uvicorn server:app --host 0.0.0.0 --port $PORT`

### Option C — Your own VPS
Standard FastAPI deployment with systemd + nginx. Heavier lift but cheapest.

## Pointing /firescout to it from thematchlightgroup.com

You have two options:

### Reverse proxy (recommended)
On your main site's web server, proxy `/firescout/*` to the engine's URL.
Example for nginx:
```nginx
location /firescout {
    proxy_pass https://your-render-url.onrender.com;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
}
```
This way sales visits `thematchlightgroup.com/firescout` and never sees the
backend URL.

### Subdomain (simpler)
If your site is on Squarespace/Wix/etc. and a reverse proxy is hard, just point
`firescout.thematchlightgroup.com` at the engine via DNS CNAME. Same effect.

## Cost per audit

Roughly **$0.50 - $2.00** in Claude API costs per audit, depending on length
and how much web research Claude does. Hosting on Render is a flat ~$7/mo.

## How to refine the audit's voice

Edit `firescout_prompt.md`. That's where the rubric, tone, and schema live.
Want a softer voice? Edit it there. Want more specific scoring guidance? Add
it there. Want to adjust the recommendation tiers? Same file.

The renderer is locked — design changes require a developer. But the *voice*
is just a markdown file your team can iterate on without touching code.

## Troubleshooting

**"Audit JSON missing keys"** — Claude returned malformed JSON. Almost always
means the prompt needs tightening. Add an example or stronger schema reminder.

**PDF looks broken** — Check that the SVG path is set correctly via
`MATCHLIGHT_LOGO_SVG` and that `poppler-utils` is installed on the host.

**Generation takes forever** — Normal range is 30-90 seconds. Most of that is
Claude's writing time. If it's longer, check Claude API status.

**Want to skip flattening for editing** — Pass `flatten=False` to
`render_audit()`. Useful if you want a vector PDF you can mark up, but always
flatten before emailing to clients.

## Future expansions

When you're ready for Path C (client-facing lead magnet):
1. Strip the password from `/firescout`
2. Add a separate `/firescout/preview` endpoint that returns just the cover +
   scores (no recommendations) until they book a discovery call
3. Wire it to your CRM via webhook on submit

The architecture supports all of this without rewrites.
