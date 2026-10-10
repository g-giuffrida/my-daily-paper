"""Reproducibly vendor OFL fonts and Apache-licensed PDF.js. Run during development."""

from pathlib import Path
import json
from urllib.request import Request, urlopen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]


def fetch(url):
    with urlopen(
        Request(url, headers={"User-Agent": "my-daily-paper-assets"}), timeout=60
    ) as response:
        return response.read()


def main():
    for family, directory in [
        ("UnifrakturCook", "unifrakturcook"),
        ("LibreBaskerville", "librebaskerville"),
        ("PlayfairDisplay", "playfairdisplay"),
        ("SourceSerif4", "sourceserif4"),
        ("Lora", "lora"),
        ("SourceSans3", "sourcesans3"),
        ("IBMPlexMono", "ibmplexmono"),
    ]:
        target = ROOT / "assets" / "fonts"
        target.mkdir(parents=True, exist_ok=True)
        entries = json.loads(
            fetch(f"https://api.github.com/repos/google/fonts/contents/ofl/{directory}")
        )
        files = [
            e
            for e in entries
            if e["name"].endswith(".ttf") and "Italic" not in e["name"]
        ]
        variable = next((f for f in files if "[" in f["name"]), None)
        for weight, suffix in [(400, "Regular"), (700, "Bold")]:
            source = variable or next(
                (f for f in files if suffix in f["name"]), files[0]
            )
            path = target / f"{family}-{suffix}.ttf"
            path.write_bytes(fetch(source["download_url"]))
            font = TTFont(path)
            if "fvar" in font:
                axes = {
                    a.axisTag: (weight if a.axisTag == "wght" else a.defaultValue)
                    for a in font["fvar"].axes
                }
                font = instantiateVariableFont(font, axes, inplace=False)
                font.save(path)
        license_file = next(e for e in entries if e["name"] == "OFL.txt")
        (target / f"{family}-OFL.txt").write_bytes(fetch(license_file["download_url"]))
        print("Bundled", family)
    viewer = ROOT / "components" / "viewer"
    viewer.mkdir(parents=True, exist_ok=True)
    for name in ["pdf.min.mjs", "pdf.worker.min.mjs"]:
        (viewer / name).write_bytes(
            fetch(f"https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/{name}")
        )
    (viewer / "PDFJS-LICENSE.txt").write_bytes(
        fetch("https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/LICENSE")
    )
    print("Bundled PDF.js 4.10.38")


if __name__ == "__main__":
    main()
