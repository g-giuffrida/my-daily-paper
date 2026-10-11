from copy import deepcopy

import fitz
import pytest
from reportlab.pdfbase import pdfmetrics

from engine import (
    compose_regions,
    demo_issue,
    font,
    paragraph,
    register_fonts,
    render_pdf,
    week_dates,
)
from settings import DEFAULT, FONTS
from typography import font_markup, printable_text

TEXT = "Zürich • café → ✓ ☀ 📈 🏋 😀 日本語 中文 한글 Ελληνικά Україна"


@pytest.mark.parametrize("family", FONTS + ["UnifrakturCook"])
@pytest.mark.parametrize("bold", [False, True])
def test_every_selected_font_gets_real_fallback_glyphs(family, bold):
    register_fonts()
    p = paragraph(TEXT + " مرحبا नमस्ते", DEFAULT, face=family, bold=bold)
    for fragment in p.frags:
        face = pdfmetrics.getFont(fragment.fontName).face
        assert all(
            face.charToGlyph.get(ord(c), 0) for c in fragment.text if not c.isspace()
        )
    assert p.wrap(250, 500)[1] > 0
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas

    canvas = Canvas(BytesIO())
    p.drawOn(canvas, 30, 300)
    canvas.save()


def test_normalization_and_safe_last_resort():
    register_fonts()
    assert printable_text("Cafe\u0301\t✓\r\nnext\x00") == "Café ✓\nnext"
    assert printable_text("🏋️‍♂️ 🇨🇭 👍🏽") == "🏋️‍♂️ 🇨🇭 👍🏽"
    text = font_markup("<script>&\ud800\ue000\U0010ffff", font("Source Serif 4"))
    assert "&lt;script&gt;&amp;" in text
    assert "[U+" not in text
    assert "<script>" not in text


def unicode_edition():
    settings = deepcopy(DEFAULT)
    settings["name"] = "The Zürich Times ☀"
    settings["tagline"] = "Café, culture & discovery → 日本語"
    issue = demo_issue(settings, "2026-10-10")
    for section in issue["sections"]:
        section["headline"] += " ✓"
        section["blocks"] = [{"type": "paragraph", "text": TEXT}]
    issue["sections"][-1]["blocks"] = [
        {
            "type": "calendar",
            "days": [
                {"date": day, "events": ["09:00 Café ☕ → office", "18:00 Gym 🏋️‍♂️ ✓"]}
                for day in week_dates(issue["day"])
            ],
        }
    ]
    return settings, issue


def test_unicode_edition_is_two_pages_with_measured_bounds():
    settings, issue = unicode_edition()
    register_fonts()
    _, placements = compose_regions(settings, issue)
    for region, flow, x, y, _ in placements:
        assert x >= region.x - 0.01 and y >= region.y - 0.01
        assert (
            y + getattr(flow, "height", getattr(flow, "_height", 0))
            <= region.y + region.height + 0.01
        )
    doc = fitz.open(stream=render_pdf(settings, issue), filetype="pdf")
    assert len(doc) == 2
    text = "".join(page.get_text() for page in doc)
    assert "日本語" in text and "Zürich" in text
    assert "man lifting weights" not in text and "[U+" not in text
    assert text.count("18:00 Gym") == 7


def test_cached_unicode_edition_renders_in_app():
    from test_app import app

    test = app()
    settings, issue = unicode_edition()
    # Keep existing controls/settings; generated content still exercises fallback.
    issue["sample"] = False
    test.session_state["edition"] = issue
    test.session_state["render_signature"] = "old-layout"
    test.session_state["generated_structure"] = [
        (s["id"], s["name"], s["prompt"]) for s in DEFAULT["sections"]
    ]
    test.run(timeout=20)
    assert not test.exception and not test.error
    assert len(fitz.open(stream=test.session_state["pdf"], filetype="pdf")) == 2
