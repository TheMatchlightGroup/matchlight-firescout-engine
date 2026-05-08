[README.md](https://github.com/user-attachments/files/27531268/README.md)
# FireScout Engine

The Matchlight Group's internal audit generator. Sales fills out a form, Claude
writes the audit, the rendering engine produces a flat, on-brand PDF.

## What's in this folder

| File | What it does | Who touches it |
|------|--------------|----------------|
| `firescout.html` | The intake form your sales team uses | Designer/dev for tweaks |
| `server.py` | FastAPI backend — orchestrates everything | Developer |
| `firescout_renderer.py` | The locked PDF renderer (the design layer) | **Treat as read-only** |
| `firescout_prompt.md` | Claude's instructions — voice, rubric, schema | **Edit this to refine the audit's voice** |
| `assets/Matchlight_isotype.svg` | Your isotype | Designer |
| `requirements.txt` | Python dependencies | pip install |

## How it works

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
                                       ▼
                       [ firescout_renderer.render_audit() ]
                                       │
                                       ▼
                            Flat, on-brand PDF
                                       │
                                       ▼
                            Sales downloads it
```

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
