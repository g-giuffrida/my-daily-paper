from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
import json
from types import SimpleNamespace

import fitz
import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from engine import (
    FitError,
    CitationError,
    collect_source_urls,
    compose_regions,
    demo_issue,
    edition_day,
    generate_issue,
    needs_news,
    register_fonts,
    render_pdf,
    validate_issue,
    week_dates,
)
from layout import allocate, budgets
from settings import DEFAULT, FONTS, clean_history, clean_settings, settings_errors

DAY = "2026-10-10"


def configuration(parts):
    s = deepcopy(DEFAULT)
    s["sections"] = [
        {
            "id": f"s{i}",
            "name": f"Section {i + 1}",
            "prompt": "Teach me something interesting.",
            "spaces": n,
        }
        for i, n in enumerate(parts)
    ]
    return s


def compositions(n):
    if n == 0:
        yield []
    for first in range(1, n + 1):
        for rest in compositions(n - first):
            yield [first] + rest


def test_all_2048_ordered_allocations():
    count = 0
    for parts in compositions(12):
        s = configuration(parts)
        regions = allocate(s)
        cells = [cell for r in regions for cell in r.cells]
        assert sorted(cells) == list(range(12))
        assert len(set(cells)) == 12
        for r in regions:
            assert r.width > 0 and r.height > 0
            assert r.x >= s["margin_mm"] * mm - 0.01
            assert r.y >= s["margin_mm"] * mm - 0.01
            assert r.x + r.width <= A4[0] - s["margin_mm"] * mm + 0.01
            for other in regions:
                if r != other and r.page == other.page:
                    assert min(r.x + r.width, other.x + other.width) <= max(
                        r.x, other.x
                    ) or min(r.y + r.height, other.y + other.height) <= max(
                        r.y, other.y
                    )
        for section, n in zip(s["sections"], parts):
            own = [r for r in regions if r.section_id == section["id"]]
            assert sum(len(r.cells) for r in own) == n
            assert not own[0].continuation and all(r.continuation for r in own[1:])
        count += 1
    assert count == 2048


@pytest.mark.parametrize("parts", [[1] * 12, [2] * 6, [3, 5, 4], [7, 5], [12]])
def test_two_pages_and_measured_bounds(parts):
    s = configuration(parts)
    issue = demo_issue(s, DAY)
    register_fonts()
    _, placements = compose_regions(s, issue)
    for r, f, x, y, _ in placements:
        assert x >= r.x - 0.01 and y >= r.y - 0.01
        assert y + f.height <= r.y + r.height + 0.01
    pdf = render_pdf(s, issue)
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) == 2
    assert all(abs(float(p.mediabox.width) - A4[0]) < 0.01 for p in reader.pages)
    assert "SAMPLE" in reader.metadata.title


def test_front_budget_smaller_and_no_back_masthead():
    s = configuration([1] * 12)
    b = budgets(s)
    assert b["s0"]["words"] < b["s6"]["words"]
    reader = PdfReader(BytesIO(render_pdf(s, demo_issue(s, DAY))))
    assert s["name"] in reader.pages[0].extract_text()
    assert s["name"] not in reader.pages[1].extract_text()


@pytest.mark.parametrize("face", FONTS)
def test_all_embedded_fonts_and_unicode(face):
    s = configuration([2] * 6)
    s["body_font"] = face
    issue = demo_issue(s, DAY)
    issue["sections"][0]["blocks"] = [
        {
            "type": "paragraph",
            "text": "Zürich, Überzeugung, perché, déjà vu. “Precision” — € 42.",
        }
    ]
    pdf = render_pdf(s, issue)
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert "Zürich" in doc[0].get_text()
    assert any(
        face.replace(" ", "") in f[3].replace("-", "") for f in doc[0].get_fonts()
    )


def test_overflow_fails_and_no_content_is_dropped():
    s = configuration([1] * 12)
    issue = demo_issue(s, DAY)
    issue["sections"][0]["blocks"] = [
        {"type": "paragraph", "text": "Important verified reporting. " * 900}
    ]
    with pytest.raises(FitError, match="Section 1"):
        render_pdf(s, issue)


def test_continuation_preserves_order_without_duplicates():
    s = configuration([5, 7])
    issue = demo_issue(s, DAY)
    issue["sample"] = False
    # Enough prose to cross the differently sized regions.
    text = " ".join(f"word{i:03d}" for i in range(250))
    issue["sections"][0]["blocks"] = [{"type": "paragraph", "text": text}]
    pdf = render_pdf(s, issue)
    extracted = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    positions = [extracted.index(f"word{i:03d}") for i in range(250)]
    assert positions == sorted(positions)
    assert all(extracted.count(f"word{i:03d}") == 1 for i in range(250))


def test_midnight_timezone_and_week_boundary():
    s = deepcopy(DEFAULT)
    now = datetime(2026, 10, 10, 22, 30, tzinfo=timezone.utc)
    assert edition_day(s, now) == "2026-10-11"
    s["timezone"] = "America/New_York"
    assert edition_day(s, now) == "2026-10-10"
    assert week_dates("2026-10-11")[0] == "2026-10-05"
    assert week_dates("2026-10-12")[0] == "2026-10-12"


def test_calendar_and_chart_render_and_validate():
    s = configuration([2] * 6)
    issue = demo_issue(s, DAY)
    issue["sections"][4]["blocks"] = [
        {
            "type": "calendar",
            "days": [
                {"date": d, "events": ["Office"] if i == 0 else []}
                for i, d in enumerate(week_dates(DAY))
            ],
        }
    ]
    issue["sections"][5]["blocks"] = [
        {
            "type": "chart",
            "title": "User supplied comparison",
            "kind": "bar",
            "labels": ["A", "B", "C"],
            "values": [-2, 0, 4],
            "unit": "units",
        }
    ]
    validate_issue(issue, s, DAY)
    text = "\n".join(
        p.extract_text() for p in PdfReader(BytesIO(render_pdf(s, issue))).pages
    )
    assert "TODAY" in text and "User supplied comparison" in text
    issue["sections"][4]["blocks"][0]["days"][0]["date"] = "2020-01-01"
    with pytest.raises(ValueError, match="Monday"):
        validate_issue(issue, s, DAY)


def test_missing_ids_unrequested_images_and_unverified_sources_rejected():
    s = configuration([2] * 6)
    issue = demo_issue(s, DAY)
    issue["sections"][0]["blocks"] = [
        {"type": "illustration", "prompt": "A tree", "caption": "A tree"}
    ]
    with pytest.raises(ValueError, match="without an illustration prompt"):
        validate_issue(issue, s, DAY)
    issue = demo_issue(s, DAY)
    issue["sections"][0]["sources"] = [
        {
            "publisher": "Source",
            "url": "https://example.org/story",
            "published_at": "2026-10-09",
        }
    ]
    with pytest.raises(ValueError, match="research results"):
        validate_issue(issue, s, DAY, set())
    issue["sections"].pop()
    with pytest.raises(ValueError, match="missing"):
        validate_issue(issue, s, DAY)


def test_whitelist_storage_and_history():
    raw = {
        **deepcopy(DEFAULT),
        "api_key": "secret",
        "password": "private",
        "timezone": "invalid",
        "body_size": 100,
        "paper": "javascript:alert(1)",
    }
    clean = clean_settings(raw)
    assert "api_key" not in clean and "password" not in clean
    assert (
        clean["timezone"] == DEFAULT["timezone"]
        and clean["body_size"] == 9
        and clean["paper"] == "#FFFFFF"
    )
    assert (
        len(
            clean_history(
                [{"day": DAY, "sections": {"lesson": "x" * 1000}, "api_key": "secret"}]
                * 40
            )
        )
        == 30
    )
    assert all(
        "api_key" not in h and len(h["sections"]["lesson"]) == 400
        for h in clean_history([{"day": DAY, "sections": {"lesson": "x" * 1000}}])
    )
    assert not settings_errors(configuration([11]))
    assert settings_errors(configuration([12, 1]))


class FakeResponse:
    def __init__(self, issue, urls=(), draft=True):
        if draft:
            sections = {}
            for section in issue["sections"]:
                entry = {k: v for k, v in section.items() if k not in ("id", "sources")}
                entry["source_refs"] = [
                    {
                        "source_id": f"S{list(urls).index(src['url']) + 1}",
                        "published_at": src["published_at"],
                    }
                    for src in section["sources"]
                ]
                sections[section["id"]] = entry
        else:
            sections = {
                s["id"]: {k: v for k, v in s.items() if k not in ("id", "sources")}
                for s in issue["sections"]
            }
        self.output_text = json.dumps({"sections": sections})
        self.urls = urls

    def scoped(self, request):
        if "tools" in request:
            return self
        result = deepcopy(self)
        ids = request["text"]["format"]["schema"]["properties"]["sections"][
            "properties"
        ]
        data = json.loads(result.output_text)
        data["sections"] = {k: v for k, v in data["sections"].items() if k in ids}
        result.output_text = json.dumps(data)
        return result

    def model_dump(self):
        return {
            "output": [
                {
                    "type": "web_search_call",
                    "action": {"sources": [{"url": u} for u in self.urls]},
                }
            ]
        }


def test_generation_captures_day_history_and_bounded_repair():
    s = configuration([1] * 12)
    issue = demo_issue(s, DAY)
    issue["sections"][0]["blocks"][0]["text"] = "Overlong material. " * 900
    good = demo_issue(s, DAY)
    calls = []
    replies = iter([FakeResponse(issue)] * 12 + [FakeResponse(good, draft=False)])

    def create(**kwargs):
        calls.append(kwargs)
        return next(replies).scoped(kwargs)

    result = generate_issue(
        s,
        "unused",
        DAY,
        [{"day": "2026-10-09", "sections": {"s0": "Old lesson"}}],
        client=SimpleNamespace(responses=SimpleNamespace(create=create)),
    )
    assert result["day"] == DAY and not result["sample"]
    assert len(calls) == 13
    assert "Old lesson" in calls[0]["input"][0]["content"]
    assert DAY in calls[0]["input"][0]["content"]
    replies = iter(
        [FakeResponse(issue)] * 12
        + [
            FakeResponse(issue, draft=False),
            FakeResponse(issue, draft=False),
        ]
    )
    with pytest.raises(FitError):
        generate_issue(
            s,
            "unused",
            DAY,
            client=SimpleNamespace(
                responses=SimpleNamespace(create=lambda **kw: next(replies).scoped(kw))
            ),
        )


def test_api_failure_propagates_without_fabricated_newspaper():
    s = configuration([2] * 6)
    s["sections"][0]["prompt"] = "Latest news today"

    def fail(**kwargs):
        raise RuntimeError("Model unavailable")

    with pytest.raises(RuntimeError, match="Model unavailable"):
        generate_issue(
            s,
            "unused",
            DAY,
            client=SimpleNamespace(responses=SimpleNamespace(create=fail)),
        )


@pytest.mark.parametrize("extreme", [False, True])
def test_design_extremes_fail_explicitly_or_fit(extreme):
    s = configuration([2] * 6)
    if extreme:
        s.update(
            margin_mm=20,
            gutter_mm=10,
            padding_mm=5,
            masthead_mm=50,
            body_size=12,
            headline_size=24,
            line_spacing=1.6,
        )
    else:
        s.update(
            margin_mm=8,
            gutter_mm=2,
            padding_mm=1,
            masthead_mm=40,
            body_size=8,
            headline_size=11,
            line_spacing=1.05,
        )
    try:
        pdf = render_pdf(s, demo_issue(s, DAY))
        assert len(PdfReader(BytesIO(pdf)).pages) == 2
    except FitError as e:
        assert e.sections


def test_long_masthead_never_truncated():
    s = configuration([2] * 6)
    s["name"] = "The Extraordinary Morning Newspaper for Curious Readers"
    text = PdfReader(BytesIO(render_pdf(s, demo_issue(s, DAY)))).pages[0].extract_text()
    assert s["name"] in " ".join(text.split())


def test_citation_tracking_variants_use_original_verified_link():
    s = configuration([2] * 6)
    issue = demo_issue(s, DAY)
    verified = "https://example.org/story?id=42&utm_source=search"
    issue["sections"][0]["sources"] = [
        {
            "publisher": "Source",
            "url": "https://example.org/story?id=42#main",
            "published_at": DAY,
        }
    ]
    validate_issue(issue, s, DAY, {verified})
    assert issue["sections"][0]["sources"][0]["url"] == verified
    issue["sections"][0]["sources"][0]["url"] = "https://example.org/story?id=43"
    with pytest.raises(CitationError):
        validate_issue(issue, s, DAY, {verified})


def test_research_and_editing_do_not_ask_model_to_copy_urls():
    s = configuration([2] * 6)
    s["sections"][0]["prompt"] = "Latest news today"
    good = demo_issue(s, DAY)
    good["sections"][0]["sources"] = [
        {
            "publisher": "example.org",
            "url": "https://example.org/new-research",
            "published_at": DAY,
        }
    ]
    calls = []
    research = FakeResponse(demo_issue(s, DAY), ["https://example.org/new-research"])
    research.output_text = "Verified reporting with publication date " + DAY
    replies = iter(
        [research] + [FakeResponse(good, ["https://example.org/new-research"])] * 6
    )

    def create(**kwargs):
        calls.append(kwargs)
        return next(replies).scoped(kwargs)

    result = generate_issue(
        s,
        "unused",
        DAY,
        client=SimpleNamespace(responses=SimpleNamespace(create=create)),
    )
    assert (
        result["sections"][0]["sources"][0]["url"] == "https://example.org/new-research"
    )
    assert len(calls) == 7 and calls[0]["tool_choice"] == "required"
    assert "tools" not in calls[1]
    fields = calls[1]["text"]["format"]["schema"]["properties"]["sections"][
        "properties"
    ]["s0"]["properties"]
    assert "sources" not in fields
    assert fields["source_refs"]["items"]["properties"]["source_id"]["enum"] == ["S1"]


def test_source_collection_includes_open_pages_and_annotations_not_written_json():
    response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {"type": "open_page", "url": "https://example.org/open"},
            },
            {
                "type": "message",
                "content": [
                    {
                        "text": '{"url":"https://example.org/fake"}',
                        "annotations": [
                            {"type": "url_citation", "url": "https://example.org/cited"}
                        ],
                    }
                ],
            },
        ]
    }
    assert collect_source_urls(response) == {
        "https://example.org/open",
        "https://example.org/cited",
    }


def test_today_lesson_does_not_require_news_research():
    assert not needs_news("Make a German B1 lesson for today.")
    assert needs_news("Tell me the latest news about ABB today.")


def test_illustration_generation_and_pdf_embedding():
    import base64
    from PIL import Image

    s = configuration([2] * 6)
    s["sections"][5]["prompt"] = "Create an illustration of a tree."
    issue = demo_issue(s, DAY)
    issue["sections"][5]["blocks"] = [
        {
            "type": "illustration",
            "prompt": "An ink drawing of a tree",
            "caption": "An ink tree",
        }
    ]
    data = BytesIO()
    Image.new("RGB", (64, 64), "#335544").save(data, format="PNG")
    image_calls = []

    def images(**kwargs):
        image_calls.append(kwargs)
        return SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(data.getvalue()).decode())]
        )

    result = generate_issue(
        s,
        "unused",
        DAY,
        client=SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **kw: FakeResponse(issue).scoped(kw)
            ),
            images=SimpleNamespace(generate=images),
        ),
    )
    assert image_calls[0]["model"] == s["image_model"]
    doc = fitz.open(stream=render_pdf(s, result), filetype="pdf")
    assert doc[1].get_images()
    assert "AI illustration" in doc[1].get_text()


def test_source_links_and_publication_date_in_pdf():
    s = configuration([2] * 6)
    issue = demo_issue(s, DAY)
    url = "https://example.org/verified-story"
    issue["sections"][0]["sources"] = [
        {"publisher": "Verified source", "url": url, "published_at": "2026-10-09"}
    ]
    validate_issue(issue, s, DAY, {url})
    doc = fitz.open(stream=render_pdf(s, issue), filetype="pdf")
    assert any(link.get("uri") == url for link in doc[0].get_links())
    assert "2026-10-09" in doc[0].get_text()
    issue["sections"][0]["sources"][0]["published_at"] = "2026-10-11"
    with pytest.raises(ValueError, match="future"):
        validate_issue(issue, s, DAY, {url})
