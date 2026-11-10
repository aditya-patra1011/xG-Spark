"""Players: scouting cards, head-to-head comparison and a leaderboard."""
import plotly.graph_objects as go
import streamlit as st

import store
import ui
from charts import shot_dots

ui.page_head("Player", "Scout", "Finishing profiles, built from every shot a player took in this data.")

summary = store.player_summary()
candidates = summary[summary["shots"] >= 10]
names = dict(zip(candidates["player_id"], candidates["player"]))
ids = candidates["player_id"].tolist()

with ui.panel(key="player-filters"):
    one, two = st.columns(2, gap="small")
    with one:
        player_id = st.selectbox("Player", ids, format_func=names.get)
    with two:
        rival_id = st.selectbox(
            "Compare with", [None] + [i for i in ids if i != player_id],
            format_func=lambda i: "Nobody" if i is None else names[i],
        )

player = summary[summary["player_id"] == player_id].iloc[0]
rival = None if rival_id is None else summary[summary["player_id"] == rival_id].iloc[0]
shots = store.shots()

st.html(f"""
<div class="scoreboard" style="text-align:left">
  <div class="team home" style="text-align:left;font-size:2.5rem">{ui.esc(player['player'])}</div>
  <div class="meta">{ui.esc(player['position'])} | {ui.esc(player['team'])}
    {'| ' + ui.esc(player['nationality']) if player['nationality'] else ''}
    | {int(player['appearances'])} appearances in this data</div>
</div>
""")
st.write("")
ui.tiles([
    ("Shots", f"{int(player['shots']):,}"),
    ("Non-penalty goals", f"{int(player['goals']):,}"),
    ("xG", f"{player['xg']:.1f}"),
    ("Goals minus xG", f"{player['goals_minus_xg']:+.1f}"),
    ("Conversion", store.percent(player["conversion"])),
    ("xG per shot", f"{player['xg_per_shot']:.3f}"),
])
st.write("")

radar_column, dial_column = st.columns([1, 1.1], gap="small")


def percentiles(row) -> list[float]:
    return [store.percentile(column, row[column]) for column in store.SCOUT_METRICS.values()]


with radar_column:
    with ui.panel("Profile"):
        labels = list(store.SCOUT_METRICS)
        closed = labels + labels[:1]
        figure = go.Figure()
        for row, color, fill in [(rival, ui.SKY, "rgba(14,165,233,0.18)"), (player, ui.GOLD, "rgba(245,197,24,0.2)")]:
            if row is None:
                continue
            values = percentiles(row)
            figure.add_trace(go.Scatterpolar(
                r=values + values[:1], theta=closed, name=row["player"], fill="toself",
                fillcolor=fill, line=dict(color=color, width=2.4), marker=dict(size=7),
                hovertemplate="%{theta}: %{r:.0f}th percentile<extra>" + row["player"] + "</extra>",
            ))
        ui.style_figure(figure, 392, margin=dict(l=54, r=54, t=34, b=26))
        figure.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], gridcolor=ui.LINE,
                                linecolor=ui.LINE, tickfont=dict(color=ui.MUTED, size=10)),
                angularaxis=dict(gridcolor=ui.LINE, linecolor=ui.LINE, tickfont=dict(color=ui.INK, size=13)),
            ),
            legend=dict(y=1.08),
        )
        ui.show(figure)
        st.html(f'<div class="note-text">Percentiles against the {len(store.scout_pool())} players '
                f"with at least {store.MIN_SCOUT_SHOTS} shots.</div>")

with dial_column:
    with ui.panel("Scouting report"):
        first = st.columns(3, gap="small")
        second = st.columns(3, gap="small")
        descriptions = {
            "Volume": f"{player['shots_per_app']:.1f} shots per game",
            "Finishing": f"{player['finish']:+.3f} goals vs xG per shot",
            "Shot quality": f"{player['xg_per_shot']:.3f} xG per shot",
            "Box presence": f"{player['box']:.0%} of shots in the box",
            "Big chances": f"{player['big']:.0%} of shots at 30%+ xG",
            "Composure": f"{player['pressure_conv']:.0%} scored under pressure",
        }
        for column, label in zip(first + second, store.SCOUT_METRICS):
            value = store.percentile(store.SCOUT_METRICS[label], player[store.SCOUT_METRICS[label]])
            with column:
                ui.gauge(value / 100, f"{value:.0f}", label, descriptions[label])

st.write("")
map_column, table_column = st.columns([1, 1.1], gap="small")

with map_column:
    with ui.panel("Shot map"):
        ui.show(shot_dots(shots[shots["player_id"] == player_id], height=470))

with table_column:
    if rival is not None:
        with ui.panel("Head to head"):
            rows = [
                ("Shots", "shots", "{:,.0f}"), ("Non-penalty goals", "goals", "{:,.0f}"),
                ("xG", "xg", "{:.1f}"), ("Goals minus xG", "goals_minus_xg", "{:+.1f}"),
                ("Conversion", "conversion", "{:.1%}"), ("xG per shot", "xg_per_shot", "{:.3f}"),
                ("Shots per game", "shots_per_app", "{:.2f}"), ("Average distance", "avg_distance", "{:.1f}"),
            ]
            ui.rows([
                (label, f"{player['player']}  vs  {rival['player']}",
                 f"{fmt.format(player[col])}  |  {fmt.format(rival[col])}")
                for label, col, fmt in rows
            ])
    else:
        with ui.panel("Leaderboard"):
            sort_options = {
                "Goals minus xG": "goals_minus_xg", "Non-penalty goals": "goals", "xG": "xg",
                "Conversion": "conversion", "xG per shot": "xg_per_shot",
            }
            chosen = st.selectbox("Rank by", list(sort_options))
            table = store.scout_pool().sort_values(sort_options[chosen], ascending=False).head(50)
            table = table.assign(rank=range(1, len(table) + 1), conversion=table["conversion"] * 100)[
                ["rank", "player", "team", "shots", "goals", "xg", "goals_minus_xg", "conversion"]
            ]
            st.dataframe(
                table, hide_index=True, width="stretch", height=362,
                column_config={
                    "rank": st.column_config.NumberColumn("#", width="small"),
                    "player": "Player", "team": "Team", "shots": "Shots", "goals": "Goals",
                    "xg": st.column_config.NumberColumn("xG", format="%.1f"),
                    "goals_minus_xg": st.column_config.NumberColumn("G-xG", format="%+.1f"),
                    "conversion": st.column_config.NumberColumn("Conv.", format="%.1f%%"),
                },
            )
            st.html('<div class="note-text">Choose someone in "Compare with" to see a head to head instead.</div>')
