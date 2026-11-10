"""Overview: the headline numbers and the best stories in the data."""
import plotly.graph_objects as go
import streamlit as st

import store
import ui
from charts import zone_heatmap

shots = store.shots()
matches = store.matches()
seasons = store.team_seasons()
summary = store.scout_pool()
metrics = store.metrics().set_index("model")

left, middle, right = st.columns([1, 3.1, 1], gap="small")

with left:
    with ui.panel("Dataset"):
        ui.rows([
            ("Matches", "9 competitions", f"{len(matches):,}"),
            ("Events", "Raw records processed", "6.28M"),
            ("Raw data", "JSON files", "5.1 GB"),
            ("Shots", "Without penalties", f"{len(shots):,}"),
            ("Players", "Took a shot", f"{shots['player_id'].nunique():,}"),
        ])

with middle:
    ui.hero("xG", "SPARK", "Every shot. Every chance. Measured.")

with right:
    with ui.panel("Goals by competition"):
        by_competition = (shots.groupby("competition")["is_goal"].sum()
                          .sort_values(ascending=False).head(6))
        ui.rows([(name, "", f"{goals:,}") for name, goals in by_competition.items()])

st.write("")
goals = int(shots["is_goal"].sum())
ui.tiles([
    ("Goals", f"{goals:,}"),
    ("Goals per shot", store.percent(goals / len(shots), 2)),
    ("Average xG per shot", f"{shots['statsbomb_xg'].mean():.3f}"),
    ("Shots per match", f"{len(shots) / len(matches):.1f}"),
    ("Model AUC", f"{metrics.loc['Gradient-Boosted Trees', 'auc']:.3f}"),
    ("Models trained", "4"),
])
st.write("")

chart_column, dial_column = st.columns([1.2, 1], gap="small")

with chart_column:
    with ui.panel("How distance kills a chance"):
        data = shots[shots["distance"] < 40].copy()
        data["band"] = (data["distance"] // 5 * 5).astype(int)
        bands = data.groupby("band")["is_goal"].mean()
        figure = go.Figure(go.Bar(
            x=[f"{band}-{band + 5}" for band in bands.index], y=bands.values, width=0.58,
            marker=dict(color=ui.GOLD, line=dict(width=0)),
            hovertemplate="%{x} units from goal: %{y:.1%}<extra></extra>",
        ))
        ui.style_figure(figure, 272)
        figure.update_yaxes(tickformat=".0%", title="Goals per shot")
        figure.update_xaxes(title="Distance from goal (StatsBomb units)", showgrid=False)
        ui.show(figure)

with dial_column:
    with ui.panel("Prediction power"):
        one, two = st.columns(2, gap="small")
        favourites = matches[matches["home_score"] != matches["away_score"]]
        home_favourite = matches["home_xg"] > matches["away_xg"]
        home_won = matches["home_score"] > matches["away_score"]
        away_won = matches["home_score"] < matches["away_score"]
        won = ((home_favourite & home_won) | (~home_favourite & away_won)).mean()
        with one:
            auc = metrics.loc["Gradient-Boosted Trees", "auc"]
            ui.gauge((auc - 0.5) / 0.5, f"{auc:.3f}", "Our best AUC", "How well shots are ranked")
        with two:
            ui.gauge(float(won), store.percent(float(won)), "xG favourite wins", "Team with higher xG")

st.write("")
ring_column, map_column = st.columns([1.35, 1], gap="small")

with ring_column:
    with ui.panel("What makes a chance"):
        columns = st.columns(3, gap="small")
        through = shots[shots["assist_type"] == "Through Ball"]["is_goal"].mean()
        one_on_one = shots[shots["one_on_one"] == 1]["is_goal"].mean()
        clear = shots[shots["defenders_in_cone"] == 0]["is_goal"].mean()
        with columns[0]:
            ui.ring(float(through), store.percent(float(through), 0), "Through balls", "Goals per shot")
        with columns[1]:
            ui.ring(float(one_on_one), store.percent(float(one_on_one), 0), "One on ones", "Goals per shot")
        with columns[2]:
            ui.ring(float(clear), store.percent(float(clear), 0), "Clear path", "No defender in the way")

with map_column:
    with ui.panel("Where shots come from"):
        ui.show(zone_heatmap(store.zone_table(shots), "Shots", height=300))

st.write("")
cards = st.columns(4, gap="small")

with cards[0]:
    with ui.panel("Biggest upsets"):
        data = matches[matches["home_score"] != matches["away_score"]].copy()
        data["winner_gap"] = data.apply(
            lambda m: (m.away_xg - m.home_xg) if m.home_score > m.away_score else (m.home_xg - m.away_xg),
            axis=1,
        )
        ui.rows([
            (f"{m.home_team} {m.home_score}-{m.away_score} {m.away_team}", m.label, f"{m.winner_gap:+.1f} xG")
            for m in data.sort_values("winner_gap", ascending=False).head(4).itertuples()
        ])
        st.page_link("views/match_centre.py", label="Open Match Centre")

with cards[1]:
    with ui.panel("Goals against the odds"):
        goals_table = shots[shots["is_goal"] == 1].sort_values("statsbomb_xg").head(4)
        ui.rows([
            (s.player, f"{s.team}, minute {s.minute}", f"1 in {round(1 / s.statsbomb_xg):,}")
            for s in goals_table.itertuples()
        ])
        st.page_link("views/shot_explorer.py", label="Open Shot Explorer")

with cards[2]:
    with ui.panel("Best finishers"):
        ui.rows([
            (p.player, f"{p.goals} goals from {p.xg:.1f} xG", f"{p.goals_minus_xg:+.1f}")
            for p in summary.sort_values("goals_minus_xg", ascending=False).head(4).itertuples()
        ])
        st.page_link("views/players.py", label="Open Players")

with cards[3]:
    with ui.panel("Most dangerous attacks"):
        leagues = seasons[seasons["competition"].isin(store.FULL_LEAGUES)].copy()
        leagues["per_match"] = leagues["xg_for"] / leagues["matches"]
        ui.rows([
            (t.team, t.label, f"{t.per_match:.2f}")
            for t in leagues.sort_values("per_match", ascending=False).head(4).itertuples()
        ])
        st.page_link("views/teams.py", label="Open Teams")
