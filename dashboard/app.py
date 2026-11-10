"""xG Spark dashboard. Start it from the project root with: streamlit run dashboard/app.py"""
from pathlib import Path

import streamlit as st

import ui

HERE = Path(__file__).resolve().parent

st.set_page_config(
    page_title="xG Spark | Football Intelligence",
    page_icon=":soccer:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.logo(str(HERE / "assets" / "logo.svg"), size="large")
ui.setup()

pages = [
    st.Page("views/home.py", title="Overview", default=True),
    st.Page("views/match_centre.py", title="Match Centre", url_path="match-centre"),
    st.Page("views/shot_explorer.py", title="Shot Explorer", url_path="shot-explorer"),
    st.Page("views/players.py", title="Players", url_path="players"),
    st.Page("views/teams.py", title="Teams", url_path="teams"),
    st.Page("views/shot_lab.py", title="Shot Lab", url_path="shot-lab"),
    st.Page("views/model_lab.py", title="Model Lab", url_path="model-lab"),
]
navigation = st.navigation(pages, position="top")
navigation.run()

st.html('<div class="note-text" style="text-align:center;margin-top:18px">'
        "Data provided by StatsBomb Open Data. Built with Apache Spark and Streamlit.</div>")
