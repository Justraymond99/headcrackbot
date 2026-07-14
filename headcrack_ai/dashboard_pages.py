from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from headcrack_ai.dashboard_ui import (
    dataframe_compact,
    hero,
    metric_row,
    pick_card,
    section,
    verdict_tag_class,
)
from headcrack_ai.explain import build_card_brief, explain_pick_rationale, format_card_brief
from headcrack_ai.ingest import load_markets_csv, load_markets_json
from headcrack_ai.llm_explain import OpenAINarrator, explain_brief_narrative
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.plain_language import (
    leg_to_friendly_row,
    simulation_to_friendly,
    value_verdict,
)
from headcrack_ai.probability import monte_carlo_soccer_match
from headcrack_ai.providers.kalshi_manual import load_kalshi_csv
from headcrack_ai.services import HeadcrackAIService
from headcrack_ai.soccer import (
    DEFAULT_SOCCER_MARKETS,
    WORLD_CUP_SPORT_KEY,
    group_legs_by_match,
)
from headcrack_ai.tools import (
    BettingAssistant,
    build_dfs_entries,
    build_match_projections,
    build_odds_screen,
    detect_whale_activity,
    find_arbitrage_opportunities,
    find_positive_ev,
    find_prediction_arbs,
    format_dfs_slip,
    format_ev_row,
    format_odds_screen_rows,
    format_whale_row,
)
from headcrack_ai.tools.projections import format_projection_card


def render_fetch_bar(service: HeadcrackAIService, league_options: dict[str, str], has_key: bool) -> None:
    if not has_key and not service.config.enable_prediction_markets:
        return
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    league_label_ui = c1.selectbox("League", list(league_options.keys()), index=0, key="fetch_league")
    sport_key = league_options[league_label_ui]
    if c2.button("Fetch league", type="primary", use_container_width=True) and has_key:
        with st.spinner(f"Loading {league_label_ui}..."):
            legs = service.fetch_live_legs(sport_key=sport_key, markets=DEFAULT_SOCCER_MARKETS)
            if sport_key == WORLD_CUP_SPORT_KEY:
                props = service.fetch_world_cup_player_props()
                existing = {leg.market.market_id: leg for leg in legs}
                existing.update({leg.market.market_id: leg for leg in props})
                legs = list(existing.values())
        st.session_state["live_legs"] = legs
        st.session_state["live_leagues"] = [league_label_ui]
        st.session_state.pop("parlay_suggestions", None)
        st.rerun()
    if c3.button("Refresh all", use_container_width=True):
        with st.spinner("Refreshing sportsbooks + Kalshi + Polymarket..."):
            pack = service.refresh_all_sources()
        st.session_state["live_legs"] = pack["sportsbook_legs"] + pack["prediction_legs"]
        st.session_state["prediction_legs"] = pack["prediction_legs"]
        st.session_state["match_results"] = pack["match_results"]
        st.session_state["live_leagues"] = pack["leagues"]
        st.session_state["source_status"] = [
            {"name": s.name, "status": s.status, "detail": s.detail} for s in pack["sources"]
        ]
        st.session_state.pop("parlay_suggestions", None)
        st.rerun()
    if c4.button("World Cup props", use_container_width=True) and has_key:
        with st.spinner("Checking World Cup player-prop markets..."):
            props = service.fetch_world_cup_player_props()
        if props:
            existing = {
                leg.market.market_id: leg
                for leg in st.session_state.get("live_legs", [])
            }
            existing.update({leg.market.market_id: leg for leg in props})
            st.session_state["live_legs"] = list(existing.values())
            st.session_state.pop("parlay_suggestions", None)
            st.session_state["world_cup_props_status"] = (
                f"Loaded {len(props)} World Cup player-prop lines."
            )
        else:
            st.session_state["world_cup_props_status"] = (
                "The provider returned no World Cup player props from supported US books."
            )
        st.rerun()

    props_status = st.session_state.pop("world_cup_props_status", None)
    if props_status:
        if props_status.startswith("Loaded"):
            st.success(props_status)
        else:
            st.info(props_status)

    sources = st.session_state.get("source_status")
    if sources:
        from headcrack_ai.dashboard_ui import source_status_strip

        source_status_strip(sources)


def render_home(live_legs: list, store: SQLiteStore, has_key: bool) -> None:
    hero("Headcrack AI", "Odds, props, projections, +EV, DFS, whale watch, and arbitrage — soccer-first.")
    matches = len(group_legs_by_match(live_legs)) if live_legs else 0
    ev_count = len(find_positive_ev(live_legs, min_edge=0.01)) if live_legs else 0
    metric_row(
        [
            ("Matches", str(matches), "on the board"),
            ("Lines", str(len(live_legs)), "live + model"),
            ("+EV spots", str(ev_count), "1%+ edge"),
            ("Data", "Live" if has_key else "Offline", "odds API"),
        ]
    )
    section("Tool suite")
    tiles = [
        ("CrackBot", "AI research & bet breakdowns"),
        ("AI Picks", "Model-backed picks & projections"),
        ("Odds Screen", "Line shop across books"),
        ("+EV Finder", "Positive expected value plays"),
        ("Prop Optimizer", "DFS & player-prop stacks"),
        ("Prediction Markets", "Kalshi & Polymarket contracts"),
        ("Whale Watch", "Big line moves & steam"),
        ("Arbitrage", "Cross-book & prediction gaps"),
    ]
    cols = st.columns(4)
    for idx, (title, desc) in enumerate(tiles):
        with cols[idx % 4]:
            st.markdown(
                f'<div class="hc-tool-tile"><h3>{title}</h3><p>{desc}</p></div>',
                unsafe_allow_html=True,
            )


def render_crackbot(live_legs: list, budget: float, min_edge: float) -> None:
    hero("CrackBot", "Your Headcrack betting copilot — grounded in live model output, not vibes.")
    llm_on = OpenAINarrator.from_env() is not None
    st.caption("LLM enabled (gpt-4o-mini)" if llm_on else "Template mode — set OPENAI_API_KEY for LLM answers")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Ask about best bets, parlays, matchups, or +EV plays. I'll only use what's on the board.",
            }
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompts = [
        "What are the best +EV bets today?",
        "Break down the top matchups",
        "Build me a parlay idea",
        "Why does the model like the top pick?",
    ]
    pcols = st.columns(4)
    for col, prompt in zip(pcols, prompts):
        if col.button(prompt, use_container_width=True):
            st.session_state.pending_prompt = prompt

    pending = st.session_state.pop("pending_prompt", None)
    question = st.chat_input("Ask Headcrack...")
    if pending:
        question = pending

    if question:
        st.session_state.chat_messages.append({"role": "user", "content": question})
        assistant = BettingAssistant()
        reply = assistant.answer(question, live_legs, budget=budget, min_edge=min_edge)
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()


def render_ai_picks(live_legs: list, budget: float, min_edge: float) -> None:
    hero("AI Picks", "Model-backed picks with matchup context and plain-English rationale.")
    if not live_legs:
        st.info("Fetch odds first — use the sidebar or Odds Screen.")
        return
    brief = build_card_brief(live_legs, budget=budget, min_edge=min_edge)
    metric_row(
        [
            ("Reviewed", str(brief["picks_reviewed"]), "lines"),
            ("Value", str(brief["value_picks"]), "positive edge"),
            ("Best single", (lambda b: (b["label"][:20] + "…") if len(b["label"]) > 20 else b["label"])(brief["best_single"]) if brief.get("best_single") else "—", "top play"),
            ("Model", "Poisson + shots", "soccer stack"),
        ]
    )
    section("Top picks")
    for row in brief.get("top_rationales", [])[:6]:
        pick_card(row["pick"], row["verdict"], row["why"], verdict_tag_class(row["verdict"]))
    section("Full brief")
    st.markdown(format_card_brief(brief))
    st.markdown(explain_brief_narrative(brief))


def render_projections(live_legs: list) -> None:
    hero("Projections", "xG estimates, win probabilities, and simulated scorelines.")
    if not live_legs:
        st.info("Load lines to generate match projections.")
        return
    projections = build_match_projections(live_legs)
    for proj in projections[:12]:
        with st.expander(proj["match"], expanded=len(projections) <= 4):
            st.markdown(format_projection_card(proj))
            st.caption(f"Top scorelines: {proj['top_scores']}")


def render_odds_screen(live_legs: list) -> None:
    hero("Odds Screen", "Compare real-time lines across sportsbooks — find the best price.")
    if not live_legs:
        st.info("Fetch odds to populate the screen.")
        return
    screen = build_odds_screen(live_legs)
    metric_row(
        [
            ("Comparable picks", str(len(screen)), "2+ books"),
            ("Books", str(len({b for r in screen for b in r['books']})), "on screen"),
            ("Best edges", str(sum(1 for r in screen if (r.get('edge_best') or 0) > 0.02)), "2%+ vs model"),
            ("Lines", str(len(live_legs)), "loaded"),
        ]
    )
    rows = format_odds_screen_rows(screen)
    if rows:
        dataframe_compact(pd.DataFrame(rows), height=480)
    else:
        st.warning("Need the same pick at multiple books — fetch with **All books** selected.")


def render_ev_finder(live_legs: list, min_edge: float) -> None:
    hero("+EV Finder", "Model-backed bets with positive expected value.")
    if not live_legs:
        st.info("Fetch odds to hunt +EV.")
        return
    floor = st.slider("Minimum edge %", 0, 10, max(0, int(min_edge * 100)), key="ev_slider")
    ev_legs = find_positive_ev(live_legs, min_edge=floor / 100.0, limit=40)
    metric_row(
        [
            ("+EV plays", str(len(ev_legs)), f"≥ {floor}% edge"),
            ("Best EV/$1", f"${max((l.ev_per_dollar for l in ev_legs), default=0):+.2f}", "top play"),
            ("Avg edge", f"{(sum(l.edge for l in ev_legs) / len(ev_legs)):.1%}" if ev_legs else "—", "on board"),
            ("Lines", str(len(live_legs)), "scanned"),
        ]
    )
    if ev_legs:
        for leg in ev_legs[:10]:
            pick_card(
                f"{leg.market.label} ({leg.market.sportsbook})",
                value_verdict(leg.edge),
                f"EV ${leg.ev_per_dollar:+.2f}/$1 · {explain_pick_rationale(leg)}",
                verdict_tag_class(value_verdict(leg.edge)),
            )
        dataframe_compact(pd.DataFrame([format_ev_row(leg) for leg in ev_legs]), height=360)
    else:
        st.warning("No plays at this edge floor. Lower the slider or scan more leagues.")


def render_dfs_optimizer(live_legs: list, min_edge: float) -> None:
    hero("Prop Optimizer", "Build smarter DFS and player-prop entries from model edges.")
    if not live_legs:
        st.info("Fetch odds with player props, or upload a props file.")
        return
    prop_types = {
        "player_shots",
        "player_shots_on_target",
        "player_goal",
        "player_assist",
    }
    prop_legs = [
        leg for leg in live_legs if leg.market.market_type.value in prop_types
    ]
    model_backed = [
        leg for leg in prop_legs if leg.prediction.model_name != "book_baseline"
    ]
    metric_row(
        [
            ("Prop lines", str(len(prop_legs)), "across books"),
            ("Players", str(len({leg.market.player for leg in prop_legs if leg.market.player})), "on board"),
            ("Model-backed", str(len(model_backed)), "eligible for optimizer"),
            ("World Cup", str(sum(1 for leg in prop_legs if leg.market.metadata.get("league") == "World Cup")), "prop lines"),
        ]
    )
    if prop_legs:
        section("Available player props")
        dataframe_compact(
            pd.DataFrame([leg_to_friendly_row(leg) for leg in prop_legs]),
            height=320,
        )

    max_picks = st.slider("Max picks on slip", 3, 8, 6)
    entries = build_dfs_entries(live_legs, min_edge=min_edge, max_picks=max_picks)
    section("Optimized slip")
    st.markdown(format_dfs_slip(entries))
    if entries:
        dataframe_compact(
            pd.DataFrame(
                [
                    {
                        "Pick": e["pick"],
                        "Book": e["book"],
                        "Odds": e["odds"],
                        "Model": e["model"],
                        "Edge": e["edge"],
                        "EV": e["ev"],
                        "Projection": e["projection"],
                    }
                    for e in entries
                ]
            ),
            height=280,
        )


def render_whale_watch(store: SQLiteStore, live_legs: list) -> None:
    hero("Whale Watch", "Track large line moves and steam — sharp money proxy.")
    sensitivity = st.slider("Min move (%)", 1, 8, 2) / 100.0
    whales = detect_whale_activity(store, live_legs=live_legs, min_implied_move=sensitivity)
    if not whales:
        st.info(
            "No big moves yet. Fetch odds twice (before/after news) to build snapshot history, "
            "then check back here."
        )
        return
    metric_row(
        [
            ("Moves", str(len(whales)), "tracked"),
            ("Big steam", str(sum(1 for w in whales if w.get("move", 0) >= 0.03)), "3%+ swings"),
            ("Snapshots", str(max(w.get("snapshots", 0) for w in whales)), "max depth"),
            ("Live sync", "Yes" if live_legs else "No", "edge overlay"),
        ]
    )
    dataframe_compact(pd.DataFrame([format_whale_row(w) for w in whales]), height=420)


def _prediction_rows(legs: list, limit: int = 40) -> list[dict]:
    ranked = sorted(
        legs,
        key=lambda leg: (leg.market.liquidity or 0.0, leg.implied_probability),
        reverse=True,
    )
    rows: list[dict] = []
    for leg in ranked[:limit]:
        label = leg.market.label
        if label.startswith("Polymarket — "):
            label = label.removeprefix("Polymarket — ")
        if label.startswith("Kalshi YES — "):
            label = label.removeprefix("Kalshi YES — ")
        if len(label) > 120:
            label = label[:117] + "..."
        liq = leg.market.liquidity
        rows.append(
            {
                "Venue": leg.market.sportsbook.title(),
                "Contract": label,
                "Implied": f"{leg.implied_probability:.1%}",
                "Liquidity": f"${liq:,.0f}" if liq is not None else "—",
                "Bid": f"{leg.market.bid:.1%}" if leg.market.bid is not None else "—",
                "Ask": f"{leg.market.ask:.1%}" if leg.market.ask is not None else "—",
            }
        )
    return rows


def render_prediction_markets(
    prediction_legs: list,
    live_legs: list,
    match_results: list | None = None,
) -> None:
    hero(
        "Prediction Markets",
        "Live Kalshi & Polymarket prices — read-only comparison against sportsbooks (no order execution).",
    )
    if not prediction_legs:
        st.warning(
            "No prediction-market contracts loaded. Click **Refresh all** on the dashboard "
            "and confirm `ENABLE_PREDICTION_MARKETS=true` in `.env`."
        )
        return

    kalshi = [leg for leg in prediction_legs if leg.market.sportsbook.lower() == "kalshi"]
    poly = [leg for leg in prediction_legs if leg.market.sportsbook.lower() == "polymarket"]
    matched = [m for m in (match_results or []) if getattr(m, "matched", False)]

    metric_row(
        [
            ("Kalshi", str(len(kalshi)), "contracts"),
            ("Polymarket", str(len(poly)), "contracts"),
            ("Linked to books", str(len(matched)), "matched outcomes"),
            ("Sportsbook lines", str(len(live_legs)), "for comparison"),
        ]
    )

    tab_kalshi, tab_poly, tab_linked = st.tabs(
        [f"Kalshi ({len(kalshi)})", f"Polymarket ({len(poly)})", f"vs Sportsbooks ({len(matched)})"]
    )
    with tab_kalshi:
        if kalshi:
            dataframe_compact(pd.DataFrame(_prediction_rows(kalshi, 60)), height=520)
        else:
            st.info("Kalshi returned no open soccer contracts on this scan.")
    with tab_poly:
        if poly:
            dataframe_compact(pd.DataFrame(_prediction_rows(poly, 60)), height=520)
        else:
            st.info("Polymarket returned no soccer contracts on this scan.")
    with tab_linked:
        if not matched:
            st.caption(
                "Contracts are loaded, but none matched a sportsbook leg tightly enough yet. "
                "Check **Arbitrage** for team-linked gaps."
            )
        else:
            linked_rows = []
            for result in matched[:40]:
                book = result.sportsbook_leg
                pred = result.prediction_leg
                linked_rows.append(
                    {
                        "Sportsbook pick": book.market.label,
                        "Book": book.market.sportsbook,
                        "Book implied": f"{book.implied_probability:.1%}",
                        "Contract": pred.market.label.replace("Polymarket — ", "").replace("Kalshi YES — ", "")[:90],
                        "Venue": pred.market.sportsbook.title(),
                        "Contract implied": f"{pred.implied_probability:.1%}",
                        "Match score": f"{result.score:.0%}",
                    }
                )
            dataframe_compact(pd.DataFrame(linked_rows), height=420)


def render_arbitrage(live_legs: list, kalshi_path: Path | None) -> None:
    hero("Arbitrage", "Cross-sportsbook arbs and sportsbook vs prediction-market gaps.")
    if not live_legs:
        st.info("Fetch multi-book odds to scan for arbitrage.")
        return

    min_profit = st.slider("Min arb margin %", 0.0, 3.0, 0.5, step=0.1) / 100.0
    arbs = find_arbitrage_opportunities(live_legs, min_profit_pct=min_profit)

    section("Sportsbook arbitrage")
    if arbs:
        for arb in arbs[:8]:
            legs_desc = " · ".join(
                f"{leg['pick']} @ {leg['book']} ({leg['odds']})" for leg in arb["legs"]
            )
            pick_card(
                arb["market"],
                f"{arb['profit_pct']:.1%} margin",
                f"{arb['note']}\n\n{legs_desc}",
                "hc-tag",
            )
    else:
        st.caption("No pure cross-book arbs at this margin — markets are efficient or need more books.")

    section("Prediction market gaps")
    prediction_legs = st.session_state.get("prediction_legs", []) or st.session_state.get("kalshi_legs", [])
    sports = [leg for leg in live_legs if leg.market.sportsbook.lower() not in {"kalshi", "polymarket"}]
    if kalshi_path and kalshi_path.exists():
        prediction_legs = list(prediction_legs)
        for market in load_kalshi_csv(kalshi_path):
            from headcrack_ai.models import BetLeg, Prediction, VenueType
            from dataclasses import replace

            market = replace(market, venue_type=VenueType.PREDICTION_MARKET)
            prediction_legs.append(
                BetLeg(
                    market=market,
                    prediction=Prediction(
                        market_id=market.market_id,
                        model_probability=market.odds.implied_probability,
                        model_name="kalshi_market",
                        confidence=0.4,
                    ),
                )
            )
        st.session_state["kalshi_legs"] = prediction_legs

    # Only use matched-or-team-linked gaps; find_prediction_arbs already requires team overlap.
    gaps = find_prediction_arbs(sports, prediction_legs)
    if gaps:
        dataframe_compact(pd.DataFrame(gaps), height=260)
    else:
        st.caption(
            "Prediction markets load automatically via **Refresh all** (public Kalshi & Polymarket). "
            "You can still upload a Kalshi CSV in the sidebar as an offline fallback."
        )


def render_build_card(uploaded, store: SQLiteStore, budget: float, min_edge: float) -> None:
    hero("Build Card", "Upload JSON/CSV picks — manual card builder & saver.")
    if uploaded is None:
        st.info("Upload a file in the sidebar, e.g. `examples/markets_argentina_egypt.json`.")
        return
    temp = Path(".headcrack_upload") / uploaded.name
    temp.parent.mkdir(exist_ok=True)
    temp.write_bytes(uploaded.read())
    legs = load_markets_json(temp) if temp.suffix == ".json" else load_markets_csv(temp)
    st.session_state["live_legs"] = legs
    if st.button("Save to database", type="primary"):
        store.save_legs(legs)
        st.success(f"Saved {len(legs)} picks")
    dataframe_compact(pd.DataFrame([leg_to_friendly_row(leg) for leg in legs]))
    st.markdown(format_card_brief(build_card_brief(legs, budget=budget, min_edge=min_edge)))


def render_simulator(live_legs: list | None = None, prediction_legs: list | None = None) -> None:
    from headcrack_ai.optimizer import suggest_parlays
    from headcrack_ai.simulation import (
        format_match_sim,
        format_parlay_sim,
        list_live_matches,
        simulate_match_from_legs,
        simulate_parlay,
    )
    from headcrack_ai.soccer import group_legs_by_match

    hero("Simulation Engine", "Odds-informed Monte Carlo for live games and whole parlays.")
    live_legs = live_legs or st.session_state.get("live_legs", [])
    prediction_legs = prediction_legs or st.session_state.get("prediction_legs", [])
    sports = [leg for leg in live_legs if leg.market.sportsbook.lower() not in {"kalshi", "polymarket"}]
    matches = list_live_matches(sports)

    tab_match, tab_slip, tab_advanced = st.tabs(["Live game", "Parlay slip", "Advanced xG"])
    with tab_match:
        if not matches:
            st.info("Refresh the board to simulate a live match (e.g. France vs Spain).")
        else:
            pick = st.selectbox("Match", matches, key="sim_match_pick")
            sims = st.slider("Simulations", 2000, 30000, 10000, step=1000, key="sim_match_n")
            if st.button("Run match simulation", type="primary", key="run_match_sim"):
                grouped = group_legs_by_match(sports)
                match_legs = grouped.get(pick, [])
                result = simulate_match_from_legs(
                    match_legs,
                    simulations=int(sims),
                    prediction_legs=prediction_legs,
                )
                metric_row(
                    [
                        ("Home", f"{result.home_win:.1%}", result.home_team),
                        ("Draw", f"{result.draw:.1%}", "regulation"),
                        ("Away", f"{result.away_win:.1%}", result.away_team),
                        ("Over 2.5", f"{result.over_2_5:.1%}", f"xG {result.home_xg:.2f}-{result.away_xg:.2f}"),
                    ]
                )
                st.markdown(format_match_sim(result))

    with tab_slip:
        band = st.selectbox("Band", ["small", "big", "nuclear"], key="sim_band")
        preset = st.selectbox(
            "Preset",
            ["balanced", "cross_game", "same_game", "player_props"],
            key="sim_preset",
        )
        slips = suggest_parlays(sports, band=band, preset=preset, count=3) if sports else []
        if not slips:
            st.info("No placeable single-venue slips for this band/preset.")
        else:
            labels = [
                f"{s.venue} · {len(s.legs)} legs · EV ${s.expected_value:+.2f}" for s in slips
            ]
            idx = st.selectbox("Suggested slip", range(len(slips)), format_func=lambda i: labels[i])
            if st.button("Simulate this parlay", type="primary", key="run_parlay_sim"):
                result = simulate_parlay(slips[idx], all_event_legs=sports, simulations=8000)
                metric_row(
                    [
                        ("Hit rate", f"{result['slip_hit_rate']:.1%}", f"{result['simulations']:,} runs"),
                        ("Fair odds", str(result.get("fair_decimal_odds") or "—"), "decimal"),
                        ("Book product", str(result.get("estimated_decimal_odds")), "estimated"),
                        ("EV", f"${result['expected_value']:+.2f}", f"${result['stake']:.0f} stake"),
                    ]
                )
                st.markdown(format_parlay_sim(result))

    with tab_advanced:
        c1, c2, c3 = st.columns(3)
        home_xg = c1.number_input("Home xG", min_value=0.0, value=1.8, step=0.1)
        away_xg = c2.number_input("Away xG", min_value=0.0, value=0.9, step=0.1)
        sims = c3.number_input("Runs", min_value=1000, value=20000, step=1000)
        if st.button("Simulate manual xG", type="primary"):
            result = monte_carlo_soccer_match(home_xg, away_xg, simulations=int(sims))
            metric_row([(k, v, "") for k, v in list(simulation_to_friendly(result).items())[:4]])
            with st.expander("Top scorelines"):
                st.json(result["top_scores"])
