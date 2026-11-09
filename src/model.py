"""Phase 6 - Train and tune the xG models with Spark MLlib."""
import time

import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.classification import (
    GBTClassifier,
    LogisticRegression,
    RandomForestClassifier,
)
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.feature import OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.config import (
    CV_FOLDS,
    CV_PARALLELISM,
    GOLD_DIR,
    MODELS_DIR,
    RANDOM_SEED,
    REPORTS_DIR,
    SILVER_DIR,
    TEST_BUCKETS,
)
from src.preprocessing import BOOLEAN_FLAGS
from src.spark_session import get_spark

LABEL = "is_goal"

NUMERIC_FEATURES = [
    "distance",
    "log_distance",
    "angle",
    "in_box",
    "defenders_in_cone",
    "nearest_defender",
    "gk_distance",
    "gk_off_line",
    "is_home",
] + BOOLEAN_FLAGS

CATEGORICAL_FEATURES = ["body_part", "technique", "shot_type", "play_pattern", "assist_type"]


def split_by_match(df: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Hold out whole matches, so shots from one game are never on both sides.

    Hashing the match id gives the same split on every run.
    """
    bucket = F.pmod(F.hash("match_id"), F.lit(TEST_BUCKETS))
    return df.filter(bucket != 0), df.filter(bucket == 0)


def add_training_columns(train: DataFrame) -> DataFrame:
    """Add a CV fold per match and a class weight that balances goals and non-goals."""
    goal_rate = train.agg(F.avg(LABEL)).first()[0]
    return (
        train.withColumn("fold", F.pmod(F.xxhash64("match_id"), F.lit(CV_FOLDS)).cast("int"))
        .withColumn(
            "class_weight",
            F.when(F.col(LABEL) == 1, 0.5 / goal_rate).otherwise(0.5 / (1 - goal_rate)),
        )
    )


def feature_stages(scale: bool) -> list:
    """Encode the categories and assemble everything into a single feature vector."""
    indexed = [f"{c}_index" for c in CATEGORICAL_FEATURES]
    encoded = [f"{c}_encoded" for c in CATEGORICAL_FEATURES]
    stages = [
        StringIndexer(inputCols=CATEGORICAL_FEATURES, outputCols=indexed, handleInvalid="keep"),
        OneHotEncoder(inputCols=indexed, outputCols=encoded),
        VectorAssembler(
            inputCols=NUMERIC_FEATURES + encoded,
            outputCol="assembled" if scale else "features",
        ),
    ]
    if scale:
        stages.append(StandardScaler(inputCol="assembled", outputCol="features"))
    return stages


def build_candidates() -> dict:
    """Each candidate is (classifier, parameter grid, needs scaled features)."""
    logistic = LogisticRegression(labelCol=LABEL, maxIter=100)
    weighted = LogisticRegression(labelCol=LABEL, maxIter=100, weightCol="class_weight")
    forest = RandomForestClassifier(labelCol=LABEL, numTrees=100, seed=RANDOM_SEED)
    boosted = GBTClassifier(labelCol=LABEL, stepSize=0.1, seed=RANDOM_SEED)

    return {
        "lr": (
            logistic,
            ParamGridBuilder().addGrid(logistic.regParam, [0.0, 0.001, 0.01]).build(),
            True,
        ),
        "lr_weighted": (
            weighted,
            ParamGridBuilder().addGrid(weighted.regParam, [0.0, 0.001, 0.01]).build(),
            True,
        ),
        "rf": (
            forest,
            ParamGridBuilder().addGrid(forest.maxDepth, [6, 10]).build(),
            False,
        ),
        "gbt": (
            boosted,
            ParamGridBuilder()
            .addGrid(boosted.maxDepth, [3, 5])
            .addGrid(boosted.maxIter, [50, 100])
            .build(),
            False,
        ),
    }


def tune(name: str, classifier, grid: list, scale: bool, train: DataFrame):
    """Pick the best hyperparameters by cross-validated AUC, folding by match."""
    pipeline = Pipeline(stages=feature_stages(scale) + [classifier])
    search = CrossValidator(
        estimator=pipeline,
        estimatorParamMaps=grid,
        evaluator=BinaryClassificationEvaluator(labelCol=LABEL),
        foldCol="fold",
        parallelism=CV_PARALLELISM,
        seed=RANDOM_SEED,
    )
    fitted = search.fit(train)

    results = [
        {
            "model": name,
            "params": ", ".join(f"{param.name}={value}" for param, value in params.items()),
            "cv_auc": round(auc, 4),
            "selected": auc == max(fitted.avgMetrics),
        }
        for params, auc in zip(grid, fitted.avgMetrics)
    ]
    return fitted.bestModel, results


def goal_probability(model, df: DataFrame, column: str) -> DataFrame:
    return model.transform(df).select(
        "shot_id", vector_to_array("probability")[1].alias(column)
    )


def feature_importance(gbt_model, sample: DataFrame) -> pd.DataFrame:
    """Match the importance scores of the boosted trees to readable feature names."""
    schema = gbt_model.transform(sample.limit(1)).schema
    attrs = schema["features"].metadata["ml_attr"]["attrs"]
    names = {a["idx"]: a["name"] for group in attrs.values() for a in group}
    scores = gbt_model.stages[-1].featureImportances.toArray()
    table = pd.DataFrame(
        {"feature": [names[i] for i in range(len(scores))], "importance": scores}
    )
    return table.sort_values("importance", ascending=False)


def main():
    spark = get_spark("xG-model")
    start = time.time()

    shots = spark.read.parquet((SILVER_DIR / "shot_features").as_posix())
    train, test = split_by_match(shots)
    train = add_training_columns(train).cache()
    test = test.cache()

    print(f"Train: {train.count():,} shots in {train.select('match_id').distinct().count():,} matches")
    print(f"Test : {test.count():,} shots in {test.select('match_id').distinct().count():,} matches")

    predictions = test.select("shot_id", "match_id", LABEL, "statsbomb_xg")
    all_results = []
    fitted_models = {}

    for name, (classifier, grid, scale) in build_candidates().items():
        model_start = time.time()
        model, results = tune(name, classifier, grid, scale, train)
        all_results.extend(results)
        fitted_models[name] = model

        model.write().overwrite().save((MODELS_DIR / name).as_posix())
        predictions = predictions.join(goal_probability(model, test, f"xg_{name}"), on="shot_id")
        best_auc = max(r["cv_auc"] for r in results)
        print(f"{name:<12} best CV AUC {best_auc:.4f}  ({time.time() - model_start:.0f} s)")

    path = (GOLD_DIR / "test_predictions").as_posix()
    predictions.coalesce(1).write.mode("overwrite").parquet(path)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_results).to_csv(REPORTS_DIR / "cv_results.csv", index=False)
    feature_importance(fitted_models["gbt"], train).to_csv(
        REPORTS_DIR / "feature_importance.csv", index=False
    )

    print(f"Test predictions: {spark.read.parquet(path).count():,} rows")
    print(f"Total time: {time.time() - start:.0f} s")
    spark.stop()


if __name__ == "__main__":
    main()
