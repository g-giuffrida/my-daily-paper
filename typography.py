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
    """Normalize invisible formatting; retain readable identities for complex emoji."""
    text = (
        unicodedata.normalize("NFC", str(value))
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    def emoji_text(chars, data):
        # Flags, skin tones and joined emoji require sequence-specific glyphs.
        # Their short labels retain the intended meaning across PDF renderers.
        if (
            "\u200d" in chars
            or "\u20e3" in chars
            or any(
                0x1F1E6 <= ord(c) <= 0x1F1FF
                or 0x1F3FB <= ord(c) <= 0x1F3FF
                or 0xE0020 <= ord(c) <= 0xE007F
                for c in chars
            )
        ):
            return "[" + data["en"].strip(":").replace("_", " ") + "]"
        return chars.replace("\ufe0e", "").replace("\ufe0f", "")

    if any(ord(c) >= 0x2000 for c in text):
        text = emoji.replace_emoji(text, replace=emoji_text)
    result = []
    for char in text:
        code, category = ord(char), unicodedata.category(char)
        if char == "\n" or char in "\u2028\u2029":
            result.append("\n")
        elif char.isspace():
            result.append(" ")
        elif (
            category in {"Cc", "Cf"}
            or 0xFE00 <= code <= 0xFE0F
            or 0xE0100 <= code <= 0xE01EF
        ):
            continue
        elif category in {"Cs", "Co", "Cn"}:
            result.append(f"[U+{code:04X}]")
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

    for char in text:
        if char == "\n":
            flush()
            runs.append("<br/>")
            current = None
            continue
        chosen = _character_font(char, preferred)
        if chosen is None:
            # Keep an explicit identity for genuinely unencoded/rare glyphs. This
            # path can never produce .notdef or an unsupported-character exception.
            char = f"[U+{ord(char):04X}]"
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
    if not any(0x0590 <= ord(c) <= 0x109F or 0x1780 <= ord(c) <= 0x17FF for c in text):
        return None
    for char in text:
        direction = unicodedata.bidirectional(char)
        if direction in {"R", "AL"}:
            return "RTL"
        if direction == "L":
            return "LTR"
    return "LTR"
