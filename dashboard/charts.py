"""Charts shared by more than one page."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pitch3d import add_shot_columns, add_zone_columns, scene
from ui import GOLD, INK, MUTED, RED, style_figure

MIN_CONVERSION_SHOTS = 10


def zone_heatmap(zones: pd.DataFrame, mode: str, height: int = 540) -> go.Figure:
    """A 3D half pitch with one column per zone, for shots, conversion or average xG."""
    table = zones.copy()
    if mode == "Shots":
        table["value"] = table["shots"].astype(float)
    else:
        table = table[table["shots"] >= MIN_CONVERSION_SHOTS]
        table["value"] = table["goals"] / table["shots"] if mode == "Conversion" else table["xg"]

    hover = [f"Shots: {row.shots:,}<br>Goals: {row.goals:,}"
             f"<br>Conversion: {row.goals / row.shots:.1%}<br>Average xG: {row.xg:.3f}"
             for row in table.itertuples()]
    fig = scene(False, height)
    if not table.empty:
        add_zone_columns(fig, table, table["value"].to_numpy(), hover, is_rate=mode != "Shots")
    return fig


def shot_dots(data: pd.DataFrame, height: int = 540, limit: int = 2500) -> go.Figure:
    """A 3D half pitch where each shot is a column: taller for better chances, gold for goals."""
    goals = data[data["is_goal"] == 1]
    misses = data[data["is_goal"] == 0]
    if len(misses) > max(limit - len(goals), 0):
        misses = misses.sample(max(limit - len(goals), 0), random_state=1)

    fig = scene(False, height)
    # One colour for shots and one for goals, whichever team they belong to
    for frame, name in [(misses, "No goal"), (goals, "Goal")]:
        if not frame.empty:
            add_shot_columns(fig, frame, GOLD, name)
    for trace in fig.data:
        if trace.name == "No goal shot":
            trace.name = "No goal"
        elif trace.name == "Goal goal":
            trace.name = "Goal"
    fig.update_layout(legend=dict(y=1.0, yanchor="top", x=0))
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
