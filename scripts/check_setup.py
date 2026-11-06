import sys
from pathlib import Path

# Allow "from src..." imports when running this script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR
from src.spark_session import get_spark


def main():
    spark = get_spark("setup-check")
    print(f"Spark version : {spark.version}")
    print(f"Master        : {spark.sparkContext.master}")
    print(f"Cores (default parallelism): {spark.sparkContext.defaultParallelism}")

    # 1. A small distributed job
    df = spark.range(1_000_000).withColumnRenamed("id", "n")
    print(f"Sum of 0..999,999 = {df.groupBy().sum('n').collect()[0][0]}")

    # 2. Parquet write + read (this is what fails if winutils is missing)
    out_path = str(DATA_DIR / "setup_check.parquet")
    df.limit(10).write.mode("overwrite").parquet(out_path)
    print(f"Parquet round-trip rows: {spark.read.parquet(out_path).count()}")

    spark.stop()
    print("Setup OK")


if __name__ == "__main__":
    main()
