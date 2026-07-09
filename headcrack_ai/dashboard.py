from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pandas as pd
    import streamlit as st
except Exception:  # pragma: no cover
    pd = None
    st = None

from headcrack_ai.explain import explain_parlay
from headcrack_ai.ingest import legs_to_rows, load_markets_csv, load_markets_json
from headcrack_ai.optimizer import build_card
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.probability import monte_carlo_soccer_match


APP_CSS = """
<style>
.stApp {
    background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.14), transparent 32rem),
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.10), transparent 30rem),
        linear-gradient(180deg, #080b12 0%, #0d111a 48%, #080b12 100%);
    color: #eef2ff;
}
.block-container { max-width: 1320px; padding-top: 2rem; padding-bottom: 4rem; }
[data-testid="stSidebar"] { background: rgba(8, 11, 18, 0.94); border-right: 1px solid rgba(255,255,255,.1); }
[data-testid="stMetric"] {
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 18px;
    padding: 18px 18px 14px 18px;
    box-shadow: 0 14px 40px rgba(0,0,0,.18);
}
.hc-hero {
    padding: 28px 30px;
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 26px;
    background: linear-gradient(135deg, rgba(255,255,255,.09), rgba(255,255,255,.035));
    box-shadow: 0 24px 80px rgba(0,0,0,.24);
    margin-bottom: 1.25rem;
}
.hc-kicker { color: #38bdf8; font-size: .78rem; letter-spacing: .18em; text-transform: uppercase; font-weight: 800; }
.hc-title { font-size: 2.7rem; line-height: 1.02; font-weight: 900; margin: .35rem 0 .6rem; }
.hc-subtitle { color: #a7b0c0; max-width: 820px; font-size: 1.02rem; line-height: 1.55; }
.hc-pill-row { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1rem; }
.hc-pill {
    border: 1px solid rgba(255,255,255,.12);
    background: rgba(255,255,255,.055);
    color: #dbeafe;
    border-radius: 999px;
    padding: .42rem .72rem;
    font-size: .82rem;
    font-weight: 700;
}
.hc-section-title { font-size: 1.2rem; font-weight: 850; margin: 1.35rem 0 .7rem; }
.hc-card {
    padding: 18px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,.12);
    background: rgba(255,255,255,.055);
    box-shadow: 0 14px 40px rgba(0,0,0,.16);
}
.hc-muted { color: #9aa4b2; }
.hc-good { color: #22c55e; font-weight: 800; }
.hc-warn { color: #fb923c; font-weight: 800; }
.hc-bad { color: #f87171; font-weight: 800; }
div[data-testid="stDataFrame"] { border-radius: 18px; overflow: hidden; border: 1px solid rgba(255,255,255,.1); }
.stTabs [data-baseweb="tab-list"] { gap: .5rem; }
.stTabs [data-baseweb="tab"] {
    border-radius: 999px;
    padding: .55rem .9rem;
    background: rgba(255,255,255,.05);
    border: 1px solid rgba(255,255,255,.08);
}
.stTabs [aria-selected="true"] { background: rgba(56,189,248,.16); border-color: rgba(56,189,248,.32); }
</style>
"""


def _currency(value: float) -> str:
    return f"${value:,.2f}"


def _prob(value: float) -> str:
    return f"{value:.1%}"


def _edge_class(edge: float) -> str:
    if edge >= 0.05:
        return "hc-good"
    if edge >= 0:
        return "hc-warn"
    return "hc-bad"


def _safe_dataframe(rows: list[dict[str, Any]]) -> Any:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    preferred = [
        "label",
        "sportsbook",
        "odds",
        "model_probability",
        "implied_probability",
        "edge",
        "ev_per_dollar",
        "market_type",
        "team",
        "player",
        "tags",
    ]
    cols = [col for col in preferred if col in frame.columns]
    extras = [col for col in frame.columns if col not in cols]
    return frame[cols + extras]


def _render_hero() -> None:
    st.markdown(
        """
        <div class="hc-hero">
            <div class="hc-kicker">Headcrack AI</div>
            <div class="hc-title">Sports betting intelligence, without the chaos.</div>
            <div class="hc-subtitle">
                A clean command center for market intake, value detection, correlated parlay building,
                bankroll discipline, and soccer simulations. Built to make every pick explainable.
            </div>
            <div class="hc-pill-row">
                <span class="hc-pill">EV first</span>
                <span class="hc-pill">Correlation-aware</span>
                <span class="hc-pill">SQLite backed</span>
                <span class="hc-pill">Kalshi manual-ready</span>
                <span class="hc-pill">Odds API-ready</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_overview(store: SQLiteStore) -> None:
    rows = store.value_board(limit=200)
    frame = pd.DataFrame(rows)
    markets = len(frame)
    avg_edge = float(frame["edge"].mean()) if not frame.empty and "edge" in frame else 0.0
    positive = int((frame["edge"] > 0).sum()) if not frame.empty and "edge" in frame else 0
    best = float(frame["edge"].max()) if not frame.empty and "edge" in frame else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stored Markets", f"{markets:,}")
    c2.metric("Positive Edges", f"{positive:,}")
    c3.metric("Average Edge", _prob(avg_edge))
    c4.metric("Best Edge", _prob(best))

    st.markdown('<div class="hc-section-title">Stored Value Board</div>', unsafe_allow_html=True)
    if frame.empty:
        st.info("No markets saved yet. Upload a JSON/CSV file in Card Builder and save it to persistence.")
        return

    display = frame.copy()
    display["edge"] = display["edge"].astype(float)
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "edge": st.column_config.ProgressColumn("Edge", min_value=-0.25, max_value=0.25, format="%.2f"),
            "model_probability": st.column_config.NumberColumn("Model P", format="%.2f"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
        },
    )


def _render_card_builder(store: SQLiteStore, budget: float, min_edge: float) -> None:
    st.markdown('<div class="hc-section-title">Card Builder</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload manual market file", type=["json", "csv"], help="Use examples/markets_argentina_egypt.json as the template.")

    if uploaded is None:
        st.markdown(
            """
            <div class="hc-card">
                <b>Drop in a slate file to start.</b><br>
                <span class="hc-muted">The dashboard will rank legs, save them to SQLite, and build small, big, and nuclear cards.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    temp = Path(".headcrack_upload") / uploaded.name
    temp.parent.mkdir(exist_ok=True)
    temp.write_bytes(uploaded.read())
    legs = load_markets_json(temp) if temp.suffix == ".json" else load_markets_csv(temp)
    rows = legs_to_rows(legs)
    value_frame = _safe_dataframe(rows)

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("Save markets", use_container_width=True):
        store.save_legs(legs)
        st.success(f"Saved {len(legs)} legs to persistence.")
    c2.metric("Uploaded Legs", f"{len(legs):,}")
    if not value_frame.empty and "edge" in value_frame:
        c3.metric("Best Uploaded Edge", _prob(float(value_frame["edge"].max())))

    st.markdown('<div class="hc-section-title">Uploaded Value Board</div>', unsafe_allow_html=True)
    st.dataframe(value_frame, use_container_width=True, hide_index=True)

    card = build_card(legs, budget=budget, min_edge=min_edge)
    st.markdown('<div class="hc-section-title">Generated Cards</div>', unsafe_allow_html=True)
    tabs = st.tabs(["Small $60-$200", "Big $500-$2k", "Nuclear $1k+"])
    for tab, band in zip(tabs, ["small", "big", "nuclear"]):
        with tab:
            parlays = card.get(band, [])
            if not parlays:
                st.warning("No parlay candidates hit this target band with the current filters.")
                continue
            for idx, parlay in enumerate(parlays[:4], start=1):
                with st.expander(f"#{idx} · {_currency(parlay.stake)} → {_currency(parlay.gross_payout)} · EV {_currency(parlay.expected_value)}", expanded=idx == 1):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Payout", _currency(parlay.gross_payout))
                    c2.metric("Adjusted Hit", _prob(parlay.adjusted_probability))
                    c3.metric("EV", _currency(parlay.expected_value))
                    c4.metric("Risk", f"{parlay.risk_score:.2f}")
                    st.code(explain_parlay(parlay), language="text")


def _render_simulator() -> None:
    st.markdown('<div class="hc-section-title">Soccer Simulation</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    home_xg = c1.number_input("Home xG", min_value=0.0, value=1.8, step=0.1)
    away_xg = c2.number_input("Away xG", min_value=0.0, value=0.9, step=0.1)
    sims = c3.number_input("Simulations", min_value=1000, value=50000, step=1000)

    if st.button("Run simulation", use_container_width=True):
        result = monte_carlo_soccer_match(home_xg, away_xg, simulations=int(sims))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Home Win", _prob(float(result["home_win"])))
        c2.metric("Draw", _prob(float(result["draw"])))
        c3.metric("Away Win", _prob(float(result["away_win"])))
        c4.metric("BTTS", _prob(float(result["btts"])))
        c5, c6 = st.columns(2)
        c5.metric("Over 2.5", _prob(float(result["over_2_5"])))
        c6.metric("Over 3.5", _prob(float(result["over_3_5"])))
        st.markdown('<div class="hc-section-title">Most Common Scores</div>', unsafe_allow_html=True)
        scores = pd.DataFrame(
            [{"score": score, "count": count} for score, count in dict(result["top_scores"]).items()]
        )
        st.dataframe(scores, use_container_width=True, hide_index=True)


def _render_settings() -> None:
    st.markdown('<div class="hc-section-title">Workflow</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hc-card">
            <b>Daily flow</b><br><br>
            1. Ingest markets from JSON/CSV or provider adapter.<br>
            2. Review the value board for positive edges.<br>
            3. Build correlated cards by payout band.<br>
            4. Save bets and track results after settlement.<br>
            5. Use results to calibrate models over time.
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_dashboard() -> None:
    if st is None or pd is None:
        raise RuntimeError("Install streamlit and pandas to run the dashboard")

    st.set_page_config(page_title="Headcrack AI", page_icon="🧠", layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🧠 Headcrack AI")
        st.caption("Decision support for value betting.")
        database_url = st.text_input("Database URL", value="sqlite:///headcrack_ai.sqlite3")
        budget = st.number_input("Card Budget", min_value=1.0, value=20.0, step=1.0)
        min_edge = st.number_input("Minimum Edge", value=-0.02, step=0.01, format="%.2f")
        st.divider()
        st.caption("Tip: keep filters loose while exploring, then tighten edge thresholds before locking a card.")

    store = SQLiteStore(database_url)
    store.initialize()

    _render_hero()

    tab_overview, tab_builder, tab_sim, tab_workflow = st.tabs([
        "Overview",
        "Card Builder",
        "Simulator",
        "Workflow",
    ])

    with tab_overview:
        _render_overview(store)

    with tab_builder:
        _render_card_builder(store, budget=budget, min_edge=min_edge)

    with tab_sim:
        _render_simulator()

    with tab_workflow:
        _render_settings()


if __name__ == "__main__":
    run_dashboard()
