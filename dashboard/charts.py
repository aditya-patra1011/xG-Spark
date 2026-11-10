"""Charts shared by more than one page."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pitch import full_pitch, half_pitch
from pitch3d import add_shot_columns, add_zone_columns, scene
from ui import GOLD, GOLD_SCALE, INK, MUTED, RED, SKY, style_figure

MIN_CONVERSION_SHOTS = 10
MIN_LABEL_HEIGHT = 360
SHOT_LIMIT = 1500
MISS_COLOR = "rgba(176,184,204,0.72)"
SHOT_KEY = "Each circle is one shot, taken from that spot. A bigger circle is a better chance. Gold stars are goals."
X_EDGES = np.arange(60, 125, 5)
Y_EDGES = np.arange(0, 85, 5)
ZONE_TITLES = {"Shots": "Shots per zone", "Conversion": "Goals per shot", "Average xG": "Average xG"}


def view_3d(key: str) -> bool:
    """A switch between the clear flat map and the rotatable 3D pitch."""
    return st.toggle("3D view (drag to rotate)", key=key)


def _key_below(fig: go.Figure) -> None:
    fig.update_layout(margin=dict(b=34))
    fig.add_annotation(text=SHOT_KEY, xref="paper", yref="paper", x=0, y=0, yshift=-30,
                       xanchor="left", yanchor="bottom", showarrow=False,
                       font=dict(color=INK, size=12))


def _shot_text(frame: pd.DataFrame) -> list[str]:
    return [f"<b>{p}</b> ({t})<br>Minute {m}: {o}<br>{b}, xG {xg:.2f}, {d:.0f} units from goal"
            for p, t, m, o, b, xg, d in zip(frame["player"], frame["team"], frame["minute"], frame["outcome"],
                                            frame["body_part"], frame["statsbomb_xg"], frame["distance"])]


def _zone_label(mode: str, shots: int, value: float) -> str:
    if mode == "Shots":
        return f"{shots / 1000:.1f}k" if shots >= 1000 else f"{shots}"
    return f"{value:.0%}" if mode == "Conversion" else f"{value:.2f}"


def zone_heatmap(zones: pd.DataFrame, mode: str, height: int = 540, three_d: bool = False) -> go.Figure:
    """Attacking half split into zones, each coloured and labelled with its value."""
    table = zones.copy()
    if mode != "Shots":
        table = table[table["shots"] >= MIN_CONVERSION_SHOTS]
    if mode == "Shots":
        table["value"] = table["shots"].astype(float)
    elif mode == "Conversion":
        table["value"] = table["goals"] / table["shots"]
    else:
        table["value"] = table["xg"]

    hover = [f"Shots: {row.shots:,}<br>Goals: {row.goals:,}"
             f"<br>Conversion: {row.goals / row.shots:.1%}<br>Average xG: {row.xg:.3f}"
             for row in table.itertuples()]
    is_rate = mode == "Conversion"

    if three_d:
        fig = scene(False, height)
        if not table.empty:
            add_zone_columns(fig, table, table["value"].to_numpy(), hover, is_rate=is_rate or mode != "Shots")
        return fig

    grid = np.full((len(X_EDGES) - 1, len(Y_EDGES) - 1), np.nan)
    tips = np.full(grid.shape, "", dtype=object)
    labels = np.full(grid.shape, "", dtype=object)
    for row, tip in zip(table.itertuples(), hover):
        i, j = int((row.zone_x - 60) / 5), int(row.zone_y / 5)
        grid[i, j] = row.value
        tips[i, j] = tip
        labels[i, j] = _zone_label(mode, row.shots, row.value)

    fig = half_pitch(height)
    fig.add_trace(go.Heatmap(
        x=Y_EDGES, y=X_EDGES, z=grid, customdata=tips, hovertemplate="%{customdata}<extra></extra>",
        text=labels, texttemplate="%{text}" if height >= MIN_LABEL_HEIGHT else None,
        textfont=dict(size=9 if height < 450 else 12),
        colorscale=GOLD_SCALE, zmin=0, xgap=1.5, ygap=1.5, hoverongaps=False,
        colorbar=dict(thickness=11, len=0.72, outlinewidth=0, tickformat=".0%" if is_rate else None,
                      tickfont=dict(color=INK), title=dict(text=ZONE_TITLES[mode], side="right", font=dict(color=INK))),
    ))
    # Keep the pitch markings above the zones
    fig.data = (fig.data[-1],) + fig.data[:-1]
    return fig


def shot_dots(data: pd.DataFrame, height: int = 540, limit: int = SHOT_LIMIT, three_d: bool = False) -> go.Figure:
    """Show where each shot was taken: circle size is xG and gold stars are goals."""
    if len(data) > limit:
        data = data.sample(limit, random_state=1)  # a fair sample keeps the real share of goals
    goals = data[data["is_goal"] == 1]
    misses = data[data["is_goal"] == 0]

    if three_d:
        fig = scene(False, height)
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

    fig = half_pitch(height)
    fig.add_trace(go.Scatter(
        x=misses["y"], y=misses["x"], mode="markers", name=f"No goal ({len(misses):,})", text=_shot_text(misses),
        hovertemplate="%{text}<extra></extra>",
        marker=dict(size=6 + misses["statsbomb_xg"] * 26, color=MISS_COLOR, line=dict(width=0)),
    ))
    fig.add_trace(go.Scatter(
        x=goals["y"], y=goals["x"], mode="markers", name=f"Goal ({len(goals):,})", text=_shot_text(goals),
        hovertemplate="%{text}<extra></extra>",
        marker=dict(symbol="star", size=12 + goals["statsbomb_xg"] * 20, color=GOLD,
                    line=dict(width=1, color="#07080c")),
    ))
    fig.update_layout(legend=dict(y=1.0, yanchor="top", x=0.01, orientation="h"))
    _key_below(fig)
    return fig


def _team_shots(fig: go.Figure, frame: pd.DataFrame, name: str, color: str, flip: bool) -> None:
    """Add one team's shots; the away side is mirrored so it attacks the left goal."""
    x = 120 - frame["x"] if flip else frame["x"]
    y = 80 - frame["y"] if flip else frame["y"]
    text = _shot_text(frame)
    is_goal = frame["is_goal"].to_numpy() == 1
    fig.add_trace(go.Scatter(
        x=x[~is_goal], y=y[~is_goal], mode="markers", name=f"{name}: shot", legendgroup=name,
        text=[t for t, goal in zip(text, is_goal) if not goal], hovertemplate="%{text}<extra></extra>",
        marker=dict(size=9 + frame["statsbomb_xg"][~is_goal] * 34, color=color, opacity=0.68, line=dict(width=0)),
    ))
    fig.add_trace(go.Scatter(
        x=x[is_goal], y=y[is_goal], mode="markers", name=f"{name}: goal", legendgroup=name,
        text=[t for t, goal in zip(text, is_goal) if goal], hovertemplate="GOAL: %{text}<extra></extra>",
        marker=dict(symbol="star", size=19 + frame["statsbomb_xg"][is_goal] * 26, color=color,
                    line=dict(width=1.5, color="#ffffff")),
    ))


def match_shot_map(home: pd.DataFrame, away: pd.DataFrame, home_name: str, away_name: str,
                   height: int = 470) -> go.Figure:
    """Both teams on one pitch, each shot shown where it was taken."""
    fig = full_pitch(height)
    _team_shots(fig, home, home_name, GOLD, flip=False)
    _team_shots(fig, away, away_name, SKY, flip=True)
    for x, text in [(90, f"<b>{home_name} attack this way →</b>"), (30, f"<b>← {away_name} attack this way</b>")]:
        fig.add_annotation(x=x, y=-4.6, text=text, showarrow=False, font=dict(color=INK, size=13))
    fig.update_layout(legend=dict(y=1.0, yanchor="bottom", x=0, orientation="h"), margin=dict(t=34, b=34))
    fig.add_annotation(text="Bigger circles are better chances. Stars are goals.", xref="paper", yref="paper",
                       x=0, y=0, yshift=-30, xanchor="left", yanchor="bottom", showarrow=False,
                       font=dict(color=INK, size=12))
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
