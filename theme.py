"""
Visual theme for the Streamlit app, matching the high-fidelity design:
cool off-white page, white cards, dark-grey sidebar, IBM Plex Sans / Mono,
and a single blue scale for charts (darker = more serious).
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------
PAGE = "#F3F4F1"
SURFACE = "#FFFFFF"
BORDER = "#E1E3DF"
INK = "#15181D"
INK_2 = "#2A2F36"
INK_MUTED = "#4A5059"
INK_FAINT = "#5B616A"
GRID = "#E6E8E4"
SIDEBAR = "#2B3038"
SIDEBAR_RAISED = "#3A414B"
SIDEBAR_TEXT = "#E8EAED"
SIDEBAR_MUTED = "#B4BAC1"

ACCENT = "#1C5CAB"   # primary blue (bars, primary buttons, first series)
ORANGE = "#EB6834"   # second series
GREEN = "#1BAF7A"    # third series
GOLD = "#EDA100"     # fourth series
SERIES = [ACCENT, ORANGE, GREEN, GOLD]
SEQ = ["#F4F8FD", "#DCE9F9", "#B7D3F6", "#86B6EF", "#5598E7", "#1C5CAB", "#0D366B"]  # light -> dark blue

FONT = "IBM Plex Sans, -apple-system, Segoe UI, sans-serif"
MONO = "IBM Plex Mono, SFMono-Regular, Menlo, monospace"


# ---------------------------------------------------------------------------
# Plotly template
# ---------------------------------------------------------------------------
def register_plotly_template():
    axis = dict(
        gridcolor=GRID, zerolinecolor="#C9CCC6", linecolor="#C9CCC6", showline=False,
        tickfont=dict(family=FONT, size=12, color=INK_MUTED),
        title=dict(font=dict(family=FONT, size=12, color=INK_MUTED)),
        automargin=True,
    )
    pio.templates["governance"] = go.layout.Template(
        layout=dict(
            font=dict(family=FONT, size=13, color=INK_2),
            title=dict(font=dict(family=FONT, size=16, color=INK), x=0, xanchor="left", pad=dict(l=4)),
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            colorway=SERIES,
            xaxis=axis,
            yaxis=axis,
            legend=dict(font=dict(size=12, color=INK_2), title=dict(font=dict(size=12))),
            hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER, font=dict(family=FONT, size=13, color=INK)),
            coloraxis=dict(colorscale=SEQ[1:], colorbar=dict(outlinewidth=0, tickfont=dict(family=MONO, size=11))),
            geo=dict(bgcolor=SURFACE, landcolor="#EEF0EC", lakecolor=SURFACE, showframe=False,
                     coastlinecolor="#C9CCC6", countrycolor=SURFACE),
            margin=dict(l=8, r=16, t=48, b=8),
            bargap=0.38,
        ),
        data=dict(
            bar=[go.Bar(marker=dict(line=dict(width=0)), textfont=dict(family=MONO, size=11, color=INK_2))],
            scatter=[go.Scatter(line=dict(width=2))],
            heatmap=[go.Heatmap(textfont=dict(family=MONO, size=12))],
        ),
    )
    pio.templates.default = "governance"


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

/* Fonts: everything except Streamlit's icon glyphs */
.stApp :is(p, li, label, input, textarea, select, button, h1, h2, h3, h4, h5, td, th, div, span, a):not([data-testid="stIconMaterial"]) {{
  font-family: {FONT};
}}
.stApp code, .stApp pre {{ font-family: {MONO}; }}
.stApp {{ background: {PAGE}; }}
.block-container {{ padding-top: 2rem; max-width: 1280px; }}

/* Page header */
.gov-eyebrow {{ font-family: {MONO} !important; font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
  color: {INK_FAINT}; margin: 0; }}
.gov-title {{ font-size: 30px; font-weight: 600; letter-spacing: -0.01em; color: {INK}; margin: 4px 0 4px 0; line-height: 1.2; }}
.gov-sub {{ font-size: 14px; color: {INK_MUTED}; margin: 0 0 8px 0; }}

/* Headings */
.stApp h2, .stApp h3 {{ font-weight: 600; color: {INK}; letter-spacing: -0.005em; }}

/* Metric cards */
[data-testid="stMetric"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 16px 18px; }}
[data-testid="stMetricLabel"] p {{ font-family: {MONO} !important; font-size: 11px !important; letter-spacing: .08em;
  text-transform: uppercase; color: {INK_FAINT} !important; }}
[data-testid="stMetricValue"] div {{ font-family: {MONO} !important; font-weight: 500; color: {INK}; }}

/* Charts and tables sit on white cards */
[data-testid="stPlotlyChart"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 6px 8px; }}
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; overflow: hidden; }}
[data-testid="stExpander"] details {{ background: {SURFACE}; border-color: {BORDER}; border-radius: 10px; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {BORDER}; flex-wrap: wrap; }}
.stTabs [data-baseweb="tab"] {{ font-size: 14px; padding: 10px 12px; }}
.stTabs [aria-selected="true"] {{ color: {ACCENT}; font-weight: 600; }}

/* Buttons */
.stButton button[kind="primary"], .stDownloadButton button {{ border-radius: 8px; }}

/* Sidebar (colours also set in .streamlit/config.toml; this is the fallback for older Streamlit) */
[data-testid="stSidebar"] {{ background-color: {SIDEBAR}; }}
[data-testid="stSidebar"] :is(p, label, span, h1, h2, h3, small, div) {{ color: {SIDEBAR_TEXT}; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ color: {SIDEBAR_MUTED} !important; }}
[data-testid="stSidebar"] h2 {{ font-family: {MONO} !important; font-size: 11px !important; font-weight: 500 !important;
  letter-spacing: .08em; text-transform: uppercase; color: {SIDEBAR_MUTED} !important; margin-top: 8px; }}
[data-testid="stSidebar"] hr {{ border-color: #3B424C; }}
.gov-brand {{ display: flex; align-items: center; gap: 10px; padding: 4px 0 14px 0; border-bottom: 1px solid #3B424C; margin-bottom: 8px; }}
.gov-brand-name {{ font-weight: 600; font-size: 15px; line-height: 1.2; color: {SIDEBAR_TEXT}; }}
.gov-brand-sub {{ font-size: 12px; color: {SIDEBAR_MUTED}; }}
.gov-side-foot {{ font-size: 12px; color: {SIDEBAR_MUTED}; line-height: 1.6; border-top: 1px solid #3B424C; padding-top: 12px; margin-top: 18px; }}
.gov-side-foot b {{ font-family: {MONO}; font-weight: 500; color: {SIDEBAR_TEXT}; }}
</style>
"""

SHIELD = (
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#86B6EF" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6l7-3z">'
    '</path><path d="M9 12l2 2 4-4"></path></svg>'
)


def apply():
    """Call once at the top of the app, after st.set_page_config."""
    register_plotly_template()
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar_brand():
    st.sidebar.markdown(
        f'<div class="gov-brand">{SHIELD}<div><div class="gov-brand-name">AI Governance</div>'
        f'<div class="gov-brand-sub">Incidents · Frameworks · Policy</div></div></div>',
        unsafe_allow_html=True,
    )


def sidebar_footer(lines):
    """lines: list of (label, value) pairs, e.g. data freshness."""
    body = "".join(f"<div>{label} <b>{value}</b></div>" for label, value in lines)
    st.sidebar.markdown(f'<div class="gov-side-foot">{body}</div>', unsafe_allow_html=True)


def page_header(eyebrow, title, subtitle):
    st.markdown(
        f'<p class="gov-eyebrow">{eyebrow}</p><div class="gov-title">{title}</div><p class="gov-sub">{subtitle}</p>',
        unsafe_allow_html=True,
    )
