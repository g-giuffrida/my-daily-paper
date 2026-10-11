from copy import deepcopy
from io import BytesIO
import json

from pypdf import PdfReader
from reportlab.platypus import Table

from engine import (
    block_flowables,
    demo_issue,
    editorial_instructions,
    register_fonts,
    render_pdf,
    week_dates,
)
from layout import allocate, assigned_cells, move_to_cell
from settings import clean_settings, settings_errors
from test_newspaper import configuration, compositions, DAY


def test_partial_and_vertical_allocations_cover_exactly_requested_cells():
    for total in range(1, 13):
        for parts in compositions(total):
            settings = configuration(parts)
            for i, s in enumerate(settings["sections"]):
                s["orientation"] = "Vertical" if i % 2 == 0 else "Horizontal"
            assert not settings_errors(settings)
            regions = allocate(settings)
            cells = [c for r in regions for c in r.cells]
            assert len(cells) == len(set(cells)) == total
            for s in settings["sections"]:
                assert (
                    sum(len(r.cells) for r in regions if r.section_id == s["id"])
                    == s["spaces"]
                )
    settings = configuration([3, 3])
    settings["sections"][0]["orientation"] = "Vertical"
    assert assigned_cells(settings)["s0"] == [0, 2, 4]
    assert len([r for r in allocate(settings) if r.section_id == "s0"]) == 1


def test_drag_wins_destination_and_reflows_neighbours_without_loss():
    settings = configuration([2] * 6)
    settings["sections"][3]["orientation"] = "Vertical"
    move_to_cell(settings, "s3", 0)
    cells = assigned_cells(settings)
    assert cells["s3"] == [0, 2]
    assert sorted(c for own in cells.values() for c in own) == list(range(12))
    restored = clean_settings(json.loads(json.dumps(settings)))
    assert assigned_cells(restored) == cells


def test_partial_allocation_still_downloads_two_a4_pages():
    settings = configuration([2, 1])
    doc = PdfReader(BytesIO(render_pdf(settings, demo_issue(settings, DAY))))
    assert len(doc.pages) == 2


def test_language_context_contains_only_own_prompt_and_history():
    settings = configuration([2, 2])
    settings["language"] = "English"
    settings["sections"][0][
        "prompt"
    ] = "Write entirely in Swiss German. UniqueSwissPrompt"
    settings["sections"][1]["prompt"] = "Explain working capital. UniqueEnglishPrompt"
    prompt = editorial_instructions(
        settings,
        DAY,
        [{"day": DAY, "sections": {"s0": "SwissHistory", "s1": "EnglishHistory"}}],
        {"s1"},
    )
    assert "DEFAULT WRITING LANGUAGE: English" in prompt
    assert "UniqueEnglishPrompt" in prompt and "EnglishHistory" in prompt
    assert "UniqueSwissPrompt" not in prompt and "SwissHistory" not in prompt


def test_calendar_stays_a_ruled_table_even_in_compact_mode():
    settings = configuration([2])
    settings["_compact_blocks"] = True
    register_fonts()
    block = {
        "type": "calendar",
        "days": [{"date": d, "events": ["Office"]} for d in week_dates(DAY)],
    }
    flows = block_flowables(block, 450, settings, DAY)
    assert len(flows) == 8 and all(isinstance(f, Table) for f in flows)
    assert all(f._linecmds for f in flows)


def test_editorial_proof_preserves_headlines_and_uses_native_graphics():
    import fitz
    from tools.verify_editorial_pdf import proof

    settings, issue = proof()
    doc = fitz.open(stream=render_pdf(settings, issue), filetype="pdf")
    assert len(doc) == 2
    text = " ".join(" ".join(p.get_text().split()) for p in doc)
    for section in issue["sections"]:
        assert section["headline"] in text
    assert all(not page.get_images() for page in doc)
    assert all(page.get_drawings() for page in doc)
    for page in doc:
        for word in page.get_text("words"):
            assert page.rect.contains(fitz.Rect(word[:4]))
