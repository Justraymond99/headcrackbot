from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

import pandas as pd

from headcrack_ai.calibration import build_calibration_report, format_calibration_report
from headcrack_ai.config import HeadcrackConfig
from headcrack_ai.settings import get_settings
from headcrack_ai.dashboard_home import render_dashboard_home
from headcrack_ai.dashboard_pages import (
    render_ai_picks,
    render_arbitrage,
    render_build_card,
    render_dfs_optimizer,
    render_ev_finder,
    render_fetch_bar,
    render_monster_gpt,
    render_odds_screen,
    render_projections,
    render_simulator,
    render_whale_watch,
)
from headcrack_ai.dashboard_ui import (
    GREEN,
    dataframe_compact,
    hero,
    inject_theme,
    section,
)
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.plain_language import value_board_to_friendly_rows
from headcrack_ai.reports import build_tracking_report, format_tracking_report
from headcrack_ai.services import HeadcrackAIService
from headcrack_ai.soccer import SOCCER_LEAGUES

# key, label, emoji
NAV = [
    (None, [("dashboard", "Dashboard", "◧")]),
    (
        "Analysis",
        [
            ("value_board", "Value Board", "◎"),
            ("parlay", "Parlay Builder", "▤"),
            ("simulation", "Simulation Engine", "◈"),
            ("line_movement", "Line Movement", "◺"),
        ],
    ),
    (
        "Tools",
        [
            ("upload", "Upload Lines", "⇪"),
            ("model_predictions", "Model Predictions", "◍"),
            ("projections", "Projections", "◭"),
            ("backtesting", "Backtesting", "◔"),
            ("bet_tracker", "Bet Tracker", "▦"),
            ("reports", "Reports", "▣"),
        ],
    ),
    (
        "Edge Tools",
        [
            ("monstergpt", "MonsterGPT", "✦"),
            ("odds_screen", "Odds Screen", "▥"),
            ("ev_finder", "+EV Finder", "▲"),
            ("prop_optimizer", "Prop Optimizer", "◆"),
            ("arbitrage", "Arbitrage", "⇄"),
        ],
    ),
    (
        "Settings",
        [
            ("preferences", "Preferences", "⚙"),
            ("api_keys", "API Keys", "⚿"),
            ("help", "Help & Docs", "?"),
        ],
    ),
]


def _has_key() -> bool:
    return bool(HeadcrackConfig.from_env().odds_api_key)


def _sidebar(config: HeadcrackConfig, store: SQLiteStore) -> tuple[str, float, str, object, object]:
    with st.sidebar:
        st.markdown(
            '<div class="hc-logo"><div class="mark">🧠</div>'
            '<div class="name">HEADCRACK <span>AI</span></div></div>',
            unsafe_allow_html=True,
        )

        active = st.session_state.get("page", "dashboard")
        for group_label, items in NAV:
            if group_label:
                st.markdown(f'<div class="hc-nav-label">{group_label}</div>', unsafe_allow_html=True)
            for key, label, icon in items:
                if st.button(
                    f"{icon}   {label}",
                    key=f"nav_{key}",
                    type="primary" if key == active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["page"] = key
                    st.rerun()

        with st.expander("Data & odds"):
            budget = st.number_input("Bet budget ($)", min_value=1.0, value=20.0, step=1.0)
            uploaded = st.file_uploader("Picks file (JSON/CSV)", type=["json", "csv"])
            kalshi_upload = st.file_uploader("Kalshi / prediction CSV", type=["csv"])
            if _has_key():
                st.markdown(f'<span class="hc-status on">Live odds connected</span>', unsafe_allow_html=True)
            else:
                st.warning("Set ODDS_API_KEY in .env")

        tracking = build_tracking_report(store)["overall"]
        bankroll = st.session_state.get("bankroll", 2450.0)
        pl = tracking.get("profit_loss", 0.0)
        pct = (pl / bankroll * 100) if bankroll else 0.0
        st.markdown(
            f'<div class="hc-bankroll"><div class="cap">Bankroll</div>'
            f'<div class="amt">${bankroll:,.2f}</div>'
            f'<div class="day">Day: <b>{"+"if pl>=0 else ""}${pl:,.2f} ({pct:+.2f}%)</b></div>'
            f'<div class="day" style="margin-top:.35rem">Updated just now 🟢</div></div>',
            unsafe_allow_html=True,
        )

    return st.session_state.get("page", "dashboard"), budget, config.database_url, uploaded, kalshi_upload


def _value_board(store: SQLiteStore) -> None:
    hero("Value Board", "Best saved picks ranked by model edge.")
    rows = store.value_board(limit=100)
    soccer = [r for r in rows if r.get("sport") == "soccer"] or rows
    if soccer:
        dataframe_compact(pd.DataFrame(value_board_to_friendly_rows(soccer)), height=520)
    else:
        st.info("No picks saved yet. Load odds from **Data & odds** or **Odds Screen**.")


def _parlay_page(live_legs: list, store: SQLiteStore, budget: float) -> None:
    hero("Parlay Builder", "Model-built parlay cards by payout band.")
    from headcrack_ai.dashboard_home import _parlay_builder

    if not live_legs:
        st.info("Load odds first to build parlays.")
        return
    left, _ = st.columns([1, 1])
    with left:
        _parlay_builder(live_legs, store, budget)


def _backtesting() -> None:
    hero("Backtesting", "Replay historical edges through the staking engine.")
    st.info(
        "Run a backtest from the CLI:\n\n"
        "`python -m headcrack_ai.cli backtest --input examples/markets_argentina_egypt.json`"
    )


def _bet_tracker(store: SQLiteStore) -> None:
    hero("Bet Tracker", "Placed bets, settlement, and ROI.")
    tracking = build_tracking_report(store)
    if tracking["overall"]["bets"]:
        st.markdown(format_tracking_report(tracking))
    else:
        st.info("No bets tracked yet. Add a parlay from the **Dashboard**.")


def _reports(store: SQLiteStore) -> None:
    hero("Reports", "Tracking and calibration summaries.")
    tracking = build_tracking_report(store)
    if tracking["overall"]["bets"]:
        st.markdown(format_tracking_report(tracking))
    else:
        st.info("No settled bets yet — reports populate after results are imported.")


def _accuracy(store: SQLiteStore) -> None:
    hero("Model Accuracy", "Calibration — are our probabilities honest?")
    calibration = build_calibration_report(store)
    if calibration["samples"]:
        st.markdown(format_calibration_report(calibration))
    else:
        st.info("Import results after matches finish.")


def _preferences() -> None:
    hero("Preferences", "Personalize your Headcrack workspace.")
    name = st.text_input("Display name", value=st.session_state.get("user_name", "there"))
    bankroll = st.number_input("Starting bankroll ($)", min_value=0.0,
                               value=float(st.session_state.get("bankroll", 2450.0)), step=50.0)
    if st.button("Save preferences", type="primary"):
        st.session_state["user_name"] = name
        st.session_state["bankroll"] = bankroll
        st.success("Preferences saved.")


def _api_keys() -> None:
    hero("API Keys", "Connected data providers.")
    odds_status = "Connected" if _has_key() else "Not set"
    openai_status = "Connected" if get_settings().openai_api_key else "Not set"
    st.markdown(
        f"- **The Odds API**: `{odds_status}` — set `ODDS_API_KEY` in `.env`\n"
        f"- **OpenAI (MonsterGPT)**: `{openai_status}` — set `OPENAI_API_KEY` in `.env`"
    )


def _help() -> None:
    hero("Help & Docs", "Getting started with Headcrack AI.")
    st.markdown(
        "1. Open **Data & odds** in the sidebar and load a picks file, or use the fetch bar.\n"
        "2. The **Dashboard** shows EV, top value, parlays, and model performance.\n"
        "3. **Edge Tools** cover odds screen, +EV, props, arbitrage, and MonsterGPT.\n\n"
        "World Cup player props: use **Upload Lines** or the CLI "
        "`python -m headcrack_ai.cli fetch-world-cup-props`."
    )


def run_dashboard() -> None:
    if st is None:
        raise RuntimeError("Install streamlit to run the dashboard")

    st.set_page_config(page_title="Headcrack AI", page_icon="⚽", layout="wide",
                       initial_sidebar_state="expanded")
    inject_theme()

    config = HeadcrackConfig.from_env()
    store = SQLiteStore(config.database_url)
    store.initialize()
    service = HeadcrackAIService(config=config, store=store)
    league_options = {label: key for key, label in SOCCER_LEAGUES}

    page, budget, _db, uploaded, kalshi_upload = _sidebar(config, store)

    kalshi_path = None
    if kalshi_upload is not None:
        kalshi_path = Path(".headcrack_upload") / kalshi_upload.name
        kalshi_path.parent.mkdir(exist_ok=True)
        kalshi_path.write_bytes(kalshi_upload.read())

    # Seamless start: pull sportsbooks + prediction markets once per data version.
    board_version = 3
    if st.session_state.get("auto_fetch_version") != board_version:
        st.session_state["auto_fetch_version"] = board_version
        try:
            with st.spinner("Loading sportsbooks, props, Kalshi & Polymarket..."):
                pack = service.refresh_all_sources() if (_has_key() or service.config.enable_prediction_markets) else None
            if pack:
                st.session_state["live_legs"] = pack["sportsbook_legs"] + pack["prediction_legs"]
                st.session_state["prediction_legs"] = pack["prediction_legs"]
                st.session_state["live_leagues"] = pack["leagues"]
                st.session_state["source_status"] = [
                    {"name": s.name, "status": s.status, "detail": s.detail} for s in pack["sources"]
                ]
                st.session_state.pop("parlay_suggestions", None)
        except Exception:
            pass  # Manual fetch bar still available.

    live_legs = st.session_state.get("live_legs", [])
    prediction_legs = st.session_state.get("prediction_legs", [])
    min_edge = 0.0
    user_name = st.session_state.get("user_name", "there")

    # Global fetch controls (kept on data-driven pages)
    if page not in {"preferences", "api_keys", "help", "dashboard"}:
        render_fetch_bar(service, league_options, _has_key())

    if page == "dashboard":
        render_fetch_bar(service, league_options, _has_key())
        render_dashboard_home(
            live_legs,
            store,
            budget,
            user_name=user_name,
            sources=st.session_state.get("source_status"),
        )
    elif page == "value_board":
        _value_board(store)
    elif page == "parlay":
        _parlay_page(live_legs, store, budget)
    elif page == "simulation":
        render_simulator(live_legs, prediction_legs)
    elif page == "line_movement":
        render_whale_watch(store, live_legs)
    elif page == "upload":
        render_build_card(uploaded, store, budget, min_edge)
    elif page == "model_predictions":
        render_ai_picks(live_legs, budget, min_edge)
    elif page == "projections":
        render_projections(live_legs)
    elif page == "backtesting":
        _backtesting()
    elif page == "bet_tracker":
        _bet_tracker(store)
    elif page == "reports":
        _reports(store)
    elif page == "monstergpt":
        render_monster_gpt(live_legs, budget, min_edge)
    elif page == "odds_screen":
        render_odds_screen(live_legs)
    elif page == "ev_finder":
        render_ev_finder(live_legs, min_edge)
    elif page == "prop_optimizer":
        render_dfs_optimizer(live_legs, min_edge)
    elif page == "arbitrage":
        render_arbitrage(live_legs, kalshi_path)
    elif page == "preferences":
        _preferences()
    elif page == "api_keys":
        _api_keys()
    elif page == "help":
        _help()


if __name__ == "__main__":
    run_dashboard()
