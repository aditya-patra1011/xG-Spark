"""Phase 10 - Prepare the small data files that the Streamlit dashboard reads.

The dashboard runs without Spark or the 5 GB dataset, so everything it needs is
exported here and stored in dashboard/datasets.
"""
import json
import time

import numpy as np
import pandas as pd
from pyspark.ml import PipelineModel
from pyspark.sql import functions as F

from src.config import BRONZE_DIR, DASHBOARD_DATA_DIR, GOLD_DIR, MODELS_DIR, SILVER_DIR
from src.model import CATEGORICAL_FEATURES, NUMERIC_FEATURES, split_by_match
from src.spark_session import get_spark

ROC_POINTS = 300
LEAGUE_POINTS = {"Home": (3, 0), "Draw": (1, 1), "Away": (0, 3)}


def read_players(lineups):
    """One row per player, preferring the short name fans actually use."""
    players = lineups.select(F.explode("lineup").alias("p"))
    return players.groupBy(F.col("p.player_id").alias("player_id")).agg(
        F.max(F.coalesce("p.player_nickname", "p.player_name")).alias("display_name"),
        F.max("p.country.name").alias("nationality"),
        F.sum((F.size("p.positions") > 0).cast("int")).alias("appearances"),
    )


def read_matches(bronze_matches):
    return bronze_matches.select(
        "match_id",
        F.to_date("match_date").alias("match_date"),
        F.col("competition.competition_name").alias("competition"),
        F.col("season.season_name").alias("season"),
        F.col("competition_stage.name").alias("stage"),
        "match_week",
        F.col("home_team.home_team_id").alias("home_id"),
        F.col("away_team.away_team_id").alias("away_id"),
        "home_score",
        "away_score",
        F.col("stadium.name").alias("stadium"),
        F.col("referee.name").alias("referee"),
        F.col("home_team.managers")[0]["name"].alias("home_manager"),
        F.col("away_team.managers")[0]["name"].alias("away_manager"),
    )


def score_distribution(chances: np.ndarray) -> np.ndarray:
    """Probability of scoring exactly 0, 1, 2... goals, treating each shot as independent."""
    distribution = np.array([1.0])
    for chance in chances:
        distribution = np.convolve(distribution, [1 - chance, chance])
    return distribution


def result_probabilities(home: np.ndarray, away: np.ndarray) -> tuple[float, float, float]:
    """Chance of a home win, draw and away win implied by the two teams' shots."""
    outcomes = np.outer(score_distribution(home), score_distribution(away))
    home_win = np.tril(outcomes, -1).sum()
    draw = np.trace(outcomes)
    return float(home_win), float(draw), float(1 - home_win - draw)


def add_match_xg(matches: pd.DataFrame, shots: pd.DataFrame) -> pd.DataFrame:
    grouped = {key: group for key, group in shots.groupby("match_id")}
    rows = []
    for match in matches.itertuples():
        match_shots = grouped.get(match.match_id)
        if match_shots is None:
            home, away = np.array([]), np.array([])
        else:
            home = match_shots.loc[match_shots["is_home"] == 1, "statsbomb_xg"].to_numpy()
            away = match_shots.loc[match_shots["is_home"] == 0, "statsbomb_xg"].to_numpy()
        home_win, draw, away_win = result_probabilities(home, away)
        rows.append({
            "match_id": match.match_id,
            "home_xg": home.sum(),
            "away_xg": away.sum(),
            "home_shots": len(home),
            "away_shots": len(away),
            "prob_home": home_win,
            "prob_draw": draw,
            "prob_away": away_win,
        })
    return matches.merge(pd.DataFrame(rows).round(4), on="match_id")


def team_seasons(matches: pd.DataFrame) -> pd.DataFrame:
    """Actual and expected league records, one row per team per competition season."""
    sides = []
    for side, other in [("home", "away"), ("away", "home")]:
        table = pd.DataFrame({
            "competition": matches["competition"],
            "season": matches["season"],
            "team_id": matches[f"{side}_id"],
            "team": matches[f"{side}_team"],
            "goals_for": matches[f"{side}_score"],
            "goals_against": matches[f"{other}_score"],
            "xg_for": matches[f"{side}_xg"],
            "xg_against": matches[f"{other}_xg"],
            "expected_points": 3 * matches[f"prob_{side}"] + matches["prob_draw"],
        })
        table["win"] = (table["goals_for"] > table["goals_against"]).astype(int)
        table["draw"] = (table["goals_for"] == table["goals_against"]).astype(int)
        table["loss"] = (table["goals_for"] < table["goals_against"]).astype(int)
        sides.append(table)

    combined = pd.concat(sides)
    combined["matches"] = 1
    summary = combined.groupby(["competition", "season", "team_id", "team"], as_index=False).sum()
    summary["points"] = 3 * summary["win"] + summary["draw"]
    return summary.round(2)


def export_logistic_model(spark, feature_sample) -> dict:
    """Write the trained Logistic Regression as plain numbers, so it runs without Spark."""
    model = PipelineModel.load((MODELS_DIR / "lr").as_posix())
    scaler, classifier = model.stages[-2], model.stages[-1]
    schema = model.transform(feature_sample.limit(1)).schema
    attrs = schema["assembled"].metadata["ml_attr"]["attrs"]
    names = {a["idx"]: a["name"] for group in attrs.values() for a in group}

    deviations = scaler.std.toArray()
    coefficients = classifier.coefficients.toArray()
    weights = {
        names[i]: float(coefficients[i] / deviations[i]) if deviations[i] > 0 else 0.0
        for i in range(len(coefficients))
    }
    categories = {
        column: sorted(
            name.split("_encoded_", 1)[1] for name in weights
            if name.startswith(f"{column}_encoded_") and "__unknown" not in name
        )
        for column in CATEGORICAL_FEATURES
    }
    # One level of each category is dropped by one-hot encoding, so add those back
    for stage in model.stages:
        if stage.__class__.__name__ == "StringIndexerModel":
            for column, labels in zip(CATEGORICAL_FEATURES, stage.labelsArray):
                categories[column] = list(labels)
    return {
        "intercept": classifier.intercept,
        "weights": weights,
        "numeric": NUMERIC_FEATURES,
        "categories": categories,
    }


def predict_logistic(exported: dict, row: dict) -> float:
    score = exported["intercept"]
    for column in exported["numeric"]:
        score += exported["weights"][column] * row[column]
    for column in CATEGORICAL_FEATURES:
        score += exported["weights"].get(f"{column}_encoded_{row[column]}", 0.0)
    return float(1 / (1 + np.exp(-score)))


def roc_points(labels: np.ndarray, scores: np.ndarray) -> pd.DataFrame:
    order = np.argsort(-scores)
    hits = labels[order]
    tpr = np.concatenate([[0], np.cumsum(hits) / hits.sum()])
    fpr = np.concatenate([[0], np.cumsum(1 - hits) / (1 - hits).sum()])
    keep = np.unique(np.linspace(0, len(tpr) - 1, ROC_POINTS).astype(int))
    return pd.DataFrame({"fpr": fpr[keep].round(4), "tpr": tpr[keep].round(4)})


def main():
    spark = get_spark("xG-dashboard-export")
    start = time.time()
    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

    features = spark.read.parquet((SILVER_DIR / "shot_features").as_posix())
    lineups = spark.read.parquet((BRONZE_DIR / "lineups").as_posix())
    bronze_matches = spark.read.parquet((BRONZE_DIR / "matches").as_posix())

    players = read_players(lineups)
    teams = features.groupBy("team_id").agg(F.max("team_name").alias("team"))

    columns = [
        "shot_id", "match_id", "competition_name", "season_name", "period", "minute", "second",
        "team_id", "team", "player_id", "player", "position", "play_pattern", "x", "y",
        "shot_type", "body_part", "technique", "assist_type", "outcome", "is_goal", "is_home",
        "statsbomb_xg", "distance", "angle", "defenders_in_cone", "nearest_defender",
        "gk_distance", "under_pressure", "first_time", "one_on_one",
    ]
    shots = (
        features.drop("team_name")
        .join(F.broadcast(teams), on="team_id")
        .join(players.select("player_id", "display_name"), on="player_id", how="left")
        .withColumn("player", F.coalesce("display_name", "player_name"))
        .select(columns)
        .toPandas()
        .rename(columns={"competition_name": "competition", "season_name": "season"})
    )
    for column, digits in [("statsbomb_xg", 4), ("distance", 2), ("angle", 4),
                           ("nearest_defender", 2), ("gk_distance", 2), ("x", 1), ("y", 1)]:
        shots[column] = shots[column].round(digits)

    home_names = teams.withColumnRenamed("team_id", "home_id").withColumnRenamed("team", "home_team")
    away_names = teams.withColumnRenamed("team_id", "away_id").withColumnRenamed("team", "away_team")
    matches = (
        read_matches(bronze_matches)
        .join(F.broadcast(home_names), on="home_id", how="left")
        .join(F.broadcast(away_names), on="away_id", how="left")
        .toPandas()
    )
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches = add_match_xg(matches, shots)
    seasons = team_seasons(matches)

    player_table = players.toPandas()

    shots.to_parquet(DASHBOARD_DATA_DIR / "shots.parquet", index=False, compression="zstd")
    matches.to_parquet(DASHBOARD_DATA_DIR / "matches.parquet", index=False, compression="zstd")
    seasons.to_parquet(DASHBOARD_DATA_DIR / "team_seasons.parquet", index=False, compression="zstd")
    player_table.to_parquet(DASHBOARD_DATA_DIR / "players.parquet", index=False, compression="zstd")

    # Export the model and prove it matches Spark's own test-set predictions
    train, test = split_by_match(features)
    exported = export_logistic_model(spark, train)
    (DASHBOARD_DATA_DIR / "lr_model.json").write_text(json.dumps(exported, indent=1), encoding="utf-8")

    spark_predictions = pd.read_parquet(GOLD_DIR / "test_predictions")
    sample = test.select("shot_id", *NUMERIC_FEATURES, *CATEGORICAL_FEATURES).toPandas()
    joined = sample.merge(spark_predictions[["shot_id", "xg_lr"]], on="shot_id")
    ours = np.array([predict_logistic(exported, row) for row in joined.to_dict("records")])
    largest_gap = float(np.abs(ours - joined["xg_lr"].to_numpy()).max())
    if largest_gap > 1e-6:
        raise ValueError(f"Exported model differs from Spark by up to {largest_gap}")

    roc = []
    for name, column in [("Logistic Regression", "xg_lr"), ("Gradient-Boosted Trees", "xg_gbt"),
                         ("Random Forest", "xg_rf"), ("StatsBomb xG", "statsbomb_xg")]:
        curve = roc_points(spark_predictions["is_goal"].to_numpy(), spark_predictions[column].to_numpy())
        curve.insert(0, "model", name)
        roc.append(curve)
    pd.concat(roc).to_csv(DASHBOARD_DATA_DIR / "roc.csv", index=False)

    print("\n----- Dashboard data -----")
    print(f"Shots    : {len(shots):,}")
    print(f"Matches  : {len(matches):,}")
    print(f"Players  : {len(player_table):,}")
    print(f"Largest gap between exported model and Spark: {largest_gap:.2e}")
    print(f"Total time: {time.time() - start:.0f} s")
    spark.stop()


if __name__ == "__main__":
    main()
