"""
server.py
=========
The Matchlight Group — FireScout Backend

A small FastAPI server that:
  1. Receives intake form data from /firescout
  2. Calls Claude with the master prompt + intake data
  3. Parses Claude's JSON response
  4. Renders the on-brand PDF using firescout_renderer
  5. Returns the flat PDF for download

DEPLOY:
  Render, Railway, Fly.io, or any container host.
  Set environment variables:
    ANTHROPIC_API_KEY      — from console.anthropic.com
    FIRESCOUT_PASSWORD     — shared password for sales team
    MATCHLIGHT_LOGO_SVG    — absolute path to your isotype SVG

  Local dev:
    pip install fastapi uvicorn anthropic reportlab svglib pdf2image pillow python-multipart
    uvicorn server:app --reload --port 8000

  Production:
    uvicorn server:app --host 0.0.0.0 --port $PORT --workers 2
"""

import os
import json
import secrets
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Form, HTTPException, Depends, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from anthropic import Anthropic

from firescout_renderer import render_audit


# =====================================================================
# CONFIG
# =====================================================================

API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
PASSWORD = os.environ.get("FIRESCOUT_PASSWORD", "matchlight-dev")
PROMPT_PATH = Path(__file__).parent / "firescout_prompt.md"

if not API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY env var must be set")

MASTER_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
client = Anthropic(api_key=API_KEY)
app = FastAPI(title="Matchlight FireScout Engine")


# =====================================================================
# AUTH (very simple HTTP Basic — fine for an internal tool)
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
# THE FORM (lives at /firescout)
# =====================================================================

INTAKE_HTML = (Path(__file__).parent / "firescout.html").read_text(encoding="utf-8")

@app.get("/firescout", response_class=HTMLResponse)
def intake_form(_: str = Depends(require_password)):
    return INTAKE_HTML


# =====================================================================
# THE GENERATE ENDPOINT
# =====================================================================

@app.post("/firescout/generate")
def generate(
    _: str = Depends(require_password),
    client_name: str          = Form(...),
    contact_names: str        = Form(...),
    location: str             = Form(...),
    founded_year: str         = Form(""),
    website_url: str          = Form(""),
    facebook_url: str         = Form(""),
    instagram_url: str        = Form(""),
    linkedin_url: str         = Form(""),
    other_social: str         = Form(""),
    industry: str             = Form(""),
    sales_notes: str          = Form(...),
    recommendation_hint: str  = Form("Ignite Storefront Cleanup"),
    salesperson: str          = Form(""),
):
    """
    Build the user-message payload, call Claude, parse JSON, render PDF.
    """

    # 1. Compose the human brief that Claude will read
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
These are the human details the salesperson observed. Surface specifics from
here throughout the audit — names, traditions, lived experience, mascots,
quirks. This is what makes a Matchlight audit feel like a Matchlight audit.

{sales_notes}

## Recommendation hint from sales
The salesperson believes this is the right fit: **{recommendation_hint}**.
Use this as your default unless the data clearly contradicts it.

## Salesperson generating this audit
{salesperson or "Matchlight team"}

---

Now produce the FireScout audit JSON exactly as specified in your system
prompt. Score honestly. Pull warmth from the sales notes.
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

    # 3. Parse JSON (be forgiving if Claude wraps it in code fences)
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        audit_data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(500,
            f"Claude returned non-JSON: {e}\n\n--- Raw output ---\n{raw[:1000]}")

    # 4. Validate critical fields
    required = ["client_name", "sections", "primary_recommendation"]
    missing = [k for k in required if k not in audit_data]
    if missing:
        raise HTTPException(500, f"Audit JSON missing keys: {missing}")
    if len(audit_data["sections"]) != 4:
        raise HTTPException(500,
            f"Expected 4 sections, got {len(audit_data['sections'])}")

    # 5. Render the PDF
    safe_name = "".join(c for c in client_name if c.isalnum() or c in " -_").strip()
    safe_name = safe_name.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(tempfile.gettempdir()) / f"{safe_name}_FireScout_{timestamp}.pdf"

    try:
        render_audit(audit_data, str(out_path), flatten=True)
    except Exception as e:
        raise HTTPException(500, f"Render error: {e}")

    return FileResponse(
        path=str(out_path),
        media_type="application/pdf",
        filename=f"{safe_name}_FireScout_Audit.pdf",
    )


# =====================================================================
# HEALTH CHECK (for hosting platform monitors)
# =====================================================================

@app.get("/health")
def health():
    return {"ok": True, "service": "firescout"}
