"""Shot Lab: build any shot and get a live prediction from the trained model."""
import plotly.graph_objects as go
import streamlit as st

import store
import ui
import xg_calculator as calc
from charts import diverging_bars
from pitch import half_pitch
from pitch3d import flight_path

SIMILAR_RADIUS = 4.0
PRESETS = {
    "Tap-in": dict(x=116.0, y=40.0, defenders=0, nearest=1.5, keeper=1.0, body="Right Foot", technique="Normal"),
    "Edge of the box": dict(x=101.0, y=40.0, defenders=2, nearest=1.8, keeper=1.8, body="Right Foot", technique="Normal"),
    "Back-post header": dict(x=113.0, y=46.0, defenders=1, nearest=1.2, keeper=1.5, body="Head", technique="Normal"),
    "Tight angle": dict(x=116.0, y=63.0, defenders=1, nearest=2.5, keeper=0.8, body="Left Foot", technique="Normal"),
    "Long shot": dict(x=88.0, y=38.0, defenders=2, nearest=4.0, keeper=2.5, body="Right Foot", technique="Normal"),
}
GRID_X = [x / 1 for x in range(61, 120, 2)]
GRID_Y = [y / 1 for y in range(1, 80, 2)]

ui.page_head("Shot", "Lab", "Click anywhere on the pitch, set the scene, and the model prices the chance.")

model = store.lr_model()
state = st.session_state
if "lab_x" not in state:
    state.lab_x, state.lab_y = 108.0, 40.0
    state.lab_seen = None
    state.lab_chart = 0
    state.lab_defenders, state.lab_nearest, state.lab_keeper = 1, 2.4, 2.1
    state.lab_body, state.lab_technique = "Right Foot", "Normal"


def apply_preset(name: str) -> None:
    preset = PRESETS[name]
    state.lab_x, state.lab_y = preset["x"], preset["y"]
    state.lab_defenders, state.lab_nearest, state.lab_keeper = preset["defenders"], preset["nearest"], preset["keeper"]
    state.lab_body, state.lab_technique = preset["body"], preset["technique"]
    # A new chart key clears the old click, so the same spot can be clicked again later
    state.lab_chart += 1
    state.lab_seen = None


preset_columns = st.columns(len(PRESETS), gap="small")
for column, name in zip(preset_columns, PRESETS):
    with column:
        st.button(name, on_click=apply_preset, args=(name,), width="stretch")

pitch_column, control_column, result_column = st.columns([1.35, 0.95, 1], gap="small")

with control_column:
    with ui.panel("Set the scene"):
        categories = model["categories"]
        body = st.selectbox("Body part", categories["body_part"], key="lab_body")
        technique = st.selectbox("Technique", categories["technique"], key="lab_technique")
        assist = st.selectbox("Assist", categories["assist_type"])
        pattern = st.selectbox("Phase of play", categories["play_pattern"])
        shot_type = st.selectbox("Shot type", categories["shot_type"])
        defenders = st.slider("Defenders between shot and goal", 0, 8, key="lab_defenders")
        nearest = st.slider("Nearest defender distance", 0.0, 20.0, step=0.1, key="lab_nearest")
        keeper = st.slider("Goalkeeper off their line", 0.0, 20.0, step=0.1, key="lab_keeper")
        one, two = st.columns(2, gap="small")
        with one:
            pressure = st.checkbox("Under pressure")
            first_time = st.checkbox("First time")
            one_on_one = st.checkbox("One on one")
            aerial = st.checkbox("Won in the air")
        with two:
            open_goal = st.checkbox("Open goal")
            dribble = st.checkbox("After a dribble")
            redirect = st.checkbox("Redirected")
            is_home = st.checkbox("Home team", value=True)

with pitch_column:
    with ui.panel("Pick the spot"):
        figure = half_pitch(640)
        grid_x, grid_y = [], []
        for pitch_x in GRID_X:
            for pitch_y in GRID_Y:
                grid_x.append(pitch_y)
                grid_y.append(pitch_x)
        figure.add_trace(go.Scatter(
            x=grid_x, y=grid_y, mode="markers", name="grid", showlegend=False,
            hovertemplate="Shoot from here<extra></extra>",
            marker=dict(size=13, color="rgba(245,197,24,0.03)", line=dict(width=0)),
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
        ))
        figure.update_layout(clickmode="event+select", dragmode="pan")
        figure.update_xaxes(fixedrange=True)
        figure.update_yaxes(fixedrange=True)
        chart_key = f"lab_pitch_{state.lab_chart}"
        event_preview = state.get(chart_key)
        points = event_preview.selection.points if event_preview else []
        if points and points[0].get("curve_number") == len(figure.data) - 1:
            clicked = (points[0]["y"], points[0]["x"])
            if clicked != state.lab_seen:
                state.lab_seen = clicked
                state.lab_x, state.lab_y = float(clicked[0]), float(clicked[1])

        x, y = state.lab_x, state.lab_y
        figure.add_trace(go.Scatter(
            x=[y, calc.RIGHT_POST, calc.LEFT_POST, y], y=[x, 120, 120, x], mode="lines", fill="toself",
            fillcolor="rgba(245,197,24,0.2)", line=dict(color=ui.GOLD, width=1.2),
            hoverinfo="skip", showlegend=False,
        ))
        figure.add_trace(go.Scatter(
            x=[y], y=[x], mode="markers", hoverinfo="skip", showlegend=False,
            marker=dict(size=19, color="#ffffff", line=dict(width=3, color=ui.GOLD)),
        ))
        ui.show(figure, on_select="rerun", selection_mode="points", key=chart_key)
        st.html('<div class="note-text">Click the pitch to move the shot. The gold cone is the '
                "part of the goal the shooter can see.</div>")

shot = {
    "x": state.lab_x, "y": state.lab_y, "defenders_in_cone": defenders, "nearest_defender": nearest,
    "gk_off_line": keeper, "is_home": int(is_home), "body_part": body, "technique": technique,
    "shot_type": shot_type, "play_pattern": pattern, "assist_type": assist,
    "under_pressure": int(pressure), "first_time": int(first_time), "one_on_one": int(one_on_one),
    "open_goal": int(open_goal), "aerial_won": int(aerial), "follows_dribble": int(dribble),
    "redirect": int(redirect),
}
chance = calc.predict(model, shot)
details = calc.build_features(shot)

with pitch_column:
    st.write("")
    with ui.panel("Flight path"):
        ui.show(flight_path(state.lab_x, state.lab_y, body == "Head", chance, keeper))
        st.html('<div class="note-text">Press Shoot to watch the ball, and drag to rotate. The route is '
                "illustrative, because the model only uses the moment the shot is taken.</div>")

with result_column:
    with ui.panel("Expected goals"):
        ui.gauge(chance, store.percent(chance), calc.verdict(chance),
                 f"Scored about {round(chance * 100)} times in 100")
        ui.tiles([
            ("Distance", f"{details['distance']:.1f}"),
            ("Goal angle", f"{details['angle'] * 57.2958:.0f} deg"),
        ])
    st.write("")
    with ui.panel("Compared with a typical shot"):
        effects = calc.effects(model, shot)
        ordered = sorted(effects.items(), key=lambda item: abs(item[1]), reverse=True)
        ui.show(diverging_bars([name for name, _ in ordered], [value for _, value in ordered], 276))
        st.html('<div class="note-text">Gold raises the chance and red lowers it, in log-odds. '
                "Zero is an average open-play shot from the edge of the box.</div>")
    st.write("")
    with ui.panel("Real shots from here"):
        data = store.shots()
        foot = data["body_part"].isin(["Right Foot", "Left Foot"])
        same_body = data["body_part"] == "Head" if body == "Head" else foot
        near = data[same_body & (((data["x"] - state.lab_x) ** 2 + (data["y"] - state.lab_y) ** 2) <= SIMILAR_RADIUS ** 2)]
        if len(near) >= 10:
            kind = "headers" if body == "Head" else "foot shots"
            ui.rows([
                (f"{len(near):,} real {kind} nearby", f"Within {SIMILAR_RADIUS:.0f} units of this spot",
                 store.percent(near["is_goal"].mean())),
            ])
        else:
            st.html('<div class="note-text">Fewer than 10 real shots were taken this close to this spot.</div>')
