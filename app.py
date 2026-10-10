"""My Daily Paper — configure a personal, sourced, two-sided A4 newspaper."""
from __future__ import annotations

import base64
from datetime import datetime
import html
import json
import os
import zlib
from zoneinfo import ZoneInfo

import streamlit as st

from engine import DEFAULT, SECTIONS, demo_issue, generate_issue, render_pdf

st.set_page_config(page_title='My Daily Paper', page_icon='🗞️', layout='wide', initial_sidebar_state='collapsed')

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
.stApp {background:#F7F7F3; color:#242A2B;}
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {font-family:'DM Sans',sans-serif;}
.block-container {padding-top:2rem; max-width:1390px;}
h1,h2,h3 {font-family:'Playfair Display', Georgia, serif !important;}
.stButton button[kind="primary"] {background:#183C42; border-color:#183C42; border-radius:8px; padding:.7rem 1.2rem;}
.stButton button[kind="primary"]:hover {background:#28535A; border-color:#28535A;}
[data-testid="stVerticalBlockBorderWrapper"] {background:#fff; border-radius:14px;}
[data-testid="stTabs"] button {font-family:'DM Sans',sans-serif;}
.brand-top {font-size:.72rem; letter-spacing:.22em; font-weight:700; color:#426466;}
.brand-name {font-family:'Playfair Display',Georgia,serif;font-size:2.25rem; line-height:1.12;margin:.15rem 0 .4rem 0;}
.brand-sub {color:#727978; font-size:.92rem;margin-bottom:.9rem;}
.preview-head {font-size:.72rem;font-weight:700;letter-spacing:.16em;color:#5A6665;margin-bottom:8px;}
.paper {background:#fff; color:#232626; padding:31px 33px 26px; border:1px solid #D9DBDA; box-shadow:0 8px 22px #17282416;min-height:640px;}
.paper .banner {font-weight:700;text-align:center;line-height:1.1;letter-spacing:-.02em;}
.paper .edition-meta {display:flex;justify-content:space-between;gap:10px;font-family:Arial,sans-serif;font-size:8.5px;text-transform:uppercase;padding:10px 0 8px;border-bottom:1px solid #C5C7C5;}
.paper .lead-kicker {font-family:Arial,sans-serif;font-size:9px;letter-spacing:.12em;font-weight:bold;margin-top:19px;}
.paper .lead-title {font-size:27px;line-height:1.12;font-weight:bold;margin:7px 0 9px;}
.paper .lead-blurb {font-size:11px;line-height:1.47;margin-bottom:14px;color:#454949;}
.paper .stories {display:grid; gap:16px; margin-top:16px;}
.paper .item {border-top:1.5px solid #B5C1BD;padding-top:11px;break-inside:avoid;}
.paper .section-name {font:700 8px Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;}
.paper .story-title {font-weight:bold;font-size:15px;line-height:1.14;margin:6px 0;}
.paper .story-desc {font-size:10.5px;line-height:1.36;margin:0;color:#464A49;}
.paper .bottom-mark {font:9px Arial,sans-serif;text-align:center;color:#8E9995;margin-top:20px;border-top:1px solid #D7DDDA;padding-top:10px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, os.environ.get(name, '')))
    except Exception:
        return str(os.environ.get(name, ''))


# Mandatory password gate when a server-held API key is configured.
server_key = secret('OPENAI_API_KEY')
password = secret('APP_PASSWORD')
if server_key and not password:
    st.error('Server-held API key detected without APP_PASSWORD. Add APP_PASSWORD to your secrets before running this public-facing app.')
    st.stop()
if password and not st.session_state.get('authorized'):
    st.markdown('<div class="brand-top">PRIVATE EDITION</div><div class="brand-name">My Daily Paper</div>', unsafe_allow_html=True)
    attempt = st.text_input('Enter your newspaper password', type='password')
    if st.button('Unlock', type='primary'):
        import hmac
        if hmac.compare_digest(attempt, password):
            st.session_state.authorized = True
            st.rerun()
        else:
            st.error('Incorrect password')
    st.stop()


def read_url_profile() -> dict:
    try:
        data = st.query_params.get('preset', '')
        if not data or len(data) > 14000:
            return {}
        raw = zlib.decompressobj().decompress(base64.urlsafe_b64decode(data.encode()), 30000)
        return json.loads(raw.decode())
    except Exception:
        return {}


def valid_settings(value):
    out = {**DEFAULT}
    if isinstance(value, dict):
        out.update({k:v for k,v in value.items() if k in DEFAULT and type(v) == type(DEFAULT[k])})
    out['sections'] = [s for s in out['sections'] if s in SECTIONS]
    if not out['sections']:
        out['sections'] = DEFAULT['sections']
    out['priorities'] = {s: max(1,min(5,int(out['priorities'].get(s,2)))) for s in SECTIONS}
    enums = {
        'theme': ['Ink & Ivory','Midnight blue','Forest green','Terracotta','Classic black'],
        'typeface': ['Editorial serif','Modern sans','Typewriter'],
        'density': ['Compact','Balanced','Airy'],
        'german_level': ['A1','A2','B1','B2','C1'],
        'language': ['English','Italian','German'],
        'tone': ['Concise, analytical, no hype','Curious and thoughtful','Financial Times style',
                 'Warm and optimistic','No-nonsense briefing'],
        'model': ['gpt-5-mini','gpt-4.1-mini','gpt-4.1'],
    }
    for key,values in enums.items():
        if out[key] not in values:
            out[key] = DEFAULT[key]
    out['columns'] = out['columns'] if out['columns'] in (2,3) else 2
    out['font_size'] = max(8,min(11,out['font_size']))
    return out


def seed(settings):
    for k in list(st.session_state):
        if k.startswith('priority_'):
            del st.session_state[k]
    for k,v in valid_settings(settings).items():
        st.session_state['p_'+k] = v
    st.session_state['_last_theme'] = st.session_state['p_theme']


if '_pending_settings' in st.session_state:
    seed(st.session_state.pop('_pending_settings'))
    st.session_state.profile_initialized = True
elif not st.session_state.get('profile_initialized'):
    seed(read_url_profile())
    st.session_state.profile_initialized = True


def get_settings():
    return valid_settings({key:st.session_state.get('p_'+key,default) for key,default in DEFAULT.items()})

st.markdown('<div class="brand-top">YOUR PERSONAL NEWSROOM</div><div class="brand-name">My Daily Paper</div><div class="brand-sub">One sheet. Two sides. Entirely yours.</div>', unsafe_allow_html=True)
left,right = st.columns([1, 1.05], gap='large')

with left:
    st.write('**Build your edition**')
    tabs = st.tabs(['Content', 'Design', 'Editorial', 'Save'])
    with tabs[0]:
        st.text_input('Newspaper title', key='p_name')
        st.text_input('Subtitle / motto', key='p_tagline')
        st.multiselect('Your sections', SECTIONS, key='p_sections', help='Only these sections are requested from OpenAI.')
        with st.expander('Fine-tune section priorities', expanded=True):
            chosen = st.session_state.p_sections
            for section in chosen:
                current = st.session_state['p_priorities'].get(section,2)
                st.session_state['p_priorities'][section] = st.slider(section,1,5,current,key='priority_'+section)
            st.caption('1 = occasional / brief. 5 = core focus.')
        st.text_input('Companies / tickers', key='p_companies', help='For monitoring and context, not invented real-time market prices.')
        st.text_area('Your interests', height=80, key='p_interests')
        st.selectbox('German level', ['A1','A2','B1','B2','C1'], key='p_german_level')
        st.text_area('Personal reminders (one per line)',height=105,key='p_reminders',help='Only the reminders you enter here are included. No access to your calendar.')
    with tabs[1]:
        themes = {'Ink & Ivory':'#183C42','Midnight blue':'#283D6A','Forest green':'#2D5946',
                  'Terracotta':'#A74A31','Classic black':'#303030'}
        st.selectbox('Color theme',list(themes),key='p_theme')
        old = st.session_state.get('_last_theme')
        if old != st.session_state.p_theme:
            st.session_state.p_accent = themes[st.session_state.p_theme]
            st.session_state._last_theme = st.session_state.p_theme
        st.color_picker('Custom accent color',key='p_accent')
        st.selectbox('Typography',['Editorial serif','Modern sans','Typewriter'],key='p_typeface')
        st.radio('Print columns',[2,3],horizontal=True,key='p_columns')
        st.select_slider('Spacing',['Compact','Balanced','Airy'],key='p_density')
        st.slider('Body text size',8,11,key='p_font_size')
        st.toggle('Show article sources in PDF',key='p_sources_visible')
        st.info('Every edition is exactly 2 A4 pages and ready for duplex printing.')
    with tabs[2]:
        st.text_input('Your home region',key='p_region')
        st.selectbox('Newspaper language',['English','Italian','German'],key='p_language')
        st.selectbox('Editorial voice',[
            'Concise, analytical, no hype', 'Curious and thoughtful', 'Financial Times style',
            'Warm and optimistic', 'No-nonsense briefing'],key='p_tone')
        st.text_area('Preferred sources',height=90,key='p_sources')
        st.text_area('Your custom editorial prompt',height=220,key='p_instructions',
            help='Tell your AI editor what matters to you, what to exclude, how to reason and what tone to use.')
        st.selectbox('OpenAI model',['gpt-5-mini','gpt-4.1-mini','gpt-4.1'],key='p_model',help='Web search is used when you generate a real issue; this incurs API usage fees.')
    with tabs[3]:
        st.write('**Your settings, without a database.**')
        st.caption('Download a profile file, or create a bookmarkable link. No API keys are included.')
        settings = get_settings()
        st.download_button('Download settings (.json)',json.dumps(settings,ensure_ascii=False,indent=2).encode(),
                           file_name='my-daily-paper-settings.json',mime='application/json',use_container_width=True)
        upload = st.file_uploader('Import a settings file',type=['json'])
        if upload is not None and st.button('Apply imported settings'):
            try:
                st.session_state['_pending_settings'] = json.load(upload)
                st.rerun()
            except Exception as e:
                st.error('Invalid settings file: '+str(e))
        if st.button('Save settings into this page URL',use_container_width=True):
            packed = base64.urlsafe_b64encode(zlib.compress(json.dumps(get_settings()).encode(),9)).decode()
            st.query_params['preset'] = packed
            st.success('Saved to the URL. Bookmark or copy this page to return to your settings.')

    st.divider()
    if server_key:
        st.success('OpenAI key connected through server secrets.')
        api_key = server_key
    else:
        api_key = st.text_input('OpenAI API key · this session only',type='password',
            help='Never added to your profile, download, or URL. For hosted usage, set it as a Streamlit secret.')
    generate = st.button('✦ Generate today’s newspaper',type='primary',use_container_width=True)
    sample = st.button('↻ Make sample PDF (no API cost)',use_container_width=True)
    st.caption('PDFs print on both sides via your normal system or iPhone AirPrint dialog.')

settings = get_settings()
# Layout changes update the latest printable PDF without another paid API call.
if 'edition' in st.session_state:
    layout_signature = json.dumps({k:v for k,v in settings.items() if k not in ('sources','tone','instructions','model')},sort_keys=True)
    if layout_signature != st.session_state.get('layout_signature'):
        st.session_state.pdf, st.session_state.omitted = render_pdf(
            settings, st.session_state.edition,
            st.session_state.get('edition_date',datetime.now(ZoneInfo('Europe/Zurich')).strftime('%A, %d %B %Y')))
        st.session_state.layout_signature = layout_signature
now = datetime.now(ZoneInfo('Europe/Zurich'))
date_label = now.strftime('%A, %d %B %Y')

if generate:
    if not api_key:
        st.error('Enter your API key or add OPENAI_API_KEY to Streamlit secrets.')
    elif not settings['sections']:
        st.error('Choose at least one section.')
    else:
        with st.spinner('Your editor is researching current sources and composing the edition…'):
            try:
                issue = generate_issue(settings,api_key,now.date().isoformat())
                pdf, omitted = render_pdf(settings,issue,date_label)
                st.session_state.edition = issue
                st.session_state.pdf = pdf
                st.session_state.omitted = omitted
                st.session_state.edition_date = date_label
                st.session_state.pop('layout_signature', None)
                st.success('Today’s edition is ready.')
            except Exception as exc:
                st.error(f'Could not generate this edition: {exc}')
if sample:
    try:
        st.session_state.edition = demo_issue()
        st.session_state.pdf, st.session_state.omitted = render_pdf(settings,st.session_state.edition,date_label)
        st.session_state.edition_date = date_label
        st.session_state.pop('layout_signature', None)
    except Exception as exc:
        st.error(f'Could not render sample PDF: {exc}')

with right:
    st.markdown('<div class="preview-head">LIVE DESIGN PREVIEW · FRONT PAGE</div>',unsafe_allow_html=True)
    issue = st.session_state.get('edition',demo_issue())
    theme_font = {'Editorial serif':'Georgia, serif','Modern sans':'Arial, sans-serif','Typewriter':'Courier New,monospace'}[settings['typeface']]
    safe = lambda s: html.escape(str(s or ''))
    cards = []
    for article in issue.get('stories',[]):
        if article.get('section') not in settings['sections']:
            continue
        cards.append(f'''<div class="item"><div class="section-name" style="color:{settings['accent']}">{safe(article['section'])}</div>
            <div class="story-title">{safe(article['headline'])}</div><p class="story-desc">{safe(article['body'])}</p></div>''')
    cards = cards[:6]
    heading = safe(settings['name'])
    st.markdown(f'''
    <div class="paper" style="font-family:{theme_font}; border-top:6px solid {settings['accent']};">
    <div class="banner" style="font-size:{30 if len(heading)<25 else 23}px">{heading}</div>
    <div class="edition-meta"><span>{safe(date_label)}</span><span>{safe(settings['tagline'])}</span></div>
    <div class="lead-kicker" style="color:{settings['accent']}">{safe(issue.get('kicker','THE LEAD'))}</div>
    <div class="lead-title">{safe(issue.get('headline',''))}</div>
    <div class="lead-blurb">{safe(issue.get('lead_body',''))}</div>
    <div class="stories" style="grid-template-columns:repeat({settings['columns']}, minmax(0,1fr)); column-gap:{'10' if settings['density']=='Compact' else '16'}px;">
       {''.join(cards)}
    </div><div class="bottom-mark">YOUR PERSONAL DAILY EDITION · FRONT / BACK</div></div>
    ''',unsafe_allow_html=True)
    st.caption('Design preview is illustrative. Download the PDF to inspect the precise A4 print layout.')
    if st.session_state.get('pdf'):
        st.download_button('↓ Download two-page PDF',st.session_state.pdf,
                           file_name=f'my-daily-paper-{now.date().isoformat()}.pdf',
                           mime='application/pdf',type='primary',use_container_width=True)
        if st.session_state.get('omitted',0):
            st.warning(f"{st.session_state.omitted} short article(s) could not fit on two pages. Reduce your font size, switch to compact layout, or select fewer topics.")
        with st.expander('Read article links in the latest edition'):
            for item in [issue]+issue.get('stories',[]):
                name = item.get('lead_source_name') or item.get('source_name')
                url = item.get('lead_source_url') or item.get('source_url')
                if name and isinstance(url,str) and url.startswith(('http://','https://')):
                    st.markdown(f'[{name}]({url})')
