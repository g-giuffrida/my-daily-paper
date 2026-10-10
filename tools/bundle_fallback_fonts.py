"""Vendor licensed Unicode fallback fonts; no font downloads at application runtime."""

from pathlib import Path
import sys
from io import BytesIO

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bundle_assets import fetch
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

TARGET = Path(__file__).resolve().parents[1] / "assets" / "fonts"


def main():
    for name, url in [
        (
            "Unifont",
            "https://unifoundry.com/pub/unifont/unifont-15.0.06/font-builds/unifont-15.0.06.ttf",
        ),
        (
            "UnifontUpper",
            "https://unifoundry.com/pub/unifont/unifont-15.0.06/font-builds/unifont_upper-15.0.06.ttf",
        ),
        (
            "NotoEmoji",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf",
        ),
        (
            "NotoSansArabic",
            "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf",
        ),
        (
            "NotoSansDevanagari",
            "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
        ),
    ]:
        data = fetch(url)
        face = TTFont(BytesIO(data))
        if "fvar" in face:
            face = instantiateVariableFont(
                face, {a.axisTag: a.defaultValue for a in face["fvar"].axes}
            )
        face.save(TARGET / f"{name}-Regular.ttf")
        print("Bundled", name)
    for name, url in [
        ("Unifont-LICENSE.txt", "https://unifoundry.com/LICENSE.txt"),
        (
            "NotoEmoji-OFL.txt",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/OFL.txt",
        ),
        (
            "NotoSansArabic-OFL.txt",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansarabic/OFL.txt",
        ),
        (
            "NotoSansDevanagari-OFL.txt",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/OFL.txt",
        ),
    ]:
        (TARGET / name).write_bytes(fetch(url))


if __name__ == "__main__":
    main()
