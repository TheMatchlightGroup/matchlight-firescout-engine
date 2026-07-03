"""
scrlaudit_web.py
================
The Matchlight Group — SCRLaudit Web Renderer (v1)

Takes the structured data from Caleb's SCRLaudit form and produces ONE
self-contained HTML file: the scrolling, phone-first SCRLaudit. Shares the
Edition 01 design system with firescout_web.py — the two audits are siblings.

SCRLaudit-specific moments:
  - "Built for thumbs" cover panel: "Your site has 4 seconds." (the one
    flame-italic moment)
  - Three pillar count-ups (Clarity / Momentum / Effort) instead of one score
  - The 10-point walkthrough as burn bars with the auditor's notes underneath
  - A score-band meter (85+ / 60-84 / below 60) with the active band lit
  - "Pick the path forward" — the three fixed SCRLsite paths, recommended
    one highlighted

Fully readable with JavaScript off; motion is progressive enhancement.
"""

import html as html_mod
from firescout_web import (
    clean, load_isotype, score_color,
    CHARCOAL, PURPLE, CRIMSON, RED, ORANGE, GOLD, GREEN_OK, FLAME_GRADIENT,
)

WALKTHROUGH_LABELS = [
    "Page loads in under 2.5 seconds on mobile",
    "Site feels responsive when scrolling and tapping",
    "Value proposition is clear in first screen view",
    "Primary CTA visible immediately",
    "Content flows logically as you scroll",
    "Sections are scannable and thumb-friendly",
    "Trust signals appear early (reviews, photos)",
    "Design feels modern and credible",
    "Contact / booking is easy on mobile",
    "Primary CTA repeated naturally in scroll",
]

BANDS = [
    (85, 100, "Elite Mobile Experience", "SCRLsite Blaze"),
    (60, 84,  "Attention & Conversion Leaks", "SCRLsite Ignite"),
    (0,  59,  "High Bounce Risk", "Custom SCRLsite Rebuild"),
]

PATHS = [
    {
        "num": "01", "title": "SCRLsite Ignite", "price": "$500 · one-time",
        "tag": "Mobile-first. Beautifully done.",
        "bullets": ["7-day build", "Custom branded to your business",
                    "Click-to-call, maps, and contact forms",
                    "Hosted &amp; maintained — no monthly agency fees"],
    },
    {
        "num": "02", "title": "SCRLsite Blaze", "price": "From $1,000",
        "tag": "Premium build with more depth.",
        "bullets": ["Everything in Ignite, plus more",
                    "Expanded content &amp; sections",
                    "Advanced animations and lead-gen integrations",
                    "Priority support"],
    },
    {
        "num": "03", "title": "Matchy App Blueprint", "price": "$4.99 – $19.99",
        "tag": "An app idea, turned into a real spec.",
        "bullets": ["Blueprint score and tech stack recommendations",
                    "API surface map and dev handoff brief",
                    "Cost comparison across build paths"],
    },
]


def band_for(score: int):
    for lo, hi, name, rec in BANDS:
        if lo <= score <= hi:
            return name, rec
    return BANDS[-1][2], BANDS[-1][3]


def default_interpretation(score: int, client: str) -> str:
    band, _ = band_for(score)
    return (f"A score of {score} puts {client} in the '{band}' band. That "
            "isn't a verdict — it's a starting line. Most of what's holding "
            "the site back is presentation, and presentation is the most "
            "fixable thing in the world.")


def render_scrlaudit_web(d: dict, cta_url: str = "https://www.thematchlightgroup.com") -> str:
    isotype = load_isotype()
    client = clean(d.get("client_name", ""))

    items = d["walkthrough"]  # list of {label, score, note}
    total = sum(int(i["score"]) for i in items)
    band_name, band_rec = band_for(total)

    interpretation = (d.get("interpretation") or "").strip() or \
        default_interpretation(total, d.get("client_name", "your site"))

    rec_headline = (d.get("rec_headline") or band_rec).strip()

    # ----- pillars -----
    pillars_meta = [
        ("Clarity", "Can someone tell what you do in 4 seconds?", d["pillar_clarity"]),
        ("Momentum", "Does the site feel fast and flow naturally?", d["pillar_momentum"]),
        ("Effort", "How hard is it to take the next step?", d["pillar_effort"]),
    ]
    pillars_html = []
    for i, (name, q, score) in enumerate(pillars_meta, start=1):
        col = score_color(int(score), 10)
        pillars_html.append(f"""
      <div class="pillar reveal">
        <p class="eyebrow">0{i} · Pillar</p>
        <h3>{name}</h3>
        <p class="pillar-q">{q}</p>
        <div class="pillar-score count" data-target="{int(score)}" style="color:{col}">{int(score)}</div>
        <p class="score-of">/ 10</p>
      </div>""")

    # ----- walkthrough -----
    walk_html = []
    for i, item in enumerate(items, start=1):
        score = int(item["score"])
        pct = score * 10
        col = score_color(score, 10)
        note = (item.get("note") or "").strip()
        note_html = f'<p class="walk-note">› {clean(note)}</p>' if note else ""
        walk_html.append(f"""
      <div class="walk reveal">
        <div class="walk-top">
          <span class="walk-num">{i:02d}</span>
          <span class="walk-label">{clean(item['label'])}</span>
          <span class="walk-score" style="color:{col}">{score} / 10</span>
        </div>
        <div class="bar-track"><div class="bar-fill" data-w="{pct}" style="width:{pct}%;background:{col}"></div></div>
        {note_html}
      </div>""")

    # ----- band meter -----
    band_rows = []
    for lo, hi, name, rec in BANDS:
        active = " active" if name == band_name else ""
        rng = f"{lo} – {hi}" if lo else f"Below {hi + 1}"
        band_rows.append(f"""
      <div class="band{active} reveal">
        <span class="band-dot"></span>
        <div class="band-body">
          <span class="band-range">{rng}</span>
          <span class="band-name">{name}</span>
          <span class="band-rec">› Recommended: {rec}</span>
        </div>
      </div>""")

    # ----- deep dive -----
    dive_rows = []
    for label, key in (("Clarity", "dive_clarity"), ("Momentum", "dive_momentum"),
                       ("Effort", "dive_effort")):
        txt = (d.get(key) or "").strip()
        if txt:
            dive_rows.append(
                f'<p class="dive reveal"><span class="dive-label">{label}:</span> {clean(txt)}</p>')
    other = [ln.strip() for ln in (d.get("other_notes") or "").splitlines() if ln.strip()]
    other_html = ""
    if other:
        lis = "".join(f"<li>{clean(x)}</li>" for x in other)
        other_html = f"""
      <div class="reveal"><p class="dive-label" style="margin-top:18px">Other notes:</p>
      <ul class="other-notes">{lis}</ul></div>"""

    conclusion = (d.get("conclusion") or "").strip()
    conclusion_html = ""
    if conclusion:
        conclusion_html = f"""
    <div class="means reveal">
      <p class="means-label">What this means</p>
      <p class="means-body">{clean(conclusion)}</p>
    </div>"""

    # ----- paths -----
    paths_html = []
    for p in PATHS:
        rec_flag = p["title"].lower() in rec_headline.lower()
        badge = '<span class="rec-badge">Recommended</span>' if rec_flag else ""
        bullets = "".join(f"<li>{b}</li>" for b in p["bullets"])
        paths_html.append(f"""
      <div class="path-card{' path-rec' if rec_flag else ''} reveal">
        <div class="path-num">{p['num']}</div>
        <div class="path-body">
          <div class="path-head"><h4>{p['title']}</h4>{badge}</div>
          <p class="path-price">{p['price']}</p>
          <p class="path-tag">{p['tag']}</p>
          <ul>{bullets}</ul>
        </div>
      </div>""")

    subtitle_bits = [clean(d.get("business_type", "")), clean(d.get("location", ""))]
    subtitle = "  |  ".join(b for b in subtitle_bits if b)
    auditor_line = f"Audited by {clean(d.get('auditor_name',''))}" if d.get("auditor_name") else ""
    if d.get("audit_date"):
        auditor_line += f"  ·  {clean(d['audit_date'])}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>SCRLaudit · {client} · The Matchlight Group</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,700;0,800;0,900;1,800&family=Lato:ital,wght@0,300;0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
  :root {{
    --charcoal: {CHARCOAL}; --purple: {PURPLE}; --crimson: {CRIMSON};
    --red: {RED}; --orange: {ORANGE}; --gold: {GOLD};
    --ink-panel: #262030; --text: #F2EFF4; --muted: #A79FB2;
    --rule: rgba(255,255,255,0.10); --flame: {FLAME_GRADIENT};
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{ background:var(--charcoal); color:var(--text);
    font-family:'Lato',-apple-system,sans-serif; font-weight:300;
    font-size:17px; line-height:1.65; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:680px; margin:0 auto; padding:0 22px; }}
  h1,h2,h3,h4 {{ font-family:'Montserrat',sans-serif; }}
  b,strong {{ font-weight:700; }}
  #progress {{ position:fixed; top:0; left:0; height:3px; width:0%;
    background:var(--flame); z-index:100; }}
  .dash {{ width:56px; height:5px; background:var(--flame); border-radius:3px; }}
  .eyebrow {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:12px;
    letter-spacing:0.22em; text-transform:uppercase; color:var(--orange); }}

  .cover {{ min-height:100svh; display:flex; flex-direction:column;
    align-items:center; justify-content:center; text-align:center;
    padding:64px 22px 48px; position:relative; }}
  .cover .isotype {{ width:92px; margin-bottom:28px; }}
  .cover .isotype svg {{ width:100%; height:auto; display:block; }}
  .cover .dash {{ margin:0 auto 22px; }}
  .cover h1 {{ font-weight:900; font-size:clamp(30px,8vw,44px); line-height:1.12;
    letter-spacing:-0.01em; margin:14px 0 12px; }}
  .cover .subtitle {{ color:var(--muted); font-size:15px; }}
  .cover .prepared {{ margin-top:38px; font-style:italic; color:var(--muted); font-size:15px; }}
  .cover .client {{ font-family:'Montserrat',sans-serif; font-weight:800;
    font-size:clamp(22px,6vw,30px); margin-top:6px; }}
  .cover .team {{ color:var(--muted); font-size:15px; margin-top:4px; }}
  .cover .date {{ color:var(--muted); font-style:italic; font-size:14px; margin-top:10px; }}
  .scroll-cue {{ position:absolute; bottom:26px; left:50%;
    transform:translateX(-50%); color:var(--muted); font-size:22px; }}

  section {{ padding:56px 0; }}
  section + section {{ border-top:1px solid var(--rule); }}
  .card {{ background:var(--ink-panel); border-radius:10px;
    padding:26px 24px; margin-bottom:16px; }}
  .card .eyebrow {{ margin-bottom:10px; }}

  .thumbs {{ background:var(--purple); border-top:4px solid var(--orange);
    border-radius:10px; padding:34px 28px; text-align:center; }}
  .thumbs .eyebrow {{ color:var(--gold); margin-bottom:14px; }}
  .thumbs p.big {{ font-family:'Montserrat',sans-serif; font-weight:800; font-size:22px; }}
  .thumbs p.flame-italic {{ margin-top:6px; font-family:'Montserrat',sans-serif;
    font-weight:800; font-style:italic; font-size:22px;
    background:linear-gradient(90deg,#C77BC5 0%,{GOLD} 100%);
    -webkit-background-clip:text; background-clip:text; color:transparent; }}
  .thumbs .tags {{ margin-top:16px; color:#D9CBE0; font-style:italic; font-size:14px; }}

  .pillars {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
  @media (max-width:560px) {{ .pillars {{ grid-template-columns:1fr; }} }}
  .pillar {{ background:var(--ink-panel); border-top:3px solid var(--orange);
    border-radius:10px; padding:22px 18px; text-align:center; }}
  .pillar h3 {{ font-weight:800; font-size:21px; margin:6px 0 4px; }}
  .pillar-q {{ color:var(--muted); font-style:italic; font-size:13.5px;
    min-height:3.2em; margin-bottom:8px; }}
  .pillar-score {{ font-family:'Montserrat',sans-serif; font-weight:900;
    font-size:56px; line-height:1; }}
  .score-of {{ color:var(--muted); font-size:14px; }}

  .walk-head h3, .glance-title {{ font-weight:800; font-size:21px; margin-bottom:22px; }}
  .walk {{ padding:16px 0; border-bottom:1px solid var(--rule); }}
  .walk:last-of-type {{ border-bottom:none; }}
  .walk-top {{ display:flex; align-items:baseline; gap:10px; margin-bottom:8px; }}
  .walk-num {{ color:var(--crimson); font-family:'Montserrat',sans-serif;
    font-weight:800; font-size:14px; }}
  .walk-label {{ font-family:'Montserrat',sans-serif; font-weight:700;
    font-size:15.5px; flex:1; }}
  .walk-score {{ font-family:'Montserrat',sans-serif; font-weight:800;
    font-size:14px; white-space:nowrap; }}
  .bar-track {{ height:10px; background:rgba(255,255,255,0.08);
    border-radius:5px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:5px;
    transition:width 1.1s cubic-bezier(.22,.9,.35,1); }}
  .walk-note {{ margin-top:8px; color:var(--muted); font-style:italic; font-size:14.5px; }}

  .scoreboard {{ text-align:center; padding:10px 0 8px; }}
  .score-label {{ font-family:'Montserrat',sans-serif; font-weight:700;
    font-size:12px; letter-spacing:0.22em; text-transform:uppercase; color:var(--muted); }}
  .score-big {{ font-family:'Montserrat',sans-serif; font-weight:900;
    font-size:clamp(88px,26vw,132px); line-height:1; background:var(--flame);
    -webkit-background-clip:text; background-clip:text; color:transparent;
    display:inline-block; margin:6px 0 2px; }}
  .score-sub {{ color:var(--muted); font-size:14px; font-style:italic; }}
  .score-callout {{ font-style:italic; color:var(--muted); max-width:540px;
    margin:22px auto 0; font-size:16px; }}

  .bands {{ margin-top:30px; }}
  .band {{ display:flex; gap:14px; align-items:flex-start;
    background:var(--ink-panel); border-radius:10px;
    padding:16px 18px; margin-bottom:10px; opacity:0.66; }}
  .band.active {{ opacity:1; border:1px solid var(--orange);
    background:rgba(107,31,106,0.25); }}
  .band-dot {{ width:10px; height:10px; border-radius:50%;
    background:rgba(255,255,255,0.25); margin-top:8px; flex:none; }}
  .band.active .band-dot {{ background:var(--orange); }}
  .band-range {{ font-family:'Montserrat',sans-serif; font-weight:800;
    font-size:15px; display:block; }}
  .band-name {{ font-size:15px; display:block; }}
  .band-rec {{ color:var(--muted); font-style:italic; font-size:13.5px; display:block; }}

  .dive-label {{ font-family:'Montserrat',sans-serif; font-weight:700;
    color:var(--orange); }}
  .dive {{ margin-bottom:16px; }}
  .other-notes {{ list-style:none; margin-top:6px; }}
  .other-notes li {{ padding-left:18px; position:relative; margin-bottom:8px; }}
  .other-notes li::before {{ content:"•"; position:absolute; left:2px;
    color:var(--orange); }}
  .means {{ margin-top:26px; background:rgba(107,31,106,0.22);
    border-top:3px solid var(--orange); border-radius:8px; padding:20px 22px; }}
  .means-label {{ font-family:'Montserrat',sans-serif; font-weight:700;
    font-size:12px; letter-spacing:0.18em; text-transform:uppercase;
    color:var(--orange); margin-bottom:8px; }}

  .paths h3 {{ font-weight:800; font-size:24px; margin:12px 0 4px; }}
  .paths .lead {{ color:var(--muted); font-style:italic; font-size:15px;
    margin-bottom:22px; }}
  .rec-move {{ background:linear-gradient(160deg,#4A1449 0%,var(--purple) 100%);
    border-top:4px solid var(--orange); border-radius:12px;
    padding:28px 26px; margin-bottom:28px; }}
  .rec-move .eyebrow {{ margin-bottom:8px; }}
  .rec-move h4 {{ font-weight:800; font-size:clamp(22px,6vw,27px); margin-bottom:8px; }}
  .rec-move p {{ font-size:16px; }}
  .path-card {{ display:flex; border-radius:10px; overflow:hidden;
    background:var(--ink-panel); margin-bottom:14px; }}
  .path-card.path-rec {{ outline:1.5px solid var(--orange); }}
  .path-num {{ background:var(--purple); color:#fff;
    font-family:'Montserrat',sans-serif; font-weight:900; font-size:20px;
    display:flex; align-items:center; justify-content:center; min-width:58px; }}
  .path-rec .path-num {{ background:var(--orange); }}
  .path-body {{ padding:20px 22px; flex:1; }}
  .path-head {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
  .path-body h4 {{ font-size:17.5px; }}
  .rec-badge {{ font-family:'Montserrat',sans-serif; font-weight:800;
    font-size:11px; letter-spacing:0.1em; text-transform:uppercase;
    background:var(--orange); color:#fff; border-radius:999px; padding:2px 10px; }}
  .path-price {{ color:var(--gold); font-weight:700; font-size:14.5px; margin:2px 0; }}
  .path-tag {{ color:var(--muted); font-style:italic; font-size:14px; margin-bottom:10px; }}
  .path-body ul {{ list-style:none; }}
  .path-body li {{ padding-left:16px; position:relative; margin-bottom:6px;
    font-size:15px; }}
  .path-body li::before {{ content:"›"; position:absolute; left:0;
    color:var(--orange); font-weight:900; }}

  .closing-panel {{ background:var(--purple); border-top:4px solid var(--orange);
    border-radius:12px; padding:30px 26px; }}
  .closing-panel .eyebrow {{ color:var(--gold); margin-bottom:12px; }}
  .cta {{ text-align:center; padding:52px 0 8px; }}
  .cta p {{ color:var(--muted); font-style:italic; margin-bottom:22px; }}
  .cta a {{ display:inline-block; font-family:'Montserrat',sans-serif;
    font-weight:800; font-size:16px; text-decoration:none; color:#fff;
    background:var(--flame); padding:15px 34px; border-radius:999px; }}
  footer {{ border-top:1px solid var(--rule); margin-top:56px;
    padding:26px 22px 40px; text-align:center; color:var(--muted); font-size:13px; }}
  footer .isotype {{ width:30px; margin:0 auto 10px; }}
  footer .isotype svg {{ width:100%; height:auto; }}

  .js .reveal {{ opacity:0; transform:translateY(14px);
    transition:opacity .6s ease, transform .6s ease; }}
  .js .reveal.in {{ opacity:1; transform:none; }}
  .js .scroll-cue {{ animation:cue 2s ease-in-out infinite; }}
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

<header class="cover">
  <div class="isotype">{isotype}</div>
  <div class="dash"></div>
  <p class="eyebrow">Welcome to your SCRLaudit</p>
  <h1>A Mobile Audit for<br/>{client}</h1>
  <p class="subtitle">a focused mobile-first review by The Matchlight Group</p>
  <p class="prepared">Prepared with gratitude for</p>
  <p class="client">{client}</p>
  <p class="team">{subtitle}</p>
  <p class="date">{auditor_line}</p>
  <div class="scroll-cue">&#8595;</div>
</header>

<section>
  <div class="wrap">
    <div class="card reveal">
      <p class="eyebrow">What this is</p>
      <p>A focused mobile-first walkthrough of your website — the way your
      customers actually experience it. Honest, peer-to-peer, and built around
      one question: what would help most right now?</p>
    </div>
    <div class="card reveal">
      <p class="eyebrow">What this is not</p>
      <p>A report card. A sales pitch in disguise. A list of everything you're
      doing wrong. Scores are diagnostic — they point at where attention will
      pay off most, nothing more.</p>
    </div>
    <div class="thumbs reveal">
      <p class="eyebrow">Built for thumbs</p>
      <p class="big">Your site has 4 seconds.</p>
      <p class="flame-italic">Let's see how it does.</p>
      <p class="tags">Mobile-first &nbsp;·&nbsp; Scroll-designed &nbsp;·&nbsp; Conversion-focused</p>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="reveal" style="margin-bottom:24px">
      <div class="dash"></div>
      <h3 class="glance-title" style="margin:14px 0 0">The three pillars</h3>
    </div>
    <div class="pillars">
      {''.join(pillars_html)}
    </div>
  </div>
</section>

<section>
  <div class="wrap walk-head">
    <h3 class="reveal">The 10-point walkthrough</h3>
    {''.join(walk_html)}
  </div>
</section>

<section>
  <div class="wrap">
    <div class="scoreboard reveal">
      <p class="score-label">Overall SCRLscore</p>
      <div class="score-big" id="score" data-target="{total}">{total}</div>
      <p class="score-sub">out of 100 &nbsp;·&nbsp; clarity · momentum · effort</p>
      <p class="score-callout">{clean(interpretation)}</p>
    </div>
    <div class="bands">
      {''.join(band_rows)}
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="reveal" style="margin-bottom:20px">
      <div class="dash"></div>
      <h3 class="glance-title" style="margin:14px 0 0">The deep dive <span style="color:var(--muted);font-size:14px;font-weight:400;font-style:italic">· auditor notes</span></h3>
    </div>
    {''.join(dive_rows)}
    {other_html}
    {conclusion_html}
  </div>
</section>

<section class="paths">
  <div class="wrap">
    <div class="reveal">
      <div class="dash"></div>
      <h3>Pick the path forward.</h3>
      <p class="lead">Based on this audit, here's what we'd suggest next.</p>
    </div>
    <div class="rec-move reveal">
      <p class="eyebrow">Our recommended move</p>
      <h4>{clean(rec_headline)}</h4>
      <p>{clean(d.get('rec_body',''))}</p>
    </div>
    {''.join(paths_html)}
  </div>
</section>

<section>
  <div class="wrap">
    <div class="closing-panel reveal">
      <p class="eyebrow">A note from Matchlight</p>
      <p>{clean(d.get('closing_note',''))}</p>
    </div>
    <div class="cta reveal">
      <p>Whenever you're ready to close the gap, we're here.</p>
      <a href="{html_mod.escape(cta_url)}">thematchlightgroup.com</a>
    </div>
  </div>
</section>

<footer>
  <div class="isotype">{isotype}</div>
  SCRLaudit &nbsp;|&nbsp; {client}<br>
  The Matchlight Group &nbsp;·&nbsp; Lynchburg, VA
</footer>

<script>
(function () {{
  document.documentElement.classList.add('js');
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var prog = document.getElementById('progress');
  function onScroll() {{
    var h = document.documentElement;
    prog.style.width = ((h.scrollTop || document.body.scrollTop) /
      (h.scrollHeight - h.clientHeight) * 100) + '%';
  }}
  window.addEventListener('scroll', onScroll, {{ passive: true }});
  onScroll();

  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduced) {{
    var io = new IntersectionObserver(function (es) {{
      es.forEach(function (e) {{
        if (e.isIntersecting) {{ e.target.classList.add('in'); io.unobserve(e.target); }}
      }});
    }}, {{ threshold: 0.12 }});
    revealEls.forEach(function (el) {{ io.observe(el); }});
  }} else {{
    revealEls.forEach(function (el) {{ el.classList.add('in'); }});
  }}

  function countUp(el, dur) {{
    var target = parseInt(el.getAttribute('data-target'), 10) || 0;
    el.textContent = '0';
    var t0 = null;
    function step(ts) {{
      if (!t0) t0 = ts;
      var p = Math.min((ts - t0) / dur, 1);
      el.textContent = Math.round((1 - Math.pow(1 - p, 3)) * target);
      if (p < 1) requestAnimationFrame(step);
    }}
    requestAnimationFrame(step);
  }}

  if ('IntersectionObserver' in window && !reduced) {{
    var counters = document.querySelectorAll('.count, #score');
    var cio = new IntersectionObserver(function (es) {{
      es.forEach(function (e) {{
        if (e.isIntersecting) {{
          countUp(e.target, e.target.id === 'score' ? 1400 : 900);
          cio.unobserve(e.target);
        }}
      }});
    }}, {{ threshold: 0.6 }});
    counters.forEach(function (el) {{ cio.observe(el); }});

    var bars = document.querySelectorAll('.bar-fill');
    bars.forEach(function (b) {{ b.style.width = '0%'; }});
    var bio = new IntersectionObserver(function (es) {{
      es.forEach(function (e) {{
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
