"""Match Centre: replay any match through its chances."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import store
import ui
from charts import match_shot_map, view_3d
from pitch3d import add_shot_columns, scene

DEFAULT_COMPETITION = "FIFA World Cup 2022"

ui.page_head("Match", "Centre", "Pick any of 1,781 matches and see how the chances really fell.")

matches = store.matches()
shots = store.shots()
labels = store.competition_labels()

with ui.panel(key="match-filters"):
    one, two, three = st.columns([1, 1, 2], gap="small")
    with one:
        competition = st.selectbox("Competition", labels, index=labels.index(DEFAULT_COMPETITION))
    available = matches[matches["label"] == competition].sort_values("match_date", ascending=False)
    with two:
        teams = sorted(set(available["home_team"]) | set(available["away_team"]))
        team = st.selectbox("Team", ["All"] + teams)
    if team != "All":
        available = available[(available["home_team"] == team) | (available["away_team"] == team)]
    with three:
        options = available["match_id"].tolist()
        names = {
            m.match_id: f"{m.home_team} {m.home_score}-{m.away_score} {m.away_team}  ({m.match_date:%d %b %Y}, {m.stage})"
            for m in available.itertuples()
        }
        match_id = st.selectbox("Match", options, format_func=names.get)

match = matches[matches["match_id"] == match_id].iloc[0]
data = shots[shots["match_id"] == match_id].sort_values(["period", "minute", "second"])
home_shots = data[data["is_home"] == 1]
away_shots = data[data["is_home"] == 0]

details = [f"{match['match_date']:%d %B %Y}", match["stage"]]
if match["stadium"]:
    details.append(match["stadium"])
if match["referee"]:
    details.append(f"Referee: {match['referee']}")

st.html(f"""
<div class="scoreboard">
  <div class="meta">{ui.esc(' | '.join(details))}</div>
  <div class="line">
    <div class="team home">{ui.esc(match['home_team'])}</div>
    <div class="score">{match['home_score']} - {match['away_score']}</div>
    <div class="team away">{ui.esc(match['away_team'])}</div>
  </div>
  <div class="meta">Non-penalty xG: <b style="color:{ui.GOLD}">{match['home_xg']:.2f}</b>
    &nbsp;to&nbsp; <b style="color:{ui.SKY}">{match['away_xg']:.2f}</b></div>
</div>
""")
st.write("")


def clock(row) -> float:
    """Place shots on one timeline, folding first-half stoppage time into minute 45."""
    if row.period == 1:
        return min(row.minute, 45)
    if row.period == 2:
        return max(45, min(row.minute, 90))
    return row.minute


def race_trace(frame: pd.DataFrame, name: str, color: str, end: float) -> list[go.Scatter]:
    times = [clock(row) + row.second / 600 for row in frame.itertuples()]
    totals = frame["statsbomb_xg"].cumsum().tolist()
    hover = [f"{m}': {p} (xG {x:.2f})<br>{name} total: {t:.2f}" for m, p, x, t in
             zip(frame["minute"], frame["player"], frame["statsbomb_xg"], totals)]
    line = go.Scatter(
        x=[0] + times + [end], y=[0] + totals + [totals[-1] if totals else 0],
        mode="lines", line=dict(color=color, width=2.6, shape="hv"), name=name,
        text=[""] + hover + [""], hovertemplate="%{text}<extra></extra>",
    )
    goal_mask = (frame["is_goal"] == 1).tolist()
    goals = go.Scatter(
        x=[t for t, g in zip(times, goal_mask) if g], y=[t for t, g in zip(totals, goal_mask) if g],
        mode="markers", name=f"{name} goal", showlegend=False,
        marker=dict(symbol="star", size=17, color=color, line=dict(width=1.2, color="#07080c")),
        text=[h for h, g in zip(hover, goal_mask) if g], hovertemplate="GOAL %{text}<extra></extra>",
    )
    return [line, goals]


race_column, odds_column = st.columns([2.2, 1], gap="small")

with race_column:
    with ui.panel("xG race"):
        regular_end = 120 if len(data) and data["period"].max() > 2 else 90
        end = max([regular_end] + [clock(row) + 1 for row in data.itertuples()])
        figure = go.Figure()
        for trace in (race_trace(home_shots, match["home_team"], ui.GOLD, end)
                      + race_trace(away_shots, match["away_team"], ui.SKY, end)):
            figure.add_trace(trace)
        ui.style_figure(figure, 330)
        figure.update_xaxes(title="Minute", range=[0, end + 1], dtick=15, showgrid=False)
        figure.update_yaxes(title="Cumulative non-penalty xG", rangemode="tozero")
        ui.show(figure)

with odds_column:
    with ui.panel("Who deserved it"):
        st.html('<div class="note-text">Chance of each result if these same shots were replayed.</div>')
        ui.gauge(float(match["prob_home"]), store.percent(float(match["prob_home"]), 0),
                 f"{match['home_team']} win")
        a, b = st.columns(2, gap="small")
        with a:
            ui.ring(float(match["prob_draw"]), store.percent(float(match["prob_draw"]), 0), "Draw")
        with b:
            ui.ring(float(match["prob_away"]), store.percent(float(match["prob_away"]), 0), "Away win")

st.write("")
map_column, list_column = st.columns([1.7, 1], gap="small")


with map_column:
    with ui.panel("Shot map"):
        three_d = view_3d("match_3d")
        if three_d:
            figure = scene(True, 470)
            add_shot_columns(figure, home_shots, ui.GOLD, match["home_team"], miss_color="#a8860e")
            add_shot_columns(figure, away_shots, ui.SKY, match["away_team"], x=120 - away_shots["x"],
                             y=80 - away_shots["y"], miss_color="#0b6f9e")
            figure.update_layout(legend=dict(y=1.0, yanchor="top", x=0))
        else:
            figure = match_shot_map(home_shots, away_shots, match["home_team"], match["away_team"], 470)
        ui.show(figure)
        st.html('<div class="note-text">Penalties and own goals are not shown, so the score can be higher '
                "than the shots suggest.</div>")

with list_column:
    with ui.panel("Best chances"):
        best = data.sort_values("statsbomb_xg", ascending=False).head(8)
        ui.rows([
            (s.player, f"{s.team}, {s.minute}', {s.outcome}", f"{s.statsbomb_xg:.2f}")
            for s in best.itertuples()
        ])
