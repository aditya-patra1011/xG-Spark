"""Phase 4 - Engineer the model features for every shot."""
import time

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.config import (
    BRONZE_DIR,
    GOAL_CENTER_Y,
    LEFT_POST_Y,
    PENALTY_BOX_X,
    PENALTY_BOX_Y_MAX,
    PENALTY_BOX_Y_MIN,
    PITCH_LENGTH,
    RIGHT_POST_Y,
    SILVER_DIR,
)
from src.preprocessing import BOOLEAN_FLAGS
from src.spark_session import get_spark

NEW_FEATURES = [
    "distance",
    "log_distance",
    "angle",
    "in_box",
    "defenders_in_cone",
    "nearest_defender",
    "gk_distance",
    "gk_off_line",
    "assist_type",
]


def add_geometry_features(df: DataFrame) -> DataFrame:
    """Add distance to goal, the visible goal angle and an in-the-box flag."""
    dx = F.lit(PITCH_LENGTH) - F.col("x")
    dy = F.lit(GOAL_CENTER_Y) - F.col("y")
    to_left_post = F.atan2(F.lit(LEFT_POST_Y) - F.col("y"), dx)
    to_right_post = F.atan2(F.lit(RIGHT_POST_Y) - F.col("y"), dx)
    in_box = (F.col("x") >= PENALTY_BOX_X) & F.col("y").between(
        PENALTY_BOX_Y_MIN, PENALTY_BOX_Y_MAX
    )

    return (
        df.withColumn("distance", F.sqrt(dx ** 2 + dy ** 2))
        .withColumn("log_distance", F.log1p("distance"))
        .withColumn("angle", F.abs(to_right_post - to_left_post))
        .withColumn("in_box", in_box.cast("int"))
    )


def add_freeze_frame_features(df: DataFrame) -> DataFrame:
    """Measure defensive pressure using the player positions at the moment of the shot.

    Uses Spark's higher-order functions, which run on arrays inside the JVM
    and are much faster than a Python UDF.
    """
    opponents = "filter(freeze_frame, p -> NOT p.teammate AND p.position.name != 'Goalkeeper')"
    goalkeeper = "filter(freeze_frame, p -> NOT p.teammate AND p.position.name = 'Goalkeeper')"

    # How far along the way to the goal line a player stands (0 = shooter, 1 = goal line)
    progress = f"(p.location[0] - x) / ({PITCH_LENGTH} - x)"
    in_cone = (
        f"p.location[0] > x AND p.location[0] <= {PITCH_LENGTH} "
        f"AND p.location[1] BETWEEN y + {progress} * ({LEFT_POST_Y} - y) "
        f"AND y + {progress} * ({RIGHT_POST_Y} - y)"
    )
    to_shooter = "sqrt(pow(p.location[0] - x, 2) + pow(p.location[1] - y, 2))"

    return (
        df.withColumn("defenders_in_cone", F.expr(f"size(filter({opponents}, p -> {in_cone}))"))
        .withColumn("nearest_defender", F.expr(f"array_min(transform({opponents}, p -> {to_shooter}))"))
        .withColumn("gk_distance", F.expr(f"array_min(transform({goalkeeper}, p -> {to_shooter}))"))
        .withColumn("gk_off_line", F.expr(f"array_min(transform({goalkeeper}, p -> {PITCH_LENGTH} - p.location[0]))"))
        # A few freeze frames have no goalkeeper or no outfield opponents
        .withColumn("nearest_defender", F.coalesce("nearest_defender", "distance"))
        .withColumn("gk_distance", F.coalesce("gk_distance", "distance"))
        .withColumn("gk_off_line", F.coalesce("gk_off_line", F.lit(0.0)))
    )


def add_assist_features(df: DataFrame, events: DataFrame) -> DataFrame:
    """Join each shot to the pass that created it and label the type of assist."""
    passes = events.filter(F.col("type.name") == "Pass").select(
        F.col("id").alias("key_pass_id"),
        F.when(F.col("pass.through_ball"), "Through Ball")
        .when(F.col("pass.cut_back"), "Cutback")
        .when(F.col("pass.cross"), "Cross")
        .otherwise("Other Pass")
        .alias("assist_type"),
    )
    return df.join(passes, on="key_pass_id", how="left").fillna(
        "No Assist", subset=["assist_type"]
    )


def flags_to_integers(df: DataFrame) -> DataFrame:
    """MLlib needs numbers, so turn the true/false columns into 1/0."""
    for column in BOOLEAN_FLAGS + ["is_home"]:
        df = df.withColumn(column, F.col(column).cast("int"))
    return df


def main():
    spark = get_spark("xG-features")
    start = time.time()

    shots = spark.read.parquet((SILVER_DIR / "shots").as_posix())
    events = spark.read.parquet((BRONZE_DIR / "events").as_posix())

    features = add_geometry_features(shots)
    features = add_freeze_frame_features(features)
    features = add_assist_features(features, events)
    features = flags_to_integers(features).drop("freeze_frame", "key_pass_id")

    path = (SILVER_DIR / "shot_features").as_posix()
    features.coalesce(4).write.mode("overwrite").parquet(path)

    # Read back from Parquet to verify
    result = spark.read.parquet(path)
    nulls = result.select(
        [F.sum(F.col(c).isNull().cast("int")).alias(c) for c in NEW_FEATURES]
    ).first()

    print("\n----- Shot features summary -----")
    print(f"Shots                  : {result.count():,}")
    print(f"Columns                : {len(result.columns)}")
    print(f"Missing in new features: {sum(nulls)}")
    print(f"Total time             : {time.time() - start:.0f} s")

    spark.stop()


if __name__ == "__main__":
    main()
