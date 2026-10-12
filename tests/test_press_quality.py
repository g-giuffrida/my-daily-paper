import base64
from copy import deepcopy
from io import BytesIO

from PIL import Image as Bitmap
from reportlab.platypus import Image, Paragraph

from engine import (
    block_flowables,
    compose_regions,
    demo_issue,
    register_fonts,
    visual_section_id,
    wants_image,
    week_dates,
)
from layout import allocate, region_headline_size
from test_newspaper import configuration, DAY


def test_portrait_comic_is_centered_in_actual_pdf_placements():
    settings = configuration([2, 10])
    issue = demo_issue(settings, DAY)
    bitmap = BytesIO()
    Bitmap.new("RGB", (120, 400), "white").save(bitmap, format="PNG")
    issue["sections"][0]["blocks"] = [
        {"type": "illustration", "prompt": "comic", "caption": "Portrait comic"}
    ]
    issue["images"] = {"s0:0": base64.b64encode(bitmap.getvalue()).decode()}
    register_fonts()
    _, placed = compose_regions(settings, issue)
    r, image, x, _, _ = next(p for p in placed if isinstance(p[1], Image))
    assert abs((x + image.drawWidth / 2) - (r.x + r.width / 2)) < 0.01
    caption = next(
        f
        for r, f, *_ in placed
        if isinstance(f, Paragraph) and "Portrait comic" in f.getPlainText()
    )
    assert caption.style.alignment == 1


def test_all_article_body_and_headline_type_is_consistent():
    settings = configuration([2] * 6)
    issue = demo_issue(settings, DAY)
    for i, section in enumerate(issue["sections"]):
        section["blocks"] = [
            {
                "type": "paragraph",
                "text": ("ArticleBody%d measured reporting. " % i) * (8 + i * 2),
            }
        ]
    register_fonts()
    _, placed = compose_regions(settings, issue)
    styles = {
        (f.style.fontName, f.style.fontSize, f.style.leading)
        for _, f, *_ in placed
        if isinstance(f, Paragraph) and f.style.alignment == 4
    }
    assert len(styles) == 1
    assert {region_headline_size(settings, r) for r in allocate(settings)} == {
        settings["headline_size"]
    }


def test_wide_planner_has_seven_equal_day_columns_without_lost_events():
    settings = configuration([2, 10])
    block = {
        "type": "calendar",
        "days": [
            {"date": d, "events": [f"Event{i}", "Gym"]}
            for i, d in enumerate(week_dates(DAY))
        ],
    }
    original = deepcopy(block)
    register_fonts()
    flows = block_flowables(block, 500, settings, DAY, max_height=160)
    assert len(flows) == 1
    table = flows[0]
    assert len(table._colWidths) == 7 and len(set(table._colWidths)) == 1
    assert table.wrap(500, 800)[1] <= 160
    assert block == original


def test_visual_commission_respects_text_only_and_calendar_prompts():
    settings = configuration([2, 2, 2])
    settings["sections"][0]["prompt"] = "My week calendar"
    settings["sections"][1]["prompt"] = "Explain bonds, text only, no charts"
    settings["sections"][2]["prompt"] = "Teach working capital with a visual diagram"
    assert visual_section_id(settings) == "s2"
    assert wants_image("Make an editorial cartoon")
    assert wants_image("A comic for today")


def test_underfilled_copy_gets_one_development_pass_not_larger_type():
    from types import SimpleNamespace
    from engine import generate_issue
    from test_newspaper import FakeResponse

    settings = configuration([2])
    settings["sections"][0][
        "prompt"
    ] = "A thoughtful essay about the craft of careful reading"
    short = demo_issue(settings, DAY)
    short["sections"][0]["blocks"] = [
        {"type": "paragraph", "text": "Read carefully and consider context."}
    ]
    developed = deepcopy(short)
    developed["sections"][0]["blocks"] = [
        {
            "type": "paragraph",
            "text": "A careful reader distinguishes the argument from its evidence. "
            * 12,
        }
    ]
    replies = iter([FakeResponse(short), FakeResponse(developed)])
    calls = []

    def create(**request):
        calls.append(request)
        return next(replies).scoped(request)

    result = generate_issue(
        settings,
        "unused",
        DAY,
        client=SimpleNamespace(responses=SimpleNamespace(create=create)),
    )
    assert len(calls) == 2
    assert "measured target" in calls[1]["input"][-1]["content"]
    assert result["sections"][0]["blocks"] == developed["sections"][0]["blocks"]
