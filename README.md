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

For a traditional broadsheet look, select **Design → Use classic broadsheet style**. This updates previously saved design settings without changing your section prompts: a blackletter masthead, ruled date strip, stronger opening headline, justified serif columns and monochrome fine rules.

News research and newspaper editing are separate stages. Each time-sensitive section gets its own web-search brief; the app builds a source catalog from the API's citation annotations and tool results. The editor selects only source IDs allowed by that section's strict output schema. It never writes citation URLs: the app inserts the exact original links, so URL-copying mismatches cannot block generation. Copy-fitting revisions cannot edit source metadata. If a search returns no verified sources, the app researches again once and asks the editor to report the absence of a verified update honestly. It does not invent news or substitute unrelated links. Publication dates remain empty when unknown. Source provenance does not independently verify every factual claim. Each researched section uses an API call before the composition call.

The visible build label is `2026.10.11-full-pages`. If a deployed app shows an earlier build or no build label, it is not running this update; confirm its GitHub repository and `main` branch in the hosting settings, then redeploy/reboot it.

Prose now targets 95% of a measured capacity budget, rather than 65% of an already discounted budget. Research gathers enough background for developed articles; the editor is instructed to add substance, not filler or invented news. Sparse existing prose can use modestly larger type (up to 11 pt) after a successful fit check. Calendars use spare row height, and illustrations scale to the actual frame with their aspect ratio preserved. Regenerate an older edition for richer writing; design-only rerenders still make no API calls.

Settings and short summaries from the last thirty generated editions are saved automatically in **this browser’s local storage**. They survive app restarts on the same origin, but do not sync between devices. If storage is disabled or full, the app displays a warning. There are no accounts, no shared profiles, and no calendar connection. Prompts remain as entered until you edit them; update explicitly dated plans for a new week.

Illustrations are generated only for section prompts that request an image, photo, drawing or illustration (including Italian/German equivalents). Charts are drawn as vectors from generated structured data, which the editor is instructed to source or label as user-supplied/illustrative. The renderer validates structured data and uses embedded fonts for Unicode coverage. Joined emoji are shaped into actual monochrome symbols, never bracketed descriptive labels. Generated copy is prompted to use professional newspaper typography without decorative emoji. Invalid/unencoded characters use the Unicode replacement glyph; no Unicode-code labels are inserted. Full bidirectional paragraph layout is not currently supported.

An edition is print-ready only if every block fits inside its assigned regions. Fitting is automatic and measured: overflowing structured sections first use their full assigned width, then a compact calendar/table layout, tighter spacing and section-local typography down to 7.5 pt. Unaffected sections keep their chosen style. Calendars flow day by day across regions; compact calendar/table records can flow across lines without losing events or cells. Charts measure their full titles and labels; illustrations resize to the available height. These retries are local, deterministic and make no API calls.

Only if local fitting is insufficient, generation makes at most two shorter prose revisions. Source lists and original calendar, table, chart and illustration data are restored by application code, with illustration assets remapped if block positions change. Extremely large content that still cannot fit readably is rejected rather than silently omitted, clipped or shrunk to microscopic type. No finite two-page layout can hold arbitrary amounts of text. API/network/model failures are separate from layout fitting. Older editions retain their generation date and filenames.

## Development and verification

```sh
pip install -r requirements-dev.txt
python -m pytest -q
node --test tests/storage.test.cjs
python tools/verify_pdf.py work/preview --day 2026-10-10
```

Tests cover all 2,048 ordered twelve-space allocations, PDF bounds and page count, fonts, continuations, overflow, timezone and week boundaries, structured blocks, configuration validation, source validation and mocked generation/retries. Inspect both PNGs produced by the verification script for visual quality. Live generation additionally needs a working OpenAI account; mocked tests make no paid requests.

Google Fonts assets carry their included SIL Open Font Licenses. PDF.js 4.10.38 carries its included Apache 2.0 license. `python tools/bundle_assets.py` rebuilds the vendored assets from their public upstream sources (fonttools required).

`python tools/bundle_fallback_fonts.py` rebuilds the embedded Noto and GNU Unifont fallback assets. Their OFL/Unifont license notices are bundled alongside the font files. Fonts are local assets; PDF rendering never downloads fonts or needs system-installed fonts.
