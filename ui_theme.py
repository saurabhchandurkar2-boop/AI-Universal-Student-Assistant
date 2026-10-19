"""
Visual theme for the Streamlit app: a quiet dark interface with one accent.

apply_theme()  - injects the CSS
render_hero()  - the page header
"""
import streamlit as st

# Palette
#   ink      #070B16  page background
#   panel    #0F1628  raised surfaces
#   panel-2  #151E36  hover and user messages
#   line     #25304D  hairlines
#   accent   #4FD1D9  primary accent (teal)
#   violet   #8B7CFF  secondary accent, used only on user messages and the upload area
#   text     #E8ECF8  body text
#   muted    #A3AFCF  secondary text

_CSS = """
<style>
/* Fonts are bundled in static/fonts (served by Streamlit), so they work offline. */
@font-face { font-family: 'Inter'; font-weight: 400; font-display: swap; src: url('/app/static/fonts/Inter-Regular.woff') format('woff'); }
@font-face { font-family: 'Inter'; font-weight: 500; font-display: swap; src: url('/app/static/fonts/Inter-Medium.woff') format('woff'); }
@font-face { font-family: 'Inter'; font-weight: 600; font-display: swap; src: url('/app/static/fonts/Inter-SemiBold.woff') format('woff'); }
@font-face { font-family: 'Inter'; font-weight: 700; font-display: swap; src: url('/app/static/fonts/Inter-Bold.woff') format('woff'); }
@font-face { font-family: 'Poppins'; font-weight: 500; font-display: swap; src: url('/app/static/fonts/Poppins-Medium.woff') format('woff'); }
@font-face { font-family: 'Poppins'; font-weight: 700; font-display: swap; src: url('/app/static/fonts/Poppins-Bold.woff') format('woff'); }

:root {
  --ink: #070B16;
  --panel: #0F1628;
  --panel-2: #151E36;
  --line: #25304D;
  --text: #E8ECF8;
  --muted: #A3AFCF;
  --accent: #4FD1D9;
  --accent-ink: #04202A;
  --violet: #8B7CFF;
  --radius: 12px;
  --font-body: 'Inter', system-ui, -apple-system, 'Segoe UI', 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
  --font-head: 'Poppins', 'Inter', system-ui, 'Segoe UI', 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
}

/* ---------- Page ---------- */
html, body, [data-testid="stAppViewContainer"], .stApp {
  background:
    radial-gradient(900px 420px at 90% -12%, rgba(139,124,255,0.16), transparent 60%),
    radial-gradient(800px 420px at 0% -8%, rgba(79,209,217,0.10), transparent 60%),
    var(--ink) !important;
  color: var(--text);
  font-family: var(--font-body);
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1080px; }

h1, h2, h3, h4 {
  font-family: var(--font-head);
  letter-spacing: -0.02em; color: var(--text);
}
h2 { font-size: 1.3rem !important; font-weight: 700 !important; }
h3 { font-size: 1.05rem !important; font-weight: 700 !important; }
p, li, label, span, div { font-family: var(--font-body); }
h1 *, h2 *, h3 *, h4 * { font-family: var(--font-head); }
button, button * { font-family: var(--font-body); }

/* Keep Material icons rendering as icons */
[data-testid="stIconMaterial"], span[class*="material-symbols"] {
  font-family: 'Material Symbols Rounded' !important;
}

/* ---------- Header ---------- */
.hero {
  position: relative; overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 2rem 2.2rem 1.8rem;
  margin-bottom: 1.5rem;
  background: linear-gradient(135deg, #111A31 0%, #0B1224 100%);
}
.hero h1 {
  position: relative; z-index: 1;
  margin: 0 0 0.55rem 0; padding: 0;
  font-size: clamp(1.6rem, 3.6vw, 2.3rem);
  line-height: 1.15; font-weight: 700; letter-spacing: -0.025em;
  color: #FFFFFF;
}
.hero p {
  position: relative; z-index: 1;
  max-width: 600px; margin: 0 0 1.2rem 0;
  color: var(--muted); font-size: 1rem; line-height: 1.6;
}
.chips { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip {
  border: 1px solid var(--line);
  background: rgba(15,22,40,0.85);
  color: var(--text);
  border-radius: 8px;
  padding: 0.28rem 0.7rem;
  font-size: 0.82rem; font-weight: 600;
}
.chip { display: inline-flex; align-items: center; gap: 0.45rem; }
.chip .e { font-size: 1.05rem; line-height: 1; }
/* Animated orbit: three rings with a dot travelling around each (decoration only) */
.rings { position: absolute; right: -70px; top: 50%; width: 340px; height: 340px;
  transform: translateY(-50%); pointer-events: none; }
.rings i { position: absolute; inset: 0; border-radius: 50%;
  border: 1px solid rgba(79,209,217,0.38);
  animation: orbit-spin 16s linear infinite; }
.rings i::after { content: ""; position: absolute; top: -5px; left: 50%;
  width: 10px; height: 10px; margin-left: -5px; border-radius: 50%;
  background: var(--accent); box-shadow: 0 0 14px 2px rgba(79,209,217,0.8); }
.rings i:nth-child(2) { inset: 48px; border-color: rgba(139,124,255,0.45);
  animation-duration: 24s; animation-direction: reverse; }
.rings i:nth-child(2)::after { background: var(--violet); box-shadow: 0 0 14px 2px rgba(139,124,255,0.85); }
.rings i:nth-child(3) { inset: 100px; border-color: rgba(79,209,217,0.3);
  animation-duration: 10s; }
.rings i:nth-child(3)::after { width: 8px; height: 8px; margin-left: -4px; top: -4px; }
.rings b { position: absolute; left: 50%; top: 50%; width: 14px; height: 14px;
  margin: -7px 0 0 -7px; border-radius: 50%; background: var(--accent);
  box-shadow: 0 0 24px 6px rgba(79,209,217,0.45); animation: orbit-pulse 3s ease-in-out infinite; }
@keyframes orbit-spin { to { transform: rotate(360deg); } }
@keyframes orbit-pulse { 0%,100% { opacity: 0.55; transform: scale(0.85); } 50% { opacity: 1; transform: scale(1.15); } }
@media (max-width: 700px) { .rings { opacity: 0.35; right: -170px; } .hero { padding: 1.4rem 1.2rem; } }

/* ---------- Tabs ---------- */
[data-baseweb="tab-list"] { gap: 0.5rem !important; border-bottom: 1px solid var(--line); }
button[role="tab"], button[data-baseweb="tab"] {
  padding: 0.75rem 1.2rem !important; margin-right: 0.25rem;
  border-radius: 8px 8px 0 0; color: var(--muted); background: transparent;
  height: auto !important;
}
button[role="tab"] p, button[data-baseweb="tab"] p {
  font-size: 1rem !important; font-weight: 600 !important; letter-spacing: -0.005em;
}
button[role="tab"] [data-testid="stIconMaterial"], button[data-baseweb="tab"] [data-testid="stIconMaterial"] {
  font-size: 1.35rem !important; margin-right: 0.45rem; vertical-align: middle;
}
button[role="tab"]:hover, button[data-baseweb="tab"]:hover { color: var(--text); background: rgba(255,255,255,0.04); }
button[role="tab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] { color: var(--accent); }
[data-baseweb="tab-highlight"] { background: var(--accent) !important; height: 2px !important; }
[data-baseweb="tab-border"] { background: var(--line) !important; }

/* ---------- Chat ---------- */
[data-testid="stChatMessage"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem 1.1rem;
  margin-bottom: 0.7rem;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) { border-left: 3px solid var(--accent); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--panel-2); border-left: 3px solid var(--violet);
}
[data-testid="stChatInput"] > div {
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
}
[data-testid="stChatInput"] > div:focus-within {
  border-color: var(--accent); box-shadow: 0 0 0 3px rgba(79,209,217,0.18);
}
/* Remove the second, inner outline so the box has a single border */
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] textarea {
  border: none !important; box-shadow: none !important;
  background: transparent !important; outline: none !important;
}

/* ---------- Buttons ---------- */
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"], [data-testid="stLinkButton"] a {
  min-height: 2.75rem; padding: 0.5rem 1.15rem;
  border-radius: 12px; font-weight: 600; font-size: 0.95rem; letter-spacing: 0.005em;
  transition: transform .12s ease, border-color .15s ease, background .15s ease, box-shadow .15s ease;
}
[data-testid="stBaseButton-secondary"], [data-testid="stLinkButton"] a {
  border: 1px solid #33426B;
  background: linear-gradient(180deg, #162040 0%, #0F1730 100%);
  color: var(--text);
  box-shadow: 0 1px 0 rgba(255,255,255,0.05) inset, 0 2px 6px rgba(0,0,0,0.25);
}
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stLinkButton"] a:hover {
  border-color: var(--accent); color: #fff; transform: translateY(-1px);
  background: linear-gradient(180deg, #1B2850 0%, #131D3B 100%);
  box-shadow: 0 6px 16px rgba(79,209,217,0.14);
}
[data-testid="stBaseButton-primary"] {
  border: 1px solid rgba(255,255,255,0.14);
  background: linear-gradient(135deg, #4FD1D9 0%, #5B9BF0 100%);
  color: #04202A; font-weight: 700;
  box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset, 0 6px 18px rgba(79,209,217,0.22);
}
[data-testid="stBaseButton-primary"]:hover {
  color: #04202A; transform: translateY(-1px); filter: brightness(1.06);
  box-shadow: 0 1px 0 rgba(255,255,255,0.4) inset, 0 10px 26px rgba(79,209,217,0.34);
}
[data-testid="stBaseButton-secondary"]:active, [data-testid="stBaseButton-primary"]:active {
  transform: translateY(0); filter: brightness(0.96);
}
[data-testid="stBaseButton-secondary"]:focus-visible, [data-testid="stBaseButton-primary"]:focus-visible,
[data-testid="stLinkButton"] a:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }
[data-testid="stBaseButton-secondary"] p, [data-testid="stBaseButton-primary"] p { font-weight: inherit; }

/* ---------- Inputs ---------- */
[data-testid="stNumberInput"] input, [data-testid="stTextInput"] input, textarea {
  background: var(--panel) !important; color: var(--text) !important; border-radius: 10px !important;
}
[data-testid="stNumberInput"] > div > div, [data-testid="stTextInput"] > div > div,
[data-testid="stTextArea"] > div > div, [data-baseweb="select"] > div { border-color: var(--line) !important; }
[data-baseweb="select"] > div { background: var(--panel) !important; border-radius: 10px !important; }
textarea:focus, [data-testid="stNumberInput"] input:focus, [data-testid="stTextInput"] input:focus {
  box-shadow: 0 0 0 3px rgba(79,209,217,0.18) !important;
}
label p { font-weight: 600; color: var(--text); }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0B1226 0%, #080D1C 100%);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] h2 { font-size: 1.05rem !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #B8C3E3; }
[data-testid="stFileUploaderDropzone"] {
  background: var(--panel); border: 1px dashed #4A5A8A; border-radius: var(--radius);
}
[data-testid="stExpander"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
}

/* ---------- Alerts, progress, footer ---------- */
[data-testid="stAlert"] { border-radius: var(--radius); border: 1px solid var(--line); }
[data-testid="stProgress"] > div > div > div > div { background: var(--accent); }
hr { border-color: var(--line) !important; }
[data-testid="stCaptionContainer"] { color: var(--muted); }
code { color: #CFF5F8; }

/* ---------- Spacing and readability ---------- */
html { font-size: 17px; }
.stApp { line-height: 1.65; }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; }
.block-container [data-testid="stVerticalBlock"] { gap: 1.15rem; }
[data-testid="stMarkdownContainer"] p { line-height: 1.7; margin-bottom: 0.8rem; }
[data-testid="stMarkdownContainer"] li { line-height: 1.7; margin: 0.3rem 0; }
h2 { margin-top: 0.4rem !important; margin-bottom: 0.9rem !important; padding: 0.2rem 0 !important; }
h3 { margin-top: 1.4rem !important; margin-bottom: 0.7rem !important; padding: 0.2rem 0 !important; }
label p { margin-bottom: 0.3rem; }

.hero { padding: 2.4rem 2.6rem 2.2rem; margin-bottom: 2rem; }
.hero p { line-height: 1.75; margin-bottom: 1.5rem; }
.chips { gap: 0.65rem; }
.chip { padding: 0.4rem 0.85rem; }

[data-baseweb="tab-list"] { margin-bottom: 1.4rem; }
button[role="tab"], button[data-baseweb="tab"] {
  padding: 0.8rem 0.95rem !important; margin-right: 0.1rem; white-space: nowrap; flex-shrink: 0;
}
button[role="tab"] p, button[data-baseweb="tab"] p { white-space: nowrap; }
[data-baseweb="tab-list"] { gap: 0.15rem !important; }

[data-testid="stChatMessage"] { padding: 1.2rem 1.5rem; margin-bottom: 1.1rem; gap: 1rem; }
[data-testid="stChatMessage"] p { line-height: 1.75; }
[data-testid="stChatInput"] { margin-top: 0.6rem; }

[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding: 1.8rem 1.3rem 2rem; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 1.1rem; }
[data-testid="stSidebar"] h2 { margin-bottom: 0.4rem !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { line-height: 1.6; }
[data-testid="stExpander"] summary { padding: 0.8rem 1rem; }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] { padding: 0.4rem 1.1rem 1.1rem; }
[data-testid="stExpander"] li { margin: 0.45rem 0; }
[data-testid="stFileUploaderDropzone"] { padding: 1.1rem; }
[data-testid="stAlert"] { padding: 0.9rem 1rem; }
[data-testid="stCaptionContainer"] p { line-height: 1.65; }

/* ---------- Wider sidebar so labels do not wrap (desktop only) ---------- */
@media (min-width: 900px) {
  [data-testid="stSidebar"][aria-expanded="true"] { min-width: 23rem !important; width: 23rem !important; }
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding: 1.6rem 1.15rem 2rem; }
[data-testid="stSidebar"] button { white-space: nowrap; }
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span { white-space: normal; }
[data-testid="stExpander"] summary p { font-weight: 600; font-size: 0.98rem; }
[data-testid="stSidebar"] h2 { font-size: 1.15rem !important; white-space: nowrap; }

/* ---------- Compact layout for mid-size windows (six tabs must fit) ---------- */
@media (max-width: 1400px) {
  [data-testid="stSidebar"][aria-expanded="true"] { min-width: 19rem !important; width: 19rem !important; }
  button[role="tab"], button[data-baseweb="tab"] { padding: 0.7rem 0.55rem !important; }
  button[role="tab"] p, button[data-baseweb="tab"] p { font-size: 0.86rem !important; }
  .block-container { padding-left: 1.6rem; padding-right: 1.6rem; }
}
</style>
"""

_HERO = """
<div class="hero">
  <div class="rings" aria-hidden="true"><i></i><i></i><i></i><b></b></div>
  <h1>AI Universal Student Assistant</h1>
  <p>Ask questions, study from your own notes and PDFs, and solve numerical
  problems with exact results. It runs on your computer with a local model,
  so your documents stay with you.</p>
  <div class="chips">
    <span class="chip"><span class="e">💻</span>Runs locally</span>
    <span class="chip"><span class="e">📄</span>Reads PDF and Word files</span>
    <span class="chip"><span class="e">🧮</span>Exact calculator and formulas</span>
    <span class="chip"><span class="e">🌐</span>Optional web search</span>
    <span class="chip"><span class="e">✨</span>Optional Gemini</span>
  </div>
</div>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


_HERO_HOSTED_TEXT = (
    "Ask questions, study from your own notes and PDFs, and solve numerical\n"
    "  problems with exact results. This online demo answers with Gemini using\n"
    "  your own free key, and your documents stay private to your session."
)
_HERO_LOCAL_TEXT = (
    "Ask questions, study from your own notes and PDFs, and solve numerical\n"
    "  problems with exact results. It runs on your computer with a local model,\n"
    "  so your documents stay with you."
)


def render_hero(hosted=False):
    html = _HERO
    if hosted:
        html = html.replace(_HERO_LOCAL_TEXT, _HERO_HOSTED_TEXT)
        html = html.replace('<span class="e">💻</span>Runs locally', '<span class="e">🌐</span>Free online demo')
        html = html.replace('<span class="e">✨</span>Optional Gemini', '<span class="e">🔑</span>Your own Gemini key')
    st.markdown(html, unsafe_allow_html=True)
