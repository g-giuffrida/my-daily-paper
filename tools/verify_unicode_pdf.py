"""Render a reproducible Unicode newspaper fixture without paid API calls."""

import argparse
from pathlib import Path
import sys

sys.path[:0] = [
    str(Path(__file__).resolve().parents[1]),
    str(Path(__file__).resolve().parents[1] / "tests"),
]
import fitz
from engine import render_pdf
from test_unicode import unicode_edition

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
args.directory.mkdir(parents=True, exist_ok=True)
settings, issue = unicode_edition()
data = render_pdf(settings, issue)
(args.directory / "newspaper-unicode-sample.pdf").write_bytes(data)
doc = fitz.open(stream=data, filetype="pdf")
assert len(doc) == 2
for i, page in enumerate(doc):
    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(
        str(args.directory / f"unicode-{i + 1}.png")
    )
print("Rendered both Unicode fixture pages")
