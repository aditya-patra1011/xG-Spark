import os 
import sys

from pyspark.sql import SparkSession

from src.config import (
    JAVA_HOME,
    HADOOP_HOME,
    SPARK_DRIVER_MEMORY,
    SPARK_SHUFFLE_PARTITIONS,
)

def _set_environment():
    """Point Spark at JDK 17 and winutils, and make workers use this venv's Python."""
    os.environ["JAVA_HOME"] = JAVA_HOME
    os.environ["HADOOP_HOME"] = HADOOP_HOME
    os.environ["PATH"] = os.path.join(HADOOP_HOME, "bin") + os.pathsep + os.environ["PATH"]
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


def get_spark(app_name: str = "xG-Spark") -> SparkSession:
    """Create (or reuse) a local SparkSession using all CPU cores"""
    _set_environment()

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.driver.memory", SPARK_DRIVER_MEMORY)
        .config("spark.sql.shuffle.partitions", SPARK_SHUFFLE_PARTITIONS)
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark
