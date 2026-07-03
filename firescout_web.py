"""
firescout_web.py
================
The Matchlight Group — FireScout Web Renderer (v1)

Takes the exact same structured audit JSON the PDF renderer consumes and
produces ONE self-contained HTML file: the scrolling, phone-first FireScout.

Design system: Brand Guidelines Edition 01 (May 2026)
  - Ground: Charcoal #1c1c1c
  - Flame:  Purple #6B1F6A -> Crimson #C0203A -> Red #E41C23
            -> Orange #F05A28 -> Gold #F5A623
  - Voice:  White
  - Type:   Montserrat (display) + Lato (body), via Google Fonts CDN

Rules honored from Edition 01:
  - One flame-italic moment per room (ours: the mission's closing line)
  - Consultation voice: name what's working before what isn't
  - Sign off by name — the closing note carries the signature

The page is fully readable with JavaScript disabled. Motion (scroll reveals,
score count-up, bar fills, progress bar) is progressive enhancement and
respects prefers-reduced-motion.

Usage:
    from firescout_web import render_web_audit
    html = render_web_audit(audit_data, cta_url="https://www.thematchlightgroup.com")
"""

import os
import re
import html as html_mod
from pathlib import Path
from datetime import date

# ---------------------------------------------------------------------
# BRAND CONSTANTS — Edition 01. Never change without design review.
# ---------------------------------------------------------------------

CHARCOAL = "#1c1c1c"
PURPLE   = "#6B1F6A"
CRIMSON  = "#C0203A"
RED      = "#E41C23"
ORANGE   = "#F05A28"
GOLD     = "#F5A623"
WHITE    = "#FFFFFF"
GREEN_OK = "#5BB04E"   # diagnostic green — shared with the PDF renderer

FLAME_GRADIENT = f"linear-gradient(90deg,{PURPLE} 0%,{CRIMSON} 30%,{RED} 52%,{ORANGE} 76%,{GOLD} 100%)"

LOGO_PATH = os.environ.get(
    "MATCHLIGHT_LOGO_SVG",
    str(Path(__file__).parent / "assets" / "Matchlight_isotype.svg"),
)


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

_ALLOWED_TAGS = re.compile(
    r"</?(?:b|i|strong|em)>|<br\s*/?>", re.IGNORECASE
)
_FONT_OPEN  = re.compile(r'<font\b[^>]*color="([^"]+)"[^>]*>', re.IGNORECASE)
_FONT_PLAIN = re.compile(r"<font\b[^>]*>", re.IGNORECASE)
_FONT_CLOSE = re.compile(r"</font>", re.IGNORECASE)
_OTHER_TAG  = re.compile(r"</?[a-zA-Z][^>]*>")


def clean(text) -> str:
    """
    Sanitize a prose string from the audit JSON for HTML output.
    The prompt allows inline <i> <b> <br/> <font color="..."> — we keep those
    (font becomes span) and strip anything else.
    """
    if text is None:
        return ""
    s = str(text)
    # Convert allowed font tags to spans
    s = _FONT_OPEN.sub(lambda m: f'<span style="color:{html_mod.escape(m.group(1))}">', s)
    s = _FONT_PLAIN.sub("<span>", s)
    s = _FONT_CLOSE.sub("</span>", s)
    # Temporarily protect allowed tags, strip the rest, restore
    protected = []
    def _protect(m):
        protected.append(m.group(0))
        return f"\x00{len(protected)-1}\x00"
    s = _ALLOWED_TAGS.sub(_protect, s)
    s = re.sub(r"</?span[^>]*>", _protect, s)
    s = _OTHER_TAG.sub("", s)
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    for i, tag in enumerate(protected):
        s = s.replace(f"\x00{i}\x00", tag)
    return s


def score_color(score: float, out_of: float) -> str:
    """Same diagnostic thresholds as the PDF renderer."""
    pct = score / out_of if out_of else 0
    if pct >= 0.7:
        return GREEN_OK
    if pct >= 0.5:
        return ORANGE
    return RED


def load_isotype() -> str:
    """Inline the isotype SVG so the page has zero image dependencies."""
    try:
        svg = Path(LOGO_PATH).read_text(encoding="utf-8")
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
        return svg
    except Exception:
        return ""  # page still works without the mark


# ---------------------------------------------------------------------
# THE RENDERER
# ---------------------------------------------------------------------

def render_web_audit(d: dict, cta_url: str = "https://www.thematchlightgroup.com") -> str:
    sections = d["sections"]
    total_score = sum(int(s["total"]) for s in sections)
    isotype = load_isotype()
    today = date.today()
    date_str = f"{today.strftime('%B')} {today.day}, {today.year}"
    client = clean(d.get("client_name", ""))

    # ----- section chapters -----
    section_html = []
    for i, s in enumerate(sections, start=1):
        crit_html = []
        for c in s["criteria"]:
            chip = score_color(c["score"], 5)
            crit_html.append(f"""
      <div class="crit reveal">
        <div class="crit-top">
          <span class="crit-letter">{clean(c['letter'])}.</span>
          <span class="crit-title">{clean(c['title'])}</span>
          <span class="chip" style="--chip:{chip}">{int(c['score'])}/5</span>
        </div>
        <p class="crit-desc">{clean(c['descriptor'])}</p>
        <p class="crit-finding">{clean(c['finding'])}</p>
      </div>""")
        band = score_color(s["total"], 25)
        section_html.append(f"""
  <section class="chapter" id="section-{i}">
    <header class="chapter-head reveal">
      <span class="chapter-num">{i}</span>
      <h2 class="chapter-name">{clean(s['name'])}</h2>
      <span class="chapter-score" style="--chip:{band}">{int(s['total'])}<span class="of"> / 25</span></span>
    </header>
    {''.join(crit_html)}
    <div class="means reveal">
      <p class="means-label">What this means</p>
      <p class="means-body">{clean(s['summary'])}</p>
    </div>
  </section>""")

    # ----- at-a-glance bars -----
    bars_html = []
    for i, s in enumerate(sections, start=1):
        pct = round(int(s["total"]) / 25 * 100)
        col = score_color(s["total"], 25)
        bars_html.append(f"""
      <div class="bar-row reveal">
        <div class="bar-label"><span>{i}.&nbsp; {clean(s['name'])}</span>
          <span class="bar-score" style="color:{col}">{int(s['total'])} / 25</span></div>
        <div class="bar-track"><div class="bar-fill" data-w="{pct}" style="width:{pct}%;background:{col}"></div></div>
      </div>""")

    # ----- strengths / gaps -----
    strengths_li = "".join(f"<li>{clean(x)}</li>" for x in d.get("strengths", []))
    gaps_li      = "".join(f"<li>{clean(x)}</li>" for x in d.get("gaps", []))

    # ----- recommendation -----
    rec = d["primary_recommendation"]
    includes_li = "".join(f"<li>{clean(x)}</li>" for x in rec.get("includes", []))

    alacarte_html = []
    for idx, r in enumerate(d.get("alacarte_items", []), start=1):
        alacarte_html.append(f"""
      <div class="ala-card reveal">
        <div class="ala-num">{idx:02d}</div>
        <div class="ala-body">
          <h4>{clean(r['title'])}</h4>
          <p class="ala-sub">{clean(r['subtitle'])}</p>
          <p>{clean(r['body'])}</p>
        </div>
      </div>""")

    # =================================================================
    # THE PAGE
    # =================================================================
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>FireScout · {client} · The Matchlight Group</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,700;0,800;0,900;1,800&family=Lato:ital,wght@0,300;0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
  :root {{
    --charcoal: {CHARCOAL};
    --purple: {PURPLE};
    --crimson: {CRIMSON};
    --red: {RED};
    --orange: {ORANGE};
    --gold: {GOLD};
    --ink-panel: #262030;
    --text: #F2EFF4;
    --muted: #A79FB2;
    --rule: rgba(255,255,255,0.10);
    --flame: {FLAME_GRADIENT};
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{
    background: var(--charcoal);
    color: var(--text);
    font-family: 'Lato', -apple-system, sans-serif;
    font-weight: 300;
    font-size: 17px;
    line-height: 1.65;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 680px; margin: 0 auto; padding: 0 22px; }}
  h1,h2,h3,h4 {{ font-family:'Montserrat',sans-serif; }}
  b, strong {{ font-weight: 700; }}

  /* ---- flame progress bar (walkthrough aid) ---- */
  #progress {{
    position: fixed; top:0; left:0; height:3px; width:0%;
    background: var(--flame); z-index: 100;
  }}

  /* ---- eyebrow + gradient dash: the Edition 01 signature marks ---- */
  .dash {{ width:56px; height:5px; background:var(--flame); border-radius:3px; }}
  .eyebrow {{
    font-family:'Montserrat',sans-serif; font-weight:700; font-size:12px;
    letter-spacing:0.22em; text-transform:uppercase; color:var(--orange);
  }}

  /* ---- cover ---- */
  .cover {{
    min-height: 100svh; display:flex; flex-direction:column;
    align-items:center; justify-content:center; text-align:center;
    padding: 64px 22px 48px; position:relative;
  }}
  .cover .isotype {{ width: 92px; margin-bottom: 28px; }}
  .cover .isotype svg {{ width:100%; height:auto; display:block; }}
  .cover .dash {{ margin: 0 auto 22px; }}
  .cover h1 {{
    font-weight: 900; font-size: clamp(30px, 8vw, 44px);
    line-height: 1.12; letter-spacing:-0.01em; margin: 14px 0 12px; color: var(--text);
  }}
  .cover .subtitle {{ color: var(--muted); font-size: 15px; }}
  .cover .prepared {{ margin-top: 42px; font-style: italic; color: var(--muted); font-size: 15px; }}
  .cover .client {{
    font-family:'Montserrat',sans-serif; font-weight:800;
    font-size: clamp(22px, 6vw, 30px); margin-top: 6px;
  }}
  .cover .team {{ color: var(--muted); font-size: 15px; margin-top: 4px; }}
  .cover .date {{ color: var(--muted); font-style: italic; font-size: 14px; margin-top: 10px; }}
  .scroll-cue {{
    position:absolute; bottom:26px; left:50%; transform:translateX(-50%);
    color: var(--muted); font-size: 22px; line-height:1;
  }}

  /* ---- generic section rhythm ---- */
  section {{ padding: 56px 0; }}
  section + section {{ border-top: 1px solid var(--rule); }}

  /* ---- is / is-not cards ---- */
  .card {{
    background: var(--ink-panel); border-radius: 10px;
    padding: 26px 24px; margin-bottom: 16px;
  }}
  .card .eyebrow {{ margin-bottom: 10px; }}
  .card p {{ color: var(--text); }}

  /* ---- mission ---- */
  .mission {{
    background: var(--purple); border-top: 4px solid var(--orange);
    border-radius: 10px; padding: 34px 28px; text-align:center;
  }}
  .mission .eyebrow {{ color: var(--gold); margin-bottom: 14px; }}
  .mission p.big {{ font-size: 19px; line-height: 1.55; }}
  .mission p.flame-italic {{
    margin-top: 16px; font-style: italic; font-weight: 400;
    background: linear-gradient(90deg, #C77BC5 0%, {GOLD} 100%);
    -webkit-background-clip:text; background-clip:text; color:transparent;
  }}

  /* ---- intro + score ---- */
  .intro h2 {{ font-weight:800; font-size:26px; margin: 14px 0 4px; }}
  .intro .subtitle {{ color: var(--muted); font-size:14px; margin-bottom: 22px; }}
  .intro p {{ margin-bottom: 16px; }}

  .scoreboard {{ text-align:center; padding: 44px 0 8px; }}
  .score-label {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:12px;
    letter-spacing:0.22em; text-transform:uppercase; color:var(--muted); }}
  .score-big {{
    font-family:'Montserrat',sans-serif; font-weight:900;
    font-size: clamp(88px, 26vw, 132px); line-height: 1;
    background: var(--flame);
    -webkit-background-clip:text; background-clip:text; color:transparent;
    display:inline-block; margin: 6px 0 2px;
  }}
  .score-of {{ color: var(--muted); font-size: 16px; }}
  .score-callout {{ font-style:italic; color:var(--muted); max-width:540px;
    margin: 22px auto 0; font-size: 16px; }}

  /* ---- at a glance bars ---- */
  .glance h3 {{ font-weight:800; font-size:21px; margin-bottom: 22px; }}
  .bar-row {{ margin-bottom: 20px; }}
  .bar-label {{ display:flex; justify-content:space-between; align-items:baseline;
    font-family:'Montserrat',sans-serif; font-weight:700; font-size:15px; margin-bottom:8px; }}
  .bar-score {{ font-size:14px; }}
  .bar-track {{ height:12px; background:rgba(255,255,255,0.08); border-radius:6px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:6px; transition: width 1.1s cubic-bezier(.22,.9,.35,1); }}

  /* ---- chapters ---- */
  .chapter-head {{
    display:flex; align-items:center; gap:14px;
    background: var(--purple); border-top: 3px solid var(--orange);
    border-radius: 8px; padding: 16px 20px; margin-bottom: 26px;
  }}
  .chapter-num {{
    font-family:'Montserrat',sans-serif; font-weight:900; font-size:22px;
    color: var(--gold); min-width: 26px;
  }}
  .chapter-name {{ font-weight:800; font-size:20px; flex:1; }}
  .chapter-score {{ font-family:'Montserrat',sans-serif; font-weight:800; font-size:19px;
    color: var(--chip, var(--text)); }}
  .chapter-score .of {{ font-size:13px; color: rgba(255,255,255,0.55); font-weight:700; }}

  .crit {{ padding: 18px 0; border-bottom: 1px solid var(--rule); }}
  .crit:last-of-type {{ border-bottom: none; }}
  .crit-top {{ display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }}
  .crit-letter {{ color: var(--crimson); font-weight:700; font-family:'Montserrat',sans-serif; }}
  .crit-title {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:16.5px; flex:1; }}
  .chip {{
    font-family:'Montserrat',sans-serif; font-weight:800; font-size:13px;
    color: var(--chip); border: 1.5px solid var(--chip);
    border-radius: 999px; padding: 1px 10px 2px; white-space:nowrap;
  }}
  .crit-desc {{ color: var(--muted); font-style:italic; font-size:14px; margin: 4px 0 8px; }}
  .crit-finding {{ font-size: 16.5px; }}

  .means {{
    margin-top: 26px; background: rgba(107,31,106,0.22);
    border-top: 3px solid var(--orange); border-radius: 8px; padding: 20px 22px;
  }}
  .means-label {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:12px;
    letter-spacing:0.18em; text-transform:uppercase; color:var(--orange); margin-bottom:8px; }}

  /* ---- strengths / gaps ---- */
  .sg h3 {{ font-weight:800; font-size:21px; margin-bottom: 20px; }}
  .sg-card {{ border-radius:10px; padding: 24px; margin-bottom: 16px; }}
  .sg-card ul {{ list-style:none; }}
  .sg-card li {{ padding-left: 18px; position:relative; margin-bottom: 10px; font-size:16px; }}
  .sg-card li::before {{ content:"·"; position:absolute; left:2px; font-weight:900; }}
  .sg-strengths {{ background: rgba(91,176,78,0.10); border-top:3px solid {GREEN_OK}; }}
  .sg-strengths .eyebrow {{ color:{GREEN_OK}; margin-bottom:12px; }}
  .sg-strengths li::before {{ color:{GREEN_OK}; }}
  .sg-gaps {{ background: rgba(228,28,35,0.08); border-top:3px solid var(--red); }}
  .sg-gaps .eyebrow {{ color: var(--red); margin-bottom:12px; }}
  .sg-gaps li::before {{ color: var(--red); }}

  /* ---- recommendation ---- */
  .help h3 {{ font-weight:800; font-size:24px; margin: 12px 0 14px; }}
  .help > .wrap > p {{ margin-bottom: 24px; }}
  .rec {{
    background: linear-gradient(160deg, #4A1449 0%, var(--purple) 100%);
    border-top: 4px solid var(--orange); border-radius: 12px;
    padding: 32px 26px; margin-bottom: 34px;
  }}
  .rec .eyebrow {{ margin-bottom: 8px; }}
  .rec h4 {{ font-weight:800; font-size: clamp(23px, 6vw, 28px); line-height:1.2; margin-bottom:8px; }}
  .rec .rec-sub {{ color: var(--gold); font-style: italic; font-size:15.5px; margin-bottom: 16px; }}
  .rec .rec-body {{ margin-bottom: 18px; }}
  .rec .inc-label {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:13px;
    letter-spacing:0.12em; text-transform:uppercase; color:#FFD9B8; margin-bottom: 8px; }}
  .rec ul {{ list-style:none; margin-bottom: 18px; }}
  .rec li {{ padding-left: 18px; position:relative; margin-bottom: 8px; font-size:16px; }}
  .rec li::before {{ content:"·"; position:absolute; left:2px; color:var(--gold); font-weight:900; }}
  .rec .why {{ font-style: italic; font-size: 15.5px; color: #EBDDF0; }}

  .ala h4 {{ font-weight:800; font-size:19px; }}
  .ala .lead {{ color: var(--muted); font-size:15px; margin: 6px 0 20px; }}
  .ala-card {{ display:flex; gap:0; border-radius:10px; overflow:hidden;
    background: var(--ink-panel); margin-bottom: 14px; }}
  .ala-num {{ background: var(--purple); color:#fff; font-family:'Montserrat',sans-serif;
    font-weight:900; font-size:20px; display:flex; align-items:center;
    justify-content:center; min-width: 58px; }}
  .ala-body {{ padding: 20px 22px; }}
  .ala-body h4 {{ font-size:17px; margin-bottom:2px; }}
  .ala-sub {{ color: var(--orange); font-style:italic; font-size:14px; margin-bottom:8px; }}
  .ala-body p {{ font-size: 15.5px; }}

  /* ---- closing ---- */
  .closing-panel {{
    background: var(--purple); border-top:4px solid var(--orange);
    border-radius: 12px; padding: 30px 26px;
  }}
  .closing-panel .eyebrow {{ color: var(--gold); margin-bottom: 12px; }}
  .cta {{ text-align:center; padding: 52px 0 8px; }}
  .cta p {{ color: var(--muted); font-style: italic; margin-bottom: 22px; }}
  .cta a {{
    display:inline-block; font-family:'Montserrat',sans-serif; font-weight:800;
    font-size: 16px; letter-spacing: 0.02em; text-decoration:none; color:#fff;
    background: var(--flame); padding: 15px 34px; border-radius: 999px;
  }}

  footer {{
    border-top: 1px solid var(--rule); margin-top: 56px;
    padding: 26px 22px 40px; text-align:center;
    color: var(--muted); font-size: 13px;
  }}
  footer .isotype {{ width: 30px; margin: 0 auto 10px; }}
  footer .isotype svg {{ width:100%; height:auto; }}

  /* ---- motion: progressive enhancement only ---- */
  .js .reveal {{ opacity:0; transform: translateY(14px);
    transition: opacity .6s ease, transform .6s ease; }}
  .js .reveal.in {{ opacity:1; transform:none; }}
  .js .scroll-cue {{ animation: cue 2s ease-in-out infinite; }}
  @keyframes cue {{ 0%,100% {{ transform:translate(-50%,0); opacity:.7; }}
    50% {{ transform:translate(-50%,7px); opacity:1; }} }}
  @media (prefers-reduced-motion: reduce) {{
    html {{ scroll-behavior:auto; }}
    .js .reveal {{ opacity:1; transform:none; transition:none; }}
    .js .scroll-cue {{ animation:none; }}
    .bar-fill {{ transition:none; }}
  }}
</style>
</head>
<body>
<div id="progress"></div>

<!-- ============ COVER ============ -->
<header class="cover">
  <div class="isotype">{isotype}</div>
  <div class="dash"></div>
  <p class="eyebrow">Welcome to your FireScout</p>
  <h1>{clean(d['cover_title'])}</h1>
  <p class="subtitle">a comprehensive Storefront Audit by The Matchlight Group</p>
  <p class="prepared">Prepared with gratitude for</p>
  <p class="client">{client}</p>
  <p class="team">{clean(d['client_team_line'])}</p>
  <p class="date">{date_str}</p>
  <div class="scroll-cue">&#8595;</div>
</header>

<!-- ============ WHAT THIS IS ============ -->
<section>
  <div class="wrap">
    <div class="card reveal">
      <p class="eyebrow">What this is</p>
      <p>An honest, peer-to-peer look at how your brand is showing up in the
      world today — across your logo, website, social media, and overall
      message. Written in the spirit of <i>doctor in the room</i>: clear,
      kind, and shoulder-to-shoulder with you.</p>
    </div>
    <div class="card reveal">
      <p class="eyebrow">What this is not</p>
      <p>A report card. A sales pitch in disguise. A list of everything you're
      doing wrong. Numbers in this document are diagnostic tools, not
      judgments — they exist to point at where attention will pay off most,
      nothing more.</p>
    </div>
    <div class="mission reveal">
      <p class="eyebrow">Our mission</p>
      <p class="big">We exist to help local businesses <b>look as good as they
      feel</b> — and to build storefronts that <b>work as hard as the people
      behind them do</b>.</p>
      <p class="flame-italic">Whether or not you ever work with us, our goal
      with this audit is simple: leave your brand better than we found it.</p>
    </div>
  </div>
</section>

<!-- ============ INTRO + SCORE ============ -->
<section class="intro">
  <div class="wrap">
    <div class="reveal">
      <div class="dash"></div>
      <h2>{client}</h2>
      <p class="subtitle">{clean(d['client_subtitle'])}</p>
    </div>
    <p class="reveal">{clean(d['intro_paragraph_1'])}</p>
    <p class="reveal">{clean(d['intro_paragraph_2'])}</p>

    <div class="scoreboard reveal">
      <p class="score-label">Overall FireScout Score</p>
      <div class="score-big" id="score" data-target="{total_score}">{total_score}</div>
      <p class="score-of">out of 100</p>
      <p class="score-callout">{clean(d['score_callout'])}</p>
    </div>
  </div>
</section>

<!-- ============ AT A GLANCE ============ -->
<section class="glance">
  <div class="wrap">
    <h3 class="reveal">At a glance</h3>
    {''.join(bars_html)}
  </div>
</section>

<!-- ============ THE FOUR SECTIONS ============ -->
<div class="wrap">
{''.join(section_html)}
</div>

<!-- ============ STRENGTHS / GAPS ============ -->
<section class="sg">
  <div class="wrap">
    <h3 class="reveal">What's working &nbsp;·&nbsp; What needs care</h3>
    <div class="sg-card sg-strengths reveal">
      <p class="eyebrow">Strengths</p>
      <ul>{strengths_li}</ul>
    </div>
    <div class="sg-card sg-gaps reveal">
      <p class="eyebrow">Gaps</p>
      <ul>{gaps_li}</ul>
    </div>
  </div>
</section>

<!-- ============ HOW MATCHLIGHT CAN HELP ============ -->
<section class="help">
  <div class="wrap">
    <div class="reveal">
      <div class="dash"></div>
      <h3>How Matchlight Can Help</h3>
    </div>
    <p class="reveal">{clean(d['recommendation_intro'])}</p>

    <div class="rec reveal">
      <p class="eyebrow">{clean(rec.get('kicker', 'Our recommended move'))}</p>
      <h4>{clean(rec['title'])}</h4>
      <p class="rec-sub">{clean(rec['subtitle'])}</p>
      <p class="rec-body">{clean(rec['body'])}</p>
      <p class="inc-label">What's included</p>
      <ul>{includes_li}</ul>
      <p class="why">{clean(rec['why_fit'])}</p>
    </div>

    <div class="ala">
      <h4 class="reveal">Prefer to go à la carte?</h4>
      <p class="lead reveal">{clean(d['alacarte_intro'])}</p>
      {''.join(alacarte_html)}
    </div>
  </div>
</section>

<!-- ============ CLOSING ============ -->
<section>
  <div class="wrap">
    <div class="closing-panel reveal">
      <p class="eyebrow">A note from Matchlight</p>
      <p>{clean(d['closing_note'])}</p>
    </div>
    <div class="cta reveal">
      <p>Whenever you're ready to talk, we're here.</p>
      <a href="{html_mod.escape(cta_url)}">thematchlightgroup.com</a>
    </div>
  </div>
</section>

<footer>
  <div class="isotype">{isotype}</div>
  FireScout Storefront Audit &nbsp;|&nbsp; {client}<br>
  The Matchlight Group &nbsp;·&nbsp; Lynchburg, VA
</footer>

<script>
(function () {{
  document.documentElement.classList.add('js');
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Scroll progress bar
  var prog = document.getElementById('progress');
  function onScroll() {{
    var h = document.documentElement;
    var pct = (h.scrollTop || document.body.scrollTop) /
              (h.scrollHeight - h.clientHeight) * 100;
    prog.style.width = pct + '%';
  }}
  window.addEventListener('scroll', onScroll, {{ passive: true }});
  onScroll();

  // Reveals
  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduced) {{
    var io = new IntersectionObserver(function (entries) {{
      entries.forEach(function (e) {{
        if (e.isIntersecting) {{ e.target.classList.add('in'); io.unobserve(e.target); }}
      }});
    }}, {{ threshold: 0.12 }});
    revealEls.forEach(function (el) {{ io.observe(el); }});
  }} else {{
    revealEls.forEach(function (el) {{ el.classList.add('in'); }});
  }}

  // Score count-up
  var scoreEl = document.getElementById('score');
  if (scoreEl && 'IntersectionObserver' in window && !reduced) {{
    var target = parseInt(scoreEl.getAttribute('data-target'), 10) || 0;
    scoreEl.textContent = '0';
    var counted = false;
    var sio = new IntersectionObserver(function (entries) {{
      entries.forEach(function (e) {{
        if (e.isIntersecting && !counted) {{
          counted = true;
          var t0 = null, dur = 1400;
          function step(ts) {{
            if (!t0) t0 = ts;
            var p = Math.min((ts - t0) / dur, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            scoreEl.textContent = Math.round(eased * target);
            if (p < 1) requestAnimationFrame(step);
          }}
          requestAnimationFrame(step);
          sio.unobserve(scoreEl);
        }}
      }});
    }}, {{ threshold: 0.6 }});
    sio.observe(scoreEl);
  }}

  // Bar fills: start at 0, grow to target on first sight
  var bars = document.querySelectorAll('.bar-fill');
  if ('IntersectionObserver' in window && !reduced) {{
    bars.forEach(function (b) {{ b.style.width = '0%'; }});
    var bio = new IntersectionObserver(function (entries) {{
      entries.forEach(function (e) {{
        if (e.isIntersecting) {{
          var w = e.target.getAttribute('data-w');
          requestAnimationFrame(function () {{ e.target.style.width = w + '%'; }});
          bio.unobserve(e.target);
        }}
      }});
    }}, {{ threshold: 0.4 }});
    bars.forEach(function (b) {{ bio.observe(b); }});
  }}
}})();
</script>
</body>
</html>"""
