"""Versioned, browser-local newspaper configuration; no credentials."""

from __future__ import annotations

from copy import deepcopy
import re
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FONTS = [
    "Libre Baskerville",
    "Playfair Display",
    "Source Serif 4",
    "Lora",
    "Source Sans 3",
    "IBM Plex Mono",
]
TEXT_MODELS = [
    "gpt-5-mini",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-6-luna",
    "gpt-6.1-sol",
    "gpt-6-astra",
]
IMAGE_MODELS = ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst"]

DEFAULT = {
    "version": 2,
    "name": "The Morning Edition",
    "tagline": "A little more informed, every day.",
    "region": "Switzerland",
    "timezone": "Europe/Zurich",
    "language": "English",
    "tone": "Concise, analytical, no hype",
    "sources": "Reuters, AP, SRF, primary research and company investor relations",
    "instructions": "Explain what matters. Be precise, thoughtful, and concise.",
    "model": "gpt-5-mini",
    "image_model": "gpt-image-2.5-flare",
    "masthead_font": "UnifrakturCook",
    "headline_font": "Playfair Display",
    "body_font": "Source Serif 4",
    "masthead_size": 46,
    "headline_size": 17,
    "body_size": 9,
    "line_spacing": 1.15,
    "ink": "#171717",
    "accent": "#171717",
    "paper": "#FFFFFF",
    "rule_color": "#353535",
    "margin_mm": 12,
    "gutter_mm": 5,
    "padding_mm": 2,
    "masthead_mm": 45,
    "rule_style": "Single",
    "rule_width": 0.5,
    "sources_visible": True,
    "sections": [
        {
            "id": "world",
            "name": "World",
            "prompt": "Explain the most important verified world news today.",
            "spaces": 2,
        },
        {
            "id": "local",
            "name": "Closer to home",
            "prompt": "Give me today’s important news in my home region.",
            "spaces": 2,
        },
        {
            "id": "business",
            "name": "Business & markets",
            "prompt": "Explain today’s most important business developments and why they matter.",
            "spaces": 2,
        },
        {
            "id": "science",
            "name": "Ideas & discovery",
            "prompt": "Teach me something interesting about science. Include a useful diagram or chart if supported by real data.",
            "spaces": 2,
        },
        {
            "id": "lesson",
            "name": "A little German",
            "prompt": "Create a short German B1 lesson, with an example and an exercise.",
            "spaces": 2,
        },
        {
            "id": "week",
            "name": "My week",
            "prompt": "Make a calendar for this week. Monday: office and gym. Wednesday: dinner with a friend. Saturday: hike. Leave other days empty.",
            "spaces": 2,
        },
    ],
}

PRESETS = {
    "Classic newspaper": {
        k: DEFAULT[k]
        for k in [
            "masthead_font",
            "headline_font",
            "body_font",
            "ink",
            "accent",
            "paper",
            "rule_color",
            "rule_style",
            "masthead_size",
            "headline_size",
            "body_size",
            "line_spacing",
            "rule_width",
        ]
    },
    "Literary review": {
        "masthead_font": "Libre Baskerville",
        "headline_font": "Lora",
        "body_font": "Libre Baskerville",
        "ink": "#28251F",
        "accent": "#775638",
        "paper": "#FFFCF5",
        "rule_color": "#AAA08D",
        "rule_style": "Double",
    },
    "Modern journal": {
        "masthead_font": "Source Sans 3",
        "headline_font": "Source Sans 3",
        "body_font": "Source Sans 3",
        "ink": "#172A38",
        "accent": "#264B70",
        "paper": "#FFFFFF",
        "rule_color": "#A4B4BF",
        "rule_style": "Single",
    },
    "Typewriter": {
        "masthead_font": "IBM Plex Mono",
        "headline_font": "IBM Plex Mono",
        "body_font": "IBM Plex Mono",
        "ink": "#202020",
        "accent": "#202020",
        "paper": "#FFFFFF",
        "rule_color": "#888888",
        "rule_style": "Dashed",
    },
}


def new_section():
    return {"id": uuid4().hex, "name": "", "prompt": "", "spaces": 1}


def clean_settings(raw):
    """Accept known, bounded configuration fields only."""
    out = deepcopy(DEFAULT)
    if not isinstance(raw, dict):
        return out
    for k, default in DEFAULT.items():
        if k != "sections" and isinstance(raw.get(k), type(default)):
            out[k] = raw[k]
    for key, options in [
        ("masthead_font", ["UnifrakturCook"] + FONTS),
        ("headline_font", FONTS),
        ("body_font", FONTS),
        ("model", TEXT_MODELS),
        ("image_model", IMAGE_MODELS),
        ("rule_style", ["Single", "Double", "Dashed", "None"]),
    ]:
        if out[key] not in options:
            out[key] = DEFAULT[key]
    for key, low, high in [
        ("masthead_size", 24, 64),
        ("headline_size", 11, 24),
        ("body_size", 8, 12),
        ("line_spacing", 1.05, 1.6),
        ("margin_mm", 8, 20),
        ("gutter_mm", 2, 10),
        ("padding_mm", 1, 5),
        ("masthead_mm", 40, 50),
        ("rule_width", 0.25, 1.5),
    ]:
        # bool is not a valid dimension; NaN is rejected as well.
        v = raw.get(key, DEFAULT[key])
        out[key] = (
            max(low, min(high, v))
            if type(v) in (int, float) and low <= v <= high
            else DEFAULT[key]
        )
        if type(DEFAULT[key]) is int:
            out[key] = int(out[key])
    for key in ["ink", "accent", "paper", "rule_color"]:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", out[key]):
            out[key] = DEFAULT[key]
    try:
        ZoneInfo(out["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        out["timezone"] = DEFAULT["timezone"]
    for k in [
        "name",
        "tagline",
        "region",
        "language",
        "tone",
        "sources",
        "instructions",
    ]:
        out[k] = out[k][:12000]
    if isinstance(raw.get("sections"), list):
        sections, ids = [], set()
        for item in raw["sections"][:12]:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id", ""))[:80]
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", sid) or sid in ids:
                sid = uuid4().hex
            ids.add(sid)
            spaces = item.get("spaces", 1)
            sections.append(
                {
                    "id": sid,
                    "name": str(item.get("name", ""))[:300],
                    "prompt": str(item.get("prompt", ""))[:12000],
                    "spaces": spaces
                    if type(spaces) is int and 1 <= spaces <= 12
                    else 1,
                }
            )
        out["sections"] = sections
    out["version"] = 2
    return out


def settings_errors(settings):
    errors = []
    if not settings["name"].strip():
        errors.append("Give your newspaper a title.")
    if not 1 <= len(settings["sections"]) <= 12:
        errors.append("Add between one and twelve sections.")
    total = sum(s["spaces"] for s in settings["sections"])
    if total != 12:
        errors.append(f"Assign exactly 12 spaces (currently {total}).")
    for i, s in enumerate(settings["sections"], 1):
        if not s["name"].strip() or not s["prompt"].strip():
            errors.append(f"Section {i} needs a name and a prompt.")
    return errors


def clean_history(raw):
    if not isinstance(raw, list):
        return []
    return [
        {
            "day": str(x.get("day", ""))[:10],
            "sections": {
                str(k)[:80]: str(v)[:400] for k, v in x.get("sections", {}).items()
            },
        }
        for x in raw[-30:]
        if isinstance(x, dict) and isinstance(x.get("sections"), dict)
    ]
