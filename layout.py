"""The single source of truth for the twelve-space A4 layout."""

from dataclasses import dataclass
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from typography import _face


@dataclass(frozen=True)
class Region:
    section_id: str
    page: int
    cells: tuple[int, ...]
    x: float
    y: float
    width: float
    height: float
    continuation: bool


def allocate(settings):
    """Fill cells in reading order, partitioning each run into maximal rectangles."""
    if sum(s["spaces"] for s in settings["sections"]) != 12:
        raise ValueError("Exactly twelve spaces must be assigned.")
    w, h = A4
    margin = settings["margin_mm"] * mm
    gap = settings["gutter_mm"] * mm
    cellw = (w - 2 * margin - gap) / 2
    result, cursor = [], 0
    for section in settings["sections"]:
        assigned = set(range(cursor, cursor + section["spaces"]))
        cursor += section["spaces"]
        first = True
        while assigned:
            start = min(assigned)
            page, local = divmod(start, 6)
            row, col = divmod(local, 2)
            choices = []
            for nr in range(1, 4 - row):
                for nc in range(1, 3 - col):
                    cells = tuple(
                        page * 6 + r * 2 + c
                        for r in range(row, row + nr)
                        for c in range(col, col + nc)
                    )
                    if set(cells) <= assigned:
                        choices.append((nr * nc, nc, nr, cells))
            _, nc, nr, cells = max(choices)
            top = h - margin - (settings["masthead_mm"] * mm if page == 0 else 0)
            cellh = (top - margin - 2 * gap) / 3
            height = nr * cellh + (nr - 1) * gap
            result.append(
                Region(
                    section["id"],
                    page,
                    cells,
                    margin + col * (cellw + gap),
                    top - row * (cellh + gap) - height,
                    nc * cellw + (nc - 1) * gap,
                    height,
                    not first,
                )
            )
            assigned.difference_update(cells)
            first = False
    return result


def region_headline_size(settings, region):
    if (
        region.section_id == settings["sections"][0]["id"]
        and not region.continuation
        and len(region.cells) >= 2
    ):
        return min(26, settings["headline_size"] + 5)
    return settings["headline_size"]


def budgets(settings):
    """Measured physical area, including heading and inner padding reservations."""
    out = {}
    pad = settings["padding_mm"] * mm
    leading = settings["body_size"] * settings["line_spacing"]
    family = settings["body_font"].replace(" ", "") + "-Regular"
    _face(family)
    sample = "A daily newspaper explains important developments with context facts and clear reporting "
    average_word_width = pdfmetrics.stringWidth(
        sample, family, settings["body_size"]
    ) / len(sample.split())
    for r in allocate(settings):
        # Conservative average character width and words per line; rendering is authoritative.
        lines = max(
            1,
            int(
                (r.height - 2 * pad - 1.6 * region_headline_size(settings, r) - 18)
                / leading
            ),
        )
        # A merged prose region still has two newspaper columns and a gutter.
        usable_width = r.width - 2 * pad
        if len({cell % 2 for cell in r.cells}) == 2:
            usable_width -= settings["gutter_mm"] * mm
        words = int(lines * usable_width / average_word_width)
        entry = out.setdefault(
            r.section_id,
            {
                "words": 0,
                "regions": [],
                "body_font": settings["body_font"],
                "body_size_pt": settings["body_size"],
                "line_height_pt": round(leading, 2),
                "headline_font": settings["headline_font"],
                "headline_size_pt": settings["headline_size"],
                "padding_mm": settings["padding_mm"],
            },
        )
        entry["words"] += max(15, int(words * 0.92))
        entry["regions"].append(
            {
                "page": r.page + 1,
                "width_mm": round((r.width - 2 * pad) / mm, 1),
                "height_mm": round((r.height - 2 * pad) / mm, 1),
            }
        )
    for entry in out.values():
        entry["target_words"] = round(entry["words"] * 0.95)
        entry["minimum_words"] = round(entry["words"] * 0.82)
    return out
