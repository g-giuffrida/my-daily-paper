"""The single source of truth for the twelve-space A4 layout."""

from dataclasses import dataclass
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


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


def budgets(settings):
    """Measured physical area, including heading and inner padding reservations."""
    out = {}
    pad = settings["padding_mm"] * mm
    leading = settings["body_size"] * settings["line_spacing"]
    for r in allocate(settings):
        # Conservative average character width and words per line; rendering is authoritative.
        lines = max(
            1,
            int((r.height - 2 * pad - 2.5 * settings["headline_size"] - 20) / leading),
        )
        word_width = 3.6 if settings["body_font"] == "IBM Plex Mono" else 2.7
        words = int(lines * (r.width - 2 * pad) / (settings["body_size"] * word_width))
        entry = out.setdefault(r.section_id, {"words": 0, "regions": []})
        entry["words"] += max(15, int(words * 0.80))
        entry["regions"].append(
            {
                "page": r.page + 1,
                "width_mm": round((r.width - 2 * pad) / mm, 1),
                "height_mm": round((r.height - 2 * pad) / mm, 1),
            }
        )
    return out
