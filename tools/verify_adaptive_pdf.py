"""Render dense and one-cell weekly planner fixtures for visual fit review (no API calls)."""

from copy import deepcopy
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz
from engine import demo_issue, render_pdf, week_dates
from settings import DEFAULT

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
args.directory.mkdir(parents=True, exist_ok=True)

for name in ["dense-back", "small-front"]:
    settings = deepcopy(DEFAULT)
    if name == "small-front":
        settings["sections"] = [
            {
                "id": "week",
                "name": "My week",
                "prompt": "A weekly planner",
                "spaces": 1,
            },
            {"id": "world", "name": "World", "prompt": "World news", "spaces": 5},
            {
                "id": "ideas",
                "name": "Ideas",
                "prompt": "Interesting ideas",
                "spaces": 6,
            },
        ]
    issue = demo_issue(settings, "2026-10-10")
    section = next(s for s in issue["sections"] if s["id"] == "week")
    section["headline"] = "The week ahead"
    section["blocks"] = [
        {
            "type": "calendar",
            "days": [
                {
                    "date": day,
                    "events": [
                        f"{hour}:00 {event}"
                        for hour, event in (
                            [
                                (9, "Office planning with the team"),
                                (13, "Lunch with friends"),
                                (18, "Gym and swimming"),
                                (20, "German practice at home"),
                            ]
                            if name == "dense-back"
                            else [(9, "Office planning then gym with friends")]
                        )
                    ],
                }
                for day in week_dates(issue["day"])
            ],
        }
    ]
    data = render_pdf(settings, issue)
    (args.directory / f"{name}.pdf").write_bytes(data)
    doc = fitz.open(stream=data, filetype="pdf")
    assert len(doc) == 2
    for n, page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(
            str(args.directory / f"{name}-{n + 1}.png")
        )
    print(f"Rendered {name}: two A4 pages")
