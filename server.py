"""
server.py
=========
The Matchlight Group — FireScout Backend (v2)

Adds:
  - Static logo serving for the form
  - Scale-signal fields for richer recommendation logic
  - Internal sales note returned via response header (never in the PDF)
"""

import os
import io
import re
import json
import base64
import secrets
import tempfile
import urllib.parse
from pathlib import Path
from datetime import datetime

import httpx
import qrcode
from fastapi import FastAPI, Form, HTTPException, Depends, Request, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from anthropic import Anthropic

from firescout_renderer import render_audit
from firescout_web import render_web_audit
from scrlaudit_web import render_scrlaudit_web, WALKTHROUGH_LABELS, band_for


# =====================================================================
# CONFIG
# =====================================================================

API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
PASSWORD = os.environ.get("FIRESCOUT_PASSWORD", "matchlight-dev")
PROMPT_PATH = Path(__file__).parent / "firescout_prompt.md"
ASSETS_DIR  = Path(__file__).parent / "assets"

if not API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY env var must be set")

MASTER_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
client = Anthropic(api_key=API_KEY)
app = FastAPI(title="Matchlight FireScout Engine")

# --- Supabase (audit storage for the web version) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
AUDITS_TABLE = "firescout_audits"

# Optional overrides:
#   FIRESCOUT_PUBLIC_BASE — e.g. https://firescout.thematchlightgroup.com
#                           (defaults to whatever host the request came in on)
#   FIRESCOUT_CTA_URL     — where the audit's closing button points
PUBLIC_BASE = os.environ.get("FIRESCOUT_PUBLIC_BASE", "").rstrip("/")
CTA_URL     = os.environ.get("FIRESCOUT_CTA_URL", "https://www.thematchlightgroup.com")


def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def store_audit(slug: str, client_name: str, audit_json: dict,
                html: str, internal_note: str, kind: str = "firescout"):
    """Insert one audit row into Supabase. Raises on failure."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        raise HTTPException(500,
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_KEY env vars (see README).")
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/{AUDITS_TABLE}",
        headers={**_sb_headers(), "Prefer": "return=minimal"},
        json={
            "slug": slug,
            "client_name": client_name,
            "audit_json": audit_json,
            "html": html,
            "internal_note": internal_note,
            "kind": kind,
        },
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise HTTPException(500, f"Supabase insert failed: {r.status_code} {r.text[:300]}")


def fetch_audit(slug: str, columns: str) -> dict | None:
    """Fetch one audit row (selected columns) by slug. Returns None if absent."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        return None
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{AUDITS_TABLE}",
        headers=_sb_headers(),
        params={"slug": f"eq.{slug}", "select": columns, "limit": 1},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    rows = r.json()
    return rows[0] if rows else None


def make_slug(client_name: str) -> str:
    """Readable but unguessable: 'empower-and-flourish-k3x9f2'."""
    base = re.sub(r"[^a-z0-9]+", "-", client_name.lower()).strip("-")[:40] or "audit"
    return f"{base}-{secrets.token_hex(3)}"


def make_qr_base64(url: str) -> str:
    """QR code PNG for the audit link, base64-encoded for inline display."""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1c1c1c", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# =====================================================================
# AUTH
# =====================================================================

security = HTTPBasic()

def require_password(creds: HTTPBasicCredentials = Depends(security)):
    correct = secrets.compare_digest(creds.password, PASSWORD)
    if not correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


# =====================================================================
# THE FORM
# =====================================================================

INTAKE_HTML = (Path(__file__).parent / "firescout.html").read_text(encoding="utf-8")

@app.get("/firescout", response_class=HTMLResponse)
def intake_form(_: str = Depends(require_password)):
    return INTAKE_HTML


# =====================================================================
# STATIC ASSETS (logo for the form header)
# =====================================================================

@app.get("/firescout/static/logo.png")
def serve_logo():
    logo_path = ASSETS_DIR / "matchy_transparent.png"
    if not logo_path.exists():
        raise HTTPException(404, "Logo asset not found")
    return FileResponse(str(logo_path), media_type="image/png")


# =====================================================================
# THE GENERATE ENDPOINT
# =====================================================================

@app.post("/firescout/generate")
def generate(
    request: Request,
    _: str = Depends(require_password),
    client_name: str           = Form(...),
    contact_names: str         = Form(...),
    location: str              = Form(...),
    founded_year: str          = Form(""),
    website_url: str           = Form(""),
    facebook_url: str          = Form(""),
    instagram_url: str         = Form(""),
    linkedin_url: str          = Form(""),
    other_social: str          = Form(""),
    industry: str              = Form(""),
    sales_notes: str           = Form(...),
    vibes: str                 = Form(""),
    salesperson: str           = Form(""),
    # Scale signals (NEW):
    storefronts_needing_work: str = Form("two-three"),
    site_scale: str            = Form("small-multi"),
    ecommerce_needed: str      = Form("no"),
    ongoing_content: str       = Form("no"),
    video_needs: str           = Form("no"),
):
    # 1. Compose the brief
    brief = f"""
# Client brief — for FireScout audit generation

## Client basics
- Name: {client_name}
- Contact names (use these in greetings): {contact_names}
- Location: {location}
- Founded: {founded_year or "not provided"}
- Industry: {industry or "infer from website"}

## Storefront URLs
- Website: {website_url or "none"}
- Facebook: {facebook_url or "none"}
- Instagram: {instagram_url or "none"}
- LinkedIn: {linkedin_url or "none"}
- Other: {other_social or "none"}

## Sales team's human notes (THE GOLD)
{sales_notes}

## Vibes & directional impulses (ABSORB ONLY — DO NOT QUOTE)
{vibes if vibes.strip() else "(none provided — write from the sales notes alone)"}

These are the salesperson's internal shorthand for the brand's energy, tone,
and creative direction. Let these shape your voice and word choices, but
NEVER reproduce phrases from this field verbatim in the audit. The client
should never see this language back. It is direction, not copy.

## Scale signals from sales (use these to pick the right tier)

- Storefronts needing real attention: **{storefronts_needing_work}**
  - "one" = recommend a single service at appropriate tier
  - "two-three" or "all" = recommend a Storefront Cleanup
  - "single-task" = recommend Hourly/Spark Credit work

- Site scale: **{site_scale}**
  - "single-page" = SCRLsite is the right call
  - "small-multi" (5 or fewer pages) = Website Ignite or SCRLsite Blaze
  - "large-multi" (6-10 pages) = Website Blaze
  - "not-applicable" = site isn't the focus of the recommendation

- E-commerce needed: **{ecommerce_needed}**
  - "yes" = pushes site recommendation to Website Blaze (only Blaze tier has e-commerce)

- Ongoing content management: **{ongoing_content}**
  - "no" = one-time brand alignment is enough
  - "light" = 90-day kickoff (fits Storefront Cleanup Blaze)
  - "ongoing" = needs Social Media Ignite or Blaze retainer; flag in internal_sales_note

- Video / multimedia: **{video_needs}**
  - "yes" = pushes social recommendation to Blaze tier; consider SCRLsite Blaze for site

## Salesperson
{salesperson or "Matchlight team"}

---

Now produce the FireScout audit JSON exactly as specified in the system prompt.
Score honestly. Pull warmth from the sales notes. Pick the recommended tier
using the catalog and the scale signals above. Always include pricing in the
recommendation subtitle. Never put Ember Club in the PDF — only in
internal_sales_note if applicable.
""".strip()

    # 2. Call Claude
    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=8000,
            system=MASTER_PROMPT,
            messages=[{"role": "user", "content": brief}],
        )
    except Exception as e:
        raise HTTPException(500, f"Claude API error: {e}")

    raw = response.content[0].text.strip()

    # 3. Parse JSON
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        audit_data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(500,
            f"Claude returned non-JSON: {e}\n\n--- Raw output ---\n{raw[:1000]}")

    # 4. Validate
    required = ["client_name", "sections", "primary_recommendation"]
    missing = [k for k in required if k not in audit_data]
    if missing:
        raise HTTPException(500, f"Audit JSON missing keys: {missing}")
    if len(audit_data["sections"]) != 4:
        raise HTTPException(500,
            f"Expected 4 sections, got {len(audit_data['sections'])}")

    # Extract internal note (NEVER passed to a renderer — never client-visible)
    internal_note = audit_data.pop("internal_sales_note", "") or ""

    # 5. Render the web version
    try:
        html = render_web_audit(audit_data, cta_url=CTA_URL)
    except Exception as e:
        raise HTTPException(500, f"Web render error: {e}")

    # 6. Store in Supabase under an unguessable slug
    slug = make_slug(client_name)
    store_audit(slug, client_name, audit_data, html, internal_note)

    # 7. Build the shareable link + QR
    base = PUBLIC_BASE or str(request.base_url).rstrip("/")
    audit_url = f"{base}/a/{slug}"

    return JSONResponse({
        "slug": slug,
        "url": audit_url,
        "pdf_url": f"{audit_url}.pdf",
        "qr_png_base64": make_qr_base64(audit_url),
        "internal_note": internal_note,
        "client_name": client_name,
    })


# =====================================================================
# PUBLIC AUDIT ROUTES — no auth; slugs are unguessable and unlisted
# =====================================================================

@app.get("/a/{slug}", response_class=HTMLResponse)
def serve_audit(slug: str):
    row = fetch_audit(slug, "html")
    if not row:
        raise HTTPException(404, "Audit not found")
    return HTMLResponse(row["html"], headers={
        "Cache-Control": "private, max-age=300",
        "X-Robots-Tag": "noindex, nofollow",
    })


@app.get("/a/{slug}.pdf")
def serve_audit_pdf(slug: str):
    """Renders the print version on demand from the stored audit JSON."""
    row = fetch_audit(slug, "client_name,audit_json,kind")
    if not row:
        raise HTTPException(404, "Audit not found")
    if (row.get("kind") or "firescout") != "firescout":
        raise HTTPException(404,
            "PDF rendering isn't available for this audit type — "
            "the web version is the deliverable.")

    safe_name = "".join(c for c in row["client_name"] if c.isalnum() or c in " -_").strip()
    safe_name = safe_name.replace(" ", "_") or "Audit"
    out_path = Path(tempfile.gettempdir()) / f"{safe_name}_{slug}.pdf"

    try:
        render_audit(row["audit_json"], str(out_path), flatten=True)
    except Exception as e:
        raise HTTPException(500, f"Render error: {e}")

    return FileResponse(str(out_path), media_type="application/pdf",
        filename=f"{safe_name}_FireScout_Audit.pdf")


@app.get("/a/{slug}/qr.png")
def serve_audit_qr(slug: str, request: Request):
    """The audit link as a QR PNG — handy for re-grabbing it later."""
    row = fetch_audit(slug, "slug")
    if not row:
        raise HTTPException(404, "Audit not found")
    base = PUBLIC_BASE or str(request.base_url).rstrip("/")
    png = base64.b64decode(make_qr_base64(f"{base}/a/{slug}"))
    return Response(content=png, media_type="image/png")


# =====================================================================
# HEALTH CHECK
# =====================================================================

# =====================================================================
# SCRLAUDIT STUDIO — Caleb's manual audit, same publish pipeline
# =====================================================================

SCRL_FORM_PATH = Path(__file__).parent / "scrlaudit.html"


@app.get("/scrlaudit", response_class=HTMLResponse)
def scrlaudit_form(_: str = Depends(require_password)):
    return HTMLResponse(SCRL_FORM_PATH.read_text(encoding="utf-8"))


@app.post("/scrlaudit/publish")
async def scrlaudit_publish(request: Request, _: str = Depends(require_password)):
    form = await request.form()

    def num(name, default=0):
        try:
            return max(0, min(10, int(form.get(name, default))))
        except (TypeError, ValueError):
            return default

    client_name = (form.get("client_name") or "").strip()
    if not client_name:
        raise HTTPException(400, "Client name is required")

    walkthrough = [
        {"label": WALKTHROUGH_LABELS[i],
         "score": num(f"w{i+1}", 5),
         "note": (form.get(f"n{i+1}") or "").strip()}
        for i in range(10)
    ]
    total = sum(w["score"] for w in walkthrough)
    _, band_rec = band_for(total)

    # Present the date the way the audits speak: "June 30, 2026"
    date_str = (form.get("audit_date") or "").strip()
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            date_str = f"{dt.strftime('%B')} {dt.day}, {dt.year}"
        except ValueError:
            pass

    data = {
        "client_name": client_name,
        "business_type": (form.get("business_type") or "").strip(),
        "location": (form.get("location") or "").strip(),
        "auditor_name": (form.get("auditor_name") or "").strip(),
        "audit_date": date_str,
        "pillar_clarity": num("pillar_clarity", 5),
        "pillar_momentum": num("pillar_momentum", 5),
        "pillar_effort": num("pillar_effort", 5),
        "walkthrough": walkthrough,
        "dive_clarity": (form.get("dive_clarity") or "").strip(),
        "dive_momentum": (form.get("dive_momentum") or "").strip(),
        "dive_effort": (form.get("dive_effort") or "").strip(),
        "other_notes": (form.get("other_notes") or "").strip(),
        "interpretation": (form.get("interpretation") or "").strip(),
        "conclusion": (form.get("conclusion") or "").strip(),
        "rec_headline": (form.get("rec_headline") or "").strip() or band_rec,
        "rec_body": (form.get("rec_body") or "").strip(),
        "closing_note": (form.get("closing_note") or "").strip(),
    }

    try:
        html = render_scrlaudit_web(data, cta_url=CTA_URL)
    except Exception as e:
        raise HTTPException(500, f"Web render error: {e}")

    slug = make_slug(client_name)
    store_audit(slug, client_name, data, html, "", kind="scrlaudit")

    base = PUBLIC_BASE or str(request.base_url).rstrip("/")
    audit_url = f"{base}/a/{slug}"

    return JSONResponse({
        "slug": slug,
        "url": audit_url,
        "qr_png_base64": make_qr_base64(audit_url),
        "client_name": client_name,
        "score": total,
    })


@app.get("/", response_class=HTMLResponse)
def studio_home():
    """A small branded front door linking both tools."""
    return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Matchlight Audit Engine</title>
<style>
 body{margin:0;background:#1c1c1c;color:#F2EFF4;min-height:100vh;
   display:flex;align-items:center;justify-content:center;
   font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
 .box{text-align:center;padding:40px 24px}
 .dash{width:56px;height:5px;border-radius:3px;margin:0 auto 22px;
   background:linear-gradient(90deg,#6B1F6A,#C0203A,#E41C23,#F05A28,#F5A623)}
 h1{font-size:22px;font-weight:800;margin:0 0 6px}
 p{color:#A79FB2;font-size:14px;margin:0 0 30px}
 a{display:block;max-width:320px;margin:0 auto 14px;padding:16px 24px;
   border-radius:10px;text-decoration:none;color:#fff;font-weight:700;
   background:#6B1F6A;border-top:3px solid #F05A28}
 a span{display:block;font-weight:400;font-size:12.5px;color:#D9CBE0;margin-top:3px}
</style></head><body><div class="box">
<div class="dash"></div>
<h1>Matchlight Audit Engine</h1>
<p>Internal tools · The Matchlight Group</p>
<a href="/firescout">FireScout<span>Comprehensive storefront audit · Claude-written</span></a>
<a href="/scrlaudit">SCRLaudit Studio<span>Focused mobile audit · auditor-written</span></a>
</div></body></html>""")


@app.get("/health")
def health():
    return {"ok": True, "service": "firescout", "version": "4"}
