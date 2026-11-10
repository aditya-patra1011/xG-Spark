"""The dashboard's look: colours, global styles and reusable visual components."""
import html
import re
from contextlib import contextmanager

import plotly.graph_objects as go
import streamlit as st

import depth
from depth import AMBER, GOLD, GREEN, RED  # noqa: F401

BG = "#07080c"
PANEL = "#10121a"
PANEL_RAISED = "#161922"
LINE = "#262a35"
INK = "#f4f2ea"
INK_SECONDARY = "#b5b3a8"
MUTED = "#8b8a82"

SKY = "#0ea5e9"

GOLD_SCALE = [[0, "#3f3208"], [0.3, "#8f6f09"], [0.6, "#d8ab0f"], [0.85, "#f5c518"], [1, "#fff3b5"]]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600&display=swap');

html, body, [class*="stApp"], .stMarkdown, button, input, select, textarea {
  font-family: 'Barlow', 'Segoe UI', sans-serif;
}
[data-testid="stAppViewContainer"] {
  background: radial-gradient(1200px 500px at 50% -120px, #171b2c 0%, #07080c 70%);
}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stDecoration"],
footer, #MainMenu, [data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"] {
  display: none !important;
}
[data-testid="stHeader"] {
  background: #07080cf2;
  border-bottom: 1px solid rgba(245, 197, 24, 0.28);
}
[data-testid="stMainBlockContainer"] {
  max-width: 1560px;
  padding: 4.6rem 1.6rem 2.4rem;
}
[data-testid="stHeader"] a, [data-testid="stHeader"] a span, [data-testid="stHeader"] a p {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif !important;
  font-size: 1.06rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
[data-testid="stHeader"] a[aria-current="page"], [data-testid="stHeader"] a[aria-current="page"] span,
[data-testid="stHeader"] a[aria-current="page"] p {
  color: #f5c518 !important;
}
[class*="st-key-panel-"] {
  background: linear-gradient(180deg, #141721 0%, #0e1017 100%);
  border: 1px solid rgba(245, 197, 24, 0.16);
  border-radius: 10px;
  padding: 14px 16px 12px;
}
.panel-title {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  font-size: 1.12rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #f4f2ea;
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 2px;
}
.panel-title::before {
  content: "";
  width: 4px;
  height: 15px;
  border-radius: 2px;
  background: #f5c518;
}
.page-head { margin: 2px 0 14px; }
.page-head h1 {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  font-size: 2.5rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  line-height: 1.05;
  margin: 0;
  padding: 0;
  color: #f4f2ea;
}
.page-head h1 b { color: #f5c518; font-weight: 700; }
.page-head p { color: #b5b3a8; margin: 3px 0 0; font-size: 1.02rem; }

.tiles { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
.tile {
  background: linear-gradient(180deg, #171a24, #10121a);
  border: 1px solid #262a35;
  border-top: 2px solid #f5c518;
  border-radius: 8px;
  padding: 11px 14px 9px;
}
.tile .value {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  font-size: 2.15rem;
  font-weight: 700;
  line-height: 1.08;
  color: #f5c518;
  font-variant-numeric: tabular-nums;
}
.tile .label {
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #b5b3a8;
}
.tile .note { font-size: 0.8rem; color: #8b8a82; }

.dial { text-align: center; padding-bottom: 12px; }
.dial svg { width: 100%; max-width: 240px; height: auto; display: block; margin: 0 auto; }
.dial .label {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  font-size: 1.04rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #f4f2ea;
  margin-top: 1px;
}
.dial .note { font-size: 0.82rem; color: #b5b3a8; line-height: 1.25; }

.rows { display: flex; flex-direction: column; }
.row-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
  padding: 7px 0;
  border-bottom: 1px solid #262a35;
}
.row-item:last-child { border-bottom: none; }
.row-item .main { color: #f4f2ea; font-size: 0.96rem; line-height: 1.2; }
.row-item .sub { color: #8b8a82; font-size: 0.8rem; line-height: 1.2; margin-top: 1px; }
.row-item .figure {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  color: #f5c518;
  font-size: 1.3rem;
  font-weight: 700;
  white-space: nowrap;
}

.hero { position: relative; border-radius: 10px; overflow: hidden; border: 1px solid rgba(245, 197, 24, 0.22); }
.hero svg { display: block; width: 100%; height: 376px; }
.hero-text { position: absolute; left: 0; right: 0; top: 22px; text-align: center; }
.hero-title {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  font-size: 3.1rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #fff;
  line-height: 1;
  text-shadow: 0 2px 14px #000;
}
.hero-title b { color: #f5c518; }
.hero-sub {
  color: #f4f2ea;
  margin: 6px 0 0;
  font-size: 1.05rem;
  letter-spacing: 0.05em;
  text-shadow: 0 1px 8px #000;
}

.scoreboard {
  background: linear-gradient(90deg, #15171f 0%, #24200f 50%, #15171f 100%);
  border: 1px solid rgba(245, 197, 24, 0.3);
  border-radius: 10px;
  padding: 14px 20px 13px;
  text-align: center;
}
.scoreboard .meta { color: #b5b3a8; font-size: 0.9rem; letter-spacing: 0.04em; }
.scoreboard .line {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 26px;
  align-items: center;
  margin: 3px 0 1px;
}
.scoreboard .team {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  font-size: 2.05rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  line-height: 1.05;
}
.scoreboard .team.home { text-align: right; color: #f5c518; }
.scoreboard .team.away { text-align: left; color: #38bdf8; }
.scoreboard .score {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  font-size: 3.6rem;
  font-weight: 700;
  line-height: 1;
  color: #fff;
}
.note-text { color: #8b8a82; font-size: 0.84rem; line-height: 1.35; }

.steps { display: flex; flex-wrap: wrap; gap: 8px; align-items: stretch; }
.step {
  flex: 1 1 120px;
  background: #171a24;
  border: 1px solid #262a35;
  border-left: 3px solid #f5c518;
  border-radius: 6px;
  padding: 8px 10px;
}
.step b {
  font-family: 'Barlow Condensed', 'Segoe UI', sans-serif;
  color: #f5c518;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.step span { display: block; color: #b5b3a8; font-size: 0.82rem; line-height: 1.25; }

[data-testid="stPageLink"] a {
  background: #f5c518;
  border-radius: 6px;
  justify-content: center;
}
[data-testid="stPageLink"] a span, [data-testid="stPageLink"] a p {
  color: #0b0b0b !important;
  font-weight: 600 !important;
}
[data-testid="stPageLink"] a:hover { background: #ffd84a; }
label, [data-testid="stWidgetLabel"] p {
  color: #b5b3a8 !important;
  font-size: 0.83rem !important;
  letter-spacing: 0.04em;
}
@media (max-width: 800px) {
  .hero svg { height: 260px; }
  .hero-title { font-size: 2.1rem; }
  .scoreboard .team { font-size: 1.3rem; }
  .scoreboard .score { font-size: 2.4rem; }
  .scoreboard .line { gap: 10px; }
}
</style>
"""


def setup() -> None:
    st.html(CSS)
    depth.install()


def _graphic(markup: str) -> None:
    """Render markup containing SVG, which st.html would strip out."""
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def esc(value) -> str:
    return html.escape(str(value))


@contextmanager
def panel(title: str | None = None, key: str | None = None):
    """A dark card with a gold-marked title; everything inside the block lands in it."""
    slug = re.sub(r"[^a-z0-9]+", "-", (key or title or "panel").lower()).strip("-")
    with st.container(key=f"panel-{slug}"):
        if title:
            st.html(f'<div class="panel-title">{esc(title)}</div>')
        yield


def page_head(title: str, highlight: str, subtitle: str) -> None:
    st.html(
        f'<div class="page-head"><h1>{esc(title)} <b>{esc(highlight)}</b></h1>'
        f"<p>{esc(subtitle)}</p></div>"
    )


def tiles(items: list[tuple]) -> None:
    """items: (label, value) or (label, value, note)."""
    cards = ""
    for item in items:
        note = f'<div class="note">{esc(item[2])}</div>' if len(item) > 2 else ""
        cards += (
            f'<div class="tile"><div class="value">{esc(item[1])}</div>'
            f'<div class="label">{esc(item[0])}</div>{note}</div>'
        )
    st.html(f'<div class="tiles">{cards}</div>')


def rows(items: list[tuple]) -> None:
    """items: (main text, small text, figure)."""
    body = ""
    for main, sub, figure in items:
        small = f'<div class="sub">{esc(sub)}</div>' if sub else ""
        body += (
            f'<div class="row-item"><div><div class="main">{esc(main)}</div>{small}</div>'
            f'<div class="figure">{esc(figure)}</div></div>'
        )
    st.html(f'<div class="rows">{body}</div>')


def gauge(fraction: float, value_text: str, label: str, note: str = "") -> None:
    extra = f'<div class="note">{esc(note)}</div>' if note else ""
    _graphic(f'<div class="dial">{depth.gauge_svg(fraction, value_text, esc(value_text))}'
             f'<div class="label">{esc(label)}</div>{extra}</div>')


def ring(fraction: float, value_text: str, label: str, note: str = "") -> None:
    """A glossy red dial."""
    uid = re.sub(r"[^a-z0-9]", "", label.lower())
    extra = f'<div class="note">{esc(note)}</div>' if note else ""
    _graphic(f'<div class="dial">{depth.ring_svg(fraction, esc(value_text), uid)}'
             f'<div class="label">{esc(label)}</div>{extra}</div>')


def hero(title: str, highlight: str, subtitle: str) -> None:
    _graphic(
        f'<div class="hero">{depth.stadium_svg()}<div class="hero-text">'
        f'<div class="hero-title">{esc(title)} <b>{esc(highlight)}</b></div>'
        f'<div class="hero-sub">{esc(subtitle)}</div></div></div>'
    )


def style_figure(fig: go.Figure, height: int, margin: dict | None = None) -> go.Figure:
    """Apply the dashboard's dark chart styling."""
    fig.update_layout(
        height=height,
        margin=margin or dict(l=48, r=14, t=12, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Barlow, Segoe UI, sans-serif", color=INK_SECONDARY, size=13),
        hoverlabel=dict(bgcolor="#1c1f2a", bordercolor=GOLD, font=dict(color=INK, size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)"),
        dragmode=False,
    )
    axis_style = dict(gridcolor=LINE, zerolinecolor=LINE, linecolor="#3b4050", tickcolor="#3b4050",
                      automargin=True, title_standoff=10)
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)
    return fig


def show(fig: go.Figure, **kwargs):
    config = {"displayModeBar": False, "scrollZoom": False}
    return st.plotly_chart(fig, use_container_width=True, theme=None, config=config, **kwargs)
