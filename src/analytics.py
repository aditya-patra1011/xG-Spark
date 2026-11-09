"""Phase 5 - Answer football questions with Spark SQL and save them as gold tables."""
import time

from src.config import BRONZE_DIR, GOLD_DIR, SILVER_DIR
from src.spark_session import get_spark

MIN_PLAYER_SHOTS = 50   # fewer shots than this says little about finishing skill
MIN_TEAM_MATCHES = 3    # the open data has only 2 matches for some teams

QUERIES = {
    # Aggregation with HAVING: who scores more than their chances suggest?
    "player_finishing": f"""
        SELECT player_id, player_name,
               COUNT(*) AS shots,
               SUM(is_goal) AS goals,
               ROUND(SUM(statsbomb_xg), 2) AS xg,
               ROUND(SUM(is_goal) - SUM(statsbomb_xg), 2) AS goals_minus_xg,
               ROUND(AVG(is_goal), 3) AS conversion,
               ROUND(AVG(statsbomb_xg), 3) AS xg_per_shot
        FROM shot_features
        GROUP BY player_id, player_name
        HAVING COUNT(*) >= {MIN_PLAYER_SHOTS}
    """,

    # CTE + window function: rank the teams inside each competition
    "team_attack": f"""
        WITH team_totals AS (
            SELECT competition_name, season_name, team_name,
                   COUNT(DISTINCT match_id) AS matches,
                   COUNT(*) AS shots,
                   SUM(is_goal) AS goals,
                   SUM(statsbomb_xg) AS xg
            FROM shot_features
            GROUP BY competition_name, season_name, team_name
            HAVING COUNT(DISTINCT match_id) >= {MIN_TEAM_MATCHES}
        )
        SELECT competition_name, season_name, team_name, matches, shots, goals,
               ROUND(xg, 2) AS xg,
               ROUND(shots / matches, 2) AS shots_per_match,
               ROUND(goals / matches, 2) AS goals_per_match,
               ROUND(xg / matches, 2) AS xg_per_match,
               RANK() OVER (PARTITION BY competition_name, season_name
                            ORDER BY xg / matches DESC) AS xg_rank
        FROM team_totals
    """,

    # CTE + broadcast join: compare each match's xG with the real result
    "match_xg": """
        WITH match_totals AS (
            SELECT match_id,
                   SUM(CASE WHEN is_home = 1 THEN statsbomb_xg ELSE 0 END) AS home_xg,
                   SUM(CASE WHEN is_home = 0 THEN statsbomb_xg ELSE 0 END) AS away_xg
            FROM shot_features
            GROUP BY match_id
        )
        SELECT /*+ BROADCAST(m) */
               t.match_id,
               m.competition.competition_name AS competition_name,
               m.season.season_name AS season_name,
               m.home_team.home_team_name AS home_team,
               m.away_team.away_team_name AS away_team,
               m.home_score,
               m.away_score,
               ROUND(t.home_xg, 3) AS home_xg,
               ROUND(t.away_xg, 3) AS away_xg,
               CASE WHEN m.home_score > m.away_score THEN 'Home'
                    WHEN m.home_score < m.away_score THEN 'Away'
                    ELSE 'Draw' END AS result,
               CASE WHEN t.home_xg > t.away_xg THEN 'Home' ELSE 'Away' END AS xg_favourite
        FROM match_totals t
        JOIN matches m ON t.match_id = m.match_id
    """,

    # Spatial binning: split the attacking half into 5 x 5 zones
    "shot_zones": """
        SELECT LEAST(FLOOR(x / 5) * 5, 115) AS zone_x,
               LEAST(FLOOR(y / 5) * 5, 75) AS zone_y,
               COUNT(*) AS shots,
               SUM(is_goal) AS goals,
               ROUND(AVG(is_goal), 3) AS conversion,
               ROUND(AVG(statsbomb_xg), 3) AS avg_xg
        FROM shot_features
        WHERE x >= 60
        GROUP BY zone_x, zone_y
    """,

    # CASE: group shots by the phase of the match
    "minute_trend": """
        SELECT CASE WHEN period > 2 THEN 'Extra Time'
                    WHEN period = 1 AND minute < 15 THEN '00-15'
                    WHEN period = 1 AND minute < 30 THEN '15-30'
                    WHEN period = 1 THEN '30-45+'
                    WHEN minute < 60 THEN '45-60'
                    WHEN minute < 75 THEN '60-75'
                    ELSE '75-90+' END AS minute_band,
               COUNT(*) AS shots,
               SUM(is_goal) AS goals,
               ROUND(AVG(is_goal), 3) AS conversion,
               ROUND(AVG(statsbomb_xg), 3) AS avg_xg
        FROM shot_features
        GROUP BY minute_band
    """,

    # PIVOT: conversion by distance, with one column for each body part
    "distance_body_part": """
        SELECT distance_band,
               ROUND(right_foot, 3) AS right_foot,
               ROUND(left_foot, 3) AS left_foot,
               ROUND(head, 3) AS head
        FROM (
            SELECT CASE WHEN distance < 6 THEN '00-06'
                        WHEN distance < 12 THEN '06-12'
                        WHEN distance < 18 THEN '12-18'
                        WHEN distance < 24 THEN '18-24'
                        ELSE '24+' END AS distance_band,
                   body_part,
                   is_goal
            FROM shot_features
        )
        PIVOT (AVG(is_goal) FOR body_part IN
               ('Right Foot' AS right_foot, 'Left Foot' AS left_foot, 'Head' AS head))
    """,
}


def main():
    spark = get_spark("xG-analytics")
    start = time.time()

    # Temporary views let Spark SQL query the Parquet data by name
    spark.read.parquet((SILVER_DIR / "shot_features").as_posix()).createOrReplaceTempView("shot_features")
    spark.read.parquet((BRONZE_DIR / "matches").as_posix()).createOrReplaceTempView("matches")

    # Cached because all the queries read the same table
    spark.catalog.cacheTable("shot_features")

    print("\n----- Gold tables -----")
    for name, query in QUERIES.items():
        path = (GOLD_DIR / name).as_posix()
        spark.sql(query).coalesce(1).write.mode("overwrite").parquet(path)
        print(f"{name:<20} {spark.read.parquet(path).count():>6,} rows")

    spark.catalog.uncacheTable("shot_features")
    print(f"Total time: {time.time() - start:.0f} s")

    spark.stop()


if __name__ == "__main__":
    main()
