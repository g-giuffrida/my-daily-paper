# My Daily Paper

A daily newspaper on one A4 sheet, printed front and back. Twelve spaces are allocated in reading order: two columns and three rows per side. The front reserves 40–50 mm for a customizable masthead; the back goes straight to the grid.

## Run

Requires Python 3.11 or later. Fonts and PDF.js are bundled; the app does not need to fetch design assets at runtime.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Enter your OpenAI API key in the app. It stays in the server session and is never saved to the browser profile. Alternatively, configure `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your-key"
APP_PASSWORD = "your-private-app-password"
```

A server-held key requires an app password. Keep secrets out of Git. For a private local instance, add `--server.address 127.0.0.1` to the launch command.

## Make your edition

- **Content:** choose a newspaper title and subtitle. Add up to twelve sections, each with a name, freeform prompt and 1–12 spaces. Reorder using the arrows. Assign exactly twelve spaces before generating.
- **Design:** choose a preset or customize fonts, sizes, colors, margins, spacing and dividers. Wide regions use readable newspaper text columns. Design changes retypeset existing content without paid generation calls.
- **Editorial:** choose language, voice, region, timezone, source preferences and text/image models. Access to a selected model depends on your OpenAI account.
- **Generate today’s newspaper:** captures the current date in your timezone, researches time-sensitive requests and generates content sized for your layout. Calendars cover that edition’s Monday–Sunday and highlight its date. Prompt events are never treated as confirmed attendance.
- **Print:** the preview shows the actual PDF, on either side or both. Use its print button, choose A4, actual size, duplex and flip on long edge in your system dialog. PDF download is available for browsers that block embedded printing. Printing does not regenerate content.

Try the sample without an API key. It is prominently labeled illustrative, not current reporting.

Settings and short summaries from the last thirty generated editions are saved automatically in **this browser’s local storage**. They survive app restarts on the same origin, but do not sync between devices. If storage is disabled or full, the app displays a warning. There are no accounts, no shared profiles, and no calendar connection. Prompts remain as entered until you edit them; update explicitly dated plans for a new week.

Illustrations are generated only for section prompts that request an image, photo, drawing or illustration (including Italian/German equivalents). Charts are drawn as vectors from generated structured data, which the editor is instructed to source or label as user-supplied/illustrative. The renderer rejects invalid data and unsupported font characters rather than printing broken glyphs. The bundled font families support English, Italian, German and other Latin-script languages; other scripts may require additional fonts.

An edition is print-ready only if every block fits inside its assigned regions. Prose can continue across regions and sides. Tables, charts, calendars and images remain intact. Generation makes at most two shorter revisions of overflowing sections; unresolved overflow is reported by section name. Text is never silently omitted or clipped. Older editions retain their generation date and filenames.

## Development and verification

```sh
pip install -r requirements-dev.txt
python -m pytest -q
node --test tests/storage.test.cjs
python tools/verify_pdf.py work/preview --day 2026-10-10
```

Tests cover all 2,048 ordered twelve-space allocations, PDF bounds and page count, fonts, continuations, overflow, timezone and week boundaries, structured blocks, configuration validation, source validation and mocked generation/retries. Inspect both PNGs produced by the verification script for visual quality. Live generation additionally needs a working OpenAI account; mocked tests make no paid requests.

Google Fonts assets carry their included SIL Open Font Licenses. PDF.js 4.10.38 carries its included Apache 2.0 license. `python tools/bundle_assets.py` rebuilds the vendored assets from their public upstream sources (fonttools required).
