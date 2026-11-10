"""Shot Explorer: slice all 43,924 shots and see them on the pitch."""
import plotly.graph_objects as go
import streamlit as st

import store
import ui
from charts import SHOT_LIMIT, shot_dots, view_3d, zone_heatmap

ui.page_head("Shot", "Explorer", "Filter every shot in the dataset by who, how and where.")

shots = store.shots()


def options(data, column: str) -> list[str]:
    return ["All"] + sorted(data[column].dropna().unique().tolist())


with ui.panel(key="explorer-filters"):
    columns = st.columns(6, gap="small")
    with columns[0]:
        competition = st.selectbox("Competition", ["All"] + store.competition_labels())
    scoped = store.filter_shots(shots, label=competition)
    with columns[1]:
        team = st.selectbox("Team", options(scoped, "team"))
    scoped = store.filter_shots(scoped, team=team)
    with columns[2]:
        player = st.selectbox("Player", options(scoped, "player"))
    with columns[3]:
        body = st.selectbox("Body part", options(shots, "body_part"))
    with columns[4]:
        assist = st.selectbox("Assist", options(shots, "assist_type"))
    with columns[5]:
        pattern = st.selectbox("Phase of play", options(shots, "play_pattern"))

data = store.filter_shots(scoped, player=player, body_part=body, assist_type=assist, play_pattern=pattern)

if data.empty:
    st.info("No shots match these filters. Try setting one of them back to All.")
    st.stop()

goals = int(data["is_goal"].sum())
total_xg = data["statsbomb_xg"].sum()
ui.tiles([
    ("Shots", f"{len(data):,}"),
    ("Goals", f"{goals:,}"),
    ("Conversion", store.percent(goals / len(data))),
    ("Total xG", f"{total_xg:,.1f}"),
    ("Goals minus xG", f"{goals - total_xg:+,.1f}"),
    ("Average distance", f"{data['distance'].mean():.1f}"),
])
st.write("")

map_column, side_column = st.columns([1.55, 1], gap="small")

with map_column:
    with ui.panel("Pitch view"):
        view = st.segmented_control(
            "View", ["Shot map", "Shots", "Conversion", "Average xG"], default="Shots",
            label_visibility="collapsed",
        ) or "Shots"
        three_d = view_3d("explorer_3d")
        if view == "Shot map":
            ui.show(shot_dots(data, height=590, three_d=three_d))
            if len(data) > SHOT_LIMIT:
                st.html(f'<div class="note-text">Showing a random sample of {SHOT_LIMIT:,} of these {len(data):,} shots, '
                        "with the same share of goals. Use the filters to see every shot.</div>")
        else:
            ui.show(zone_heatmap(store.zone_table(data), view, height=590, three_d=three_d))
            if view != "Shots":
                st.html('<div class="note-text">Only zones with at least 10 shots are shown.</div>')

with side_column:
    with ui.panel("How the shots ended"):
        outcomes = data["outcome"].value_counts(ascending=True)
        figure = go.Figure(go.Bar(
            y=outcomes.index, x=outcomes.values, orientation="h", width=0.58,
            marker=dict(color=[ui.GOLD if name == "Goal" else "#5b6072" for name in outcomes.index],
                        line=dict(width=0)),
            text=[f"{v:,}" for v in outcomes.values], textposition="outside", cliponaxis=False,
            textfont=dict(color=ui.INK), hovertemplate="%{y}: %{x:,}<extra></extra>",
        ))
        ui.style_figure(figure, 270, margin=dict(l=8, r=52, t=6, b=28))
        figure.update_yaxes(automargin=True, showgrid=False, tickfont=dict(color=ui.INK))
        ui.show(figure)

    st.write("")
    with ui.panel("Most clinical moments"):
        best = data[data["is_goal"] == 1].sort_values("statsbomb_xg").head(5)
        if best.empty:
            st.html('<div class="note-text">No goals in this selection.</div>')
        else:
            ui.rows([
                (s.player, f"{s.team}, {s.label}", f"1 in {round(1 / s.statsbomb_xg):,}")
                for s in best.itertuples()
            ])
            st.html('<div class="note-text">The least likely goals here, by xG.</div>')
