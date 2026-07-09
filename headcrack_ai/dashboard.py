from __future__ import annotations

from pathlib import Path

try:
    import pandas as pd
    import streamlit as st
except Exception:  # pragma: no cover
    pd = None
    st = None

from .explain import explain_card
from .ingest import legs_to_rows, load_markets_csv, load_markets_json
from .optimizer import build_card
from .probability import monte_carlo_soccer_match


def run_dashboard() -> None:
    if st is None or pd is None:
        raise RuntimeError("Install streamlit and pandas to run the dashboard")

    st.set_page_config(page_title="Headcrack AI", layout="wide")
    st.title("Headcrack AI")
    st.caption("Sports betting decision-support, EV finder, parlay optimizer, and tracker.")

    with st.sidebar:
        st.header("Inputs")
        budget = st.number_input("Budget", min_value=1.0, value=20.0, step=1.0)
        min_edge = st.number_input("Minimum edge", value=-0.02, step=0.01, format="%.2f")
        uploaded = st.file_uploader("Market file", type=["json", "csv"])

    tab_card, tab_sim = st.tabs(["Card Builder", "Soccer Simulation"])

    with tab_card:
        if uploaded is None:
            st.info("Upload a JSON or CSV market file. See examples/markets_argentina_egypt.json.")
        else:
            temp = Path(".headcrack_upload") / uploaded.name
            temp.parent.mkdir(exist_ok=True)
            temp.write_bytes(uploaded.read())
            legs = load_markets_json(temp) if temp.suffix == ".json" else load_markets_csv(temp)
            st.subheader("Value Board")
            st.dataframe(pd.DataFrame(legs_to_rows(legs)), use_container_width=True)
            card = build_card(legs, budget=budget, min_edge=min_edge)
            st.subheader("Generated Card")
            st.markdown(explain_card(card))

    with tab_sim:
        col1, col2, col3 = st.columns(3)
        home_xg = col1.number_input("Home xG", min_value=0.0, value=1.8, step=0.1)
        away_xg = col2.number_input("Away xG", min_value=0.0, value=0.9, step=0.1)
        sims = col3.number_input("Simulations", min_value=1000, value=50000, step=1000)
        if st.button("Run simulation"):
            st.json(monte_carlo_soccer_match(home_xg, away_xg, simulations=int(sims)))


if __name__ == "__main__":
    run_dashboard()
