"""Phase 3 - Turn raw events into one clean, flat table of shots (silver layer)"""
import time

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.config import BRONZE_DIR, PITCH_LENGTH, PITCH_WIDTH, SILVER_DIR
from src.spark_session import get_spark

#StatsBomb only records these flags when they are true, so null means false
BOOLEAN_FLAGS = [
    "under_pressure",
    "first_time",
    "one_on_one",
    "open_goal",
    "aerial_won",
    "follows_dribble",
    "redirect",
]

#A shot cannot be used without these columns
REQUIRED_COLUMNS = ["shot_id", "match_id", "x", "y", "shot_type", "body_part", "outcome"]

def read_bronze(spark: SparkSession, name: str) -> DataFrame:
    return spark.read.parquet((BRONZE_DIR / name).as_posix())

def flatten_shots(events: DataFrame) -> DataFrame:
    """Keep only shot events and turn the nested fields into plain columns.
    
    Fields describing what happened after the shot (end_location, deflected,
    saved_off_target, saved_to_post) are left out to prevent data leakage.
    """
    return events.filter(F.col("type.name") == "Shot").select(
        F.col("id").alias("shot_id"),
        "match_id",
        "competition_id",
        "season_id",
        "period",
        "minute",
        "second",
        "possession",
        F.col("team.id").alias("team_id"),
        F.col("team.name").alias("team_name"),
        F.col("player.id").alias("player_id"),
        F.col("player.name").alias("player_name"),
        F.col("position.name").alias("position"),
        F.col("play_pattern.name").alias("play_pattern"),
        F.col("location")[0].alias("x"),
        F.col("location")[1].alias("y"),
        "under_pressure",
        F.col("shot.type.name").alias("shot_type"),
        F.col("shot.body_part.name").alias("body_part"),
        F.col("shot.technique.name").alias("technique"),
        "shot.first_time",
        "shot.one_on_one",
        "shot.open_goal",
        "shot.aerial_won",
        "shot.follows_dribble",
        "shot.redirect",
        "shot.key_pass_id",
        "shot.freeze_frame",
        "shot.statsbomb_xg",
        F.col("shot.outcome.name").alias("outcome"),
    )

def clean_shots(shots: DataFrame) -> DataFrame:
    """Remove unusable rows, fill flags, fix coordinates, and create the label."""
    print(f"Raw shots : {shots.count():>7,}")

    complete = shots.dropna(subset=REQUIRED_COLUMNS)
    print(f"After removing incomplete: {complete.count():>7,}")

    unique = complete.dropDuplicates(["shot_id"])
    print(f"After removing duplicates: {unique.count():>7,}")

    no_penalties = unique.filter(F.col("shot_type") != "Penalty")
    print(f"After removing penalties : {no_penalties.count():>7,}")

    return (
        no_penalties
        .fillna(False, subset=BOOLEAN_FLAGS)
        .withColumn("x", F.least(F.greatest("x", F.lit(0.0)), F.lit(PITCH_LENGTH)))
        .withColumn("y", F.least(F.greatest("y", F.lit(0.0)), F.lit(PITCH_WIDTH)))
        .withColumn("is_goal", (F.col("outcome") == "Goal").cast("int"))
    )

def add_match_context(shots: DataFrame, matches: DataFrame) -> DataFrame:
    """Add match date, competition details and whether the shooting team was at home."""
    context = matches.select(
        "match_id",
        F.to_date("match_date").alias("match_date"),
        F.col("competition.competition_name").alias("competition_name"),
        F.col("season.season_name").alias("season_name"),
        F.col("competition_stage.name").alias("competition_stage"),
        F.col("home_team.home_team_id").alias("home_team_id"),
    )
    return (
        shots.join(F.broadcast(context), on="match_id", how="left")
        .withColumn("is_home", F.col("team_id") == F.col("home_team_id"))
        .drop("home_team_id")
    )

def main():
    spark = get_spark("xG-preprocessing")
    start = time.time()

    events = read_bronze(spark, "events")
    matches = read_bronze(spark, "matches")

    #Cached because clean_shots counts the data at every step
    raw_shots = flatten_shots(events).cache()
    silver = add_match_context(clean_shots(raw_shots), matches)

    path = (SILVER_DIR / "shots").as_posix()
    silver.coalesce(4).write.mode("overwrite").parquet(path)
    raw_shots.unpersist()

    #Read back from Parquet to verify the silver layer
    shots = spark.read.parquet(path)
    total = shots.count()
    goals = shots.agg(F.sum("is_goal")).first()[0]

    print("\n---------Silver Layer Summary-----------")
    print(f"Shots       : {total:,}")
    print(f"Goals       : {goals:,}")
    print(f"Goal Rate   : {goals / total:.2%}")
    print(f"Matches     : {shots.select('match_id').distinct().count():,}")
    print(f"Total time  : {time.time() - start:.0f} s")

    spark.stop()


if __name__ == "__main__":
    main()
