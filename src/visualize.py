"""Phase 8 - Turn the gold tables and model results into report figures."""
import time

import matplotlib

matplotlib.use("Agg")    # draw to files; no window needed

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import VerticalPitch

from src.config import FIGURES_DIR, GOLD_DIR, REPORTS_DIR

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

BLUE = "#2a78d6"
RED = "#e34948"

# Each model keeps the same colour in every figure
MODEL_COLORS = {
    "Logistic Regression": "#2a78d6",
    "Gradient-Boosted Trees": "#eb6834",
    "StatsBomb xG": "#1baf7a",
    "Logistic Regression (weighted)": "#eda100",
}
ROC_MODELS = {
    "Logistic Regression": "xg_lr",
    "Gradient-Boosted Trees": "xg_gbt",
    "StatsBomb xG": "statsbomb_xg",
}

SEQUENTIAL = LinearSegmentedColormap.from_list(
    "blues", ["#cde2fb", "#86b6ef", "#2a78d6", "#184f95", "#0d366b"]
)

MIN_ZONE_SHOTS = 30     # conversion rates from fewer shots are mostly noise
MIN_LEAGUE_MATCHES = 30

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 11,
    "text.color": INK,
    "axes.labelcolor": SECONDARY_INK,
    "axes.edgecolor": BASELINE,
    "axes.titlesize": 14,
    "axes.titleweight": "semibold",
    "axes.titlelocation": "left",
    "axes.titlepad": 14,
    "xtick.color": MUTED_INK,
    "ytick.color": MUTED_INK,
    "xtick.labelcolor": SECONDARY_INK,
    "ytick.labelcolor": SECONDARY_INK,
    "legend.frameon": False,
})


def gold(name: str) -> pd.DataFrame:
    return pd.read_parquet(GOLD_DIR / name)


def clean_axes(ax, grid_axis: str = "y") -> None:
    """Keep only a light baseline and hairline gridlines."""
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def save(fig, name: str) -> None:
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"  {name}.png")


def zone_map(zones: pd.DataFrame, column: str, title: str, colorbar_label: str, name: str,
             percent: bool = False) -> None:
    """Draw one value per 5 x 5 zone on the attacking half of the pitch."""
    x_edges = np.arange(60, 125, 5)
    y_edges = np.arange(0, 85, 5)
    grid = np.full((len(y_edges) - 1, len(x_edges) - 1), np.nan)
    for row in zones.itertuples():
        grid[int(row.zone_y / 5), int((row.zone_x - 60) / 5)] = getattr(row, column)
    x_grid, y_grid = np.meshgrid(x_edges, y_edges)

    pitch = VerticalPitch(pitch_type="statsbomb", half=True, pitch_color=SURFACE,
                          line_color=SECONDARY_INK, linewidth=1, line_zorder=3)
    fig, ax = pitch.draw(figsize=(8.5, 6.5))
    mesh = pitch.heatmap({"statistic": grid, "x_grid": x_grid, "y_grid": y_grid}, ax=ax,
                         cmap=SEQUENTIAL, vmin=0, edgecolors=SURFACE, linewidth=1, zorder=2)
    bar = fig.colorbar(mesh, ax=ax, shrink=0.7, pad=0.02)
    bar.set_label(colorbar_label, color=SECONDARY_INK)
    bar.outline.set_visible(False)
    bar.ax.tick_params(length=0)
    if percent:
        bar.ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    else:
        bar.ax.yaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")
    ax.set_title(title, loc="left")
    save(fig, name)


def shot_volume_map() -> None:
    zone_map(gold("shot_zones"), "shots", "Most shots come from the central penalty area",
             "Shots per zone", "01_shot_volume")


def conversion_map() -> None:
    zones = gold("shot_zones").query("shots >= @MIN_ZONE_SHOTS")
    zone_map(zones, "conversion", "Chances of scoring fall quickly away from goal",
             f"Goals per shot (zones with at least {MIN_ZONE_SHOTS} shots)", "02_zone_conversion",
             percent=True)


def conversion_by_distance() -> None:
    table = gold("distance_body_part").sort_values("distance_band")
    fig, ax = plt.subplots(figsize=(8.5, 5))
    styles = [("right_foot", "Right foot", "#2a78d6", "o"),
              ("left_foot", "Left foot", "#eb6834", "s"),
              ("head", "Head", "#1baf7a", "^")]
    for column, label, color, marker in styles:
        ax.plot(table["distance_band"], table[column], color=color, marker=marker,
                linewidth=2, markersize=8, label=label, clip_on=False, zorder=3)
    ax.set_title("Headers convert far less often than foot shots at the same distance")
    ax.set_xlabel("Distance from goal (StatsBomb units)")
    ax.set_ylabel("Goals per shot")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right")
    clean_axes(ax)
    save(fig, "03_conversion_by_distance")


def player_finishing() -> None:
    table = gold("player_finishing").sort_values("goals_minus_xg", ascending=False)
    shown = pd.concat([table.head(10), table.tail(5)]).iloc[::-1]
    colors = [BLUE if value > 0 else RED for value in shown["goals_minus_xg"]]

    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.barh(shown["player_name"], shown["goals_minus_xg"], color=colors, height=0.6)
    ax.axvline(0, color=BASELINE, linewidth=1)
    for position in [0, len(shown) - 1]:
        value = shown["goals_minus_xg"].iloc[position]
        ax.annotate(f"{value:+.1f}", (value, position), xytext=(6 if value > 0 else -6, 0),
                    textcoords="offset points", va="center",
                    ha="left" if value > 0 else "right", color=SECONDARY_INK)
    ax.set_title("Best and worst finishers against StatsBomb xG (at least 50 shots)")
    ax.set_xlabel("Non-penalty goals minus xG")
    ax.margins(x=0.1)
    clean_axes(ax, "x")
    ax.spines["bottom"].set_visible(False)
    save(fig, "04_player_finishing")


def team_goals_vs_xg() -> None:
    table = gold("team_attack").query("matches >= @MIN_LEAGUE_MATCHES")
    fig, ax = plt.subplots(figsize=(8, 6.5))
    ax.scatter(table["xg_per_match"], table["goals_per_match"], s=70, color=BLUE,
               edgecolors=SURFACE, linewidths=1.5, zorder=3)
    limits = [0.5, 2.8]
    ax.plot(limits, limits, color=MUTED_INK, linewidth=1, zorder=1)
    ax.annotate("Goals = xG", (2.5, 2.5), xytext=(6, -14), textcoords="offset points",
                color=MUTED_INK, fontsize=10)

    for team in ["Barcelona", "Real Madrid", "Paris Saint-Germain", "Juventus", "Aston Villa"]:
        row = table[table["team_name"] == team].iloc[0]
        ax.annotate(team, (row["xg_per_match"], row["goals_per_match"]), xytext=(-8, 4),
                    textcoords="offset points", ha="right", color=SECONDARY_INK, fontsize=10)

    ax.set_xlim(limits)
    ax.set_ylim(limits)
    ax.set_title("League teams' goals track the quality of their chances")
    ax.set_xlabel("Non-penalty xG per match")
    ax.set_ylabel("Non-penalty goals per match")
    clean_axes(ax, "both")
    save(fig, "05_team_goals_vs_xg")


def xg_favourite_results() -> None:
    table = gold("match_xg")
    won = (table["result"] == table["xg_favourite"]).sum()
    drawn = (table["result"] == "Draw").sum()
    counts = pd.Series({"Favourite lost": len(table) - won - drawn, "Draw": drawn,
                        "Favourite won": won})
    shares = counts / len(table)

    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.barh(shares.index, shares.values, color=BLUE, height=0.55)
    for position, (share, count) in enumerate(zip(shares, counts)):
        ax.annotate(f"{share:.1%}  ({count:,} matches)", (share, position), xytext=(6, 0),
                    textcoords="offset points", va="center", color=SECONDARY_INK)
    ax.set_title("The team with the higher xG won just over half of all matches")
    ax.set_xlim(0, 0.8)
    ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.set_xlabel("Share of 1,781 matches")
    clean_axes(ax, "x")
    ax.spines["bottom"].set_visible(False)
    save(fig, "06_xg_favourite_results")


def minute_trend() -> None:
    table = gold("minute_trend").sort_values("minute_band")
    fig, (shots_ax, rate_ax) = plt.subplots(1, 2, figsize=(11, 4.5))
    shots_ax.bar(table["minute_band"], table["shots"], color=BLUE, width=0.6)
    shots_ax.set_title("Shots rise late in matches")
    shots_ax.set_ylabel("Shots")
    shots_ax.yaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")

    rate_ax.bar(table["minute_band"], table["conversion"], color=BLUE, width=0.6)
    rate_ax.set_title("Conversion stays almost flat in normal time")
    rate_ax.set_ylabel("Goals per shot")
    rate_ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")

    for ax in (shots_ax, rate_ax):
        ax.set_xlabel("Match minute")
        ax.tick_params(axis="x", labelsize=9)
        clean_axes(ax)
    fig.tight_layout(w_pad=3)
    save(fig, "07_minute_trend")


def readable_feature(name: str) -> str:
    if "_encoded_" in name:
        group, value = name.split("_encoded_")
        return f"{group.replace('_', ' ').capitalize()}: {value}"
    return name.replace("_", " ").capitalize().replace("Gk", "GK")


def feature_importance() -> None:
    table = pd.read_csv(REPORTS_DIR / "feature_importance.csv").head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.barh(table["feature"].map(readable_feature), table["importance"], color=BLUE, height=0.6)
    top = table.iloc[-1]
    ax.annotate(f"{top['importance']:.0%}", (top["importance"], len(table) - 1), xytext=(6, 0),
                textcoords="offset points", va="center", color=SECONDARY_INK)
    ax.set_title("Shot angle and goalkeeper position drive the boosted-tree model")
    ax.set_xlabel("Share of total feature importance")
    ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    clean_axes(ax, "x")
    ax.spines["bottom"].set_visible(False)
    save(fig, "08_feature_importance")


def roc_points(labels: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(-scores)
    hits = labels[order]
    tpr = np.concatenate([[0], np.cumsum(hits) / hits.sum()])
    fpr = np.concatenate([[0], np.cumsum(1 - hits) / (1 - hits).sum()])
    return fpr, tpr


def roc_curves() -> None:
    predictions = gold("test_predictions")
    metrics = pd.read_csv(REPORTS_DIR / "metrics.csv").set_index("model")

    fig, ax = plt.subplots(figsize=(7, 6.5))
    ax.plot([0, 1], [0, 1], color=MUTED_INK, linewidth=1, label="Random guess")
    for name, column in ROC_MODELS.items():
        fpr, tpr = roc_points(predictions["is_goal"].to_numpy(), predictions[column].to_numpy())
        ax.plot(fpr, tpr, color=MODEL_COLORS[name], linewidth=2,
                label=f"{name} (AUC {metrics.loc[name, 'auc']:.3f})")
    ax.set_title("Our models rank shots almost as well as StatsBomb's xG")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    clean_axes(ax, "both")
    save(fig, "09_roc_curves")


def calibration_curves() -> None:
    table = pd.read_csv(REPORTS_DIR / "calibration.csv")
    fig, (main_ax, weighted_ax) = plt.subplots(1, 2, figsize=(11.5, 5.5), sharex=True, sharey=True)

    for ax in (main_ax, weighted_ax):
        ax.plot([0, 1], [0, 1], color=MUTED_INK, linewidth=1, zorder=1, label="Perfect calibration")

    for name in ROC_MODELS:
        rows = table[table["model"] == name]
        main_ax.plot(rows["predicted"], rows["actual"], color=MODEL_COLORS[name],
                     marker="o", markersize=7, linewidth=2, label=name)
    main_ax.set_title("Unweighted models are well calibrated")
    main_ax.legend(loc="upper left")

    name = "Logistic Regression (weighted)"
    rows = table[table["model"] == name]
    weighted_ax.plot(rows["predicted"], rows["actual"], color=MODEL_COLORS[name],
                     marker="o", markersize=7, linewidth=2, label=name)
    weighted_ax.set_title("Class weights inflate every probability")
    weighted_ax.legend(loc="upper left")

    for ax in (main_ax, weighted_ax):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Predicted goal probability")
        clean_axes(ax, "both")
    main_ax.set_ylabel("Actual goal rate")
    fig.tight_layout(w_pad=3)
    save(fig, "10_calibration")


def main():
    start = time.time()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("----- Figures -----")
    shot_volume_map()
    conversion_map()
    conversion_by_distance()
    player_finishing()
    team_goals_vs_xg()
    xg_favourite_results()
    minute_trend()
    feature_importance()
    roc_curves()
    calibration_curves()
    print(f"Total time: {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
