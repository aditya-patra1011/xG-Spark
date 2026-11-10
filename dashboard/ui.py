"""The dashboard's look: colours, global styles and reusable visual components."""
import html
import math
import random
import re
from contextlib import contextmanager

import plotly.graph_objects as go
import streamlit as st

BG = "#07080c"
PANEL = "#10121a"
PANEL_RAISED = "#161922"
LINE = "#262a35"
INK = "#f4f2ea"
INK_SECONDARY = "#b5b3a8"
MUTED = "#8b8a82"

GOLD = "#f5c518"
AMBER = "#ff9f1c"
RED = "#ef4444"
GREEN = "#22c55e"
SKY = "#0ea5e9"

GOLD_SCALE = [[0, "#1c1a0e"], [0.25, "#5c4a08"], [0.55, "#a8860e"], [0.8, "#f5c518"], [1, "#fff0a8"]]

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


def _point(cx: float, cy: float, radius: float, degrees: float) -> tuple[float, float]:
    angle = math.radians(degrees)
    return cx + radius * math.cos(angle), cy - radius * math.sin(angle)


def _segment_color(position: float) -> str:
    if position < 0.25:
        return RED
    if position < 0.5:
        return AMBER
    if position < 0.75:
        return GOLD
    return GREEN


def gauge_svg(fraction: float, value_text: str) -> str:
    """A segmented semicircle running from red through yellow to green."""
    fraction = max(0.0, min(1.0, fraction))
    cx, cy, radius = 120, 118, 92
    segments = 34
    arcs = ""
    for index in range(segments):
        start = 180 - index * 180 / segments - 1.2
        end = 180 - (index + 1) * 180 / segments + 1.2
        x1, y1 = _point(cx, cy, radius, start)
        x2, y2 = _point(cx, cy, radius, end)
        position = (index + 0.5) / segments
        color = _segment_color(position) if position <= fraction else "#262a35"
        arcs += (
            f'<path d="M{x1:.1f} {y1:.1f} A{radius} {radius} 0 0 1 {x2:.1f} {y2:.1f}" '
            f'stroke="{color}" stroke-width="21" fill="none"/>'
        )
    return (
        f'<svg viewBox="0 0 240 132" role="img" aria-label="{esc(value_text)}">'
        f'<circle cx="{cx}" cy="{cy}" r="71" fill="#0b0c12" stroke="#2b2f3b" stroke-width="1"/>'
        f"{arcs}"
        f'<text x="{cx}" y="{cy - 18}" text-anchor="middle" fill="{GOLD}" font-size="39" '
        f"font-weight=\"700\" font-family=\"'Barlow Condensed','Segoe UI',sans-serif\">{esc(value_text)}</text>"
        f"</svg>"
    )


def gauge(fraction: float, value_text: str, label: str, note: str = "") -> None:
    extra = f'<div class="note">{esc(note)}</div>' if note else ""
    _graphic(f'<div class="dial">{gauge_svg(fraction, value_text)}'
             f'<div class="label">{esc(label)}</div>{extra}</div>')


def ring(fraction: float, value_text: str, label: str, note: str = "") -> None:
    """A red dial with a dark red centre."""
    fraction = max(0.0, min(1.0, fraction))
    radius = 66
    circumference = 2 * math.pi * radius
    filled = circumference * fraction
    uid = re.sub(r"[^a-z0-9]", "", label.lower())
    extra = f'<div class="note">{esc(note)}</div>' if note else ""
    _graphic(
        f'<div class="dial"><svg viewBox="0 0 170 170" role="img" aria-label="{esc(value_text)}">'
        f'<defs><radialGradient id="c{uid}"><stop offset="0" stop-color="#8f1a20"/>'
        f'<stop offset="1" stop-color="#430a10"/></radialGradient>'
        f'<linearGradient id="g{uid}"><stop offset="0" stop-color="{AMBER}"/>'
        f'<stop offset="1" stop-color="{RED}"/></linearGradient></defs>'
        f'<circle cx="85" cy="85" r="{radius}" fill="none" stroke="#3a1419" stroke-width="15"/>'
        f'<circle cx="85" cy="85" r="{radius}" fill="none" stroke="url(#g{uid})" stroke-width="15" '
        f'stroke-linecap="round" stroke-dasharray="{filled:.1f} {circumference:.1f}" '
        f'transform="rotate(-90 85 85)"/>'
        f'<circle cx="85" cy="85" r="52" fill="url(#c{uid})"/>'
        f'<text x="85" y="97" text-anchor="middle" fill="#fff" font-size="34" font-weight="700" '
        f"font-family=\"'Barlow Condensed','Segoe UI',sans-serif\">{esc(value_text)}</text>"
        f'</svg><div class="label">{esc(label)}</div>{extra}</div>'
    )


@st.cache_data
def _stadium_svg() -> str:
    """A floodlit stadium, generated in code so the artwork belongs to this project."""
    rng = random.Random(7)
    crowd = []
    palette = ["#6d7490", "#9aa1bb", "#c8486a", "#d9b53a", "#4a78c8", "#e6e3da", "#3f4560"]
    for _ in range(1900):
        angle = rng.uniform(math.pi * 1.0, math.pi * 2.0)
        band = rng.uniform(0.0, 1.0)
        rx = 410 + band * 290
        ry = 150 + band * 175
        x = 600 + rx * math.cos(angle)
        y = 318 + ry * math.sin(angle)
        crowd.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{1.1 + band * 0.9:.1f}" '
            f'fill="{rng.choice(palette)}" opacity="{0.4 + rng.random() * 0.55:.2f}"/>'
        )

    stripes = ""
    for index in range(10):
        if index % 2 == 0:
            top_left = 330 + index * 54
            bottom_left = 130 + index * 94
            stripes += (
                f'<polygon points="{top_left},214 {top_left + 54},214 '
                f'{bottom_left + 94},420 {bottom_left},420" fill="#2fa83a" opacity="0.65"/>'
            )

    lights = ""
    for x in (150, 370, 830, 1050):
        lights += (
            f'<polygon points="{x - 34},30 {x + 34},30 {600 + (x - 600) * 0.45 + 170},300 '
            f'{600 + (x - 600) * 0.45 - 170},300" fill="url(#beam)"/>'
            f'<circle cx="{x}" cy="26" r="56" fill="url(#glow)"/>'
            f'<rect x="{x - 31}" y="17" width="62" height="17" rx="2" fill="#fff7d8"/>'
        )

    return f"""
<svg viewBox="0 0 1200 420" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Floodlit football stadium">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#04050a"/><stop offset="1" stop-color="#101735"/>
    </linearGradient>
    <linearGradient id="grass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1c8a2c"/><stop offset="1" stop-color="#38c648"/>
    </linearGradient>
    <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff5c4" stop-opacity="0.22"/><stop offset="1" stop-color="#fff5c4" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glow">
      <stop offset="0" stop-color="#fff4c0" stop-opacity="0.95"/><stop offset="1" stop-color="#fff4c0" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#07080c" stop-opacity="0.72"/><stop offset="0.3" stop-color="#07080c" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="420" fill="url(#sky)"/>
  <ellipse cx="600" cy="318" rx="720" ry="345" fill="#14182a"/>
  <ellipse cx="600" cy="318" rx="560" ry="240" fill="#1b2036"/>
  {''.join(crowd)}
  <ellipse cx="600" cy="318" rx="392" ry="135" fill="#0c0f1c" stroke="#f5c518" stroke-width="3" stroke-dasharray="26 7"/>
  <rect x="470" y="150" width="82" height="24" rx="2" fill="#c8202c"/>
  <text x="511" y="167" text-anchor="middle" font-size="14" font-weight="700" fill="#fff" font-family="Segoe UI, sans-serif">xG</text>
  <rect x="648" y="150" width="82" height="24" rx="2" fill="#1f5fd0"/>
  <text x="689" y="167" text-anchor="middle" font-size="14" font-weight="700" fill="#fff" font-family="Segoe UI, sans-serif">SPARK</text>
  <polygon points="330,214 870,214 1070,420 130,420" fill="url(#grass)"/>
  {stripes}
  <g fill="none" stroke="#eef8ee" stroke-width="2.4" opacity="0.92">
    <polygon points="352,226 848,226 1012,404 188,404"/>
    <line x1="600" y1="226" x2="600" y2="404"/>
    <ellipse cx="600" cy="298" rx="82" ry="30"/>
    <polygon points="340,256 276,256 212,322 234,404 188,404 352,226"/>
    <polygon points="860,256 924,256 988,322 966,404 1012,404 848,226"/>
  </g>
  {lights}
  <rect width="1200" height="420" fill="url(#fade)"/>
</svg>
"""


def hero(title: str, highlight: str, subtitle: str) -> None:
    _graphic(
        f'<div class="hero">{_stadium_svg()}<div class="hero-text">'
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
