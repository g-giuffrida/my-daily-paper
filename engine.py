"""Source-grounded news generation and print-ready two-page PDF."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
import json
import math
import re
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

SECTIONS = [
    'World news', 'Switzerland', 'Markets & investing', 'AI & technology',
    'Science & nature', 'German lesson', 'Week ahead', 'Philosophy', 'Personal interests',
]

DEFAULT = {
    'name': 'THE MORNING EDITION',
    'tagline': 'A little more informed, every day.',
    'region': 'Switzerland',
    'language': 'English',
    'sections': ['World news', 'Switzerland', 'Markets & investing', 'German lesson', 'Week ahead', 'Philosophy'],
    'priorities': {'World news': 3, 'Switzerland': 3, 'Markets & investing': 4, 'German lesson': 3, 'Week ahead': 2, 'Philosophy': 1},
    'companies': 'ACLN.SW, ABBN.SW, NXT, UBER',
    'interests': 'Swiss industrial businesses, long-term investing, geopolitics, science and the outdoors',
    'german_level': 'A2',
    'reminders': 'Review weekly goals\nPlan a weekend hike',
    'tone': 'Concise, analytical, no hype',
    'instructions': 'Prioritize news that changes my understanding of the world. Explain why financial developments matter, not just what moved. Avoid sensationalism and repetition.',
    'sources': 'Reuters, AP, SRF, Financial Times, Swiss Federal Council, company investor relations',
    'theme': 'Ink & Ivory',
    'accent': '#183C42',
    'typeface': 'Editorial serif',
    'columns': 2,
    'font_size': 9,
    'density': 'Balanced',
    'sources_visible': True,
    'model': 'gpt-5-mini',
}

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'kicker': {'type': 'string'},
        'headline': {'type': 'string'},
        'lead_body': {'type': 'string'},
        'lead_source_name': {'type': 'string'},
        'lead_source_url': {'type': 'string'},
        'stories': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'properties': {'section': {'type': 'string'}, 'headline': {'type': 'string'},
                           'body': {'type': 'string'}, 'source_name': {'type': 'string'},
                           'source_url': {'type': 'string'}},
            'required': ['section', 'headline', 'body', 'source_name', 'source_url'],
        }},
        'german': {'type': 'object', 'additionalProperties': False, 'properties': {
            'word': {'type': 'string'}, 'meaning': {'type': 'string'},
            'example_de': {'type': 'string'}, 'example_en': {'type': 'string'},
            'exercise': {'type': 'string'}
        }, 'required': ['word', 'meaning', 'example_de', 'example_en', 'exercise']},
        'thought': {'type': 'object', 'additionalProperties': False, 'properties': {
            'text': {'type': 'string'}, 'author': {'type': 'string'}
        }, 'required': ['text', 'author']},
    },
    'required': ['kicker', 'headline', 'lead_body', 'lead_source_name',
                 'lead_source_url', 'stories', 'german', 'thought']
}


def generate_issue(settings: dict, key: str, day: str) -> dict:
    """One web-grounded OpenAI call returning structured newspaper content."""
    selected = settings['sections']
    requested = {s: settings.get('priorities', {}).get(s, 2) for s in selected}
    count = min(12, max(6, 2 * len([s for s in selected if s not in ('German lesson', 'Week ahead', 'Philosophy')])))
    instructions = (
        'You are the fact-checking editor of a compact personal newspaper. '
        f'Today is {day} in Europe/Zurich. Search the WEB for recent, relevant developments. '
        'Use real sources with working URLs, and only describe verifiable factual events. '
        'Never fabricate headlines, dates, stock prices, financial metrics, URLs or quotations. '
        'Separate observations from interpretations. Stories should concern the last 24-72 hours when appropriate. '
        'If a specific topic has no verified development, choose evergreen, factual educational material instead, clearly labelled. '
        'Return structured data for a TWO-SIDED SINGLE A4 SHEET. '
        f'Choose ~{count} short stories total; body of each story 35-65 words; lead_body 70-100 words. '
        'Order items according to editorial priority. Avoid duplicates. No markdown in fields. '
        'Put the original publication name in source_name and a real direct source link in source_url. '
        'For timeless lessons or ideas where no external source is used, use empty source_name and source_url. '
        f'Selected sections (ONLY use these): {selected}. Priorities 1 to 5: {requested}. '
        'If German lesson is selected, create one truly useful micro-lesson with grammar or idiom, a worked example and a small exercise. '
        'If Philosophy is selected, use an original thought, not an invented historical quotation; author may be "Editorial note". '
        'If Week ahead is selected, do NOT pretend to know the user calendar. The user provides their reminders separately. '
        f'User region: {settings["region"]}; writing language: {settings["language"]}; German level: {settings["german_level"]}. '
        f'Stocks to monitor: {settings["companies"]}. Interests: {settings["interests"]}. '
        f'Source preferences: {settings["sources"]}. Preferred editorial tone: {settings["tone"]}. '
        f'CUSTOM EDITORIAL INSTRUCTIONS (apply unless conflicting with sourcing/safety): {settings["instructions"]}'
    )
    from openai import OpenAI
    client = OpenAI(api_key=key, timeout=180)
    response = client.responses.create(
        model=settings.get('model', 'gpt-5-mini'),
        tools=[{'type': 'web_search', 'search_context_size': 'medium'}],
        input=[{'role': 'system', 'content': instructions},
               {'role': 'user', 'content': f'Produce the {day} edition now. Research sources before composing the articles.'}],
        text={'format': {'type': 'json_schema', 'name': 'daily_newspaper',
                         'strict': True, 'schema': SCHEMA}},
    )
    if not response.output_text:
        raise ValueError('The model returned no article content. Try again.')
    issue = json.loads(response.output_text)
    # Ensure no model-generated section can inject unrelated sections.
    issue['stories'] = [s for s in issue.get('stories', []) if s.get('section') in selected]
    return issue


def demo_issue() -> dict:
    """Non-current demonstration only; never represented as real news."""
    return {
        'kicker': 'DESIGN PREVIEW · SAMPLE CONTENT',
        'headline': 'A quieter, clearer way to begin the day',
        'lead_body': ('This preview uses illustrative writing, not current reporting. '
                      'Your actual edition will collect recent news from the web and cite its sources. '
                      'Change the palette, typography, columns and sections to see how your own newspaper will look.'),
        'lead_source_name': '', 'lead_source_url': '',
        'stories': [
            {'section': 'World news', 'headline': 'What deserves attention today?',
             'body': 'The real paper will prioritize substantive international developments and explain their context, rather than fill the page with noise.',
             'source_name': '', 'source_url': ''},
            {'section': 'Switzerland', 'headline': 'The local lens',
             'body': 'Swiss policy, business and everyday developments can take priority here. Use the settings to define your focus and preferred sources.',
             'source_name': '', 'source_url': ''},
            {'section': 'Markets & investing', 'headline': 'Beyond the market ticker',
             'body': 'Your edition can track businesses you follow, explain earnings and valuations, and distinguish meaningful signals from ordinary volatility.',
             'source_name': '', 'source_url': ''},
            {'section': 'AI & technology', 'headline': 'Useful technology, not noise',
             'body': 'Track developments that change what software and AI can really do. Favor primary research and practical implications.',
             'source_name': '', 'source_url': ''},
            {'section': 'Science & nature', 'headline': 'An idea worth exploring',
             'body': 'A short window into science, nature or the natural world creates space for curiosity beyond the headlines.',
             'source_name': '', 'source_url': ''},
            {'section': 'World news', 'headline': 'Understanding the bigger picture',
             'body': 'Explore the context behind important developments: who is affected, what has genuinely changed, and which questions remain open.',
             'source_name': '', 'source_url': ''},
            {'section': 'Switzerland', 'headline': 'Signals from the Swiss economy',
             'body': 'A useful briefing might compare employment, manufacturing activity, or economic expectations, with attention to the original data.',
             'source_name': '', 'source_url': ''},
            {'section': 'Markets & investing', 'headline': 'Quality over excitement',
             'body': 'The long-term investor benefits from earnings quality, durable cash flow, competitive advantages, sensible valuation, and a clear account of uncertainty.',
             'source_name': '', 'source_url': ''},
            {'section': 'Personal interests', 'headline': 'A little something for you',
             'body': 'Your personal interests shape this space. Describe them in the app and change them whenever you like.',
             'source_name': '', 'source_url': ''},
        ],
        'german': {'word': 'die Zuversicht', 'meaning': 'confidence, optimism',
                   'example_de': 'Ich blicke mit Zuversicht auf die Woche.',
                   'example_en': 'I look ahead to the week with confidence.',
                   'exercise': 'Write your own sentence using “Zuversicht”.'},
        'thought': {'text': 'Begin with what matters. Leave room for what surprises you.',
                    'author': 'Sample editorial note'},
    }


def _ink(value: str):
    return colors.HexColor(value if re.fullmatch(r'#[0-9A-Fa-f]{6}', value) else '#183C42')


def _source_url(value: str) -> str:
    try:
        parsed = urlparse(value)
        return value if parsed.scheme in ('http', 'https') and parsed.netloc else ''
    except (ValueError, TypeError):
        return ''


def render_pdf(settings: dict, issue: dict, day: str) -> tuple[bytes, int]:
    """Guarantee exactly two A4 pages. Returns (PDF, number of stories that couldn't fit)."""
    stream = BytesIO()
    c = Canvas(stream, pagesize=A4, pageCompression=1)
    c.setTitle(f'{settings["name"]} - {day}')
    W, H = A4
    accent = _ink(settings['accent'])
    black = colors.HexColor('#242A2B')
    gray = colors.HexColor('#686F70')
    margin = 39
    gap = 17
    cols = int(settings['columns'])
    colw = (W - margin * 2 - gap * (cols-1)) / cols
    serif = settings['typeface'] == 'Editorial serif'
    mono = settings['typeface'] == 'Typewriter'
    bodyfont = 'Times-Roman' if serif else ('Courier' if mono else 'Helvetica')
    boldfont = 'Times-Bold' if serif else ('Courier-Bold' if mono else 'Helvetica-Bold')
    sz = float(settings['font_size'])
    density_factor = {'Compact': 1.14, 'Balanced': 1.27, 'Airy': 1.44}[settings['density']]
    miny = 47
    page = 1
    column = 0
    skipped = 0

    def p(txt, font, size, color=black, line_factor=1.22):
        return Paragraph(escape(str(txt or '')), ParagraphStyle(
            'x', fontName=font, fontSize=size, leading=size*line_factor,
            textColor=color, spaceAfter=0, allowWidows=0, allowOrphans=0,
        ))

    def draw_para(para, x, y, width):
        _, height = para.wrap(width, H)
        para.drawOn(c, x, y-height)
        return y-height

    def meta(y_value, page_num):
        c.setFont('Helvetica', 7.2)
        c.setFillColor(gray)
        c.drawString(margin, 27, settings['name'][:40].upper())
        c.drawCentredString(W/2, 27, 'ILLUSTRATIVE PREVIEW' if issue['kicker'].startswith('DESIGN PREVIEW') else day)
        c.drawRightString(W-margin, 27, f'{page_num} / 2')
        c.setStrokeColor(colors.HexColor('#CACBCC'))
        c.setLineWidth(.45)
        c.line(margin, 38, W-margin, 38)

    def top(first):
        c.setFillColor(accent)
        c.rect(0, H-9, W, 9, fill=1, stroke=0)
        if first:
            c.setFillColor(black)
            c.setFont(boldfont, 27 if len(settings['name']) < 24 else 21)
            c.drawCentredString(W/2, H-67, settings['name'][:34])
            c.setStrokeColor(accent); c.setLineWidth(.9); c.line(margin,H-82,W-margin,H-82)
            c.setFillColor(gray); c.setFont('Helvetica', 8)
            c.drawString(margin, H-97, day.upper())
            c.drawRightString(W-margin, H-97, settings['tagline'][:60])
            return H-111
        c.setFont(boldfont, 14); c.setFillColor(black)
        c.drawString(margin,H-48,settings['name'][:40])
        c.setFont('Helvetica',8);c.setFillColor(gray)
        c.drawRightString(W-margin,H-48,'THE OTHER SIDE · '+day)
        c.setStrokeColor(accent);c.line(margin,H-58,W-margin,H-58)
        return H-72

    # Lead article across the full width on page one.
    topy = top(True)
    c.setFillColor(accent);c.setFont('Helvetica-Bold',7.8)
    c.drawString(margin,topy-7,(issue.get('kicker') or 'THE LEAD STORY')[:80].upper())
    hy = topy-15
    headline = p(issue.get('headline','A new day, a new page'),boldfont,24 if len(issue.get('headline','')) < 58 else 20,black,1.08)
    hy = draw_para(headline,margin,hy,W-2*margin)
    body = p(issue.get('lead_body',''),bodyfont,sz+0.3,black,1.26)
    hy = draw_para(body,margin,hy-9,W-2*margin)
    if settings['sources_visible'] and issue.get('lead_source_name') and _source_url(issue.get('lead_source_url','')):
        hy = draw_para(p('SOURCE: '+issue['lead_source_name'],'Helvetica',7,accent),margin,hy-5,W-2*margin)
        c.linkURL(_source_url(issue['lead_source_url']), (margin,hy,W-margin,hy+11), relative=0)
    c.setStrokeColor(accent);c.setLineWidth(1);c.line(margin,hy-13,W-margin,hy-13)
    current_y = hy-27
    page_tops = {1: current_y}

    def advance():
        nonlocal page,column,current_y
        if page == 2 and column == cols - 1:
            return False
        column += 1
        if column >= cols:
            page += 1
            if page > 2:
                return False
            meta(current_y, 1)
            c.showPage()
            current_y = top(False)
            page_tops[2] = current_y
            column = 0
        else:
            current_y = page_tops[page]
        return True

    selected = settings['sections']
    stories = [item for item in issue.get('stories',[]) if item.get('section') in selected]
    # Place utility sections on the back page when practical.
    if 'German lesson' in selected:
        g = issue['german']
        stories.append({'section': 'German lesson', 'headline': g.get('word','Word of the day'),
                       'body': (f"{g.get('meaning','')}\n{g.get('example_de','')}\n"
                                f"{g.get('example_en','')}\nTRY: {g.get('exercise','')}"),
                        'source_name': '', 'source_url': ''})
    if 'Week ahead' in selected:
        reminders = [v.strip() for v in settings.get('reminders','').splitlines() if v.strip()]
        if reminders:
            stories.append({'section': 'Week ahead', 'headline': 'Your reminders',
                            'body': '  •  '.join(reminders[:8]), 'source_name': '', 'source_url': ''})
    if 'Philosophy' in selected:
        t = issue.get('thought',{})
        stories.append({'section':'Philosophy', 'headline': 'A thought for today',
                        'body': t.get('text','')+'  — '+t.get('author',''),
                        'source_name':'', 'source_url':''})

    # Reserve the back page for meaningful content, even when everything would fit on the front.
    # A single issue is always one physical A4 sheet, printed on both sides.
    front_target = max(1, min(4, math.ceil(len(stories) / 2)))
    for index, story in enumerate(stories):
        if index == front_target and page == 1:
            while page == 1:
                advance()
        # Distribute short articles over all columns rather than filling only the left.
        side_start = 0 if index < front_target else front_target
        side_count = front_target if index < front_target else len(stories) - front_target
        per_column = max(1, math.ceil(side_count / cols))
        desired_column = min(cols-1, (index-side_start)//per_column)
        while page <= 2 and column < desired_column:
            if not advance():
                break
        if page > 2:
            skipped += 1
            continue
        label = p(story.get('section','').upper(),'Helvetica-Bold',7.2,accent,1.0)
        head = p(story.get('headline',''),boldfont,sz+3.7,black,1.12)
        paragraphs = [p(line,bodyfont,sz,black,density_factor) for line in story.get('body','').split('\n') if line.strip()]
        src = _source_url(story.get('source_url',''))
        ref = p('SOURCE: '+story.get('source_name',''), 'Helvetica',6.8,gray) if settings['sources_visible'] and story.get('source_name') and src else None
        def estimate():
            height = 9
            for para,space in [(label,7),(head,8)]:
                height += para.wrap(colw,H)[1] + space
            for para in paragraphs:
                height += para.wrap(colw,H)[1] + 4
            if ref:
                height += ref.wrap(colw,H)[1]+6
            return height+14
        need = estimate()
        if current_y-need < miny:
            if not advance():
                skipped += 1
                continue
        if current_y-need < miny:
            skipped += 1
            continue
        x = margin + column*(colw+gap)
        c.setFillColor(accent); c.rect(x,current_y-2,18,2,fill=1,stroke=0)
        y = draw_para(label,x,current_y-8,colw)-8
        y = draw_para(head,x,y,colw)-8
        for para in paragraphs:
            y = draw_para(para,x,y,colw)-4
        if ref:
            ry = y-2
            y = draw_para(ref,x,ry,colw)
            c.linkURL(src,(x,y,x+colw,ry),relative=0)
        y -= 13
        c.setStrokeColor(colors.HexColor('#DDDFDF'));c.setLineWidth(.4)
        c.line(x,y,x+colw,y)
        current_y = y-13

    if page == 1:
        meta(current_y, 1)
        c.showPage()
        top(False)
        meta(current_y, 2)
    else:
        meta(current_y, 2)
    c.save()
    return stream.getvalue(), skipped
