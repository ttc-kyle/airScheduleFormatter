"""Hosts the static HTML Email Formatter inside Streamlit as a client-side component.

The editor runs entirely in the browser, so draft text never reaches the Streamlit server.
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).parent
IFRAME_HEIGHT = 1050


def _stamp():
	"""Modified times of the source files; changing any of them invalidates the cached page."""
	return tuple((HERE / name).stat().st_mtime_ns for name in ('index.html', 'styles.css', 'app.js'))


@st.cache_data
def _build_page(stamp):
	html = (HERE / 'index.html').read_text(encoding='utf-8')
	css = (HERE / 'styles.css').read_text(encoding='utf-8')
	js = (HERE / 'app.js').read_text(encoding='utf-8')

	link_tag = '<link rel="stylesheet" href="styles.css">'
	script_tag = '<script src="app.js"></script>'
	for tag in (link_tag, script_tag, '<body>'):
		if tag not in html:
			raise RuntimeError(f"index.html no longer contains {tag!r}; update email_tab.py")
	if '</script>' in js:
		raise RuntimeError("app.js contains a literal </script>, which would end the inlined script early")

	html = html.replace(link_tag, f'<style>\n{css}\n</style>')
	html = html.replace(script_tag, f'<script>\n{js}\n</script>')
	return html.replace('<body>', '<body class="embedded">', 1)


def render_email_formatter():
	page = _build_page(_stamp())
	# components.v1.html is deprecated in favour of st.iframe; fall back for older hosted Streamlit versions.
	if hasattr(st, 'iframe'):
		st.iframe(page, height=IFRAME_HEIGHT)
	else:
		components.html(page, height=IFRAME_HEIGHT, scrolling=True)
