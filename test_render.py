"""
Smoke test: feed the renderer a structured payload (the same audit data
Claude would produce) and verify it produces a working PDF.

Run from inside firescout_engine/:
    MATCHLIGHT_LOGO_SVG=/mnt/user-data/uploads/Matchlight_isotype.svg python test_render.py
"""

import os
os.environ.setdefault("MATCHLIGHT_LOGO_SVG",
                      "/mnt/user-data/uploads/Matchlight_isotype.svg")

from firescout_renderer import render_audit

# This is the structured audit data — exactly what Claude would return as JSON.
audit_data = {
    "client_name": "Independent Lifestyles",
    "client_subtitle": "Mobility Specialist  |  Madison Heights, VA  |  Serving the community since 2002",
    "client_team_line": "Dave, Carrie, and the team",
    "cover_title": "A warm spark,<br/>with notes and room to grow.",
    "intro_paragraph_1": (
        "Dave and Carrie — first, thank you for the work you do. Twenty-three "
        "years of giving people back their freedom and dignity is no small "
        "thing, and it shows up the second anyone walks through your door "
        "(or gets greeted by Riley)."
    ),
    "intro_paragraph_2": (
        "On the pages ahead, you'll find a section-by-section breakdown of "
        "how your brand is showing up today, what's already working, where "
        "the gaps are, and how we'd recommend approaching them. Take your "
        "time. Disagree where you want to. Write in the margins. This "
        "document is yours."
    ),
    "score_callout": (
        "A score of 50/100 isn't a failing grade — it's a clear signal that "
        "the heart of Independent Lifestyles is bigger than the brand "
        "currently showing it. The good news? That's the easiest kind of "
        "gap to close."
    ),
    "sections": [
        {
            "name": "Logo",
            "total": 12,
            "criteria": [
                {"letter":"a","score":2,"title":"Current Design",
                 "descriptor":"Is the design up to current trends/standards?",
                 "finding":"The current mark layers three different typefaces inside a rounded blue outline — a visual language that reads more like late-1990s storefront signage than a 2026 brand."},
                {"letter":"b","score":2,"title":"Colors",
                 "descriptor":"Do the colors complement each other? Emotional evocation?",
                 "finding":"Red, blue, black, and white together feel patriotic and clinical — closer to municipal signage than to a warm, family-run business."},
                {"letter":"c","score":4,"title":"Industry Clarity",
                 "descriptor":"Do we understand your industry upon seeing it?",
                 "finding":"This is genuinely a strength. Anyone seeing the logo knows exactly what you do."},
                {"letter":"d","score":2,"title":"Design Elements",
                 "descriptor":"Isotype, logotype, typeface harmony.",
                 "finding":"The isotype is the standard International Symbol of Access — recognizable, but not <i>yours</i>."},
                {"letter":"e","score":2,"title":"Uniqueness",
                 "descriptor":"Does it differentiate from competitors?",
                 "finding":"Side-by-side with other mobility dealers, the mark blends in."},
            ],
            "summary":"Your logo communicates <b>what you do</b> very clearly, but not <b>who you are</b>."
        },
        {
            "name": "Website",
            "total": 13,
            "criteria": [
                {"letter":"a","score":3,"title":"Logo & Brand Consistency",
                 "descriptor":"Are the colors, assets, and brand throughout?",
                 "finding":"Brand consistency is decent — but you're being consistent with a logo that itself needs work."},
                {"letter":"b","score":2,"title":"Fonts",
                 "descriptor":"Are they consistent with the logo? Are they complementary?",
                 "finding":"System sans-serifs that don't echo the logo's personality. There's no clear typographic hierarchy."},
                {"letter":"c","score":3,"title":"Website Copy",
                 "descriptor":"Too much? Too little? Core tones?",
                 "finding":"Your About page copy is genuinely beautiful, but it lives only there. Homepage copy is short and transactional."},
                {"letter":"d","score":3,"title":"Effectiveness",
                 "descriptor":"Does the website serve its purpose?",
                 "finding":"Functionally yes, but not optimized for conversion. Desktop-first in a mobile-first world."},
                {"letter":"e","score":2,"title":"Interactiveness",
                 "descriptor":"Contact forms? Chat? Ecommerce where applicable?",
                 "finding":"Contact form exists, but no live chat, no instant-response options, no testimonial scroller."},
            ],
            "summary":"Functional but burying your story. The warmth on your About page is gold — let's bring it to the front door."
        },
        {
            "name": "Social Media",
            "total": 11,
            "criteria": [
                {"letter":"a","score":2,"title":"Posting Frequency & Consistency",
                 "descriptor":"Are you scheduling posts for consistent days and times?",
                 "finding":"Facebook is most active. No visible content calendar or rhythm."},
                {"letter":"b","score":2,"title":"Content Quality & Diversity",
                 "descriptor":"Mix of entertaining, trust-building, sales posts?",
                 "finding":"Most posts skew toward inventory and product features. The human side is missing."},
                {"letter":"c","score":3,"title":"Community Interaction",
                 "descriptor":"Are you commenting back? Response time?",
                 "finding":"You do respond to comments — that's a real strength. Opportunity to be more proactive."},
                {"letter":"d","score":2,"title":"Biography & Look/Feel",
                 "descriptor":"Consistent visual identity? Bio sounds like the brand?",
                 "finding":"Page bios are functional but transactional — they list what you sell rather than what you stand for."},
                {"letter":"e","score":2,"title":"Hashtag Usage",
                 "descriptor":"Niched-down hashtags driving engagement?",
                 "finding":"Hashtags appear sporadically and tend toward the broad."},
            ],
            "summary":"This is where the gap between 'who you are' and 'how you show up' is widest. Highest-ROI fix on the audit."
        },
        {
            "name": "Overall Brand",
            "total": 14,
            "criteria": [
                {"letter":"a","score":3,"title":"Branding Consistency",
                 "descriptor":"Brand consistent across all platforms?",
                 "finding":"Reasonably consistent — but consistency only matters if what's being repeated is working."},
                {"letter":"b","score":3,"title":"The Big Problem",
                 "descriptor":"Is the problem you solve stated and understood?",
                 "finding":"Visitors understand what you sell, but not the deeper problem — loss of independence, fear of being a burden."},
                {"letter":"c","score":3,"title":"Product Pitch",
                 "descriptor":"Is your service/product presented as the answer?",
                 "finding":"Products are listed but not framed as solutions. A van isn't a van — it's the ability to take your grandkids to the lake again."},
                {"letter":"d","score":2,"title":"Ideal Client",
                 "descriptor":"Do you call out and address your ideal client?",
                 "finding":"Site speaks generically. Your real ideal clients are aging adults, families, veterans, individuals with SCI."},
                {"letter":"e","score":3,"title":"Personality",
                 "descriptor":"Are your values and tone strongly present?",
                 "finding":"Your <i>actual</i> personality is one of the strongest in the category — but it's almost entirely undocumented."},
            ],
            "summary":"Highest-scoring section, and the most exciting — because the <b>raw material of a great brand is already here</b>."
        }
    ],
    "strengths": [
        "23 years of community trust",
        "A team with lived experience (Ashley)",
        "Veteran Affairs liaison built in",
        "Dealer status w/ BraunAbility, VMI, etc.",
        "Beautiful 'About' page copy",
        "Industry clarity in the logo",
        "Decent brand color consistency",
        "Active on Facebook",
        "Riley the door greeter (everyone's favorite)"
    ],
    "gaps": [
        "Logo feels dated and undifferentiated",
        "Palette fights the warm message",
        "Website is desktop-first in a mobile world",
        "Story buried two clicks deep",
        "No content calendar / posting rhythm",
        "Product-focused social, no humans",
        "No direct address of ideal clients",
        "Personality isn't documented anywhere",
        "No live chat / instant contact options"
    ],
    "recommendation_intro": (
        "The FireScout pointed at three storefronts that all need attention "
        "at once — your logo, your website, and your social media. When that's "
        "the picture, fixing them as a bundle is almost always smarter (and "
        "significantly cheaper) than fixing them one by one."
    ),
    "primary_recommendation": {
        "kicker": "OUR RECOMMENDED MOVE",
        "title": "The Ignite Storefront Cleanup",
        "subtitle": "Logo refresh + Website rebuild + Social Media kickoff · one project, one quote",
        "body": (
            "A Storefront Cleanup is exactly what it sounds like: when more "
            "than one of your storefronts is in disrepair, we tackle them "
            "together as a single, coordinated project — and give you one "
            "clear, one-time quote instead of three separate ones."
        ),
        "includes": [
            "A modernized primary logo + complete brand kit (palette, type, photo style, social templates)",
            "A mobile-first website rebuild — story-forward, conversion-ready, with your team on the homepage",
            "Social media kickoff — content strategy, branded post templates, and a 90-day posting plan to humanize the feed",
            "Honest expert direction at every step, from peers — not vendors"
        ],
        "why_fit": (
            "Why this fits you specifically: your team — Carrie's 23 years, "
            "Ashley's lived experience, Dave's leadership, Riley at the door "
            "— is already the brand. A Storefront Cleanup just puts that "
            "brand on every surface where a customer meets you."
        )
    },
    "alacarte_intro": (
        "Totally fair. If you'd rather tackle one piece at a time, here's "
        "the order we'd recommend — starting with the foundation and working "
        "outward. (Heads up: à la carte will run more in total than the "
        "bundled Cleanup.)"
    ),
    "alacarte_items": [
        {
            "title": "Brand Refresh: Logo, Palette & Visual System",
            "subtitle": "Highest impact, foundation for everything else.",
            "body": "Your warmth, longevity, and lived experience deserve a mark that carries them. We'd build you a new primary logo, a refined color palette that reads as <i>warm and trustworthy</i> rather than <i>clinical</i>, and a complete brand kit."
        },
        {
            "title": "Website Rebuild — Mobile-First, Story-Forward",
            "subtitle": "Where most of your prospects actually meet you.",
            "body": "Mobile-first rebuild with your team and story <b>on the homepage</b>. Clear pathways for distinct audiences. Outcome-driven copy. A 'Talk to a Mobility Specialist' button. Faster, cleaner, built to convert anxious shoppers into confident callers."
        },
        {
            "title": "Social Media Management — Humanize the Feed",
            "subtitle": "The fastest, most visible win.",
            "body": "Content planning and creation with a consistent posting rhythm across Facebook, Instagram, and LinkedIn. Real customer moments, team videos, Riley appearances. Within 90 days, your social would feel like the shop itself."
        }
    ],
    "closing_note": (
        "Dave and Carrie — whether you decide to work with us or not, we "
        "genuinely mean it when we say we want to leave your brand better "
        "than we found it. The team you have built over 23 years is the "
        "kind of thing money can't buy and big regional competitors can't "
        "fake. Our job, if you let us do it, is just to make sure the world "
        "can see what we already see when we walked through your door."
    ),
}

if __name__ == "__main__":
    out = "/tmp/test_audit.pdf"
    render_audit(audit_data, out, flatten=True)
    print(f"Rendered: {out}")
    print(f"Size: {os.path.getsize(out) // 1024} KB")
