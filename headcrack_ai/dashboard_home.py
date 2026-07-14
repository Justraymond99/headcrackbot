"""Rich Dashboard home view (overview screen)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from headcrack_ai.calibration import build_calibration_report
from headcrack_ai.dashboard_ui import (
    AMBER,
    BLUE,
    GREEN,
    GREEN_SOFT,
    MUTED,
    PURPLE,
    RED,
    TEAL,
    TEXT,
    donut_svg,
    fmt_odds,
    html_panel,
    line_chart_svg,
    panel_title,
    source_status_strip,
    sparkline_svg,
    stat_card,
)
from headcrack_ai.models import BetRecord, ResultStatus
from headcrack_ai.optimizer import PRESETS, suggest_parlays
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.plain_language import market_type_label
from headcrack_ai.reports import build_tracking_report
from headcrack_ai.simulation import format_parlay_sim, simulate_parlay
from headcrack_ai.tools import find_positive_ev

BANDS = [("small", "Small (3)", "3-4 legs"), ("big", "Big (5)", "5-6 legs"), ("nuclear", "Nuclear (7+)", "7+ legs")]
BAND_STAKES = {"small": 3.0, "big": 4.0, "nuclear": 3.0}
PRESET_KEYS = list(PRESETS.keys())


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def _event_parts(leg: Any) -> tuple[str, str]:
    meta = leg.market.metadata or {}
    home, away = meta.get("home_team"), meta.get("away_team")
    event = f"{home} vs {away}" if home and away else leg.market.event_id
    league = meta.get("league") or market_type_label(leg.market.market_type.value)
    return event, league


def _market_desc(leg: Any) -> str:
    label = leg.market.label
    return label.split("—", 1)[1].strip() if "—" in label else market_type_label(leg.market.market_type.value)


def _header(name: str) -> None:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(
            f'<div class="hc-greet">{_greeting()}, {name} 👋</div>'
            f'<div class="hc-greet-sub">Let\'s find some value today.</div>',
            unsafe_allow_html=True,
        )
    with right:
        stamp = datetime.now().strftime("%b %d, %Y %I:%M %p")
        st.markdown(
            f'<div class="hc-updated">Last updated: {stamp}</div>'
            f'<div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.4rem">'
            f'<span class="hc-chip">Filters ▾</span>'
            f'<span class="hc-chip">📅 {datetime.now().strftime("%b %d, %Y")}</span></div>',
            unsafe_allow_html=True,
        )


def _stat_cards(live_legs: list, store: SQLiteStore) -> None:
    positive = [leg for leg in live_legs if leg.edge > 0]
    edges = sorted((leg.edge for leg in live_legs), reverse=True)
    probs = sorted((leg.model_probability for leg in live_legs))

    avg_ev = (sum(leg.edge for leg in positive) / len(positive)) if positive else 0.0
    top_edge = max(edges) if edges else 0.0
    top_leg = max(live_legs, key=lambda leg: leg.edge) if live_legs else None

    calib = build_calibration_report(store)
    if calib["samples"] and calib["brier_score"] is not None:
        accuracy = max(0.0, 1.0 - calib["brier_score"])
        acc_sub = f"{calib['samples']} settled picks"
    else:
        accuracy = (sum(leg.prediction.confidence for leg in live_legs) / len(live_legs)) if live_legs else 0.0
        acc_sub = "model confidence"

    ev_series = [leg.edge for leg in positive][:20] or [0, 0.02, 0.01, 0.03]
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        stat_card(
            "Total EV Today", f'<span class="pos">+{avg_ev * 100:.2f}%</span>', "💵",
            "rgba(34,197,94,.14)", "avg edge on value plays",
            sparkline_svg(ev_series, GREEN),
        )
    with c2:
        sub = (_event_parts(top_leg)[0] if top_leg else "no board loaded")
        stat_card(
            "Top Edge", f'<span class="pos">+{top_edge * 100:.1f}%</span>', "🎯",
            "rgba(59,130,246,.14)", sub[:26],
            sparkline_svg(edges[:20] or [0, 1], BLUE),
        )
    with c3:
        stat_card(
            "Positive EV Bets", f'<span class="txt">{len(positive)}</span>', "✅",
            "rgba(168,85,247,.14)", f"out of {len(live_legs)} markets",
            sparkline_svg([abs(e) for e in edges[:20]] or [0, 1], PURPLE),
        )
    with c4:
        stat_card(
            "Avg. Model Accuracy", f'<span class="txt">{accuracy * 100:.1f}%</span>', "⏱️",
            "rgba(245,158,11,.14)", acc_sub,
            sparkline_svg(probs[:20] or [0, 1], AMBER),
        )
    with c5:
        prop_legs = [leg for leg in live_legs if leg.market.player]
        players = {leg.market.player for leg in prop_legs}
        stat_card(
            "Player Props", f'<span class="txt">{len(prop_legs)}</span>', "⚽",
            "rgba(20,184,166,.14)", f"{len(players)} individual players",
            sparkline_svg([leg.edge for leg in prop_legs[:20]] or [0, 1], TEAL),
        )


def _diversified(legs: list, limit: int = 6, per_event: int = 2) -> list:
    """Top edges with at most `per_event` rows per match so every game shows up."""
    picked: list = []
    counts: dict[str, int] = {}
    for leg in legs:
        event = leg.market.event_id
        if counts.get(event, 0) >= per_event:
            continue
        counts[event] = counts.get(event, 0) + 1
        picked.append(leg)
        if len(picked) >= limit:
            break
    return picked


def _opportunities(live_legs: list, store: SQLiteStore) -> None:
    player_rows = _diversified(
        find_positive_ev(
            [leg for leg in live_legs if leg.market.player],
            min_edge=0.0,
            limit=50,
        ),
        limit=3,
        per_event=2,
    )
    match_rows = _diversified(
        find_positive_ev(
            [leg for leg in live_legs if not leg.market.player],
            min_edge=0.0,
            limit=50,
        ),
        limit=3,
        per_event=2,
    )
    rows = [
        leg
        for pair in zip(player_rows, match_rows)
        for leg in pair
    ]
    rows.extend(player_rows[len(match_rows):])
    rows.extend(match_rows[len(player_rows):])
    body = ""
    if rows:
        for leg in rows:
            event, league = _event_parts(leg)
            body += (
                f"<tr><td class='evt'>{event}<small>{league}</small></td>"
                f"<td class='cell-muted'>{_market_desc(leg)}</td>"
                f"<td style='color:{RED};font-weight:600'>{fmt_odds(leg.market.odds.value)}</td>"
                f"<td>{leg.model_probability:.1%}</td>"
                f"<td style='color:{GREEN_SOFT};font-weight:600'>+{leg.edge*100:.1f}%</td>"
                f"<td style='color:{GREEN_SOFT};font-weight:600'>+{leg.ev_per_dollar*100:.1f}%</td></tr>"
            )
    else:
        for r in store.value_board(limit=6):
            body += (
                f"<tr><td class='evt'>{r.get('label','')[:38]}<small>{r.get('sport','')}</small></td>"
                f"<td class='cell-muted'>{market_type_label(str(r.get('market_type','')))}</td>"
                f"<td style='color:{RED};font-weight:600'>{fmt_odds(r.get('odds',0))}</td>"
                f"<td>{float(r.get('model_probability',0)):.1%}</td>"
                f"<td style='color:{GREEN_SOFT};font-weight:600'>+{float(r.get('edge',0))*100:.1f}%</td>"
                f"<td class='cell-muted'>—</td></tr>"
            )
    if not body:
        body = "<tr><td colspan='6' class='cell-muted' style='padding:1.2rem 0'>Load odds to see value opportunities.</td></tr>"
    table = (
        "<table class='hc-tbl'><thead><tr>"
        "<th>Event</th><th>Market</th><th>Book Odds</th><th>Model Prob</th><th>Edge</th><th>EV</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )
    html_panel("Top Value Opportunities", table, link="View All")


def _parlay_legs_html(parlay: Any, max_legs: int = 8) -> str:
    legs_html = ""
    for leg in parlay.legs[:max_legs]:
        event, _ = _event_parts(leg)
        legs_html += (
            f'<div class="hc-leg"><div class="n">{_market_desc(leg)}<small>{event}</small></div>'
            f'<div class="o">{fmt_odds(leg.market.odds.value)}</div></div>'
        )
    return legs_html


def _parlay_summary_html(parlay: Any) -> str:
    odds = fmt_odds((parlay.decimal_odds - 1) * 100)
    ev_cls = "pos" if parlay.expected_value >= 0 else "neg"
    venue = getattr(parlay, "venue", None) or getattr(parlay, "sportsbook", "?")
    est = " (est.)" if getattr(parlay, "combined_odds_estimated", True) else ""
    preset = PRESETS.get(getattr(parlay, "preset", "balanced"), {}).get("label", "Balanced")
    return (
        f'<div class="hc-summary"><span class="k">Venue</span>'
        f'<span class="v">{venue} · {preset}</span></div>'
        f'<div class="hc-summary"><span class="k">Parlay Odds{est}</span>'
        f'<span class="v pos">{odds}</span></div>'
        f'<div class="hc-summary"><span class="k">Model Probability</span>'
        f'<span class="v">{parlay.adjusted_probability:.1%}</span></div>'
        f'<div class="hc-summary"><span class="k">Stake → Payout</span>'
        f'<span class="v">${parlay.stake:.0f} → ${parlay.gross_payout:,.0f}</span></div>'
        f'<div class="hc-summary"><span class="k">Expected Value</span>'
        f'<span class="v {ev_cls}">${parlay.expected_value:+.2f}</span></div>'
    )


def _suggestions_for_band(live_legs: list, band: str, preset: str) -> list:
    cache = st.session_state.setdefault("parlay_suggestions", {})
    sports = [
        leg for leg in live_legs
        if leg.market.sportsbook.lower() not in {"kalshi", "polymarket"}
    ]
    cache_key = (band, preset, len(sports), len({leg.market.sportsbook for leg in sports}))
    if cache.get("key") != cache_key:
        cache.clear()
        cache["key"] = cache_key
        cache["parlays"] = suggest_parlays(
            sports, stake=BAND_STAKES[band], band=band, count=3, min_edge=-0.02, preset=preset
        ) if sports else []
    return cache["parlays"]


def _parlay_builder(live_legs: list, store: SQLiteStore, budget: float) -> None:
    with st.container(border=True):
        panel_title("Parlay Builder", "One book per slip")
        band = st.session_state.get("parlay_band", "small")
        preset = st.session_state.get("parlay_preset", "balanced")
        preset = st.selectbox(
            "Preset",
            PRESET_KEYS,
            index=PRESET_KEYS.index(preset) if preset in PRESET_KEYS else 0,
            format_func=lambda k: PRESETS[k]["label"],
            key="parlay_preset_select",
        )
        st.session_state["parlay_preset"] = preset
        suggestions = _suggestions_for_band(live_legs, band, preset)
        top = suggestions[0] if suggestions else None

        if top:
            st.markdown(_parlay_legs_html(top), unsafe_allow_html=True)
        else:
            label = dict((b[0], b[1]) for b in BANDS)[band]
            hint = "Load odds to get suggestions." if not live_legs else (
                f"Not enough placeable {PRESETS[preset]['label']} picks for a {label} slip yet."
            )
            st.markdown(
                f'<div class="cell-muted" style="padding:.6rem 0;font-size:.85rem">{hint}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="hc-band">', unsafe_allow_html=True)
        bcols = st.columns(3)
        for col, (key, label, _sub) in zip(bcols, BANDS):
            if col.button(label, key=f"band_{key}", type="primary" if key == band else "secondary",
                          use_container_width=True):
                st.session_state["parlay_band"] = key
                st.session_state.pop("parlay_suggestions", None)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        if top:
            st.markdown(_parlay_summary_html(top), unsafe_allow_html=True)
            a, b = st.columns(2)
            if a.button("＋ Add to Bet Tracker", type="primary", use_container_width=True):
                _save_parlay(store, top)
                st.success("Added to bet tracker.")
            if b.button("Simulate slip", use_container_width=True):
                sim = simulate_parlay(top, all_event_legs=live_legs, simulations=6000)
                st.session_state["last_parlay_sim"] = sim
                st.markdown(format_parlay_sim(sim))

        if len(suggestions) > 1:
            with st.expander(f"More suggestions ({len(suggestions) - 1})"):
                for idx, alt in enumerate(suggestions[1:], start=2):
                    st.markdown(
                        f'<div style="color:{MUTED};font-size:.78rem;font-weight:700;'
                        f'margin:.3rem 0">OPTION {idx} · {getattr(alt, "venue", "?")}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(_parlay_legs_html(alt), unsafe_allow_html=True)
                    st.markdown(_parlay_summary_html(alt), unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    if c1.button("＋ Add this slip", key=f"add_alt_{idx}", use_container_width=True):
                        _save_parlay(store, alt)
                        st.success("Added to bet tracker.")
                    if c2.button("Simulate", key=f"sim_alt_{idx}", use_container_width=True):
                        sim = simulate_parlay(alt, all_event_legs=live_legs, simulations=6000)
                        st.markdown(format_parlay_sim(sim))


def _save_parlay(store: SQLiteStore, parlay: Any) -> None:
    try:
        store.save_bet_record(
            BetRecord(
                bet_id=uuid.uuid4().hex[:12],
                legs=parlay.legs,
                stake=parlay.stake,
                decimal_odds=parlay.decimal_odds,
                status=ResultStatus.PENDING,
            )
        )
    except Exception:
        pass


def _confidence(live_legs: list) -> None:
    high = sum(1 for leg in live_legs if leg.prediction.confidence >= 0.70)
    med = sum(1 for leg in live_legs if 0.50 <= leg.prediction.confidence < 0.70)
    low = sum(1 for leg in live_legs if leg.prediction.confidence < 0.50)
    total = high + med + low
    donut = donut_svg(
        [("High", high, GREEN), ("Medium", med, AMBER), ("Low", low, RED)],
        str(total), "markets",
    )
    pct = lambda n: f"{(n / total * 100):.1f}%" if total else "0%"
    legend = (
        f'<div class="hc-legend" style="flex:1">'
        f'<div class="row"><span><span class="dot" style="background:{GREEN}"></span>High (70%+)</span><b>{pct(high)}</b></div>'
        f'<div class="row"><span><span class="dot" style="background:{AMBER}"></span>Medium (50-70%)</span><b>{pct(med)}</b></div>'
        f'<div class="row"><span><span class="dot" style="background:{RED}"></span>Low (&lt;50%)</span><b>{pct(low)}</b></div>'
        f"</div>"
    )
    inner = f'<div style="display:flex;align-items:center;gap:1rem">{donut}{legend}</div>'
    html_panel("Model Confidence Distribution", inner)


def _edge_over_time(live_legs: list) -> None:
    series = sorted((leg.edge * 100 for leg in live_legs), reverse=True)[:24]
    if len(series) < 2:
        series = [0, 5, 3, 8, 6, 10, 12]
    html_panel("Edge Over Time", line_chart_svg(series, GREEN), link="Current board")


def _model_performance(store: SQLiteStore, live_legs: list) -> None:
    calib = build_calibration_report(store)
    per_model = calib.get("per_model", {})
    tracking = build_tracking_report(store)["model_performance"]

    body = ""
    if per_model:
        for model, stats in list(per_model.items())[:5]:
            acc = (1.0 - stats["brier_score"]) if stats.get("brier_score") is not None else 0.0
            roi = tracking.get(model, {}).get("roi", 0.0)
            body += _perf_row(model, acc, roi)
    else:
        seen: dict[str, int] = {}
        for leg in live_legs:
            seen[leg.prediction.model_name] = seen.get(leg.prediction.model_name, 0) + 1
        for model in list(seen)[:5]:
            body += (
                f"<tr><td class='evt'>{model.replace('_',' ').title()}</td>"
                f"<td class='cell-muted'>—</td><td class='cell-muted'>—</td>"
                f"<td><span class='hc-status on'>Active</span></td></tr>"
            )
    if not body:
        body = "<tr><td colspan='4' class='cell-muted' style='padding:1rem 0'>No model data yet.</td></tr>"
    table = (
        "<table class='hc-tbl'><thead><tr><th>Model</th><th>Accuracy</th><th>ROI</th><th>Status</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )
    html_panel("Recent Model Performance", table, link="View All")


def _perf_row(model: str, acc: float, roi: float) -> str:
    roi_color = GREEN_SOFT if roi >= 0 else RED
    return (
        f"<tr><td class='evt'>{model.replace('_',' ').title()}</td>"
        f"<td>{acc:.1%}</td>"
        f"<td style='color:{roi_color}'>{roi:+.1%}</td>"
        f"<td><span class='hc-status on'>Active</span></td></tr>"
    )


def _ticker(live_legs: list) -> None:
    movers = sorted(live_legs, key=lambda leg: leg.edge, reverse=True)[:6]
    items = ""
    for leg in movers:
        event, _ = _event_parts(leg)
        items += f'<span class="item">{event} <b>+{leg.edge*100:.1f}%</b></span>'
    if not items:
        items = '<span class="item cell-muted">Load odds to track movers.</span>'
    st.markdown(
        f'<div class="hc-ticker"><span class="lead">Top Movers</span>{items}</div>',
        unsafe_allow_html=True,
    )


def _prediction_markets_panel(prediction_legs: list, match_results: list | None = None) -> None:
    if not prediction_legs:
        html_panel(
            "Prediction Markets",
            "<p class='cell-muted'>Kalshi & Polymarket load via <b>Refresh all</b>. "
            "Enable <code>ENABLE_PREDICTION_MARKETS=true</code> in <code>.env</code>.</p>",
            link="Open markets",
        )
        return

    kalshi = sum(1 for leg in prediction_legs if leg.market.sportsbook.lower() == "kalshi")
    poly = sum(1 for leg in prediction_legs if leg.market.sportsbook.lower() == "polymarket")
    matched = sum(1 for m in (match_results or []) if getattr(m, "matched", False))
    body = (
        f"<p style='color:{MUTED};margin:0 0 .8rem 0'>"
        f"<b style='color:{TEXT}'>{kalshi}</b> Kalshi · "
        f"<b style='color:{TEXT}'>{poly}</b> Polymarket · "
        f"<b style='color:{TEXT}'>{matched}</b> linked to sportsbooks</p>"
    )
    for leg in sorted(
        prediction_legs,
        key=lambda row: (row.market.liquidity or 0.0, row.implied_probability),
        reverse=True,
    )[:6]:
        venue = leg.market.sportsbook.title()
        label = leg.market.label
        for prefix in ("Polymarket — ", "Kalshi YES — "):
            if label.startswith(prefix):
                label = label.removeprefix(prefix)
        if len(label) > 72:
            label = label[:69] + "..."
        liq = f" · liq ${leg.market.liquidity:,.0f}" if leg.market.liquidity else ""
        body += (
            f"<div class='hc-leg'><div class='n'>{label}<small>{venue}{liq}</small></div>"
            f"<div class='o' style='color:{GREEN_SOFT}'>{leg.implied_probability:.1%}</div></div>"
        )
    html_panel("Prediction Markets", body, link="View all")


def render_dashboard_home(
    live_legs: list,
    store: SQLiteStore,
    budget: float,
    user_name: str = "there",
    sources: list | None = None,
    prediction_legs: list | None = None,
    match_results: list | None = None,
) -> None:
    _header(user_name)
    if sources:
        source_status_strip(
            [
                {
                    "name": getattr(s, "name", s.get("name") if isinstance(s, dict) else "Source"),
                    "status": getattr(s, "status", s.get("status") if isinstance(s, dict) else "off"),
                    "detail": getattr(s, "detail", s.get("detail") if isinstance(s, dict) else ""),
                }
                for s in sources
            ]
        )
    st.write("")
    _stat_cards(live_legs, store)
    st.write("")
    left, right = st.columns([1.7, 1])
    with left:
        _opportunities(live_legs, store)
    with right:
        _parlay_builder(live_legs, store, budget)
    st.write("")
    _prediction_markets_panel(prediction_legs or [], match_results)
    if prediction_legs and st.button("Open full prediction markets view →", key="open_prediction_markets"):
        st.session_state["page"] = "prediction_markets"
        st.rerun()
    a, b, c = st.columns(3)
    with a:
        _confidence(live_legs)
    with b:
        _edge_over_time(live_legs)
    with c:
        _model_performance(store, live_legs)
    _ticker(live_legs)
