"""Football pitches drawn as Plotly figures, using StatsBomb's 120 x 80 coordinates."""
import numpy as np
import plotly.graph_objects as go

from ui import style_figure

TURF = "#0c1712"
PITCH_LINE = "#5a7468"


def _line(x0, y0, x1, y1) -> dict:
    return dict(type="line", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=PITCH_LINE, width=1.4), layer="above")


def _box(x0, y0, x1, y1) -> dict:
    return dict(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=PITCH_LINE, width=1.4), layer="above")


def _circle(cx, cy, radius) -> dict:
    return dict(type="circle", x0=cx - radius, y0=cy - radius, x1=cx + radius, y1=cy + radius,
                line=dict(color=PITCH_LINE, width=1.4), layer="above")


def _arc(cx, cy, radius, start, end, swap=False):
    angles = np.radians(np.linspace(start, end, 40))
    a = cx + radius * np.cos(angles)
    b = cy + radius * np.sin(angles)
    return (b, a) if swap else (a, b)


def _arc_trace(x, y) -> go.Scatter:
    return go.Scatter(x=x, y=y, mode="lines", line=dict(color=PITCH_LINE, width=1.4),
                      hoverinfo="skip", showlegend=False)


def full_pitch(height: int = 500) -> go.Figure:
    """Horizontal pitch: the home side attacks right, the away side attacks left."""
    fig = go.Figure()
    shapes = [
        dict(type="rect", x0=0, y0=0, x1=120, y1=80, fillcolor=TURF, line=dict(color=PITCH_LINE, width=1.4), layer="below"),
        _line(60, 0, 60, 80), _circle(60, 40, 10),
        _box(0, 18, 18, 62), _box(102, 18, 120, 62),
        _box(0, 30, 6, 50), _box(114, 30, 120, 50),
        _box(-2, 36, 0, 44), _box(120, 36, 122, 44),
    ]
    fig.update_layout(shapes=shapes)
    fig.add_trace(_arc_trace(*_arc(12, 40, 10, -53, 53)))
    fig.add_trace(_arc_trace(*_arc(108, 40, 10, 127, 233)))
    fig.update_xaxes(range=[-4, 124], visible=False, constrain="domain")
    fig.update_yaxes(range=[82, -2], visible=False, scaleanchor="x", scaleratio=1)
    style_figure(fig, height, margin=dict(l=4, r=4, t=30, b=4))
    return fig


def half_pitch(height: int = 520) -> go.Figure:
    """Attacking half with the goal at the top. Plot x is pitch y, plot y is pitch x."""
    fig = go.Figure()
    shapes = [
        dict(type="rect", x0=0, y0=60, x1=80, y1=120, fillcolor=TURF, line=dict(color=PITCH_LINE, width=1.4), layer="below"),
        _box(18, 102, 62, 120), _box(30, 114, 50, 120), _box(36, 120, 44, 122),
    ]
    fig.update_layout(shapes=shapes)
    fig.add_trace(_arc_trace(*_arc(108, 40, 10, 127, 233, swap=True)))
    fig.add_trace(_arc_trace(*_arc(60, 40, 10, 0, 90, swap=True)))
    fig.add_trace(_arc_trace(*_arc(60, 40, 10, -90, 0, swap=True)))
    fig.add_trace(go.Scatter(x=[40], y=[108], mode="markers", marker=dict(size=4, color=PITCH_LINE),
                             hoverinfo="skip", showlegend=False))
    fig.update_xaxes(range=[-2, 82], visible=False, constrain="domain")
    fig.update_yaxes(range=[58, 124], visible=False, scaleanchor="x", scaleratio=1)
    style_figure(fig, height, margin=dict(l=4, r=4, t=4, b=4))
    return fig
