"""Load the exported data and work out the figures the pages share."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DASHBOARD_DIR = Path(__file__).resolve().parent
DATA = DASHBOARD_DIR / "datasets"
REPORTS = DASHBOARD_DIR.parent / "reports"

FULL_LEAGUES = ["Premier League", "La Liga", "Serie A", "Ligue 1"]
MIN_SCOUT_SHOTS = 50
BIG_CHANCE = 0.3

SCOUT_METRICS = {
    "Volume": "shots_per_app",
    "Finishing": "finish",
    "Shot quality": "xg_per_shot",
    "Box presence": "box",
    "Big chances": "big",
    "Composure": "pressure_conv",
}


@st.cache_data
def shots() -> pd.DataFrame:
    table = pd.read_parquet(DATA / "shots.parquet")
    table["label"] = table["competition"] + " " + table["season"]
    table["in_box"] = ((table["x"] >= 102) & table["y"].between(18, 62)).astype(int)
    return table


@st.cache_data
def matches() -> pd.DataFrame:
    table = pd.read_parquet(DATA / "matches.parquet")
    table["label"] = table["competition"] + " " + table["season"]
    return table


@st.cache_data
def team_seasons() -> pd.DataFrame:
    table = pd.read_parquet(DATA / "team_seasons.parquet")
    table["label"] = table["competition"] + " " + table["season"]
    return table


@st.cache_data
def players() -> pd.DataFrame:
    return pd.read_parquet(DATA / "players.parquet")


@st.cache_data
def lr_model() -> dict:
    return json.loads((DATA / "lr_model.json").read_text(encoding="utf-8"))


@st.cache_data
def roc() -> pd.DataFrame:
    return pd.read_csv(DATA / "roc.csv")


@st.cache_data
def metrics() -> pd.DataFrame:
    return pd.read_csv(REPORTS / "metrics.csv")


@st.cache_data
def calibration() -> pd.DataFrame:
    return pd.read_csv(REPORTS / "calibration.csv")


@st.cache_data
def feature_importance() -> pd.DataFrame:
    return pd.read_csv(REPORTS / "feature_importance.csv")


@st.cache_data
def competition_labels() -> list[str]:
    table = matches()
    latest = table.groupby("label")["match_date"].max().sort_values(ascending=False)
    return list(latest.index)


@st.cache_data
def player_summary() -> pd.DataFrame:
    """One row per player with the numbers behind the scouting cards."""
    data = shots().copy()
    data["big"] = (data["statsbomb_xg"] >= BIG_CHANCE).astype(int)
    summary = data.groupby("player_id", as_index=False).agg(
        player=("player", "max"),
        shots=("is_goal", "size"),
        goals=("is_goal", "sum"),
        xg=("statsbomb_xg", "sum"),
        box=("in_box", "mean"),
        big=("big", "mean"),
        avg_distance=("distance", "mean"),
        matches_with_shot=("match_id", "nunique"),
        position=("position", lambda s: s.mode().iat[0]),
        team=("team", lambda s: s.mode().iat[0]),
    )
    pressured = (data[data["under_pressure"] == 1].groupby("player_id")["is_goal"].mean()
                 .rename("pressure_conv"))
    summary = summary.merge(pressured, on="player_id", how="left")
    summary = summary.merge(players()[["player_id", "nationality", "appearances"]], on="player_id", how="left")
    summary["appearances"] = summary[["appearances", "matches_with_shot"]].max(axis=1)
    summary["pressure_conv"] = summary["pressure_conv"].fillna(0.0)
    summary["goals_minus_xg"] = summary["goals"] - summary["xg"]
    summary["conversion"] = summary["goals"] / summary["shots"]
    summary["xg_per_shot"] = summary["xg"] / summary["shots"]
    summary["finish"] = summary["goals_minus_xg"] / summary["shots"]
    summary["shots_per_app"] = summary["shots"] / summary["appearances"]
    return summary.sort_values("shots", ascending=False)


@st.cache_data
def scout_pool() -> pd.DataFrame:
    table = player_summary()
    return table[table["shots"] >= MIN_SCOUT_SHOTS]


def percentile(column: str, value: float) -> float:
    pool = scout_pool()[column].to_numpy()
    return float((pool <= value).mean() * 100)


def percent(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def filter_shots(data: pd.DataFrame, **conditions) -> pd.DataFrame:
    """Keep rows matching each column=value, ignoring any filter left on 'All'."""
    for column, value in conditions.items():
        if value != "All":
            data = data[data[column] == value]
    return data


def zone_table(data: pd.DataFrame) -> pd.DataFrame:
    """Count shots and goals in each 5 x 5 zone of the attacking half."""
    attacking = data[data["x"] >= 60].copy()
    attacking["zone_x"] = np.minimum(np.floor(attacking["x"] / 5) * 5, 115)
    attacking["zone_y"] = np.minimum(np.floor(attacking["y"] / 5) * 5, 75)
    return attacking.groupby(["zone_x", "zone_y"], as_index=False).agg(
        shots=("is_goal", "size"), goals=("is_goal", "sum"), xg=("statsbomb_xg", "mean")
    )
