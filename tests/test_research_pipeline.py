"""Regression tests for the API -> evidence IDs -> newspaper -> preview flow."""

from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path

try:
    import httpx2 as httpx
except ImportError:  # OpenAI SDK 1.x/2.x
    import httpx
import jsonschema
from openai import OpenAI
from pypdf import PdfReader
import pytest

from engine import (
    SECTION_SCHEMA,
    demo_issue,
    edition_day,
    generate_issue,
    object_schema,
    render_pdf,
    needs_news,
    validate_issue,
    week_dates,
)
from layout import budgets
from research import draft_schema, resolve_draft, source_catalog
from settings import TEXT_MODELS
from test_newspaper import configuration

URL = "https://example.org/story?id=42&utm_source=web#facts"
DAY = "2026-10-11"


def client_fixture(settings, day=DAY, empty=False):
    calls = []

    def reply(request):
        payload = json.loads(request.content)
        calls.append(payload)
        annotations = []
        if "tools" in payload:
            text = (
                "No verified update was found."
                if empty
                else "Research fixture: published on " + day
            )
            if not empty:
                annotations = [
                    {
                        "type": "url_citation",
                        "url": URL,
                        "title": "Verified test evidence",
                        "start_index": 0,
                        "end_index": len(text),
                    }
                ]
        else:
            sections = {}
            schema = payload["text"]["format"]["schema"]
            for section in demo_issue(settings, day)["sections"]:
                if section["id"] not in schema["properties"]["sections"]["properties"]:
                    continue
                fields = schema["properties"]["sections"]["properties"][section["id"]][
                    "properties"
                ]
                refs = fields["source_refs"]
                sections[section["id"]] = {
                    "headline": section["headline"],
                    "summary": section["summary"],
                    "blocks": section["blocks"],
                    "source_refs": (
                        [{"source_id": "S1", "published_at": day}]
                        if refs["maxItems"]
                        else []
                    ),
                }
                if "visual" in fields:
                    sections[section["id"]]["visual"] = {
                        "type": "diagram",
                        "title": "Learning cycle",
                        "steps": ["Read an example", "Practise"],
                        "caption": "Illustrative learning method",
                    }
                if empty and needs_news(
                    next(
                        s["prompt"]
                        for s in settings["sections"]
                        if s["id"] == section["id"]
                    )
                ):
                    sections[section["id"]]["blocks"] = [
                        {
                            "type": "paragraph",
                            "text": "No verified update was found for this edition.",
                        }
                    ]
            draft = {"sections": sections}
            jsonschema.validate(draft, schema)
            text = json.dumps(draft)
        return httpx.Response(
            200,
            json={
                "id": "resp_fixture",
                "object": "response",
                "created_at": 0,
                "model": settings["model"],
                "status": "completed",
                "output": [
                    {
                        "id": "msg_fixture",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": text,
                                "annotations": annotations,
                            }
                        ],
                    }
                ],
            },
        )

    return (
        OpenAI(
            api_key="test-local-mock",
            http_client=httpx.Client(transport=httpx.MockTransport(reply)),
        ),
        calls,
    )


def configuration_with_news():
    settings = configuration([2, 1, 3, 6])
    for s, prompt in zip(
        settings["sections"],
        [
            "Latest stock news",
            "My week: Monday office, Wednesday gym",
            "A German B1 lesson",
            "Current local weather",
        ],
    ):
        s["prompt"] = prompt
    return settings


@pytest.mark.parametrize("model", TEXT_MODELS)
def test_real_sdk_serialization_research_to_two_page_pdf(model):
    settings = configuration_with_news()
    settings["model"] = model
    client, calls = client_fixture(settings)
    issue = generate_issue(settings, "unused", DAY, client=client)
    assert (
        len(calls) == 6
    )  # two researches, four isolated copy desks, no citation retries
    assert all(c["tool_choice"] == "required" for c in calls[:2])
    assert "tools" not in calls[-1]
    for section in issue["sections"]:
        assert all(s["url"] == URL for s in section["sources"])
    reader = PdfReader(BytesIO(render_pdf(settings, issue)))
    assert len(reader.pages) == 2
    assert DAY in reader.metadata.title
    links = [
        a.get_object()["/A"]["/URI"]
        for page in reader.pages
        for a in page.get("/Annots", [])
    ]
    assert links == [URL, URL]


def test_empty_search_is_researched_again_and_reported_honestly_not_a_citation_error():
    settings = configuration_with_news()
    client, calls = client_fixture(settings, empty=True)
    issue = generate_issue(settings, "unused", DAY, client=client)
    assert len(calls) == 8
    assert not any(s["sources"] for s in issue["sections"])
    for i in [0, 3]:
        assert "No verified update" in issue["sections"][i]["blocks"][0]["text"]
    assert len(PdfReader(BytesIO(render_pdf(settings, issue))).pages) == 2


def test_source_catalog_ignores_model_written_links_and_accepts_both_annotation_shapes():
    data = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "text": '{"url":"https://fake.invalid"}',
                        "annotations": [
                            {"type": "url_citation", "url": URL, "title": "Story"},
                            {
                                "type": "url_citation",
                                "url_citation": {"url": "https://other.example/story"},
                            },
                        ],
                    }
                ],
            },
            {"type": "web_search_call", "action": {"type": "open_page", "url": URL}},
        ]
    }
    catalog = source_catalog(data)
    assert [s["url"] for s in catalog.values()] == [URL, "https://other.example/story"]
    assert catalog["S1"]["publisher"] == "example.org"


def test_schema_cannot_emit_unknown_source_ids_or_source_urls():
    settings = configuration([6, 6])
    research = {"s0": {"sources": {"S1": {"url": URL, "publisher": "example.org"}}}}
    schema = draft_schema(settings, research, SECTION_SCHEMA, object_schema)
    draft = {
        "sections": {
            s["id"]: {
                "headline": "A headline",
                "summary": "Summary",
                "blocks": [{"type": "paragraph", "text": "An article."}],
                "source_refs": (
                    [{"source_id": "S1", "published_at": "unknown"}]
                    if s["id"] == "s0"
                    else []
                ),
            }
            for s in settings["sections"]
        }
    }
    jsonschema.validate(draft, schema)
    assert resolve_draft(draft, settings, research, DAY)["sections"][0]["sources"][
        0
    ] == {"url": URL, "publisher": "example.org", "published_at": ""}
    for target, key, value in [
        ("s0", "source_refs", [{"source_id": "MADE_UP", "published_at": DAY}]),
        ("s1", "source_refs", [{"source_id": "S1", "published_at": DAY}]),
        ("s0", "sources", [{"url": "https://fake.invalid"}]),
    ]:
        bad = deepcopy(draft)
        bad["sections"][target][key] = value
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_budgets_include_selected_font_metrics_and_tighten_with_larger_type():
    settings = configuration([2] * 6)
    normal = budgets(settings)["s0"]
    settings.update(body_size=12, line_spacing=1.6)
    large = budgets(settings)["s0"]
    assert large["words"] < normal["words"]
    assert large["body_size_pt"] == 12 and large["line_height_pt"] == 19.2


def test_explicit_next_week_planner_does_not_fail_or_move_events_to_today():
    settings = configuration([2, 1, 1, 2, 2, 2, 2])
    settings.update(
        masthead_size=40,
        headline_size=14,
        body_size=9,
        line_spacing=1.2,
        margin_mm=9,
        gutter_mm=3,
        padding_mm=2,
        masthead_mm=40,
        sources_visible=False,
    )
    issue = demo_issue(settings, DAY)
    section = issue["sections"][3]
    section["headline"] = "Plans for 12–18 October"
    section["blocks"] = [
        {
            "type": "calendar",
            "days": [
                {"date": d, "events": ["Office; gym; project preparation"]}
                for d in week_dates("2026-10-12")
            ],
        },
        {
            "type": "paragraph",
            "text": "Daily habits: healthy food; German practice; AI course.",
        },
        {
            "type": "list",
            "items": [
                "Set new goals",
                "Close project tasks",
                "Finish ERP work",
                "Plan finance initiative",
            ],
        },
    ]
    validate_issue(issue, settings, DAY)
    text = " ".join(
        p.extract_text() for p in PdfReader(BytesIO(render_pdf(settings, issue))).pages
    )
    assert "Mon 12" in text and "Sun 18" in text
    assert "TODAY" not in text
    assert not needs_news(
        "Weekly planner: current date; research stocks; Monday office"
    )
    assert needs_news("An AI lesson with references to official documentation")


def test_generate_button_completes_researched_edition_and_history(monkeypatch):
    from streamlit.testing.v1 import AppTest

    settings = configuration_with_news()
    day = edition_day(settings)
    client, calls = client_fixture(settings, day)
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: client)
    test = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    test.session_state["settings"] = settings
    test.session_state["history"] = []
    test.run(timeout=20)
    test.text_input(key="api_key").set_value("local-test-key").run()
    next(
        b for b in test.button if b.label == "✦ Generate today’s newspaper"
    ).click().run(timeout=30)
    assert not test.exception and not test.error
    assert len(calls) == 6
    assert test.session_state["edition"]["day"] == day
    assert test.session_state["history"][-1]["day"] == day
    assert len(PdfReader(BytesIO(test.session_state["pdf"])).pages) == 2
    assert any("2026.10.12-press-4" in c.value for c in test.caption)
