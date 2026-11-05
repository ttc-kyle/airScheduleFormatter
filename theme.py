"""Minimalist-ui styling for the Streamlit shell, mirroring the tokens in styles.css.

Selectors cover both the current Streamlit DOM (data-testid / role hooks) and the older
data-baseweb DOM, since the hosted Streamlit version may differ from the local one.
"""
import streamlit as st

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');

:root {
	--canvas: #FBFBFA;
	--surface: #FFFFFF;
	--bone: #F7F6F3;
	--line: #EAEAEA;
	--text: #2F3437;
	--ink: #111111;
	--muted: #787774;
	--red-bg: #FDEBEC;    --red-fg: #9F2F2D;
	--blue-bg: #E1F3FE;   --blue-fg: #1F6C9F;
	--green-bg: #EDF3EC;  --green-fg: #346538;
	--yellow-bg: #FBF3DB; --yellow-fg: #956400;
	--sans: 'Geist', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
	--serif: 'Newsreader', 'Instrument Serif', 'Lyon Text', Georgia, serif;
	--mono: 'Geist Mono', 'SF Mono', Consolas, monospace;
}

/* Streamlit chrome end users should not see: top bar (GitHub link, deploy, menu),
   footer / hosted-by badge, profile avatar. display:none so no space is reserved. */
header, footer,
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stFooter"], #MainMenu,
[data-testid="appCreatorAvatar"], [class^="_profile"],
[class*="viewerBadge"], [class*="_viewerBadge"] {
	display: none !important;
}

/* Canvas and type */
.stApp { background: var(--canvas); color: var(--text); font-family: var(--sans); }
.stApp :is(p, label, li, a, input, textarea, button, [data-baseweb="select"] div) {
	font-family: var(--sans) !important;
}
[data-testid="stMainBlockContainer"], .block-container {
	max-width: 1560px;
	padding: 16px clamp(16px, 3vw, 48px) 16px;
}
h1, h2, h3, h4 {
	font-family: var(--serif) !important;
	font-weight: 400 !important;
	color: var(--ink);
	letter-spacing: -0.02em;
	line-height: 1.1;
}
h1 { font-size: clamp(36px, 5vw, 52px) !important; letter-spacing: -0.03em; }
h3 { font-size: 26px !important; }
.stApp p, .stApp li { line-height: 1.6; }
hr { border-color: var(--line) !important; }

/* Tabs: flat, underline only */
[role="tablist"], [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid var(--line); }
[data-testid="stTab"], button[data-baseweb="tab"] { background: transparent; padding: 10px 0; }
[data-testid="stTab"] p, button[data-baseweb="tab"] p { color: var(--muted); font-size: 15px; font-weight: 500; }
[data-testid="stTab"][aria-selected="true"] p, button[data-baseweb="tab"][aria-selected="true"] p { color: var(--ink); }
[data-baseweb="tab-highlight"] { background-color: var(--ink) !important; height: 2px; }
[data-baseweb="tab-border"] { display: none; }

/* The email formatter fills the window below the tab bar, scrolling inside itself.
   Top padding 16 + tab bar ~56 + panel gap 16 + bottom padding 16 = ~104px of chrome. */
iframe[data-testid="stIFrame"] {
	height: max(560px, calc(100vh - 108px)) !important;
	border: 0;
}

/* Buttons */
.stButton > button {
	background: var(--ink);
	color: #FFFFFF;
	border: 1px solid var(--ink);
	border-radius: 6px;
	box-shadow: none;
	min-height: 2.5em;
	padding: 0.5em 1.1em;
	font-size: 14px;
	font-weight: 500;
	transition: background 150ms ease, transform 150ms ease;
}
.stButton > button p { color: #FFFFFF; }
.stButton > button:hover { background: #333333; border-color: #333333; color: #FFFFFF; }
.stButton > button:focus:not(:active) { background: var(--ink); border-color: var(--ink); color: #FFFFFF; outline: none; }
.stButton > button:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
.stButton > button:active { background: #333333; transform: scale(0.98); box-shadow: none; }

/* Inputs */
[data-testid="stTextAreaRootElement"], [data-testid="stTextInputRootElement"], [data-testid="stSelectbox"] [role="group"],
[data-baseweb="textarea"], [data-baseweb="input"], [data-baseweb="select"] > div {
	background: var(--surface);
	border: 1px solid var(--line);
	border-radius: 8px;
	box-shadow: none;
}
[data-testid="stTextAreaRootElement"] textarea, [data-testid="stTextInputRootElement"] input,
[data-baseweb="textarea"] textarea, [data-baseweb="input"] input { background: transparent; color: var(--text); }
[data-testid="stTextAreaRootElement"]:focus-within, [data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stSelectbox"] [role="group"]:focus-within,
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {
	border-color: var(--ink);
}
[data-testid="stWidgetLabel"] p { color: var(--text); font-size: 14px; }
[data-testid="stTooltipIcon"] { color: var(--muted); }

/* Status messages use the pastel palette */
[data-testid="stAlert"] { border: 1px solid var(--line); border-radius: 8px; }
[data-testid="stAlertContentWarning"] { color: var(--yellow-fg); }
[data-testid="stAlertContentInfo"] { color: var(--blue-fg); }
[data-testid="stAlertContentError"] { color: var(--red-fg); }
[data-testid="stAlertContentSuccess"] { color: var(--green-fg); }
div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) { background: var(--yellow-bg); }
div[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) { background: var(--blue-bg); }
div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) { background: var(--red-bg); }
div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) { background: var(--green-bg); }

/* Expanders */
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }
</style>
"""


def inject_theme():
	st.markdown(THEME_CSS, unsafe_allow_html=True)
