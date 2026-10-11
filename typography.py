"""Printable Unicode with embedded per-run font fallback and a total last resort."""

from functools import lru_cache
from pathlib import Path
from threading import RLock
import unicodedata
from xml.sax.saxutils import escape

import emoji
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
FALLBACKS = (
    "NotoSansArabic-Regular",
    "NotoSansDevanagari-Regular",
    "NotoEmoji-Regular",
    "Unifont-Regular",
    "UnifontUpper-Regular",
)
_font_lock = RLock()


def _face(name):
    with _font_lock:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / (name + ".ttf"))))
        return pdfmetrics.getFont(name)


def printable_text(value):
    """Normalize text without inserting descriptive labels into the newspaper."""
    text = (
        unicodedata.normalize("NFC", str(value))
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    result = []
    for char in text:
        code, category = ord(char), unicodedata.category(char)
        if char == "\n" or char in "\u2028\u2029":
            result.append("\n")
        elif char.isspace():
            result.append(" ")
        elif category == "Cc" or (
            category == "Cf"
            and char not in "\u200c\u200d"
            and not 0xE0020 <= code <= 0xE007F
        ):
            continue
        elif category in {"Cs", "Co", "Cn"}:
            result.append("\ufffd")
        else:
            result.append(char)
    return "".join(result)


@lru_cache(maxsize=32768)
def _character_font(char, preferred):
    weight = "Bold" if preferred.endswith("-Bold") else "Regular"
    candidates = (
        preferred,
        "SourceSerif4-" + weight,
        "SourceSans3-" + weight,
        *FALLBACKS,
    )
    for name in dict.fromkeys(candidates):
        if _face(name).face.charToGlyph.get(ord(char), 0):
            return name
    return None


def font_markup(value, preferred):
    """Escape untrusted text and wrap only unsupported runs in a known fallback font."""
    text = printable_text(value)
    runs, current, chunk = [], None, []

    def flush():
        if chunk:
            content = escape("".join(chunk))
            runs.append(
                content
                if current == preferred
                else f'<font name="{current}">{content}</font>'
            )
            chunk.clear()

    # Keep joined emoji in a single font run for HarfBuzz's GSUB shaping.
    sequences = (
        {item["match_start"]: item for item in emoji.emoji_list(text)}
        if any(ord(c) >= 0x2000 for c in text)
        else {}
    )
    position = 0
    while position < len(text):
        item = sequences.get(position)
        if item:
            char = item["emoji"]
            position = item["match_end"]
            chosen = "NotoEmoji-Regular"
            _face(chosen)
        else:
            char = text[position]
            position += 1
            chosen = _character_font(char, preferred)
        if char == "\n":
            flush()
            runs.append("<br/>")
            current = None
            continue
        if chosen is None:
            char = "\ufffd"
            chosen = "SourceSans3-Regular"
        if chosen != current:
            flush()
            current = chosen
        chunk.append(char)
    flush()
    return "".join(runs)


def text_direction(value):
    """Enable glyph shaping only where needed, preserving existing Latin layouts."""
    text = printable_text(value)
    if any(ord(c) >= 0x2000 for c in text) and emoji.emoji_list(text):
        return "LTR"
    if not any(0x0590 <= ord(c) <= 0x109F or 0x1780 <= ord(c) <= 0x17FF for c in text):
        return None
    for char in text:
        direction = unicodedata.bidirectional(char)
        if direction in {"R", "AL"}:
            return "RTL"
        if direction == "L":
            return "LTR"
    return "LTR"
