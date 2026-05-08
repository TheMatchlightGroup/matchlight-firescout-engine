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
import json
import secrets
import tempfile
import urllib.parse
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Form, HTTPException, Depends, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from anthropic import Anthropic

from firescout_renderer import render_audit


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

    # Extract internal note (NEVER passed to renderer — stays out of PDF)
    internal_note = audit_data.pop("internal_sales_note", "") or ""

    # 5. Render
    safe_name = "".join(c for c in client_name if c.isalnum() or c in " -_").strip()
    safe_name = safe_name.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(tempfile.gettempdir()) / f"{safe_name}_FireScout_{timestamp}.pdf"

    try:
        render_audit(audit_data, str(out_path), flatten=True)
    except Exception as e:
        raise HTTPException(500, f"Render error: {e}")

    # Read PDF bytes so we can return it WITH a custom header
    pdf_bytes = out_path.read_bytes()

    # URL-encode the internal note so it survives an HTTP header
    encoded_note = urllib.parse.quote(internal_note) if internal_note else ""

    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}_FireScout_Audit.pdf"',
        "X-Internal-Sales-Note": encoded_note or "-",
        "Access-Control-Expose-Headers": "X-Internal-Sales-Note",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


# =====================================================================
# HEALTH CHECK
# =====================================================================

@app.get("/health")
def health():
    return {"ok": True, "service": "firescout", "version": "2"}
