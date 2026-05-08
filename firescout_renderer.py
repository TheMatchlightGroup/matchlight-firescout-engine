"""
firescout_renderer.py
=====================
The Matchlight Group — FireScout Audit Renderer
Locked, on-brand renderer. Takes structured audit_data, produces a flat PDF.

Sales team NEVER touches this file. Claude returns structured JSON → this
renders it → result looks identical to every other audit.

Usage:
    from firescout_renderer import render_audit
    render_audit(audit_data, output_path="/path/to/audit.pdf", flatten=True)
"""

import os
import io
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable
)
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

# Optional: PDF flattening (for email-safe output)
try:
    import pypdfium2 as pdfium
    from PIL import Image
    FLATTEN_AVAILABLE = True
except ImportError:
    FLATTEN_AVAILABLE = False


# =====================================================================
# BRAND CONSTANTS — never change these without design review
# =====================================================================

ML_PURPLE     = HexColor("#3D1E5C")
ML_PURPLE_LT  = HexColor("#EDE6F4")
ML_RED        = HexColor("#C42434")
ML_ORANGE     = HexColor("#F26B3A")
ML_INK        = HexColor("#1C1626")
ML_GRAY       = HexColor("#6E6577")
ML_RULE       = HexColor("#D9D2E0")
GREEN_OK      = HexColor("#5BB04E")

PAGE_W, PAGE_H = LETTER
MARGIN = 0.6 * inch

# Path to the locked Matchlight isotype SVG. Set via env var or default.
ML_LOGO_SVG = os.environ.get(
    "MATCHLIGHT_LOGO_SVG",
    str(Path(__file__).parent / "assets" / "Matchlight_isotype.svg")
)


# =====================================================================
# FLOWABLES
# =====================================================================

class CenteredLogo(Flowable):
    def __init__(self, width, target_h):
        Flowable.__init__(self)
        self.width = width
        self.target_h = target_h
        self.height = target_h

    def draw(self):
        try:
            drawing = svg2rlg(ML_LOGO_SVG)
            scale = self.target_h / drawing.height
            drawing.scale(scale, scale)
            drawing.width  = drawing.minWidth() * scale
            drawing.height = self.target_h
            x = (self.width - drawing.width) / 2
            renderPDF.draw(drawing, self.canv, x, 0)
        except Exception:
            pass


class HeaderBanner(Flowable):
    def __init__(self, title, subtitle, width):
        Flowable.__init__(self)
        self.title = title
        self.subtitle = subtitle
        self.width = width
        self.height = 0.95 * inch

    def draw(self):
        c = self.canv
        c.setFillColor(ML_PURPLE_LT)
        c.roundRect(0, 0, self.width, self.height, 6, stroke=0, fill=1)
        try:
            drawing = svg2rlg(ML_LOGO_SVG)
            target_h = 0.70 * inch
            scale = target_h / drawing.height
            drawing.scale(scale, scale)
            drawing.width  = drawing.minWidth() * scale
            drawing.height = target_h
            x = self.width - drawing.width - 0.30 * inch
            y = (self.height - drawing.height) / 2
            renderPDF.draw(drawing, c, x, y)
        except Exception:
            pass
        c.setFillColor(ML_PURPLE)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(0.4*inch, self.height - 0.42*inch, self.title)
        c.setFont("Helvetica", 11)
        c.setFillColor(ML_GRAY)
        c.drawString(0.4*inch, self.height - 0.65*inch, self.subtitle)


class ScoreBar(Flowable):
    def __init__(self, score, total, width, label):
        Flowable.__init__(self)
        self.score = score
        self.total = total
        self.width = width
        self.label = label
        self.height = 0.62 * inch

    def draw(self):
        c = self.canv
        c.setFillColor(ML_PURPLE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0, self.height - 0.18*inch, self.label)
        bar_x, bar_y = 0, 0.05 * inch
        bar_h = 0.22 * inch
        bar_w = self.width - 1.1 * inch
        c.setFillColor(ML_RULE)
        c.roundRect(bar_x, bar_y, bar_w, bar_h, 3, stroke=0, fill=1)
        pct = self.score / self.total
        fill_w = bar_w * pct
        if pct >= 0.7:    color = GREEN_OK
        elif pct >= 0.5:  color = ML_ORANGE
        else:             color = ML_RED
        c.setFillColor(color)
        if fill_w > 0:
            c.roundRect(bar_x, bar_y, fill_w, bar_h, 3, stroke=0, fill=1)
        c.setFillColor(ML_INK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(bar_w + 0.15*inch, bar_y + 0.04*inch,
                     f"{self.score} / {self.total}")


class TotalScoreCard(Flowable):
    def __init__(self, total, width):
        Flowable.__init__(self)
        self.total = total
        self.width = width
        self.height = 1.6 * inch

    def draw(self):
        c = self.canv
        c.setFillColor(ML_PURPLE)
        c.roundRect(0, 0, self.width, self.height, 8, stroke=0, fill=1)
        c.setFillColor(HexColor("#D9C9EA"))
        c.setFont("Helvetica", 10)
        c.drawCentredString(self.width/2, self.height - 0.32*inch,
                            "OVERALL FIRESCOUT SCORE")
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 54)
        c.drawCentredString(self.width/2, self.height - 1.0*inch, f"{self.total}")
        c.setFillColor(HexColor("#D9C9EA"))
        c.setFont("Helvetica", 14)
        c.drawCentredString(self.width/2, self.height - 1.28*inch, "out of 100")


# =====================================================================
# PAGE CHROME (footer)
# =====================================================================

def make_page_chrome(client_name):
    def draw_page_chrome(canv, doc):
        canv.saveState()
        if doc.page == 1:
            canv.setFillColor(ML_GRAY)
            canv.setFont("Helvetica", 9)
            canv.drawCentredString(PAGE_W/2, 0.45*inch,
                                   "thematchlightgroup.com  ·  Lynchburg, VA")
            canv.restoreState()
            return
        canv.setStrokeColor(ML_RULE)
        canv.setLineWidth(0.5)
        canv.line(MARGIN, 0.55*inch, PAGE_W - MARGIN, 0.55*inch)
        canv.setFillColor(ML_GRAY)
        canv.setFont("Helvetica", 8)
        canv.drawString(MARGIN, 0.38*inch,
                        f"FireScout Storefront Audit  |  {client_name}")
        canv.drawRightString(PAGE_W - MARGIN, 0.38*inch,
                             f"The Matchlight Group  |  Page {doc.page - 1}")
        try:
            drawing = svg2rlg(ML_LOGO_SVG)
            target_h = 0.22 * inch
            scale = target_h / drawing.height
            drawing.scale(scale, scale)
            drawing.width  = drawing.minWidth() * scale
            drawing.height = target_h
            url_text = "thematchlightgroup.com"
            canv.setFont("Helvetica-Bold", 8)
            url_w = canv.stringWidth(url_text, "Helvetica-Bold", 8)
            combo_w = drawing.width + 0.06*inch + url_w
            x_logo = (PAGE_W - combo_w) / 2
            renderPDF.draw(drawing, canv, x_logo, 0.30 * inch)
            canv.setFillColor(ML_PURPLE)
            canv.drawString(x_logo + drawing.width + 0.06*inch,
                            0.38*inch, url_text)
        except Exception:
            canv.setFillColor(ML_PURPLE)
            canv.setFont("Helvetica-Bold", 8)
            canv.drawCentredString(PAGE_W/2, 0.38*inch, "thematchlightgroup.com")
        canv.restoreState()
    return draw_page_chrome


# =====================================================================
# STYLES
# =====================================================================

styles = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
    fontSize=20, textColor=ML_PURPLE, spaceAfter=8, leading=24)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=15, textColor=ML_PURPLE, spaceBefore=12, spaceAfter=6, leading=18)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=10, textColor=ML_INK, leading=14, spaceAfter=6)
BODY_SM = ParagraphStyle("BodySm", parent=BODY, fontSize=9, leading=12,
    textColor=ML_GRAY)
CALLOUT = ParagraphStyle("Callout", parent=BODY, fontSize=10, leading=14,
    textColor=ML_PURPLE, fontName="Helvetica-Oblique")
CRITERION = ParagraphStyle("Criterion", parent=BODY, fontSize=9.5, leading=13,
    textColor=ML_INK, leftIndent=14)
INTRO = ParagraphStyle("Intro", parent=BODY, fontSize=10.5, leading=15,
    textColor=ML_INK, spaceAfter=8)


# =====================================================================
# CONTENT BUILDERS
# =====================================================================

def criterion_row(letter, score, title, descriptor, finding):
    line1 = (
        f'<b><font color="#C42434">{letter}.</font></b> '
        f'<b>{title}</b> &nbsp;&nbsp; <font color="#3D1E5C"><b>{score}/5</b></font>'
        f'<br/><font color="#6E6577" size="8.5"><i>{descriptor}</i></font>'
    )
    return [Paragraph(line1, BODY),
            Paragraph(finding, CRITERION),
            Spacer(1, 0.07*inch)]


def section_block(num, section_name, total, criteria, summary):
    out = []
    header = Table(
        [[Paragraph(f'<font color="white"><b>{num}. {section_name}</b></font>',
                    ParagraphStyle("sh", fontName="Helvetica-Bold", fontSize=13,
                                   textColor=white, leading=16)),
          Paragraph(f'<font color="white"><b>{total} / 25</b></font>',
                    ParagraphStyle("sh2", fontName="Helvetica-Bold", fontSize=13,
                                   textColor=white, leading=16, alignment=TA_RIGHT))]],
        colWidths=[5.0*inch, 1.8*inch]
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ML_PURPLE),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    out.append(header)
    out.append(Spacer(1, 0.12*inch))
    for c in criteria:
        out.extend(criterion_row(c["letter"], c["score"], c["title"],
                                 c["descriptor"], c["finding"]))
    out.append(Spacer(1, 0.05*inch))
    summary_table = Table(
        [[Paragraph(f'<b>What this means:</b> {summary}',
                    ParagraphStyle("sumstyle", fontName="Helvetica",
                                   fontSize=9.5, textColor=ML_PURPLE, leading=13))]],
        colWidths=[6.8*inch]
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ML_PURPLE_LT),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LINEABOVE", (0,0), (-1,0), 2, ML_ORANGE),
    ]))
    out.append(summary_table)
    out.append(Spacer(1, 0.20*inch))
    return out


# =====================================================================
# THE STORY
# =====================================================================

def build_story(d):
    """Build the audit Platypus story from a structured audit_data dict."""
    story = []
    content_w = PAGE_W - 2*MARGIN
    sections = d["sections"]
    total_score = sum(s["total"] for s in sections)

    # ---------- COVER ----------
    story.append(Spacer(1, 0.3*inch))
    story.append(CenteredLogo(content_w, 1.4*inch))
    story.append(Spacer(1, 0.35*inch))

    cover_kicker = ParagraphStyle("ck", fontName="Helvetica-Bold", fontSize=11,
        textColor=ML_ORANGE, leading=14, alignment=TA_CENTER, spaceAfter=6)
    cover_title = ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=28,
        textColor=ML_PURPLE, leading=32, alignment=TA_CENTER, spaceAfter=4)
    cover_sub = ParagraphStyle("cs", fontName="Helvetica", fontSize=13,
        textColor=ML_GRAY, leading=17, alignment=TA_CENTER, spaceAfter=18)
    cover_for = ParagraphStyle("cf", fontName="Helvetica-Oblique", fontSize=11,
        textColor=ML_PURPLE, leading=14, alignment=TA_CENTER, spaceAfter=4)

    story.append(Paragraph("WELCOME TO YOUR FIRESCOUT", cover_kicker))
    story.append(Paragraph(d["cover_title"], cover_title))
    story.append(Paragraph("a comprehensive Storefront Audit by The Matchlight Group", cover_sub))
    story.append(Spacer(1, 0.10*inch))
    story.append(Paragraph("Prepared with gratitude for", cover_for))
    story.append(Paragraph(f"<b>{d['client_name']}</b>",
        ParagraphStyle("cfb", fontName="Helvetica-Bold", fontSize=18,
            textColor=ML_PURPLE, leading=22, alignment=TA_CENTER, spaceAfter=2)))
    story.append(Paragraph(d["client_team_line"],
        ParagraphStyle("cft", fontName="Helvetica", fontSize=11,
            textColor=ML_GRAY, leading=14, alignment=TA_CENTER, spaceAfter=4)))

    today = date.today()
    date_str = f"{today.strftime('%B')}&nbsp;{today.day}, {today.year}"
    story.append(Paragraph(f"<i>{date_str}</i>",
        ParagraphStyle("cdate", fontName="Helvetica-Oblique", fontSize=10,
            textColor=ML_GRAY, leading=12, alignment=TA_CENTER, spaceAfter=24)))

    cbl = ParagraphStyle("cbl", fontName="Helvetica-Bold", fontSize=9,
        textColor=ML_ORANGE, leading=12, spaceAfter=4)
    cbb = ParagraphStyle("cbb", fontName="Helvetica", fontSize=10,
        textColor=ML_INK, leading=13.5)
    is_isnt = Table([[
        [Paragraph("WHAT THIS IS", cbl),
         Paragraph("An honest, peer-to-peer look at how your brand is showing "
                   "up in the world today — across your logo, website, social "
                   "media, and overall message. Written in the spirit of "
                   "<i>doctor in the room</i>: clear, kind, and "
                   "shoulder-to-shoulder with you.", cbb)],
        [Paragraph("WHAT THIS IS NOT", cbl),
         Paragraph("A report card. A sales pitch in disguise. A list of "
                   "everything you're doing wrong. Numbers in this document "
                   "are diagnostic tools, not judgments — they exist to point "
                   "at where attention will pay off most, nothing more.", cbb)]
    ]], colWidths=[3.3*inch, 3.3*inch])
    is_isnt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ML_PURPLE_LT),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 16),
        ("TOPPADDING", (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("LINEAFTER", (0,0), (0,0), 0.5, ML_RULE),
    ]))
    story.append(is_isnt)
    story.append(Spacer(1, 0.20*inch))

    creed = Table([[Paragraph(
        '<font color="#F26B3A"><b>OUR MISSION</b></font><br/><br/>'
        '<font color="white" size="13">We exist to help local businesses '
        '<b>look as good as they feel</b> — and to build storefronts that '
        '<b>work as hard as the people behind them do</b>.</font><br/><br/>'
        '<font color="#D9C9EA"><i>Whether or not you ever work with us, our '
        'goal with this audit is simple: leave your brand better than we '
        'found it.</i></font>',
        ParagraphStyle("creed", fontName="Helvetica", fontSize=11,
            textColor=white, leading=16, alignment=TA_CENTER))]],
        colWidths=[6.8*inch])
    creed.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ML_PURPLE),
        ("LEFTPADDING", (0,0), (-1,-1), 28),
        ("RIGHTPADDING", (0,0), (-1,-1), 28),
        ("TOPPADDING", (0,0), (-1,-1), 22),
        ("BOTTOMPADDING", (0,0), (-1,-1), 22),
        ("LINEABOVE", (0,0), (-1,0), 3, ML_ORANGE),
    ]))
    story.append(creed)
    story.append(PageBreak())

    # ---------- INTRO + SCORES ----------
    story.append(HeaderBanner("Welcome to your FireScout",
                              "your comprehensive Storefront Audit", content_w))
    story.append(Spacer(1, 0.25*inch))
    story.append(Paragraph(d["client_name"], H1))
    story.append(Paragraph(d["client_subtitle"], BODY_SM))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(d["intro_paragraph_1"], INTRO))
    story.append(Paragraph(d["intro_paragraph_2"], INTRO))
    story.append(Spacer(1, 0.15*inch))
    story.append(TotalScoreCard(total_score, content_w))
    story.append(Spacer(1, 0.18*inch))
    story.append(Paragraph("At a glance", H2))
    for i, s in enumerate(sections, start=1):
        story.append(ScoreBar(s["total"], 25, content_w, f"{i}.  {s['name']}"))
    story.append(Spacer(1, 0.10*inch))
    story.append(Paragraph(f"<i>{d['score_callout']}</i>", CALLOUT))
    story.append(PageBreak())

    # ---------- SECTIONS ----------
    for i, s in enumerate(sections, start=1):
        story.extend(section_block(i, s["name"], s["total"],
                                   s["criteria"], s["summary"]))
        if i == 2:  # page break after section 2 to balance layout
            story.append(PageBreak())

    story.append(PageBreak())

    # ---------- STRENGTHS / GAPS ----------
    story.append(Paragraph("What's working &nbsp;·&nbsp; What needs care", H1))
    story.append(Spacer(1, 0.1*inch))

    strengths_html = "<br/>".join(f"• {s}" for s in d["strengths"])
    gaps_html = "<br/>".join(f"• {g}" for g in d["gaps"])

    sg = Table([
        [Paragraph('<b><font color="#5BB04E">STRENGTHS</font></b>', BODY),
         Paragraph('<b><font color="#C42434">GAPS</font></b>', BODY)],
        [Paragraph(strengths_html, BODY),
         Paragraph(gaps_html, BODY)]
    ], colWidths=[3.4*inch, 3.4*inch])
    sg.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), HexColor("#E8F5E5")),
        ("BACKGROUND", (1,0), (1,0), HexColor("#FBE5E7")),
        ("BACKGROUND", (0,1), (0,1), HexColor("#F5FBF3")),
        ("BACKGROUND", (1,1), (1,1), HexColor("#FDF3F4")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LINEBELOW", (0,0), (0,0), 2, GREEN_OK),
        ("LINEBELOW", (1,0), (1,0), 2, ML_RED),
    ]))
    story.append(sg)
    story.append(Spacer(1, 0.25*inch))

    # ---------- HERO RECOMMENDATION ----------
    story.append(Paragraph("How Matchlight Can Help", H1))
    story.append(Paragraph(d["recommendation_intro"], INTRO))
    story.append(Spacer(1, 0.05*inch))

    rec = d["primary_recommendation"]
    incl_html = "<br/>".join(
        f'&nbsp;&nbsp;<b>·</b>&nbsp; {x}' for x in rec["includes"])

    ignite_inner = [
        Paragraph(f'<font color="#F26B3A" size="9"><b>{rec["kicker"]}</b></font>',
            ParagraphStyle("igk", fontName="Helvetica-Bold", fontSize=9,
                textColor=ML_ORANGE, leading=11, spaceAfter=2)),
        Paragraph(f'<font color="white"><b>{rec["title"]}</b></font>',
            ParagraphStyle("igt", fontName="Helvetica-Bold", fontSize=20,
                textColor=white, leading=24, spaceAfter=4)),
        Paragraph(f'<font color="#D9C9EA"><i>{rec["subtitle"]}</i></font>',
            ParagraphStyle("igs", fontName="Helvetica-Oblique", fontSize=10.5,
                textColor=HexColor("#D9C9EA"), leading=14, spaceAfter=10)),
        Paragraph(f'<font color="white">{rec["body"]}</font>',
            ParagraphStyle("igb", fontName="Helvetica", fontSize=10.5,
                textColor=white, leading=15, spaceAfter=10)),
        Paragraph('<font color="#FFD9B8"><b>What\'s included:</b></font>',
            ParagraphStyle("igi", fontName="Helvetica-Bold", fontSize=10,
                textColor=HexColor("#FFD9B8"), leading=13, spaceAfter=4)),
        Paragraph(f'<font color="white">{incl_html}</font>',
            ParagraphStyle("igl", fontName="Helvetica", fontSize=10,
                textColor=white, leading=15, spaceAfter=10)),
        Paragraph(f'<font color="white"><i>{rec["why_fit"]}</i></font>',
            ParagraphStyle("igw", fontName="Helvetica-Oblique", fontSize=10,
                textColor=white, leading=14)),
    ]
    ignite_card = Table([[ignite_inner]], colWidths=[6.8*inch])
    ignite_card.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ML_PURPLE),
        ("LEFTPADDING", (0,0), (-1,-1), 22),
        ("RIGHTPADDING", (0,0), (-1,-1), 22),
        ("TOPPADDING", (0,0), (-1,-1), 22),
        ("BOTTOMPADDING", (0,0), (-1,-1), 22),
        ("LINEABOVE", (0,0), (-1,0), 4, ML_ORANGE),
    ]))
    story.append(ignite_card)
    story.append(Spacer(1, 0.20*inch))

    # ---------- A LA CARTE ----------
    story.append(Paragraph("Prefer to go à la carte?",
        ParagraphStyle("aladiv", fontName="Helvetica-Bold", fontSize=14,
            textColor=ML_PURPLE, leading=18, spaceAfter=4)))
    story.append(Paragraph(d["alacarte_intro"], BODY_SM))
    story.append(Spacer(1, 0.10*inch))

    for idx, r in enumerate(d["alacarte_items"], start=1):
        rec_table = Table([[
            Paragraph(f'<font color="white" size="22"><b>{idx:02d}</b></font>',
                ParagraphStyle("rn", fontName="Helvetica-Bold", fontSize=22,
                    textColor=white, alignment=TA_CENTER, leading=24)),
            [Paragraph(f'<b>{r["title"]}</b>',
                ParagraphStyle("rt", fontName="Helvetica-Bold", fontSize=12.5,
                    textColor=ML_PURPLE, leading=15)),
             Paragraph(f'<i>{r["subtitle"]}</i>',
                ParagraphStyle("rs", fontName="Helvetica-Oblique", fontSize=9.5,
                    textColor=ML_ORANGE, leading=12, spaceAfter=4)),
             Paragraph(r["body"], BODY)]
        ]], colWidths=[0.85*inch, 5.95*inch])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,0), ML_PURPLE),
            ("BACKGROUND", (1,0), (1,0), ML_PURPLE_LT),
            ("VALIGN", (0,0), (0,0), "MIDDLE"),
            ("VALIGN", (1,0), (1,0), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
            ("ALIGN", (0,0), (0,0), "CENTER"),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 0.12*inch))

    story.append(Spacer(1, 0.15*inch))

    # ---------- CLOSING ----------
    closing = Table([[Paragraph(
        '<font color="white"><b>A note from Matchlight</b></font><br/><br/>'
        f'<font color="white">{d["closing_note"]}</font><br/><br/>'
        '<font color="white">Whenever you\'re ready to talk, we\'re here.</font><br/><br/>'
        '<font color="#F26B3A"><b>thematchlightgroup.com</b></font>',
        BODY)]], colWidths=[6.8*inch])
    closing.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ML_PURPLE),
        ("LEFTPADDING", (0,0), (-1,-1), 18),
        ("RIGHTPADDING", (0,0), (-1,-1), 18),
        ("TOPPADDING", (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
    ]))
    story.append(closing)
    story.append(PageBreak())

    # ---------- NOTES ----------
    story.append(Paragraph("Notes", H1))
    story.append(Paragraph(
        "Use this space to jot down questions, reactions, or ideas as you "
        "review the audit.", BODY_SM))
    story.append(Spacer(1, 0.2*inch))
    notes_table = Table([[""]] * 22,
        colWidths=[6.8*inch], rowHeights=[0.32*inch]*22)
    notes_table.setStyle(TableStyle([
        ("LINEBELOW", (0,0), (-1,-1), 0.5, ML_RULE),
    ]))
    story.append(notes_table)

    return story


# =====================================================================
# PUBLIC API
# =====================================================================

def render_audit(audit_data, output_path, flatten=True):
    """
    Render a FireScout audit to PDF.

    Args:
        audit_data: dict matching the FireScout schema (see SCHEMA.md)
        output_path: where to write the PDF
        flatten: if True, rasterize the output for email-safe distribution

    Returns:
        Path to the final PDF.
    """
    # Build the vector PDF
    vector_path = output_path.replace(".pdf", "_vector.pdf") if flatten else output_path
    doc = SimpleDocTemplate(
        vector_path, pagesize=LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=0.7*inch,
        title=f"FireScout Storefront Audit — {audit_data['client_name']}",
        author="The Matchlight Group",
    )
    chrome = make_page_chrome(audit_data["client_name"])
    doc.build(build_story(audit_data),
              onFirstPage=chrome, onLaterPages=chrome)

    if not flatten:
        return vector_path

    if not FLATTEN_AVAILABLE:
        raise RuntimeError("Flattening requested but pdf2image/Pillow not installed.")

    # Rasterize at 200 DPI for email-safe output
    pdf = pdfium.PdfDocument(vector_path)
    flat_pages = []
    for page in pdf:
        # 200 DPI = scale factor of 200/72 ≈ 2.78
        bitmap = page.render(scale=200/72)
        pil_img = bitmap.to_pil()
        if pil_img.mode != "RGB":
            bg = Image.new("RGB", pil_img.size, "white")
            bg.paste(pil_img, mask=pil_img.split()[3] if pil_img.mode == "RGBA" else None)
            flat_pages.append(bg)
        else:
            flat_pages.append(pil_img)
    pdf.close()
    flat_pages[0].save(output_path, save_all=True,
                       append_images=flat_pages[1:], resolution=200.0)

    # Clean up the vector intermediate
    try:
        os.remove(vector_path)
    except OSError:
        pass

    return output_path
