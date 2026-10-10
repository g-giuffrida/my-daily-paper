from copy import deepcopy
from pathlib import Path
from streamlit.testing.v1 import AppTest
from settings import DEFAULT


def app():
    test = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    test.session_state["settings"] = deepcopy(DEFAULT)
    test.session_state["history"] = []
    return test.run(timeout=20)


def test_tabs_and_section_controls():
    test = app()
    assert not test.exception
    assert [tab.label for tab in test.tabs] == ["Content", "Design", "Editorial"]
    labels = [t.label for t in test.text_input]
    assert "Companies / tickers" not in labels
    assert labels.count("Section name") == 6
    test.text_input(key="setting_name").set_value("A changed title").run()
    assert test.session_state["settings"]["name"] == "A changed title"
    test.text_area(key="section_world_prompt").set_value(
        "My completely custom topic."
    ).run()
    assert (
        test.session_state["settings"]["sections"][0]["prompt"]
        == "My completely custom topic."
    )


def test_allocation_controls_disable_generation_and_reorder():
    test = app()
    test.button(key="down_world").click().run()
    assert test.session_state["settings"]["sections"][0]["id"] == "local"
    test.selectbox(key="section_world_spaces").select(1).run()
    assert next(
        b for b in test.button if b.label == "✦ Generate today’s newspaper"
    ).disabled
    test.selectbox(key="section_world_spaces").select(2).run()
    assert not next(
        b for b in test.button if b.label == "✦ Generate today’s newspaper"
    ).disabled
    test.button(key="remove_world").click().run()
    assert len(test.session_state["settings"]["sections"]) == 5
    assert not test.exception


def test_presets_and_sample_generation():
    test = app()
    test.selectbox(key="design_preset").select("Modern journal").run()
    assert test.session_state["settings"]["body_font"] == "Source Sans 3"
    next(
        b for b in test.button if b.label == "Make sample newspaper · no API cost"
    ).click().run()
    assert not test.exception
    assert test.session_state["edition"]["sample"]
    assert test.session_state["history"] == []
    next(
        b for b in test.button if b.label == "Use classic broadsheet style"
    ).click().run()
    assert not test.exception
    assert test.session_state["settings"]["accent"] == "#171717"
    assert test.session_state["settings"]["masthead_font"] == "UnifrakturCook"
    assert test.session_state["settings"]["line_spacing"] == 1.15


def test_dense_week_preview_refits_cached_edition_without_api_calls():
    from engine import demo_issue, edition_day, week_dates
    from pypdf import PdfReader
    from io import BytesIO
    import json

    test = app()
    settings = deepcopy(DEFAULT)
    day = edition_day(settings)
    issue = demo_issue(settings, day)
    issue["sample"] = False
    issue["sections"][-1]["blocks"] = [
        {
            "type": "calendar",
            "days": [
                {
                    "date": d,
                    "events": [
                        f"Event{n}{e}: Office planning then gym and dinner with friends"
                        for e in range(4)
                    ],
                }
                for n, d in enumerate(week_dates(day))
            ],
        }
    ]
    test.session_state["edition"] = issue
    test.session_state["pdf"] = b"stale cached PDF"
    test.session_state["render_signature"] = json.dumps(settings, sort_keys=True)
    test.session_state["generated_structure"] = [
        (s["id"], s["name"], s["prompt"]) for s in settings["sections"]
    ]
    test.run(timeout=20)
    assert not test.exception and not test.error
    assert test.session_state["render_signature"].startswith("unicode-layout-v2:")
    reader = PdfReader(BytesIO(test.session_state["pdf"]))
    assert len(reader.pages) == 2
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert all(text.count(f"Event{n}{e}") == 1 for n in range(7) for e in range(4))
