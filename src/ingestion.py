"""Phase 2: Ingest raw StatsBomb JSON with Spark and store it as Parquet (Bronze Layer)"""

import time 

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.config import BRONZE_DIR, RAW_DIR
from src.spark_session import get_spark

def read_json(spark: SparkSession, path) -> DataFrame:
    """Read StatsBomb JSON files. Each file is one JSON array, so multiline is required."""
    return spark.read.option("multiLine", True).json(path.as_posix())

def add_match_id(df: DataFrame) -> DataFrame:
    """Take match_id from the source file name, e.g., events/3754058.json -> 3754058"""
    file_name = F.col("_metadata.file_name")
    return df.withColumn(
        "match_id", F.regexp_extract(file_name, r"(\d+)\.json$", 1).cast("long")
    )

def ingest_competitions(spark: SparkSession) -> DataFrame:
    return read_json(spark, RAW_DIR / "competitions.json")

def ingest_matches(spark: SparkSession) -> DataFrame:
    return read_json(spark, RAW_DIR / "matches" / "*" / "*.json")

def ingest_lineups(spark: SparkSession) -> DataFrame:
    return add_match_id(read_json(spark, RAW_DIR / "lineups" / "*.json"))

def ingest_events(spark: SparkSession, matches: DataFrame) -> DataFrame:
    """Read all event files and tag every event with its competition and season."""
    events = add_match_id(read_json(spark, RAW_DIR / "events" / "*.json"))
    match_keys = matches.select(
        "match_id",
        F.col("competition.competition_id").alias("competition_id"),
        F.col("season.season_id").alias("season_id"),
    )
    # matches is tiny (1,781 rows): broadcast it to every core instead of shuffling 6M events
    return events.join(F.broadcast(match_keys), on="match_id", how="left")

def write_parquet(df: DataFrame, name: str, partition_by=None, single_file=False) -> str:
    """Write a DataFrame to data/bronze/<name> as Parquet"""
    path = (BRONZE_DIR / name).as_posix()
    if single_file:
        df = df.coalesce(1)
    writer = df.write.mode("overwrite")
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.parquet(path)
    return path

def main():
    spark = get_spark("xG-ingestion")
    start = time.time()

    print("Reading competitions and matches...")
    competitions = ingest_competitions(spark)
    matches = ingest_matches(spark)
    write_parquet(competitions, "competitions", single_file=True)
    write_parquet(matches, "matches", single_file=True)

    print("Reading Lineups...")
    write_parquet(ingest_lineups(spark), "lineups")

    print("Reading events (about 5 GB of JSON - this takes a few minutes)...")
    events = ingest_events(spark, matches)
    print(f"    Input partitions: {events.rdd.getNumPartitions()}")
    write_parquet(events, "events", partition_by=["competition_id", "season_id"])

    #Read back from Parquet to verify the bronze layer
    print("\n-------BRONZE LAYER SUMMARY-----------")
    for name in ["competitions", "matches", "lineups", "events"]:
        n = spark.read.parquet((BRONZE_DIR / name).as_posix()).count()
        print(f"{name:<13}: {n:>10,} rows")

    bronze_events = spark.read.parquet((BRONZE_DIR / "events").as_posix())
    unmatched = bronze_events.filter(F.col("competition_id").isNull()).count()
    print(f"Events without a competition: {unmatched}")
    print(f"Total time: {time.time() - start:.0f} s")

    spark.stop()

if __name__ == "__main__":
    main()
