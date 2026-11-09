"""Phase 7 - Score the xG models on unseen matches and compare them with StatsBomb's xG."""
import time

import pandas as pd
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.feature import Bucketizer
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.config import GOLD_DIR, REPORTS_DIR, SILVER_DIR
from src.model import LABEL, split_by_match
from src.spark_session import get_spark

MODELS = {
    "Baseline (goal rate)": "xg_baseline",
    "Logistic Regression": "xg_lr",
    "Logistic Regression (weighted)": "xg_lr_weighted",
    "Random Forest": "xg_rf",
    "Gradient-Boosted Trees": "xg_gbt",
    "StatsBomb xG": "statsbomb_xg",
}

# Narrow at the low end, because most shots have a small chance of scoring
CALIBRATION_SPLITS = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0000001]

EPSILON = 1e-15     # keeps log(0) out of the log loss


def log_loss_and_brier(df: DataFrame, column: str) -> tuple[float, float]:
    p = F.least(F.greatest(F.col(column), F.lit(EPSILON)), F.lit(1 - EPSILON))
    y = F.col(LABEL)
    row = df.agg(
        F.avg(-(y * F.log(p) + (1 - y) * F.log(1 - p))).alias("log_loss"),
        F.avg((p - y) ** 2).alias("brier"),
    ).first()
    return row["log_loss"], row["brier"]


def auc(df: DataFrame, column: str) -> float:
    evaluator = BinaryClassificationEvaluator(
        labelCol=LABEL, rawPredictionCol=column, metricName="areaUnderROC"
    )
    return evaluator.evaluate(df.withColumn(LABEL, F.col(LABEL).cast("double")))


def calibration_table(df: DataFrame, name: str, column: str) -> pd.DataFrame:
    """Group shots by predicted chance and compare the prediction with what happened."""
    bucketizer = Bucketizer(splits=CALIBRATION_SPLITS, inputCol=column, outputCol="bucket")
    grouped = (
        bucketizer.transform(df)
        .groupBy("bucket")
        .agg(
            F.count("*").alias("shots"),
            F.avg(column).alias("predicted"),
            F.avg(LABEL).alias("actual"),
        )
        .orderBy("bucket")
        .toPandas()
    )
    grouped.insert(0, "model", name)
    return grouped


def main():
    spark = get_spark("xG-evaluate")
    start = time.time()

    shots = spark.read.parquet((SILVER_DIR / "shot_features").as_posix())
    train, _ = split_by_match(shots)
    train_goal_rate = train.agg(F.avg(LABEL)).first()[0]

    predictions = (
        spark.read.parquet((GOLD_DIR / "test_predictions").as_posix())
        .withColumn("xg_baseline", F.lit(train_goal_rate))
        .cache()
    )

    metrics, calibration = [], []
    for name, column in MODELS.items():
        log_loss, brier = log_loss_and_brier(predictions, column)
        table = calibration_table(predictions, name, column)
        calibration.append(table)

        error = ((table["predicted"] - table["actual"]).abs() * table["shots"]).sum() / table["shots"].sum()
        metrics.append({
            "model": name,
            "auc": round(auc(predictions, column), 4),
            "log_loss": round(log_loss, 4),
            "brier": round(brier, 4),
            "mean_xg": round(predictions.agg(F.avg(column)).first()[0], 4),
            "calibration_error": round(error, 4),
        })

    metrics = pd.DataFrame(metrics)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(REPORTS_DIR / "metrics.csv", index=False)
    pd.concat(calibration).to_csv(REPORTS_DIR / "calibration.csv", index=False)

    print("\n----- Test set results -----")
    print(f"Shots: {predictions.count():,}   Actual goal rate: {predictions.agg(F.avg(LABEL)).first()[0]:.4f}")
    print(metrics.to_string(index=False))
    print(f"Total time: {time.time() - start:.0f} s")

    spark.stop()


if __name__ == "__main__":
    main()
