"""Charts shared by more than one page."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pitch import half_pitch
from ui import GOLD, GOLD_SCALE, INK, MUTED, RED, style_figure

X_EDGES = np.arange(60, 125, 5)
Y_EDGES = np.arange(0, 85, 5)
MIN_CONVERSION_SHOTS = 10


def zone_heatmap(zones: pd.DataFrame, mode: str, height: int = 540) -> go.Figure:
    """Half-pitch heatmap of shots, conversion or average xG per zone."""
    grid = np.full((len(X_EDGES) - 1, len(Y_EDGES) - 1), np.nan)
    hover = np.empty(grid.shape, dtype=object)
    hover[:] = ""
    for row in zones.itertuples():
        i, j = int((row.zone_x - 60) / 5), int(row.zone_y / 5)
        hover[i, j] = (f"Shots: {row.shots:,}<br>Goals: {row.goals:,}"
                       f"<br>Conversion: {row.goals / row.shots:.1%}<br>Average xG: {row.xg:.3f}")
        if mode == "Shots":
            grid[i, j] = row.shots
        elif row.shots >= MIN_CONVERSION_SHOTS:
            grid[i, j] = row.goals / row.shots if mode == "Conversion" else row.xg

    fig = half_pitch(height)
    is_rate = mode != "Shots"
    fig.add_trace(go.Heatmap(
        x=Y_EDGES, y=X_EDGES, z=grid, text=hover, hovertemplate="%{text}<extra></extra>",
        colorscale=GOLD_SCALE, zmin=0, xgap=1.5, ygap=1.5, hoverongaps=False,
        colorbar=dict(thickness=11, len=0.72, outlinewidth=0, tickformat=".0%" if is_rate else ",",
                      tickfont=dict(color=INK), title=None),
    ))
    # Keep the pitch markings above the heatmap
    fig.data = (fig.data[-1],) + fig.data[:-1]
    return fig


def shot_dots(data: pd.DataFrame, height: int = 540, limit: int = 2500) -> go.Figure:
    """Half-pitch shot map: bubble size shows xG and gold stars are goals."""
    goals = data[data["is_goal"] == 1]
    misses = data[data["is_goal"] == 0]
    if len(misses) > max(limit - len(goals), 0):
        misses = misses.sample(max(limit - len(goals), 0), random_state=1)

    def text(frame: pd.DataFrame) -> list[str]:
        return [f"<b>{p}</b><br>{t}<br>{o}, xG {xg:.2f}" for p, t, o, xg in
                zip(frame["player"], frame["team"], frame["outcome"], frame["statsbomb_xg"])]

    fig = half_pitch(height)
    fig.add_trace(go.Scatter(
        x=misses["y"], y=misses["x"], mode="markers", name="No goal", text=text(misses),
        hovertemplate="%{text}<extra></extra>",
        marker=dict(size=5 + misses["statsbomb_xg"] * 22, color="rgba(170,176,190,0.42)",
                    line=dict(width=0)),
    ))
    fig.add_trace(go.Scatter(
        x=goals["y"], y=goals["x"], mode="markers", name="Goal", text=text(goals),
        hovertemplate="%{text}<extra></extra>",
        marker=dict(symbol="star", size=8 + goals["statsbomb_xg"] * 20, color=GOLD,
                    line=dict(width=0.6, color="#07080c")),
    ))
    fig.update_layout(legend=dict(y=1.0, yanchor="bottom", x=0))
    fig.update_layout(margin=dict(l=4, r=4, t=30, b=4))
    return fig


def diverging_bars(labels, values, height: int, value_format: str = "{:+.2f}") -> go.Figure:
    colors = [GOLD if value >= 0 else RED for value in values]
    fig = go.Figure(go.Bar(
        y=labels, x=values, orientation="h", marker=dict(color=colors, line=dict(width=0)), width=0.56,
        hovertemplate="%{y}: %{x:.2f}<extra></extra>",
        text=[value_format.format(v) for v in values], textposition="outside",
        textfont=dict(color=INK), cliponaxis=False,
    ))
    style_figure(fig, height, margin=dict(l=8, r=46, t=8, b=30))
    fig.update_yaxes(automargin=True, showgrid=False, autorange="reversed", tickfont=dict(color=INK))
    span = max(max(values) - min(min(values), 0), 0.5)
    fig.update_xaxes(zerolinecolor=MUTED, zerolinewidth=1,
                     range=[min(min(values), 0) - span * 0.32, max(max(values), 0) + span * 0.32])
    return fig
