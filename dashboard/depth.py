"""The dashboard's 3D look: depth styles, mouse motion and solid-looking graphics."""
import math
import random

import streamlit as st
import streamlit.components.v1 as components

GOLD = "#f5c518"
AMBER = "#ff9f1c"
RED = "#ef4444"
GREEN = "#22c55e"

DEPTH_CSS = """
<style>
[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  left: -30%;
  right: -30%;
  bottom: -32vh;
  height: 72vh;
  background-image:
    linear-gradient(rgba(245, 197, 24, 0.11) 1px, transparent 1px),
    linear-gradient(90deg, rgba(245, 197, 24, 0.11) 1px, transparent 1px);
  background-size: 64px 64px;
  transform: perspective(520px) rotateX(66deg);
  -webkit-mask-image: linear-gradient(to top, #000 0%, transparent 78%);
  mask-image: linear-gradient(to top, #000 0%, transparent 78%);
  pointer-events: none;
  z-index: 0;
}
[data-testid="stMainBlockContainer"] { position: relative; z-index: 1; }

[class*="st-key-panel-"], .tile {
  transform: perspective(1100px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg)) translateZ(0);
  transition: transform 0.16s ease-out, box-shadow 0.2s ease-out;
  will-change: transform;
}
[class*="st-key-panel-"] {
  background: linear-gradient(150deg, rgba(38, 42, 60, 0.92) 0%, rgba(17, 19, 29, 0.94) 42%, rgba(9, 10, 16, 0.96) 100%);
  -webkit-backdrop-filter: blur(7px);
  backdrop-filter: blur(7px);
  border: 1px solid rgba(245, 197, 24, 0.2);
  border-top-color: rgba(255, 255, 255, 0.2);
  box-shadow:
    0 7px 0 -1px #05060a,
    0 22px 40px rgba(0, 0, 0, 0.68),
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    inset 0 -18px 34px rgba(245, 197, 24, 0.035);
}
[class*="st-key-panel-"]:hover {
  box-shadow:
    0 9px 0 -1px #05060a,
    0 32px 52px rgba(0, 0, 0, 0.78),
    0 0 26px rgba(245, 197, 24, 0.13),
    inset 0 1px 0 rgba(255, 255, 255, 0.14),
    inset 0 -18px 34px rgba(245, 197, 24, 0.05);
}
.tile {
  background: linear-gradient(150deg, #292d3f 0%, #141722 55%, #0c0e16 100%);
  border-color: #30354a;
  box-shadow:
    0 6px 0 -1px #05060a,
    0 16px 26px rgba(0, 0, 0, 0.62),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
.tile:hover { box-shadow: 0 8px 0 -1px #05060a, 0 24px 34px rgba(0, 0, 0, 0.72), 0 0 20px rgba(245, 197, 24, 0.16); }
.tile .value { text-shadow: 0 1px 0 #b98f05, 0 2px 0 #8a6a03, 0 3px 0 #5e4802, 0 7px 12px rgba(0, 0, 0, 0.7); }
.row-item .figure { text-shadow: 0 1px 0 #8a6a03, 0 3px 6px rgba(0, 0, 0, 0.6); }
.page-head h1 { text-shadow: 0 1px 0 #9a9890, 0 2px 0 #6c6b64, 0 3px 0 #45443f, 0 9px 16px rgba(0, 0, 0, 0.75); }
.page-head h1 b { text-shadow: 0 1px 0 #c79b05, 0 2px 0 #967403, 0 3px 0 #624b02, 0 9px 16px rgba(0, 0, 0, 0.75); }
.panel-title::before { box-shadow: 0 0 9px rgba(245, 197, 24, 0.75); }

.scoreboard {
  background: linear-gradient(150deg, #2a2b35 0%, #171821 48%, #2c2410 100%);
  box-shadow: 0 8px 0 -1px #05060a, 0 26px 44px rgba(0, 0, 0, 0.72), inset 0 1px 0 rgba(255, 255, 255, 0.14);
}
.scoreboard .score { text-shadow: 0 1px 0 #bdbdbd, 0 2px 0 #8d8d8d, 0 3px 0 #5e5e5e, 0 4px 0 #3a3a3a, 0 10px 18px rgba(0, 0, 0, 0.8); }
.scoreboard .team { text-shadow: 0 2px 0 rgba(0, 0, 0, 0.55), 0 7px 12px rgba(0, 0, 0, 0.6); }

.dial .lit { filter: drop-shadow(0 0 5px rgba(245, 197, 24, 0.5)); }
.dial .red-glow { filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.62)); }

.step { box-shadow: 0 5px 0 -1px #05060a, 0 12px 20px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.09); }

[data-testid="stPageLink"] a {
  background: linear-gradient(180deg, #ffe067 0%, #f5c518 52%, #d3a40c 100%);
  box-shadow: 0 4px 0 #8a6a03, 0 9px 14px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.55);
  transition: transform 0.08s ease-out, box-shadow 0.08s ease-out;
}
[data-testid="stPageLink"] a:active { transform: translateY(3px); box-shadow: 0 1px 0 #8a6a03, 0 3px 6px rgba(0, 0, 0, 0.5); }
[data-testid="stButton"] button {
  background: linear-gradient(180deg, #2c3043 0%, #171a25 100%);
  border: 1px solid #3a3f55;
  box-shadow: 0 4px 0 #05060a, 0 9px 14px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.12);
  transition: transform 0.08s ease-out, box-shadow 0.08s ease-out;
}
[data-testid="stButton"] button:active { transform: translateY(3px); box-shadow: 0 1px 0 #05060a; }
[data-testid="stHeader"] a[aria-current="page"] {
  box-shadow: 0 3px 0 #8a6a03, 0 8px 14px rgba(245, 197, 24, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.hero {
  box-shadow: 0 9px 0 -1px #05060a, 0 30px 54px rgba(0, 0, 0, 0.8), 0 0 34px rgba(245, 197, 24, 0.12);
  background: #04050a;
}
.hero svg {
  transform: perspective(1400px) rotateX(calc(var(--my, 0) * -2.4deg)) rotateY(calc(var(--mx, 0) * 3.2deg)) scale(1.07);
  transition: transform 0.2s ease-out;
}
.hero .layer-far { transform: translate(calc(var(--mx, 0) * 5px), calc(var(--my, 0) * 2px)); }
.hero .layer-upper { transform: translate(calc(var(--mx, 0) * -7px), calc(var(--my, 0) * -3px)); }
.hero .layer-lower { transform: translate(calc(var(--mx, 0) * -14px), calc(var(--my, 0) * -6px)); }
.hero .layer-pitch { transform: translate(calc(var(--mx, 0) * -24px), calc(var(--my, 0) * -10px)); }
.hero .layer-lights { transform: translate(calc(var(--mx, 0) * -32px), calc(var(--my, 0) * -9px)); }
.hero [class^="layer-"] { transition: transform 0.2s ease-out; }
.hero-text {
  transform: translate(calc(var(--mx, 0) * 14px), calc(var(--my, 0) * 7px));
  transition: transform 0.2s ease-out;
}
.hero-title { text-shadow: 0 1px 0 #cfcfcf, 0 2px 0 #9b9b9b, 0 3px 0 #666, 0 4px 0 #3b3b3b, 0 12px 22px #000; }
.hero-title b { text-shadow: 0 1px 0 #cda006, 0 2px 0 #a17d04, 0 3px 0 #6e5502, 0 4px 0 #453501, 0 12px 22px #000; }

.hero .beam {
  transform-box: fill-box;
  transform-origin: 50% 0;
  animation: xg-sway 8s ease-in-out infinite alternate;
}
.hero .beam.b2 { animation-duration: 10s; animation-delay: -3s; }
.hero .beam.b3 { animation-duration: 7s; animation-delay: -5s; }
.hero .beam.b4 { animation-duration: 11s; animation-delay: -2s; }
@keyframes xg-sway { from { transform: rotate(-3.6deg); } to { transform: rotate(3.6deg); } }

.hero .ball { animation: xg-bounce 1.5s cubic-bezier(0.42, 0, 0.58, 1) infinite alternate; }
.hero .ball-shadow { transform-box: fill-box; transform-origin: center; animation: xg-shadow 1.5s cubic-bezier(0.42, 0, 0.58, 1) infinite alternate; }
@keyframes xg-bounce { from { transform: translateY(0); } to { transform: translateY(-34px); } }
@keyframes xg-shadow { from { transform: scale(1); opacity: 0.55; } to { transform: scale(0.55); opacity: 0.22; } }

.hero .flash { opacity: 0; animation: xg-flash 4.5s linear infinite; }
.hero .flash.f1 { animation-delay: -0.6s; }
.hero .flash.f2 { animation-delay: -1.5s; }
.hero .flash.f3 { animation-delay: -2.2s; }
.hero .flash.f4 { animation-delay: -3.1s; }
.hero .flash.f5 { animation-delay: -3.9s; }
@keyframes xg-flash { 0%, 91%, 100% { opacity: 0; } 94% { opacity: 1; } 97% { opacity: 0.2; } }

iframe[height="0"] { position: absolute; }
[data-testid="stElementContainer"]:has(> iframe[height="0"]),
[data-testid="stElementContainer"]:has(iframe[height="0"]) { position: absolute; height: 0; }

@media (prefers-reduced-motion: reduce) {
  .hero .beam, .hero .ball, .hero .ball-shadow, .hero .flash { animation: none; }
  [class*="st-key-panel-"], .tile, .hero svg, .hero-text, .hero [class^="layer-"] { transition: none; }
}
</style>
"""

# Runs once in the main page, so the tilt keeps working as pages change
MOTION_SCRIPT = """
<script>
(function () {
  var page = window.parent.document;
  if (page.getElementById("xg-motion")) { return; }
  var script = page.createElement("script");
  script.id = "xg-motion";
  script.textContent = "(" + function () {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { return; }
    var MAX_TILT = 3;
    var active = null;
    var CARD = '[class*="st-key-panel-"], .tile';
    var FIXED = '[class*="-filters"], [class*="st-key-panel-pick-the-spot"], [class*="st-key-panel-set-the-scene"]';
    function canTilt(card) { return !card.matches(FIXED) && !card.querySelector("canvas"); }
    function reset() {
      if (active) { active.style.removeProperty("--rx"); active.style.removeProperty("--ry"); active = null; }
    }
    document.addEventListener("mousemove", function (event) {
      if (!event.target.closest) { return; }
      var hero = event.target.closest(".hero");
      if (hero) {
        var box = hero.getBoundingClientRect();
        hero.style.setProperty("--mx", (((event.clientX - box.left) / box.width) * 2 - 1).toFixed(3));
        hero.style.setProperty("--my", (((event.clientY - box.top) / box.height) * 2 - 1).toFixed(3));
      }
      var card = event.target.closest(CARD);
      if (card !== active) { reset(); }
      if (card && canTilt(card)) {
        var area = card.getBoundingClientRect();
        var across = (event.clientX - area.left) / area.width - 0.5;
        var down = (event.clientY - area.top) / area.height - 0.5;
        card.style.setProperty("--rx", (-down * 2 * MAX_TILT).toFixed(2) + "deg");
        card.style.setProperty("--ry", (across * 2 * MAX_TILT).toFixed(2) + "deg");
        active = card;
      }
    }, { passive: true });
    document.addEventListener("mouseleave", reset);
  } + ")();";
  page.head.appendChild(script);
})();
</script>
"""


def install() -> None:
    """Add the depth styles and start the mouse motion."""
    st.html(DEPTH_CSS)
    components.html(MOTION_SCRIPT, height=0)


def _point(cx: float, cy: float, radius: float, degrees: float) -> tuple[float, float]:
    angle = math.radians(degrees)
    return cx + radius * math.cos(angle), cy - radius * math.sin(angle)


def _arc(cx: float, cy: float, radius: float, start: float, end: float, color: str, width: float,
         opacity: float = 1.0) -> str:
    x1, y1 = _point(cx, cy, radius, start)
    x2, y2 = _point(cx, cy, radius, end)
    return (f'<path d="M{x1:.1f} {y1:.1f} A{radius} {radius} 0 0 1 {x2:.1f} {y2:.1f}" '
            f'stroke="{color}" stroke-width="{width}" stroke-opacity="{opacity}" fill="none"/>')


def _segment_color(position: float) -> str:
    if position < 0.25:
        return RED
    if position < 0.5:
        return AMBER
    if position < 0.75:
        return GOLD
    return GREEN


def gauge_svg(fraction: float, value_text: str, safe_text: str) -> str:
    """A solid segmented dial with a metal hub, running from red through yellow to green."""
    fraction = max(0.0, min(1.0, fraction))
    cx, cy, radius = 120, 118, 92
    segments = 34
    under, lit, unlit = "", "", ""
    for index in range(segments):
        start = 180 - index * 180 / segments - 1.2
        end = 180 - (index + 1) * 180 / segments + 1.2
        position = (index + 0.5) / segments
        under += _arc(cx, cy + 6, radius, start, end, "#04050a", 21)
        if position <= fraction:
            color = _segment_color(position)
            lit += _arc(cx, cy, radius, start, end, color, 21)
            lit += _arc(cx, cy, radius - 7, start, end, "#000000", 7, 0.3)
            lit += _arc(cx, cy, radius + 8, start, end, "#ffffff", 3.5, 0.5)
        else:
            unlit += _arc(cx, cy, radius, start, end, "#2b2f3d", 21)
            unlit += _arc(cx, cy, radius + 8, start, end, "#ffffff", 3, 0.07)
    font = "'Barlow Condensed','Segoe UI',sans-serif"
    return (
        f'<svg viewBox="0 0 240 142" role="img" aria-label="{safe_text}">'
        '<defs>'
        '<radialGradient id="xgHub" cx="42%" cy="26%" r="84%">'
        '<stop offset="0" stop-color="#3e4356"/><stop offset="0.55" stop-color="#171a25"/>'
        '<stop offset="1" stop-color="#07080d"/></radialGradient>'
        '<linearGradient id="xgRim" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#f1f1ec"/><stop offset="0.45" stop-color="#575b6b"/>'
        '<stop offset="1" stop-color="#c7a93d"/></linearGradient>'
        '</defs>'
        f'<g>{under}</g><g>{unlit}</g><g class="lit">{lit}</g>'
        f'<circle cx="{cx}" cy="{cy + 5}" r="72" fill="#030407"/>'
        f'<circle cx="{cx}" cy="{cy}" r="71" fill="url(#xgHub)" stroke="url(#xgRim)" stroke-width="2.6"/>'
        f'<text x="{cx}" y="{cy - 15}" text-anchor="middle" fill="#6e5502" font-size="39" '
        f'font-weight="700" font-family="{font}">{safe_text}</text>'
        f'<text x="{cx}" y="{cy - 18}" text-anchor="middle" fill="{GOLD}" font-size="39" '
        f'font-weight="700" font-family="{font}">{safe_text}</text>'
        '</svg>'
    )


def ring_svg(fraction: float, safe_text: str, uid: str) -> str:
    """A glossy red sphere inside a raised ring."""
    fraction = max(0.0, min(1.0, fraction))
    radius = 66
    circumference = 2 * math.pi * radius
    filled = circumference * fraction
    dash = f'stroke-dasharray="{filled:.1f} {circumference:.1f}" transform="rotate(-90 85 85)"'
    font = "'Barlow Condensed','Segoe UI',sans-serif"
    return (
        f'<svg viewBox="0 0 170 178" role="img" aria-label="{safe_text}">'
        f'<defs><radialGradient id="c{uid}" cx="40%" cy="30%" r="78%">'
        '<stop offset="0" stop-color="#d43a3f"/><stop offset="0.5" stop-color="#7f151c"/>'
        '<stop offset="1" stop-color="#2d060a"/></radialGradient>'
        f'<linearGradient id="g{uid}"><stop offset="0" stop-color="{AMBER}"/>'
        f'<stop offset="1" stop-color="{RED}"/></linearGradient></defs>'
        f'<circle cx="85" cy="92" r="{radius}" fill="none" stroke="#04050a" stroke-width="16"/>'
        f'<circle cx="85" cy="85" r="{radius}" fill="none" stroke="#3a1419" stroke-width="15"/>'
        f'<g class="red-glow"><circle cx="85" cy="85" r="{radius}" fill="none" stroke="url(#g{uid})" '
        f'stroke-width="15" stroke-linecap="round" {dash}/></g>'
        f'<circle cx="85" cy="85" r="{radius + 5}" fill="none" stroke="#ffffff" stroke-opacity="0.45" '
        f'stroke-width="2.5" stroke-linecap="round" stroke-dasharray="{filled * 1.075:.1f} {circumference * 1.075:.1f}" '
        'transform="rotate(-90 85 85)"/>'
        f'<circle cx="85" cy="90" r="52" fill="#030407"/>'
        f'<circle cx="85" cy="85" r="52" fill="url(#c{uid})"/>'
        '<ellipse cx="72" cy="61" rx="25" ry="12" fill="#ffffff" fill-opacity="0.22"/>'
        f'<text x="85" y="100" text-anchor="middle" fill="#280508" font-size="34" font-weight="700" '
        f'font-family="{font}">{safe_text}</text>'
        f'<text x="85" y="97" text-anchor="middle" fill="#ffffff" font-size="34" font-weight="700" '
        f'font-family="{font}">{safe_text}</text>'
        '</svg>'
    )


@st.cache_data
def stadium_svg() -> str:
    """A layered floodlit stadium, generated in code so the artwork belongs to this project."""
    rng = random.Random(7)
    upper, lower, flashes = [], [], []
    palette = ["#6d7490", "#9aa1bb", "#c8486a", "#d9b53a", "#4a78c8", "#e6e3da", "#3f4560"]
    for _ in range(1900):
        angle = rng.uniform(math.pi, math.pi * 2.0)
        band = rng.uniform(0.0, 1.0)
        x = 600 + (410 + band * 290) * math.cos(angle)
        y = 318 + (150 + band * 175) * math.sin(angle)
        dot = (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{1.1 + band * 0.9:.1f}" '
               f'fill="{rng.choice(palette)}" opacity="{0.4 + rng.random() * 0.55:.2f}"/>')
        (upper if band > 0.5 else lower).append(dot)
    for index in range(60):
        angle = rng.uniform(math.pi, math.pi * 2.0)
        band = rng.uniform(0.0, 1.0)
        x = 600 + (410 + band * 290) * math.cos(angle)
        y = 318 + (150 + band * 175) * math.sin(angle)
        flashes.append(f'<circle class="flash f{index % 6}" cx="{x:.0f}" cy="{y:.0f}" r="3.4" fill="#ffffff"/>')

    stripes = ""
    for index in range(0, 10, 2):
        top_left = 330 + index * 54
        bottom_left = 130 + index * 94
        stripes += (f'<polygon points="{top_left},214 {top_left + 54},214 '
                    f'{bottom_left + 94},420 {bottom_left},420" fill="#2fa83a" opacity="0.65"/>')

    beams, lamps = "", ""
    for number, x in enumerate((150, 370, 830, 1050), start=1):
        target = 600 + (x - 600) * 0.45
        beams += (f'<polygon class="beam b{number}" points="{x - 34},30 {x + 34},30 '
                  f'{target + 170},300 {target - 170},300" fill="url(#beam)"/>')
        lamps += (f'<circle cx="{x}" cy="26" r="56" fill="url(#glow)"/>'
                  f'<rect x="{x - 31}" y="17" width="62" height="17" rx="2" fill="#fff7d8"/>')

    return f"""
<svg viewBox="0 0 1200 420" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Floodlit football stadium">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#04050a"/><stop offset="1" stop-color="#101735"/></linearGradient>
    <linearGradient id="grass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c8a2c"/><stop offset="1" stop-color="#38c648"/></linearGradient>
    <linearGradient id="slab" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a5f09"/><stop offset="1" stop-color="#241b02"/></linearGradient>
    <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff5c4" stop-opacity="0.24"/><stop offset="1" stop-color="#fff5c4" stop-opacity="0"/></linearGradient>
    <radialGradient id="glow"><stop offset="0" stop-color="#fff4c0" stop-opacity="0.95"/><stop offset="1" stop-color="#fff4c0" stop-opacity="0"/></radialGradient>
    <radialGradient id="ballface" cx="36%" cy="30%" r="74%"><stop offset="0" stop-color="#ffffff"/><stop offset="0.65" stop-color="#d6d6d0"/><stop offset="1" stop-color="#6f6f6a"/></radialGradient>
    <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#07080c" stop-opacity="0.72"/><stop offset="0.3" stop-color="#07080c" stop-opacity="0"/></linearGradient>
  </defs>
  <rect width="1200" height="420" fill="url(#sky)"/>
  <g class="layer-far"><ellipse cx="600" cy="318" rx="720" ry="345" fill="#14182a"/></g>
  <g class="layer-upper">{''.join(upper)}{''.join(flashes[:30])}</g>
  <g class="layer-lower">
    <ellipse cx="600" cy="318" rx="560" ry="240" fill="#1b2036" fill-opacity="0.72"/>
    {''.join(lower)}{''.join(flashes[30:])}
    <ellipse cx="600" cy="326" rx="392" ry="135" fill="#04050a"/>
    <ellipse cx="600" cy="318" rx="392" ry="135" fill="#0c0f1c" stroke="#f5c518" stroke-width="3" stroke-dasharray="26 7"/>
    <rect x="470" y="150" width="82" height="24" rx="2" fill="#c8202c"/>
    <text x="511" y="167" text-anchor="middle" font-size="14" font-weight="700" fill="#fff" font-family="Segoe UI, sans-serif">xG</text>
    <rect x="648" y="150" width="82" height="24" rx="2" fill="#1f5fd0"/>
    <text x="689" y="167" text-anchor="middle" font-size="14" font-weight="700" fill="#fff" font-family="Segoe UI, sans-serif">SPARK</text>
  </g>
  <g class="layer-pitch">
    <polygon points="130,420 1070,420 1070,444 130,444" fill="url(#slab)"/>
    <polygon points="330,214 870,214 1070,420 130,420" fill="url(#grass)"/>
    {stripes}
    <g fill="none" stroke="#eef8ee" stroke-width="2.4" opacity="0.92">
      <polygon points="352,226 848,226 1012,404 188,404"/>
      <line x1="600" y1="226" x2="600" y2="404"/>
      <ellipse cx="600" cy="298" rx="82" ry="30"/>
      <polygon points="340,256 276,256 212,322 234,404 188,404 352,226"/>
      <polygon points="860,256 924,256 988,322 966,404 1012,404 848,226"/>
    </g>
    <ellipse class="ball-shadow" cx="600" cy="312" rx="17" ry="5.5" fill="#031006"/>
    <g class="ball">
      <circle cx="600" cy="296" r="14" fill="url(#ballface)"/>
      <path d="M600 289l6 4.5-2.3 7h-7.4l-2.3-7z" fill="#22232a"/>
    </g>
  </g>
  <g class="layer-lights">{beams}{lamps}</g>
  <rect width="1200" height="420" fill="url(#fade)"/>
</svg>
"""
