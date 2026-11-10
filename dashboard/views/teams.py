"""Teams: real tables against expected tables, attacking style and form."""
import plotly.graph_objects as go
import streamlit as st

import store
import ui
from charts import shot_dots, view_3d

FORM_WINDOW = 5

ui.page_head("Team", "Analysis", "Who earned their results, and who got lucky.")

seasons = store.team_seasons()
matches = store.matches()
labels = store.competition_labels()

with ui.panel(key="team-filters"):
    one, two = st.columns(2, gap="small")
    with one:
        default = labels.index("La Liga 2015/2016")
        competition = st.selectbox("Competition", labels, index=default)
    table = seasons[(seasons["label"] == competition) & (seasons["matches"] >= 3)].copy()
    with two:
        table = table.sort_values(["points", "xg_for"], ascending=False)
        team = st.selectbox("Team", table["team"].tolist())

is_league = competition.rsplit(" ", 1)[0] in store.FULL_LEAGUES
table["goal_difference"] = table["goals_for"] - table["goals_against"]
table["xg_difference"] = table["xg_for"] - table["xg_against"]
table["luck"] = table["points"] - table["expected_points"]

table_column, scatter_column = st.columns([1.5, 1], gap="small")

with table_column:
    with ui.panel("League table" if is_league else "Team table"):
        if is_league:
            view = table.sort_values(["points", "goal_difference"], ascending=False)
            view = view.assign(rank=range(1, len(view) + 1))
            columns = ["rank", "team", "matches", "win", "draw", "loss", "goal_difference", "points",
                       "xg_for", "xg_against", "expected_points", "luck"]
        else:
            view = table.sort_values("xg_difference", ascending=False)
            view = view.assign(rank=range(1, len(view) + 1))
            columns = ["rank", "team", "matches", "win", "draw", "loss", "goal_difference",
                       "xg_for", "xg_against", "xg_difference"]
        st.dataframe(
            view[columns], hide_index=True, width="stretch", height=422,
            column_config={
                "rank": st.column_config.NumberColumn("#", width="small"),
                "team": "Team", "matches": "P", "win": "W", "draw": "D", "loss": "L",
                "goal_difference": st.column_config.NumberColumn("GD", format="%+d"),
                "points": "Pts",
                "xg_for": st.column_config.NumberColumn("xG", format="%.1f"),
                "xg_against": st.column_config.NumberColumn("xGA", format="%.1f"),
                "xg_difference": st.column_config.NumberColumn("xGD", format="%+.1f"),
                "expected_points": st.column_config.NumberColumn("xPts", format="%.1f"),
                "luck": st.column_config.NumberColumn("Pts-xPts", format="%+.1f"),
            },
        )
        if is_league:
            st.html('<div class="note-text">xG and xPts exclude penalties and own goals, so xPts tends to '
                    "run below real points. Compare teams with each other.</div>")
        elif competition.startswith("1. Bundesliga"):
            st.html('<div class="note-text">Bayer Leverkusen is the only team with a full season in this data.</div>')

with scatter_column:
    with ui.panel("Attack against defence"):
        per_match_for = table["xg_for"] / table["matches"]
        per_match_against = table["xg_against"] / table["matches"]
        selected = table["team"] == team
        figure = go.Figure()
        figure.add_trace(go.Scatter(
            x=per_match_for[~selected], y=per_match_against[~selected], mode="markers", name="Others",
            text=table["team"][~selected], showlegend=False,
            hovertemplate="<b>%{text}</b><br>xG for: %{x:.2f}<br>xG against: %{y:.2f}<extra></extra>",
            marker=dict(size=12, color="#7b8094", line=dict(width=1.5, color=ui.PANEL)),
        ))
        figure.add_trace(go.Scatter(
            x=per_match_for[selected], y=per_match_against[selected], mode="markers+text", name=team,
            text=table["team"][selected], textposition="top center", showlegend=False,
            textfont=dict(color=ui.GOLD), hovertemplate="<b>%{text}</b><br>xG for: %{x:.2f}<br>xG against: %{y:.2f}<extra></extra>",
            marker=dict(size=17, color=ui.GOLD, line=dict(width=1.5, color=ui.PANEL)),
        ))
        ui.style_figure(figure, 440)
        figure.update_xaxes(title="xG for per match")
        figure.update_yaxes(title="xG against per match (best at the top)", autorange="reversed")
        ui.show(figure)

st.write("")
row = table[table["team"] == team].iloc[0]
ui.tiles([
    ("Record", f"{int(row['win'])}-{int(row['draw'])}-{int(row['loss'])}", "Won, drawn, lost"),
    ("Goals", f"{int(row['goals_for'])}-{int(row['goals_against'])}", "For and against"),
    ("xG for", f"{row['xg_for']:.1f}"),
    ("xG against", f"{row['xg_against']:.1f}"),
    ("xG difference", f"{row['xg_difference']:+.1f}"),
    ("Points vs xPts" if is_league else "Matches",
     f"{row['luck']:+.1f}" if is_league else f"{int(row['matches'])}"),
])
st.write("")

form_column, map_column = st.columns([1.5, 1], gap="small")

games = matches[(matches["label"] == competition)
                & ((matches["home_team"] == team) | (matches["away_team"] == team))].sort_values("match_date")
is_home = games["home_team"] == team
xg_for = games["home_xg"].where(is_home, games["away_xg"])
xg_against = games["away_xg"].where(is_home, games["home_xg"])
goals_for = games["home_score"].where(is_home, games["away_score"])
goals_against = games["away_score"].where(is_home, games["home_score"])
opponent = games["away_team"].where(is_home, games["home_team"])

with form_column:
    with ui.panel("Form"):
        window = min(FORM_WINDOW, max(len(games) // 3, 1))
        numbers = list(range(1, len(games) + 1))
        hover = [f"{d:%d %b %Y}<br>vs {o}: {f}-{a}" for d, o, f, a in
                 zip(games["match_date"], opponent, goals_for, goals_against)]
        figure = go.Figure()
        figure.add_trace(go.Scatter(
            x=numbers, y=xg_for.rolling(window, min_periods=1).mean(), mode="lines", name="xG for",
            line=dict(color=ui.GOLD, width=2.6), text=hover,
            hovertemplate="%{text}<br>xG for (average): %{y:.2f}<extra></extra>",
        ))
        figure.add_trace(go.Scatter(
            x=numbers, y=xg_against.rolling(window, min_periods=1).mean(), mode="lines", name="xG against",
            line=dict(color=ui.RED, width=2.6), text=hover,
            hovertemplate="%{text}<br>xG against (average): %{y:.2f}<extra></extra>",
        ))
        ui.style_figure(figure, 400)
        figure.update_xaxes(title=f"Match number ({window}-match rolling average)", showgrid=False)
        figure.update_yaxes(title="xG per match", rangemode="tozero")
        ui.show(figure)

with map_column:
    with ui.panel("Where they shoot from"):
        shots = store.shots()
        three_d = view_3d("team_3d")
        ui.show(shot_dots(shots[(shots["team"] == team) & (shots["label"] == competition)], height=430,
                          three_d=three_d))
