"""Model Lab: how the models were built and how good they really are."""
import plotly.graph_objects as go
import streamlit as st

import store
import ui

COLORS = {
    "Logistic Regression": ui.GOLD,
    "Gradient-Boosted Trees": ui.RED,
    "Random Forest": "#a78bfa",
    "StatsBomb xG": ui.SKY,
}
SHORT = {
    "Logistic Regression": "Logistic Reg.",
    "Gradient-Boosted Trees": "Boosted Trees",
    "Random Forest": "Random Forest",
    "StatsBomb xG": "StatsBomb xG",
}

ui.page_head("Model", "Lab", "Four Spark MLlib models, tested on 364 matches they never saw.")

metrics = store.metrics().set_index("model")

with ui.panel("Ranking power (AUC on unseen matches)"):
    columns = st.columns(len(COLORS), gap="small")
    for column, name in zip(columns, COLORS):
        value = metrics.loc[name, "auc"]
        with column:
            ui.gauge((value - 0.5) / 0.5, f"{value:.3f}", SHORT[name],
                     f"Log loss {metrics.loc[name, 'log_loss']:.4f}")

st.write("")
roc_column, calibration_column = st.columns(2, gap="small")

with roc_column:
    with ui.panel("ROC curves"):
        roc = store.roc()
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random guess",
                                    line=dict(color=ui.MUTED, width=1), hoverinfo="skip"))
        for name, color in COLORS.items():
            curve = roc[roc["model"] == name]
            figure.add_trace(go.Scatter(
                x=curve["fpr"], y=curve["tpr"], mode="lines", name=SHORT[name],
                line=dict(color=color, width=2.3),
                hovertemplate=f"{SHORT[name]}<br>False positives: %{{x:.2f}}<br>True positives: %{{y:.2f}}<extra></extra>",
            ))
        ui.style_figure(figure, 410)
        figure.update_xaxes(title="False positive rate", range=[0, 1])
        figure.update_yaxes(title="True positive rate", range=[0, 1])
        ui.show(figure)

with calibration_column:
    with ui.panel("Calibration"):
        options = ["Logistic Regression", "Gradient-Boosted Trees", "Random Forest",
                   "Logistic Regression (weighted)", "StatsBomb xG"]
        chosen = st.selectbox("Model", options, label_visibility="collapsed")
        rows = store.calibration()
        rows = rows[rows["model"] == chosen]
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect calibration",
                                    line=dict(color=ui.MUTED, width=1), hoverinfo="skip"))
        figure.add_trace(go.Scatter(
            x=rows["predicted"], y=rows["actual"], mode="lines+markers", name=chosen,
            line=dict(color=ui.GOLD, width=2.4), marker=dict(size=10, color=ui.GOLD),
            text=rows["shots"],
            hovertemplate="Predicted: %{x:.1%}<br>Actually scored: %{y:.1%}<br>%{text:,} shots<extra></extra>",
        ))
        ui.style_figure(figure, 362)
        figure.update_xaxes(title="Predicted goal chance", range=[0, 1], tickformat=".0%")
        figure.update_yaxes(title="Actual goal rate", range=[0, 1], tickformat=".0%")
        ui.show(figure)

st.write("")
importance_column, lesson_column = st.columns([1.25, 1], gap="small")

with importance_column:
    with ui.panel("What the boosted trees look at"):
        table = store.feature_importance().head(12)

        def readable(name: str) -> str:
            if "_encoded_" in name:
                group, value = name.split("_encoded_")
                return f"{group.replace('_', ' ').capitalize()}: {value}"
            return name.replace("_", " ").capitalize().replace("Gk", "GK")

        figure = go.Figure(go.Bar(
            y=table["feature"].map(readable), x=table["importance"], orientation="h", width=0.58,
            marker=dict(color=ui.GOLD, line=dict(width=0)),
            hovertemplate="%{y}: %{x:.1%}<extra></extra>",
        ))
        ui.style_figure(figure, 410, margin=dict(l=8, r=16, t=6, b=36))
        figure.update_yaxes(autorange="reversed", automargin=True, showgrid=False, tickfont=dict(color=ui.INK))
        figure.update_xaxes(tickformat=".0%", title="Share of feature importance")
        ui.show(figure)

with lesson_column:
    with ui.panel("All scores"):
        table = store.metrics().rename(columns={
            "model": "Model", "auc": "AUC", "log_loss": "Log loss", "brier": "Brier",
            "mean_xg": "Mean xG", "calibration_error": "Cal. error",
        })
        st.dataframe(table, hide_index=True, width="stretch", height=250)
    st.write("")
    with ui.panel("The class-weights lesson"):
        weighted = metrics.loc["Logistic Regression (weighted)", "mean_xg"]
        plain = metrics.loc["Logistic Regression", "mean_xg"]
        one, two = st.columns(2, gap="small")
        with one:
            ui.ring(float(plain), store.percent(float(plain)), "Unweighted", "Average prediction")
        with two:
            ui.ring(float(weighted), store.percent(float(weighted)), "Weighted", "Real rate is 9.5%")

st.write("")
with ui.panel("How it was built"):
    steps = [
        ("Ingest", "6.28M JSON events to partitioned Parquet"),
        ("Clean", "43,924 non-penalty shots"),
        ("Engineer", "Angle, pressure and keeper features"),
        ("Query", "Six Spark SQL gold tables"),
        ("Train", "MLlib pipelines, 3-fold CV by match"),
        ("Test", "364 unseen matches"),
    ]
    st.html('<div class="steps">' + "".join(
        f"<div class=\"step\"><b>{ui.esc(a)}</b><span>{ui.esc(b)}</span></div>" for a, b in steps
    ) + "</div>")
