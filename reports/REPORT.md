# Practical 10: Big Data Analytics Using Apache Spark

## Expected Goals (xG) Model on StatsBomb Open Data

**Author:** Aditya Patra
**Source code:** <https://github.com/aditya-patra1011/xG-Spark>

---

## 1. Aim

To build an end-to-end big data pipeline in PySpark that ingests a large football event dataset, preprocesses it, analyses it with Spark SQL, trains machine learning models with MLlib, and presents the results with Matplotlib and mplsoccer.

## 2. Introduction

A football score hides how well a team actually played. A shot from one metre and a shot from forty metres each count as one attempt, yet their chances of scoring are very different. **Expected Goals (xG)** solves this by giving each shot the probability that it becomes a goal, based on the situation when it was taken.

Calculating xG is a big data problem. It starts from millions of nested JSON events, and each shot needs information such as the positions of all visible players at that moment. Apache Spark suits this work because it processes semi-structured data in parallel, offers SQL for analysis, and includes a machine learning library that runs on the same engine.

This project asks three questions:

1. Which features of a shot best predict a goal?
2. Can models trained in Spark MLlib approach the quality of StatsBomb's professional xG?
3. What do xG-based analyses reveal about players, teams and matches?

## 3. Theory

### 3.1 Apache Spark

Apache Spark is a distributed data processing engine. A **driver** program plans the work and **executors** run tasks in parallel on **partitions** of the data. This project uses local mode (`local[*]`), where the driver and executors share one machine and run on its 12 CPU cores.

| Concept | Meaning | Use in this project |
|---|---|---|
| DataFrame | A distributed table with named columns | All data processing |
| Lazy evaluation | Transformations only run when an action needs a result | Spark plans a whole phase before running it |
| DAG | The graph of steps Spark builds for a job | Lets Spark combine and reorder steps |
| Catalyst optimizer | Rewrites a logical query into an efficient physical plan | Visible through `explain()` |
| Shuffle | Moving rows between partitions, for example for a `GROUP BY` | Aggregations and joins |
| Partitioning | Splitting data into separate folders or files | Events are stored by competition and season |
| Partition pruning | Reading only the folders a query needs | A filter on one competition skips the rest |
| Broadcast join | Copying a small table to every executor, which avoids a shuffle | Joining matches to shots |
| Caching | Keeping a table in memory for reuse | Tables used by several queries |

### 3.2 Medallion architecture

Data moves through increasingly refined layers:

- **Raw:** the original JSON files.
- **Bronze:** the same data as compressed, partitioned Parquet.
- **Silver:** clean, validated tables with engineered features.
- **Gold:** aggregated tables ready for analysis and charts.

Parquet stores data by column, so a query reads only the columns it needs.

### 3.3 Spark SQL

Spark SQL runs SQL queries on DataFrames registered as temporary views. Queries go through the same optimizer as DataFrame code. This project uses Common Table Expressions (CTEs), `HAVING`, the `RANK()` window function, `CASE`, `PIVOT` and a broadcast join hint.

**Higher-order functions** such as `filter` and `transform` work on array columns directly inside the JVM. They are used for the player positions at each shot and avoid a much slower Python UDF.

### 3.4 Spark MLlib

MLlib provides distributed machine learning. A **Pipeline** chains preparation steps and a model into one object, so the same steps are applied in training and prediction. `StringIndexer` and `OneHotEncoder` encode categories, `VectorAssembler` builds the feature vector, and `StandardScaler` scales it for Logistic Regression. `CrossValidator` tries each hyperparameter setting across several folds.

| Algorithm | How it works |
|---|---|
| Logistic Regression | Fits a weighted sum of features and converts it into a probability |
| Random Forest | Averages many decision trees, each trained on a random sample of the data |
| Gradient-Boosted Trees | Adds small trees one at a time, each correcting the remaining error |

### 3.5 Evaluation metrics

| Metric | What it measures | Best value |
|---|---|---|
| AUC | How well the model ranks goals above non-goals | 1.0 |
| Log loss | Accuracy of the probabilities, penalising confident errors heavily | 0 |
| Brier score | Mean squared error of the probabilities | 0 |
| Calibration | Whether shots given a 20% chance are scored about 20% of the time | On the diagonal |

Calibration is essential here because an xG value is used as a probability, not only as a ranking.

## 4. Dataset Details

**Source:** [StatsBomb Open Data](https://github.com/statsbomb/open-data), a public collection of detailed football event data in JSON format.

| Competition | Season | Matches |
|---|---|---|
| Premier League | 2015/16 | 380 |
| La Liga | 2015/16 | 380 |
| Serie A | 2015/16 | 380 |
| Ligue 1 | 2015/16 | 377 |
| 1. Bundesliga (Bayer Leverkusen's season) | 2015/16 | 34 |
| FIFA World Cup | 2018 | 64 |
| FIFA World Cup | 2022 | 64 |
| UEFA Euro | 2020 | 51 |
| UEFA Euro | 2024 | 51 |
| **Total** | | **1,781** |

| Property | Value |
|---|---|
| Event records | 6,279,749 |
| Lineup records | 3,562 |
| Shot events | 44,557 |
| Shots after removing penalties | 43,924 |
| Goals | 4,158 (9.47% of shots) |
| Raw JSON size | 5.1 GB |
| Bronze Parquet size | about 710 MB |

Each shot record includes its location, body part, technique, outcome, StatsBomb's xG and a **freeze frame** of the visible players' positions at the moment of the shot. Locations use StatsBomb's 120 × 80 pitch, with the goal at x = 120 between y = 36 and y = 44.

## 5. System Architecture and Procedure

```
StatsBomb JSON (5.1 GB)
   |  Phase 1: parallel download
   v
Raw files
   |  Phase 2: ingestion
   v
Bronze: partitioned Parquet
   |  Phase 3: cleaning
   v
Silver: clean shots (43,924 rows)
   |  Phase 4: feature engineering
   v
Silver: shot features (43 columns)
   |--- Phase 5: Spark SQL ---> Gold: 6 analysis tables
   |--- Phase 6: MLlib -------> Saved models and test predictions
                                   |  Phase 7: evaluation
                                   v
                                Metrics and calibration
                                   |  Phase 8: visualization
                                   v
                                10 report figures
```

| Phase | Work done | Output |
|---|---|---|
| 1. Download | Fetched the JSON files in parallel, with retries | 5.1 GB of raw files |
| 2. Ingestion | Read multi-line JSON and wrote Parquet partitioned by competition and season | Bronze layer |
| 3. Preprocessing | Flattened shots, removed penalties and incomplete rows, filled flags, added match context | 43,924 clean shots |
| 4. Feature engineering | Added 9 features for geometry, defensive pressure and assists | `shot_features` |
| 5. Analytics | Ran 6 Spark SQL queries | Gold tables |
| 6. Machine learning | Tuned 4 models with cross-validation | Saved pipelines |
| 7. Evaluation | Scored models on unseen matches | Metrics and calibration |
| 8. Visualization | Produced charts and pitch maps | 10 figures |

### 5.1 Preventing data leakage

Fields that describe what happened after the shot, such as `end_location`, `deflected`, `saved_off_target` and `saved_to_post`, were excluded. The `goal_assist` flag was also excluded because it reveals the result. StatsBomb's xG was used only as a benchmark, never as a model input.

### 5.2 Engineered features

| Feature | Meaning |
|---|---|
| `distance`, `log_distance` | Distance to the centre of the goal |
| `angle` | The angle of the goal visible from the shot location |
| `in_box` | Whether the shot was inside the penalty area |
| `defenders_in_cone` | Opponents inside the triangle from the shooter to the posts |
| `nearest_defender` | Distance to the closest outfield opponent |
| `gk_distance`, `gk_off_line` | Goalkeeper's distance from the shooter and from the goal line |
| `assist_type` | Through ball, cutback, cross, other pass or no assist |

### 5.3 Model training

The models used 16 numeric and 5 categorical inputs. Whole matches were assigned to training (35,117 shots in 1,417 matches) or testing (8,807 shots in 364 matches), and no match appears in both. The three cross-validation folds were also split by match.

Hyperparameters were chosen by cross-validated AUC:

| Model | Selected settings | CV AUC |
|---|---|---|
| Logistic Regression | `regParam = 0` | 0.8066 |
| Logistic Regression (weighted) | `regParam = 0` | 0.8070 |
| Random Forest | `numTrees = 100`, `maxDepth = 10` | 0.7972 |
| Gradient-Boosted Trees | `maxDepth = 3`, `maxIter = 100` | 0.8045 |

## 6. Results

### 6.1 Model performance on unseen matches

| Model | AUC | Log loss | Brier | Mean xG | Calibration error |
|---|---|---|---|---|---|
| Baseline (always the goal rate) | 0.5000 | 0.3146 | 0.0862 | 0.0945 | not meaningful |
| Logistic Regression | 0.8217 | **0.2451** | 0.0695 | 0.0965 | 0.0069 |
| Logistic Regression (weighted) | 0.8221 | 0.5270 | 0.1727 | 0.3869 | 0.2916 |
| Random Forest | 0.8159 | 0.2498 | 0.0707 | 0.0958 | 0.0120 |
| Gradient-Boosted Trees | **0.8253** | 0.2455 | **0.0694** | 0.0976 | 0.0120 |
| StatsBomb xG (benchmark) | 0.8324 | 0.2411 | 0.0685 | 0.0929 | 0.0105 |

The actual goal rate in the test set was 0.0953. Bold marks the best of the models trained in this project.

- Every unweighted model improves strongly on the baseline.
- Gradient-Boosted Trees rank shots best, and Logistic Regression has the best log loss. The gap between them is too small to name a clear winner.
- StatsBomb's xG is still slightly better on every measure.
- Class weights hardly change the ranking but raise the mean prediction from 0.097 to 0.387. They are unsuitable when the output must be a true probability.

![ROC curves](figures/09_roc_curves.png)

![Calibration curves](figures/10_calibration.png)

### 6.2 What drives a goal

The angle of the goal visible to the shooter is the most important input, followed by the goalkeeper's position and defensive pressure. Importance can be shared between related inputs, which partly explains why `distance` ranks below `angle`.

![Feature importance](figures/08_feature_importance.png)

| Shot situation | Goals per shot |
|---|---|
| Under 5 units from goal | 55.3% |
| 30–35 units from goal | 1.6% |
| Inside the penalty area | 13.8% |
| Outside the penalty area | 3.4% |
| No defender in the shooting cone | 13.7% |
| One defender in the shooting cone | 5.9% |
| From a through ball | 30.5% |
| From a cross | 13.7% |

![Shot volume](figures/01_shot_volume.png)

![Conversion by zone](figures/02_zone_conversion.png)

![Conversion by distance and body part](figures/03_conversion_by_distance.png)

### 6.3 Spark SQL findings

**Players.** Luis Suárez outperformed xG the most, with 39 non-penalty goals from 25.65 xG (+13.35). These totals cover only the competitions in this dataset.

![Player finishing](figures/04_player_finishing.png)

**Teams.** League teams' goals closely follow their xG. Barcelona had the highest xG per match of the full league seasons, at 2.01.

![Team goals against xG](figures/05_team_goals_vs_xg.png)

**Matches.** The team with the higher non-penalty xG won 54.9% of matches, drew 26.1% and lost 19.0%. Real scores include penalties and own goals.

![Results of xG favourites](figures/06_xg_favourite_results.png)

**Timing.** The last 15 minutes of normal time produce the most shots, while conversion stays between 9% and 10% across normal time.

![Shots and conversion by minute](figures/07_minute_trend.png)

### 6.4 Interactive dashboard

The results are also presented in a seven-page Streamlit dashboard, with top navigation for Overview, Match Centre, Shot Explorer, Players, Teams, Shot Lab and Model Lab. Pitch views are interactive 3D scenes where each zone or shot stands as a column. The Shot Lab runs the trained Logistic Regression model as plain Python. Its predictions match Spark's to within 1e-15 on all 8,807 test shots.

![Dashboard overview](screenshots/dashboard_overview.png)

## 7. Output Screenshots

These are the executed notebook outputs for each phase.

### Phase 2: Ingestion

![Phase 2 output](screenshots/phase2_ingestion.png)

### Phase 3: Preprocessing

![Phase 3 output](screenshots/phase3_preprocessing.png)

### Phase 4: Feature Engineering

![Phase 4 output](screenshots/phase4_features.png)

### Phase 5: Spark SQL Analytics

![Phase 5 output](screenshots/phase5_spark_sql.png)

### Phase 6: Machine Learning

![Phase 6 output](screenshots/phase6_mllib.png)

### Phase 7: Evaluation

![Phase 7 output](screenshots/phase7_evaluation.png)

## 8. Limitations

- All test results come from one held-out split, so small differences between models may not be statistically meaningful.
- The pipeline ran in Spark local mode on a single machine, and it hasn't been tested on a multi-node cluster.
- The models use only what the event data records. They don't know the shooter's skill or exactly how the ball was struck.
- Competition coverage is uneven: most league data is from 2015/16, and Bayer Leverkusen is the only Bundesliga team with a full season.
- Hyperparameters were searched over a small grid to keep training time practical.

## 9. Conclusion

The project built a complete Spark pipeline, from 5.1 GB of raw JSON to tuned models and report figures. Spark handled 6.3 million nested events on a single laptop, and its higher-order functions, SQL engine and MLlib covered each stage of the work.

The trained models reach an AUC of 0.82–0.83 on unseen matches and are well calibrated, close to StatsBomb's professional xG. Shot angle, goalkeeper position and defensive pressure were the strongest signals. The main modelling lesson is that class balancing, which is common for imbalanced data, damaged the probabilities that xG depends on.

## 10. Source Code

| Module | Purpose |
|---|---|
| [`config.py`](../src/config.py) | Paths, Spark settings and pitch geometry |
| [`spark_session.py`](../src/spark_session.py) | Creates the Spark session |
| [`download_data.py`](../src/download_data.py) | Phase 1: data download |
| [`ingestion.py`](../src/ingestion.py) | Phase 2: bronze layer |
| [`preprocessing.py`](../src/preprocessing.py) | Phase 3: silver layer |
| [`features.py`](../src/features.py) | Phase 4: feature engineering |
| [`analytics.py`](../src/analytics.py) | Phase 5: Spark SQL |
| [`model.py`](../src/model.py) | Phase 6: MLlib training |
| [`evaluate.py`](../src/evaluate.py) | Phase 7: evaluation |
| [`visualize.py`](../src/visualize.py) | Phase 8: visualization |
| [`export_dashboard.py`](../src/export_dashboard.py) | Phase 10: dashboard data |
| [`dashboard/`](../dashboard/app.py) | Streamlit dashboard |
| [`xg_pipeline.ipynb`](../notebooks/xg_pipeline.ipynb) | Full notebook with outputs |

## References

1. StatsBomb Open Data: <https://github.com/statsbomb/open-data>
2. Apache Spark documentation: <https://spark.apache.org/docs/3.5.3/>
3. mplsoccer documentation: <https://mplsoccer.readthedocs.io/>
