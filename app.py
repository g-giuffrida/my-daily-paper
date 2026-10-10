"""My Daily Paper — twelve spaces, one sheet, a fresh edition every day."""

from __future__ import annotations
import base64
from copy import deepcopy
import hmac
import json
import os
from pathlib import Path
from zoneinfo import available_timezones
import streamlit as st
import streamlit.components.v1 as components
from engine import FitError, demo_issue, edition_day, generate_issue, render_pdf
from settings import (
    DEFAULT,
    FONTS,
    IMAGE_MODELS,
    PRESETS,
    TEXT_MODELS,
    clean_history,
    clean_settings,
    new_section,
    settings_errors,
)

ROOT = Path(__file__).resolve().parent
storage = components.declare_component(
    "paper_storage", path=str(ROOT / "components" / "storage")
)
viewer = components.declare_component(
    "paper_viewer", path=str(ROOT / "components" / "viewer")
)
st.set_page_config(
    page_title="My Daily Paper",
    page_icon="🗞️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(
    """<style>
.stApp{background:#f7f7f3;color:#242a2b}.block-container{padding-top:2rem;max-width:1450px}
h1,h2,h3{font-family:Georgia,serif!important}.stButton button[kind="primary"]{background:#183c42;border-color:#183c42;border-radius:7px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:10px}
.eyebrow{font:700 11px system-ui;letter-spacing:.2em;color:#426466}.brand{font:38px Georgia,serif;margin:6px 0}.intro{color:#687471;margin-bottom:22px}
</style>""",
    unsafe_allow_html=True,
)


def secret(name):
    try:
        return str(st.secrets.get(name, os.environ.get(name, "")))
    except Exception:
        return os.environ.get(name, "")


server_key, password = secret("OPENAI_API_KEY"), secret("APP_PASSWORD")
if server_key and not password:
    st.error(
        "Configure APP_PASSWORD alongside the server-held OPENAI_API_KEY before running the app."
    )
    st.stop()
if password and not st.session_state.get("authorized"):
    st.title("My Daily Paper")
    attempt = st.text_input("Newspaper password", type="password")
    if st.button("Unlock", type="primary"):
        if hmac.compare_digest(attempt, password):
            st.session_state.authorized = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()

# Hydrate before initializing controls. Only whitelisted settings reach localStorage.
profile = None
if "settings" in st.session_state:
    profile = {
        "version": 2,
        "settings": clean_settings(st.session_state.settings),
        "history": clean_history(st.session_state.get("history", [])),
    }
restored = storage(profile=profile, key="browser_profile", default=None)
if "settings" not in st.session_state:
    if restored is None:
        st.caption("Restoring your newspaper settings…")
        st.stop()
    raw = restored.get("profile", {}) if isinstance(restored, dict) else {}
    st.session_state.settings = (
        clean_settings(raw.get("settings", {}))
        if isinstance(raw, dict)
        else deepcopy(DEFAULT)
    )
    st.session_state.history = (
        clean_history(raw.get("history", [])) if isinstance(raw, dict) else []
    )
    st.rerun()
if isinstance(restored, dict) and restored.get("warning"):
    st.warning(restored["warning"])


def change_setting(field, widget):
    st.session_state.settings[field] = st.session_state[widget]


def change_section(sid, field, widget):
    for s in st.session_state.settings["sections"]:
        if s["id"] == sid:
            s[field] = st.session_state[widget]


def move_section(sid, delta):
    sections = st.session_state.settings["sections"]
    i = next(i for i, s in enumerate(sections) if s["id"] == sid)
    j = i + delta
    if 0 <= j < len(sections):
        sections[i], sections[j] = sections[j], sections[i]


def delete_section(sid):
    st.session_state.settings["sections"] = [
        s for s in st.session_state.settings["sections"] if s["id"] != sid
    ]


def add_section():
    if len(st.session_state.settings["sections"]) < 12:
        st.session_state.settings["sections"].append(new_section())


def apply_preset():
    preset = PRESETS[st.session_state.design_preset]
    st.session_state.settings.update(preset)
    for field, value in preset.items():
        st.session_state["setting_" + field] = value


def use_classic_style():
    st.session_state.design_preset = "Classic newspaper"
    apply_preset()


def control(method, label, field, *args, **kwargs):
    key = "setting_" + field
    if key not in st.session_state:
        st.session_state[key] = st.session_state.settings[field]
    return method(
        label, *args, key=key, on_change=change_setting, args=(field, key), **kwargs
    )


st.markdown(
    '<div class="eyebrow">YOUR PERSONAL NEWSROOM</div><div class="brand">My Daily Paper</div><div class="intro">One sheet. Two sides. A new edition every day.</div>',
    unsafe_allow_html=True,
)
left, right = st.columns([1, 1.12], gap="large")
with left:
    content, design, editorial = st.tabs(["Content", "Design", "Editorial"])
    with content:
        control(st.text_input, "Newspaper title", "name")
        control(st.text_input, "Subtitle / motto", "tagline")
        sections = st.session_state.settings["sections"]
        total = sum(s["spaces"] for s in sections)
        st.markdown(f"**{total} / 12 spaces assigned** · {len(sections)} sections")
        st.progress(min(total / 12, 1))
        if total != 12:
            st.caption(
                f"{12 - total} spaces remaining."
                if total < 12
                else f"Remove {total - 12} allocated spaces before generating."
            )
        for i, section in enumerate(sections):
            sid = section["id"]
            with st.container(border=True):
                for field, label, method in [
                    ("name", "Section name", st.text_input),
                    ("prompt", "What should appear here?", st.text_area),
                    ("spaces", "Spaces", st.selectbox),
                ]:
                    key = f"section_{sid}_{field}"
                    if key not in st.session_state:
                        st.session_state[key] = section[field]
                    extras = (
                        {
                            "height": 100,
                            "help": "Describe any topic: news, lessons, a weekly plan, charts, or an illustration.",
                        }
                        if field == "prompt"
                        else {}
                    )
                    if field == "spaces":
                        extras["options"] = list(range(1, 13))
                    method(
                        label,
                        key=key,
                        on_change=change_section,
                        args=(sid, field, key),
                        **extras,
                    )
                up, down, remove = st.columns([1, 1, 2])
                up.button(
                    "↑",
                    help="Move earlier",
                    key="up_" + sid,
                    on_click=move_section,
                    args=(sid, -1),
                    disabled=i == 0,
                    use_container_width=True,
                )
                down.button(
                    "↓",
                    help="Move later",
                    key="down_" + sid,
                    on_click=move_section,
                    args=(sid, 1),
                    disabled=i == len(sections) - 1,
                    use_container_width=True,
                )
                remove.button(
                    "Remove",
                    key="remove_" + sid,
                    on_click=delete_section,
                    args=(sid,),
                    use_container_width=True,
                )
        st.button(
            "＋ Add section",
            on_click=add_section,
            disabled=len(sections) >= 12,
            use_container_width=True,
        )
        st.caption(
            "Placement follows section order: left to right, top to bottom, front then back. Settings are remembered in this browser automatically."
        )
    with design:
        st.selectbox(
            "Design preset", list(PRESETS), key="design_preset", on_change=apply_preset
        )
        st.button("Use classic broadsheet style", on_click=use_classic_style,
                  help="Blackletter masthead, serif headlines, justified columns and fine black rules. Keeps your content and prompts.")
        control(
            st.selectbox, "Masthead font", "masthead_font", ["UnifrakturCook"] + FONTS
        )
        control(st.selectbox, "Headline font", "headline_font", FONTS)
        control(st.selectbox, "Body font", "body_font", FONTS)
        for field, label, low, high in [
            ("masthead_size", "Masthead size (pt)", 24, 64),
            ("headline_size", "Headline size (pt)", 11, 24),
            ("body_size", "Body size (pt)", 8, 12),
        ]:
            control(st.slider, label, field, low, high)
        control(st.slider, "Line spacing", "line_spacing", 1.05, 1.6, step=0.05)
        for field, label in [
            ("ink", "Text color"),
            ("accent", "Accent color"),
            ("paper", "Paper color"),
            ("rule_color", "Divider color"),
        ]:
            control(st.color_picker, label, field)
        for field, label, low, high in [
            ("margin_mm", "Page margins (mm)", 8, 20),
            ("gutter_mm", "Space between sections (mm)", 2, 10),
            ("padding_mm", "Section padding (mm)", 1, 5),
            ("masthead_mm", "Front masthead height (mm)", 40, 50),
        ]:
            control(st.slider, label, field, low, high)
        control(
            st.selectbox,
            "Divider style",
            "rule_style",
            ["Single", "Double", "Dashed", "None"],
        )
        control(st.slider, "Divider weight (pt)", "rule_width", 0.25, 1.5, step=0.25)
        control(st.toggle, "Show source citations in the paper", "sources_visible")
        st.caption(
            "Two columns × three rows on each side. Only your chosen section dividers are printed."
        )
    with editorial:
        control(st.text_input, "Home region", "region")
        control(st.text_input, "Newspaper language", "language")
        control(st.text_input, "Editorial voice", "tone")
        control(
            st.selectbox, "Edition timezone", "timezone", sorted(available_timezones())
        )
        control(st.text_area, "Preferred sources", "sources", height=90)
        control(st.text_area, "Global editorial prompt", "instructions", height=180)
        control(st.selectbox, "OpenAI text model", "model", TEXT_MODELS)
        control(st.selectbox, "OpenAI image model", "image_model", IMAGE_MODELS)
        st.caption(
            "Illustrations are generated only when requested in a section prompt. Model access depends on your OpenAI account."
        )
    st.divider()
    if server_key:
        api_key = server_key
        st.caption("OpenAI connected through server secrets.")
    else:
        api_key = st.text_input(
            "OpenAI API key · this session only", type="password", key="api_key"
        )
    settings = clean_settings(st.session_state.settings)
    errors = settings_errors(settings)
    for error in errors:
        st.warning(error)
    generate = st.button(
        "✦ Generate today’s newspaper",
        type="primary",
        disabled=bool(errors),
        use_container_width=True,
    )
    sample = st.button(
        "Make sample newspaper · no API cost",
        disabled=bool(errors),
        use_container_width=True,
    )
    st.caption(
        "Generate whenever you want a fresh edition. Printing uses your normal system dialog."
    )

if generate or sample:
    if generate and not api_key:
        st.error("Enter an OpenAI API key to generate a researched edition.")
    else:
        day = edition_day(settings)
        with st.spinner(
            "Researching and fitting today’s edition…"
            if generate
            else "Typesetting the sample…"
        ):
            try:
                issue = (
                    generate_issue(settings, api_key, day, st.session_state.history)
                    if generate
                    else demo_issue(settings, day)
                )
                pdf = render_pdf(settings, issue)
                st.session_state.edition = issue
                st.session_state.generated_structure = [
                    (s["id"], s["name"], s["prompt"]) for s in settings["sections"]
                ]
                st.session_state.pdf = pdf
                st.session_state.render_signature = json.dumps(settings, sort_keys=True)
                if generate:
                    st.session_state.history = (
                        st.session_state.history
                        + [
                            {
                                "day": day,
                                "sections": {
                                    s["id"]: s["summary"][:400]
                                    for s in issue["sections"]
                                },
                            }
                        ]
                    )[-30:]
                st.session_state.pop("generation_error", None)
                st.rerun()
            except Exception as exc:
                st.session_state.generation_error = str(exc)

with right:
    st.markdown("**YOUR NEWSPAPER · EXACT PRINT PREVIEW**")
    if st.session_state.get("generation_error"):
        st.error(
            "Could not produce a print-ready edition: "
            + st.session_state.generation_error
        )
    issue = st.session_state.get("edition")
    if issue is None and not errors:
        issue = demo_issue(settings)
    if issue is None:
        st.info("Assign twelve spaces to preview both sides of your newspaper.")
    else:
        structure = [(s["id"], s["name"], s["prompt"]) for s in settings["sections"]]
        if not issue.get("sample") and structure != st.session_state.get(
            "generated_structure"
        ):
            st.warning(
                "Your content prompts or section order changed. Generate a new edition to apply them."
            )
        if not issue.get("sample") and issue["day"] != edition_day(settings):
            st.warning(
                f"This is the {issue['day']} edition. Generate again for today’s newspaper."
            )
        try:
            if errors:
                raise ValueError(
                    "Complete the twelve-space allocation to update the preview."
                )
            if issue.get("sample"):
                issue = demo_issue(settings)
            signature = json.dumps(settings, sort_keys=True)
            if not issue.get("sample") and signature == st.session_state.get(
                "render_signature"
            ):
                pdf = st.session_state.pdf
            else:
                pdf = render_pdf(settings, issue)
                if not issue.get("sample"):
                    st.session_state.pdf = pdf
                    st.session_state.render_signature = signature
            viewer(
                pdf=base64.b64encode(pdf).decode(),
                day=issue["day"],
                is_today=issue["day"] == edition_day(settings),
                sample=issue.get("sample", False),
                key="exact_pdf",
                default=None,
            )
            st.download_button(
                "↓ Download sample PDF"
                if issue.get("sample")
                else "↓ Download two-page PDF",
                pdf,
                file_name=f"my-daily-paper-{issue['day']}"
                + ("-sample" if issue.get("sample") else "")
                + ".pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            with st.expander("Sources in this edition"):
                sources = [src for s in issue["sections"] for src in s["sources"]]
                if not sources:
                    st.caption(
                        "No external sources in this illustrative or educational content."
                    )
                for src in sources:
                    st.link_button(
                        src["publisher"]
                        + (" · " + src["published_at"] if src["published_at"] else ""),
                        src["url"],
                    )
        except (FitError, ValueError) as exc:
            st.error("Preview is not print-ready: " + str(exc))
            st.caption(
                "Adjust the section spaces or design, or regenerate for shorter content. No articles have been silently removed."
            )
