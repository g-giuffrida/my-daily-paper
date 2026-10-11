from copy import deepcopy
from io import BytesIO
import base64

from PIL import Image
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4

from engine import (
    block_flowables,
    compose_regions,
    demo_issue,
    editorial_instructions,
    register_fonts,
    render_pdf,
    week_dates,
)
from layout import budgets
from settings import DEFAULT
from test_newspaper import configuration


def test_prose_targets_use_capacity_instead_of_second_safety_discount():
    settings = configuration([2, 1, 1, 2, 2, 2, 2])
    settings.update(
        headline_size=14, margin_mm=9, gutter_mm=3, masthead_mm=40, line_spacing=1.2
    )
    target = budgets(settings)["s0"]
    assert target["target_words"] >= 200
    assert target["minimum_words"] >= 175
    prompt = editorial_instructions(settings, "2026-10-11", [])
    assert "65%" not in prompt
    assert "Do NOT apply another safety discount" in prompt
    assert "never invent extra news" in prompt


def test_developed_sample_fills_most_of_front_regions_without_losing_copy():
    settings = deepcopy(DEFAULT)
    issue = demo_issue(settings, "2026-10-11")
    register_fonts()
    regions, placements = compose_regions(settings, issue)
    for region in regions:
        if region.page != 0:
            continue
        own = [(f, x, y) for r, f, x, y, _ in placements if r == region]
        assert (
            region.y + region.height - min(y for _, _, y in own)
        ) / region.height >= 0.75
        for flow, x, y in own:
            width, height = flow.wrap(flow.width, A4[1])
            assert x + width <= region.x + region.width + 0.01
            assert y >= region.y and y + height <= region.y + region.height + 0.01
    assert len(PdfReader(BytesIO(render_pdf(settings, issue))).pages) == 2


def test_short_copy_gets_readable_type_not_invented_paragraphs():
    settings = configuration([2] * 6)
    issue = demo_issue(settings, "2026-10-11")
    issue["sections"][0]["blocks"] = [
        {"type": "paragraph", "text": "OriginalReporting " * 45}
    ]
    original = deepcopy(issue)
    register_fonts()
    _, placements = compose_regions(settings, issue)
    body = [
        f
        for r, f, _, _, _ in placements
        if r.section_id == "s0"
        and hasattr(f, "getPlainText")
        and "OriginalReporting" in f.getPlainText()
    ]
    assert all(9 < f.style.fontSize <= 11 for f in body)
    assert issue == original
    text = " ".join(
        p.extract_text() for p in PdfReader(BytesIO(render_pdf(settings, issue))).pages
    )
    assert text.count("OriginalReporting") == 45


def test_comic_uses_available_frame_and_preserves_aspect_ratio():
    register_fonts()
    buffer = BytesIO()
    Image.new("RGB", (240, 160), "#eeeeee").save(buffer, format="PNG")
    flows = block_flowables(
        {"type": "illustration", "caption": "Sample cartoon", "prompt": "Cartoon"},
        250,
        DEFAULT,
        "2026-10-11",
        base64.b64encode(buffer.getvalue()).decode(),
        max_height=190,
    )
    image = flows[0]
    assert abs(image.drawWidth - 250) < .001 and image.drawHeight > 110
    assert abs(image.drawWidth / image.drawHeight - 1.5) < 0.001
    assert sum(f.wrap(250, 500)[1] for f in flows) + DEFAULT["body_size"] * 0.65 <= 190


def test_calendar_uses_spare_height_but_does_not_add_events():
    register_fonts()
    block = {
        "type": "calendar",
        "days": [{"date": d, "events": ["Office"]} for d in week_dates("2026-10-11")],
    }
    original = deepcopy(block)
    compact = block_flowables(block, 500, DEFAULT, "2026-10-11")
    full = block_flowables(block, 500, DEFAULT, "2026-10-11", max_height=190)
    assert sum(f.wrap(500, 500)[1] for f in full) > sum(
        f.wrap(500, 500)[1] for f in compact
    )
    assert sum(f.wrap(500, 500)[1] for f in full) <= 190
    assert block == original
