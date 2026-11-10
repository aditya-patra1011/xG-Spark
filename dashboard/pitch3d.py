"""Rotatable 3D pitches, glowing columns and the Shot Lab's flight path."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ui import GOLD, GOLD_SCALE, INK, style_figure

TURF = "#0d2317"
SLAB = "#3a2f08"
PITCH_LINE = "#b9d2c5"
COLUMN_LIGHT = dict(ambient=0.62, diffuse=0.75, specular=0.75, roughness=0.3, fresnel=0.5)
GOAL_HEIGHT = 2.67
MAX_COLUMN = 15.0
ZONE = 5.0
ZONE_GAP = 0.45


def _segments(items: list[tuple]) -> tuple[list, list, list]:
    """Join separate line pieces into one trace, with gaps between them."""
    xs, ys, zs = [], [], []
    for points in items:
        for x, y, z in points:
            xs.append(x)
            ys.append(y)
            zs.append(z)
        xs.append(None)
        ys.append(None)
        zs.append(None)
    return xs, ys, zs


def _box(x0, x1, y0, y1) -> list[tuple]:
    return [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y0, 0)]


def _circle(cx, cy, radius, start=0.0, end=360.0) -> list[tuple]:
    angles = np.radians(np.linspace(start, end, 48))
    return [(cx + radius * np.cos(a), cy + radius * np.sin(a), 0) for a in angles]


def _cuboid(x0, x1, y0, y1, z0, z1) -> tuple[list, list, list, list, list, list]:
    x = [x0, x1, x1, x0, x0, x1, x1, x0]
    y = [y0, y0, y1, y1, y0, y0, y1, y1]
    z = [z0, z0, z0, z0, z1, z1, z1, z1]
    i = [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3]
    j = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4]
    k = [2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7]
    return x, y, z, i, j, k


def _goal(fig: go.Figure, x: float, depth: float) -> None:
    """A goal frame with a net behind it."""
    frame = [[(x, 36, 0), (x, 36, GOAL_HEIGHT), (x, 44, GOAL_HEIGHT), (x, 44, 0)]]
    net = []
    for y in np.arange(36, 44.01, 1):
        net.append([(x, y, GOAL_HEIGHT), (x + depth, y, 0)])
    for fraction in np.linspace(0, 1, 5):
        net.append([(x + depth * fraction, 36, GOAL_HEIGHT * (1 - fraction)),
                    (x + depth * fraction, 44, GOAL_HEIGHT * (1 - fraction))])
    xs, ys, zs = _segments(net)
    fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", hoverinfo="skip", showlegend=False,
                               line=dict(color="rgba(240,240,235,0.34)", width=2)))
    xs, ys, zs = _segments(frame)
    fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", hoverinfo="skip", showlegend=False,
                               line=dict(color="#ffffff", width=7)))


def scene(full: bool, height: int, z_top: float = MAX_COLUMN + 2) -> go.Figure:
    """A dark pitch on a raised slab. Drag it to rotate."""
    x_start = 0.0 if full else 60.0
    fig = go.Figure()

    x, y, z, i, j, k = _cuboid(x_start, 120, 0, 80, -1.6, -0.06)
    fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=SLAB, flatshading=True, hoverinfo="skip",
                            lighting=dict(ambient=0.75, diffuse=0.6, specular=0.2)))
    fig.add_trace(go.Mesh3d(x=[x_start, 120, 120, x_start], y=[0, 0, 80, 80], z=[0, 0, 0, 0],
                            i=[0, 0], j=[1, 2], k=[2, 3], color=TURF, hoverinfo="skip",
                            lighting=dict(ambient=1, diffuse=0, specular=0)))

    lines = [_box(x_start, 120, 0, 80), _box(102, 120, 18, 62), _box(114, 120, 30, 50),
             _circle(108, 40, 10, 127, 233)]
    if full:
        lines += [[(60, 0, 0), (60, 80, 0)], _circle(60, 40, 10), _box(0, 18, 18, 62), _box(0, 6, 30, 50),
                  _circle(12, 40, 10, -53, 53)]
    else:
        lines += [_circle(60, 40, 10, -90, 90)]
    xs, ys, zs = _segments(lines)
    fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", hoverinfo="skip", showlegend=False,
                               line=dict(color=PITCH_LINE, width=3)))
    _goal(fig, 120, 2.4)
    if full:
        _goal(fig, 0, -2.4)

    hidden = dict(visible=False, showbackground=False, showgrid=False, zeroline=False, showspikes=False)
    if full:
        camera = dict(eye=dict(x=0.0, y=-0.98, z=0.62), center=dict(x=0, y=0.04, z=-0.16), up=dict(x=0, y=0, z=1))
        ratio = dict(x=1.5, y=1.0, z=0.42)
        x_range = [-5, 125]
    else:
        camera = dict(eye=dict(x=-0.86, y=0.0, z=0.56), center=dict(x=0.08, y=0, z=-0.18), up=dict(x=0, y=0, z=1))
        ratio = dict(x=0.8, y=1.05, z=0.5)
        x_range = [58, 125]
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=x_range, **hidden),
            yaxis=dict(range=[82, -2], **hidden),
            zaxis=dict(range=[-1.7, z_top], **hidden),
            aspectmode="manual",
            aspectratio=ratio,
            camera=camera,
            bgcolor="rgba(0,0,0,0)",
            dragmode="orbit",
        ),
        uirevision="keep",
    )
    style_figure(fig, height, margin=dict(l=0, r=0, t=26, b=0))
    return fig


def add_zone_columns(fig: go.Figure, zones: pd.DataFrame, values: np.ndarray, hover: list[str],
                     is_rate: bool) -> None:
    """Raise a lit column on each zone of the pitch, taller where the value is higher."""
    top = float(np.nanmax(values)) if len(values) else 1.0
    xs, ys, zs, i, j, k, intensity = [], [], [], [], [], [], []
    tip_x, tip_y, tip_z = [], [], []
    for zone_x, zone_y, value in zip(zones["zone_x"], zones["zone_y"], values):
        height = 0.25 + (value / top) * MAX_COLUMN
        x, y, z, a, b, c = _cuboid(zone_x + ZONE_GAP, zone_x + ZONE - ZONE_GAP,
                                   zone_y + ZONE_GAP, zone_y + ZONE - ZONE_GAP, 0, height)
        offset = len(xs)
        xs += x
        ys += y
        zs += z
        i += [v + offset for v in a]
        j += [v + offset for v in b]
        k += [v + offset for v in c]
        intensity += [value * 0.3] * 4 + [value] * 4
        tip_x.append(zone_x + ZONE / 2)
        tip_y.append(zone_y + ZONE / 2)
        tip_z.append(height)

    fig.add_trace(go.Mesh3d(
        x=xs, y=ys, z=zs, i=i, j=j, k=k, intensity=intensity, intensitymode="vertex",
        colorscale=GOLD_SCALE, cmin=0, cmax=top, flatshading=True, hoverinfo="skip",
        lighting=COLUMN_LIGHT, lightposition=dict(x=-400, y=200, z=900),
        colorbar=dict(thickness=11, len=0.66, outlinewidth=0, x=0.97,
                      tickformat=".0%" if is_rate else ",", tickfont=dict(color=INK)),
    ))
    fig.add_trace(go.Scatter3d(
        x=tip_x, y=tip_y, z=tip_z, mode="markers", showlegend=False, text=hover,
        hovertemplate="%{text}<extra></extra>",
        marker=dict(size=9, color="#000000", opacity=0.01, line=dict(width=0)),
    ))


def add_shot_columns(fig: go.Figure, frame: pd.DataFrame, color: str, name: str, *, x=None, y=None,
                     miss_color: str = "#6b7287") -> None:
    """Stand each shot up as a column: its height shows xG and goals glow."""
    x = frame["x"] if x is None else x
    y = frame["y"] if y is None else y
    heights = 1.4 + frame["statsbomb_xg"].to_numpy() * MAX_COLUMN
    text = [f"<b>{p}</b> {m}'<br>{o}, {b}<br>xG {v:.2f}" for p, m, o, b, v in
            zip(frame["player"], frame["minute"], frame["outcome"], frame["body_part"], frame["statsbomb_xg"])]

    for is_goal, label in [(False, f"{name} shot"), (True, f"{name} goal")]:
        mask = frame["is_goal"].to_numpy() == int(is_goal)
        if not mask.any():
            continue
        px, py, tops = np.asarray(x)[mask], np.asarray(y)[mask], heights[mask]
        words = [t for t, keep in zip(text, mask) if keep]
        xs, ys, zs = _segments([[(a, b, 0), (a, b, c)] for a, b, c in zip(px, py, tops)])
        if is_goal:
            fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", hoverinfo="skip", showlegend=False,
                                       line=dict(color=color, width=16), opacity=0.28))
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", hoverinfo="skip", showlegend=False,
                                   line=dict(color=color if is_goal else miss_color, width=7 if is_goal else 3)))
        fig.add_trace(go.Scatter3d(
            x=px, y=py, z=tops, mode="markers", name=label, text=words, showlegend=True,
            hovertemplate="%{text}<extra></extra>",
            marker=dict(size=7 if is_goal else 3.5, color=color if is_goal else miss_color,
                        symbol="diamond" if is_goal else "circle", line=dict(width=0)),
        ))


def flight_path(x: float, y: float, is_header: bool, chance: float, keeper: float, height: int = 430) -> go.Figure:
    """Animate an illustrative route for the ball from the shot to the goal."""
    fig = scene(False, height, z_top=11.0)
    target_y = float(np.clip(40 + (y - 40) * 0.08, 37.2, 42.8))
    target_z = 1.25
    start_z = 2.0 if is_header else 0.15
    distance = float(np.hypot(120 - x, 40 - y))
    peak = min(0.7 + distance * 0.17, 8.5)

    steps = np.linspace(0, 1, 31)  # every second point becomes an animation frame
    path_x = x + (120 - x) * steps
    path_y = y + (target_y - y) * steps
    path_z = start_z + (target_z - start_z) * steps + 4 * peak * steps * (1 - steps)

    fig.add_trace(go.Scatter3d(x=[x, 120, x], y=[y, 36, y], z=[0, 0, 0], mode="lines", hoverinfo="skip",
                               showlegend=False, line=dict(color="rgba(245,197,24,0.6)", width=3)))
    fig.add_trace(go.Scatter3d(x=[x, 120], y=[y, 44], z=[0, 0], mode="lines", hoverinfo="skip",
                               showlegend=False, line=dict(color="rgba(245,197,24,0.6)", width=3)))
    fig.add_trace(go.Scatter3d(x=path_x, y=path_y, z=np.zeros_like(path_z), mode="lines", hoverinfo="skip",
                               showlegend=False, line=dict(color="rgba(0,0,0,0.72)", width=6)))
    fig.add_trace(go.Scatter3d(x=path_x, y=path_y, z=path_z, mode="lines", hoverinfo="skip", showlegend=False,
                               line=dict(color=GOLD, width=13), opacity=0.25))
    fig.add_trace(go.Scatter3d(x=path_x, y=path_y, z=path_z, mode="lines", hoverinfo="skip", showlegend=False,
                               line=dict(color=GOLD, width=5)))

    keeper_x = 120 - keeper
    fig.add_trace(go.Scatter3d(x=[keeper_x, keeper_x], y=[40, 40], z=[0, 2.0], mode="lines+markers",
                               showlegend=False, text=["Goalkeeper"] * 2, hovertemplate="%{text}<extra></extra>",
                               line=dict(color="#0ea5e9", width=11), marker=dict(size=3, color="#0ea5e9")))

    fig.add_trace(go.Scatter3d(x=[x], y=[y], z=[0.1], mode="markers", hoverinfo="skip", showlegend=False,
                               marker=dict(size=7, color=GOLD)))
    fig.add_trace(go.Scatter3d(x=[x, 120], y=[y, 40], z=[3.2 + start_z, GOAL_HEIGHT + 1.6], mode="text",
                               text=["<b>SHOT</b>", "<b>GOAL</b>"], hoverinfo="skip", showlegend=False,
                               textfont=dict(color=INK, size=13)))

    ball_index = len(fig.data)
    fig.add_trace(go.Scatter3d(x=[x], y=[y], z=[start_z], mode="markers", showlegend=False,
                               hovertemplate=f"xG {chance:.1%}<extra></extra>",
                               marker=dict(size=10, color="#ffffff", line=dict(color=GOLD, width=3))))

    fig.frames = [
        go.Frame(data=[go.Scatter3d(x=[a], y=[b], z=[c])], traces=[ball_index], name=str(n))
        for n, (a, b, c) in enumerate(zip(path_x[::2], path_y[::2], path_z[::2]))
    ]
    fig.update_layout(updatemenus=[dict(
        type="buttons", direction="left", x=0.01, y=0.99, xanchor="left", yanchor="top", showactive=False,
        bgcolor=GOLD, bordercolor=GOLD, font=dict(color="#0b0b0b", size=13),
        buttons=[dict(label="  Shoot  ", method="animate", args=[None, dict(
            frame=dict(duration=38, redraw=True), transition=dict(duration=0),
            fromcurrent=False, mode="immediate",
        )])],
    )])
    return fig
