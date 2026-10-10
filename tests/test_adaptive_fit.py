"""Regression coverage for daily editions, especially the formerly indivisible planner."""

from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4

from engine import (
    compose_regions,
    demo_issue,
    generate_issue,
    register_fonts,
    render_pdf,
    week_dates,
)
from settings import DEFAULT, FONTS
from test_newspaper import DAY, FakeResponse, compositions, configuration


def planner(events=1, long=False):
    return {
        "type": "calendar",
        "days": [
            {
                "date": day,
                "events": [
                    f"Event{d}{e} "
                    + (
                        "Office planning then gym with friends"
                        if long
                        else "Office and gym"
                    )
                    for e in range(events)
                ],
            }
            for d, day in enumerate(week_dates(DAY))
        ],
    }


def assert_fitted(settings, issue, events=()):
    register_fonts()
    _, placements = compose_regions(settings, issue)
    for region, flow, x, y, _ in placements:
        width, height = flow.wrap(getattr(flow, "width", region.width), A4[1])
        assert x >= region.x - 0.01 and y >= region.y - 0.01
        assert x + width <= region.x + region.width + 0.01
        assert y + height <= region.y + region.height + 0.01
    reader = PdfReader(BytesIO(render_pdf(settings, issue)))
    assert len(reader.pages) == 2
    text = " ".join(" ".join(p.extract_text().split()) for p in reader.pages)
    for event in events:
        assert text.count(event) == 1
    assert "TODAY" in text
    return text


@pytest.mark.parametrize("spaces", range(1, 13))
@pytest.mark.parametrize("extreme", [False, True])
def test_week_planner_fits_every_allocation_and_design_extremes(spaces, extreme):
    settings = configuration([spaces, 12 - spaces] if spaces < 12 else [12])
    if extreme:
        settings.update(
            body_size=12,
            headline_size=24,
            line_spacing=1.6,
            margin_mm=20,
            gutter_mm=10,
            padding_mm=5,
            masthead_mm=50,
        )
    issue = demo_issue(settings, DAY)
    issue["sections"][0]["headline"] = "My week ahead"
    issue["sections"][0]["blocks"] = [planner(long=True)]
    assert_fitted(settings, issue, [f"Event{d}0" for d in range(7)])


@pytest.mark.parametrize("spaces", range(1, 7))
def test_planner_on_back_page(spaces):
    settings = configuration([6, spaces, 6 - spaces] if spaces < 6 else [6, 6])
    issue = demo_issue(settings, DAY)
    issue["sections"][1]["blocks"] = [planner(long=True)]
    assert_fitted(settings, issue, [f"Event{d}0" for d in range(7)])


def test_dense_two_space_planner_uses_full_width_without_losing_events():
    settings = deepcopy(DEFAULT)
    issue = demo_issue(settings, DAY)
    issue["sections"][-1]["blocks"] = [
        planner(events=4, long=True),
        {
            "type": "paragraph",
            "text": "These are supplied plans, not confirmed attendance.",
        },
    ]
    assert_fitted(settings, issue, [f"Event{d}{e}" for d in range(7) for e in range(4)])


def test_calendar_continues_across_differently_sized_regions_in_order():
    settings = configuration([1, 5, 6])
    issue = demo_issue(settings, DAY)
    issue["sections"][1]["blocks"] = [
        {"type": "paragraph", "text": "Useful contextual reporting. " * 100},
        planner(events=3),
    ]
    text = assert_fitted(
        settings, issue, [f"Event{d}{e}" for d in range(7) for e in range(3)]
    )
    assert [text.index(f"Event{d}0") for d in range(7)] == sorted(
        text.index(f"Event{d}0") for d in range(7)
    )


def test_week_overflow_is_fixed_without_paid_revisions_or_mutating_issue():
    settings = deepcopy(DEFAULT)
    issue = demo_issue(settings, DAY)
    issue["sections"][-1]["blocks"] = [planner(events=4, long=True)]
    original = deepcopy(issue)
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return FakeResponse(issue, ["https://example.org/researched"])

    result = generate_issue(
        settings,
        "unused",
        DAY,
        client=SimpleNamespace(responses=SimpleNamespace(create=create)),
    )
    assert len(calls) == 1
    assert result["sections"] == original["sections"]
    assert_fitted(
        settings, result, [f"Event{d}{e}" for d in range(7) for e in range(4)]
    )


def test_dense_table_flows_without_losing_cells():
    settings = configuration([1, 5, 6])
    issue = demo_issue(settings, DAY)
    issue["sections"][1]["blocks"] = [
        {
            "type": "table",
            "columns": ["Name", "Notes"],
            "rows": [
                [f"Record{i:02d}", "Office and gym, then meet friends for dinner"]
                for i in range(20)
            ],
        },
        planner(),
    ]
    text = assert_fitted(settings, issue, [f"Record{i:02d}" for i in range(20)])
    assert "Notes" in text


@pytest.mark.parametrize("face", FONTS)
def test_small_planner_in_wide_fonts(face):
    settings = configuration([1] * 12)
    settings.update(
        body_font=face,
        body_size=12,
        line_spacing=1.6,
        headline_size=24,
        margin_mm=20,
        padding_mm=5,
        gutter_mm=10,
        masthead_mm=50,
    )
    issue = demo_issue(settings, DAY)
    issue["sections"][0]["headline"] = "My week"
    issue["sections"][0]["blocks"] = [planner(long=True)]
    assert_fitted(settings, issue, [f"Event{d}0" for d in range(7)])


def test_all_2048_allocations_with_calendars_have_in_bounds_placements():
    register_fonts()
    for parts in compositions(12):
        settings = configuration(parts)
        issue = demo_issue(settings, DAY)
        for section in issue["sections"]:
            section["headline"] = "The week ahead"
            section["blocks"] = [planner()]
        _, placements = compose_regions(settings, issue)
        for region, flow, x, y, _ in placements:
            width, height = flow.wrap(getattr(flow, "width", region.width), A4[1])
            assert x >= region.x - 0.01 and y >= region.y - 0.01
            assert x + width <= region.x + region.width + 0.01
            assert y + height <= region.y + region.height + 0.01


def test_shortening_keeps_original_calendar_and_sources_even_if_model_changes_them():
    settings = configuration([2] * 6)
    issue = demo_issue(settings, DAY)
    section = issue["sections"][0]
    section["blocks"] = [
        {"type": "paragraph", "text": "Verbose reporting. " * 900},
        planner(),
    ]
    section["sources"] = [
        {
            "publisher": "Verified",
            "url": "https://example.org/verified",
            "published_at": DAY,
        }
    ]
    revised = deepcopy(issue)
    revised["sections"][0]["headline"] = "My week"
    revised["sections"][0]["blocks"] = [
        {"type": "paragraph", "text": "A concise introduction."},
        planner(),
    ]
    revised["sections"][0]["blocks"][1]["days"][0]["events"] = ["Invented attendance"]
    revised["sections"][0]["sources"][0]["url"] = "https://example.org/unverified"
    replies = iter(
        [FakeResponse(issue, ["https://example.org/verified"]), FakeResponse(revised)]
    )
    result = generate_issue(
        settings,
        "unused",
        DAY,
        client=SimpleNamespace(
            responses=SimpleNamespace(create=lambda **kw: next(replies))
        ),
    )
    assert result["sections"][0]["sources"] == section["sources"]
    assert result["sections"][0]["blocks"][1] == section["blocks"][1]
    assert_fitted(settings, result, [f"Event{d}0" for d in range(7)])


@pytest.mark.parametrize("spaces", [1, 2, 3, 6, 12])
def test_charts_measure_long_titles_and_labels_before_drawing(spaces):
    settings = configuration([spaces, 12 - spaces] if spaces < 12 else [12])
    issue = demo_issue(settings, DAY)
    issue["sections"][0]["headline"] = "A useful comparison"
    issue["sections"][0]["blocks"] = [
        {
            "type": "chart",
            "title": "A sourced comparison with a longer title that must wrap instead of being clipped",
            "kind": "bar",
            "labels": ["First quarter", "Second quarter", "Third quarter"],
            "values": [10, -5, 15],
            "unit": "units",
        },
        planner(),
    ]
    assert_fitted(settings, issue, [f"Event{d}0" for d in range(7)])


@pytest.mark.parametrize("graphic_first", [True, False])
def test_one_cell_illustration_and_calendar_both_fit(graphic_first):
    import base64
    import fitz
    from PIL import Image

    settings = configuration([1] * 12)
    issue = demo_issue(settings, DAY)
    graphic = {
        "type": "illustration",
        "prompt": "An ink tree",
        "caption": "An ink tree",
    }
    section = issue["sections"][0]
    section["headline"] = "My week"
    section["blocks"] = [graphic, planner()] if graphic_first else [planner(), graphic]
    buffer = BytesIO()
    Image.new("RGB", (64, 64), "#335544").save(buffer, format="PNG")
    issue["images"] = {
        f"s0:{0 if graphic_first else 1}": base64.b64encode(buffer.getvalue()).decode()
    }
    assert_fitted(settings, issue, [f"Event{d}0" for d in range(7)])
    doc = fitz.open(stream=render_pdf(settings, issue), filetype="pdf")
    assert doc[0].get_images()


def test_shortening_remaps_illustration_when_prose_blocks_are_removed():
    import base64
    import fitz
    from PIL import Image

    settings = configuration([2] * 6)
    settings["sections"][0]["prompt"] = "A story with an illustration"
    issue = demo_issue(settings, DAY)
    section = issue["sections"][0]
    section["blocks"] = [
        {"type": "paragraph", "text": "Verbose verified reporting. " * 900},
        {"type": "paragraph", "text": "Another introduction."},
        {"type": "illustration", "prompt": "Ink tree", "caption": "Original caption"},
    ]
    buffer = BytesIO()
    Image.new("RGB", (64, 64), "#335544").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    revised = deepcopy(issue)
    revised["sections"][0]["blocks"] = [
        {"type": "paragraph", "text": "Short reporting."}
    ]
    replies = iter([FakeResponse(issue), FakeResponse(revised)])
    client = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **kw: next(replies)),
        images=SimpleNamespace(
            generate=lambda **kw: SimpleNamespace(
                data=[SimpleNamespace(b64_json=encoded)]
            )
        ),
    )
    result = generate_issue(settings, "unused", DAY, client=client)
    assert result["sections"][0]["blocks"][1] == section["blocks"][2]
    assert result["images"] == {"s0:1": encoded}
    doc = fitz.open(stream=render_pdf(settings, result), filetype="pdf")
    assert len(doc) == 2 and doc[0].get_images()
