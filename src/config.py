from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "statsbomb"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

MODELS_DIR = PROJECT_ROOT / "models"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

# Local Spark Environment (Windows)
JAVA_HOME = r"C:\Program Files\Java\jdk-17"
HADOOP_HOME = r"C:\hadoop"

SPARK_DRIVER_MEMORY = "4g"
SPARK_SHUFFLE_PARTITIONS = 16

# StatsBomb Open Data
STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# (competition_id, season_id) pairs to download - men's football
COMPETITIONS = [
    (2, 27),    # Premier League 2015/2016
    (11, 27),   # La Liga 2015/2016
    (12, 27),   # Serie A 2015/2016
    (7, 27),    # Ligue 1 2015/2016
    (9, 27),    # 1. Bundesliga 2015/2016
    (43, 3),    # FIFA World Cup 2018
    (43, 106),  # FIFA World Cup 2022
    (55, 43),   # UEFA Euro 2020
    (55, 282),  # UEFA Euro 2024
]

DOWNLOAD_WORKERS = 16   # Files download in parallel
DOWNLOAD_RETRIES = 3    # attempts per file before giving up
