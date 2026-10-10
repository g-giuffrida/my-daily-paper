"""Generate a sample and render both sides for visual inspection."""

from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz
from engine import demo_issue, render_pdf
from settings import DEFAULT

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--day", default="2026-10-10")
args = parser.parse_args()
args.directory.mkdir(parents=True, exist_ok=True)
pdf = render_pdf(DEFAULT, demo_issue(DEFAULT, args.day))
(args.directory / "newspaper-sample.pdf").write_bytes(pdf)
doc = fitz.open(stream=pdf, filetype="pdf")
for i, page in enumerate(doc):
    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(
        str(args.directory / f"newspaper-{i + 1}.png")
    )
print("Verified and rendered", len(doc), "A4 pages")
