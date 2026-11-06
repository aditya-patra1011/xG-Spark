from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "statsbomb"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

MODELS_DIR = PROJECT_ROOT / "models"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

# Local Spark Environment (Windows)
JAVA_HOME = r"C:\Program Files\Java\jdk-17"
HADOOP_HOME = r"C:\hadoop"

SPARK_DRIVER_MEMORY = "4g"
SPARK_SHUFFLE_PARTITIONS = 16
