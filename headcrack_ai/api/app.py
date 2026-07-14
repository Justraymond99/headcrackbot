from __future__ import annotations

from dataclasses import asdict, replace

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ..config import HeadcrackConfig
from ..logging_config import get_logger, new_correlation_id, setup_logging
from ..models import BetLeg, Parlay, VenueType
from ..optimizer import suggest_parlays
from ..persistence import SQLiteStore
from ..plain_language import value_board_to_friendly_rows
from ..providers.matcher import match_prediction_to_books
from ..services import HeadcrackAIService
from ..simulation import simulate_match_from_legs, simulate_parlay
from ..soccer import group_legs_by_match

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Headcrack AI", version="0.2.0", description="Soccer betting decision-support API")


@app.middleware("http")
async def add_correlation_id(request, call_next):
    new_correlation_id()
    response = await call_next(request)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    config = HeadcrackConfig.from_env()
    store = SQLiteStore(config.database_url)
    if not store.path.exists():
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": str(store.path),
                "reason": "database is not initialized",
            },
        )
    with store.connect() as conn:
        conn.execute("SELECT 1")
    return {"status": "ready", "database": str(store.path)}


@app.get("/v1/value-board")
def value_board(limit: int = 25):
    service = HeadcrackAIService.from_env()
    rows = service.value_board(limit=limit)
    return value_board_to_friendly_rows(rows)


@app.get("/v1/unified-board")
def unified_board(
    refresh: bool = False,
    include_prediction_markets: bool | None = None,
    limit: int = 100,
):
    service = _service_with_prediction_override(include_prediction_markets)
    try:
        if refresh:
            pack = service.refresh_all_sources()
            sportsbook_legs = pack["sportsbook_legs"]
            prediction_legs = pack["prediction_legs"]
            matches = pack["match_results"]
            sources = [asdict(source) for source in pack["sources"]]
            leagues = pack["leagues"]
        else:
            legs = service.store.latest_legs(limit=limit)
            sportsbook_legs = [leg for leg in legs if not _is_prediction_market(leg)]
            prediction_legs = [leg for leg in legs if _is_prediction_market(leg)]
            matches = match_prediction_to_books(prediction_legs, sportsbook_legs)
            sources = [
                {
                    "name": "Persistence",
                    "status": "live" if legs else "off",
                    "detail": f"{len(legs)} stored lines",
                    "count": len(legs),
                }
            ]
            leagues = sorted(
                {
                    str(leg.market.metadata.get("league"))
                    for leg in sportsbook_legs
                    if leg.market.metadata.get("league")
                }
            )
        return {
            "refresh": refresh,
            "counts": {
                "sportsbook_lines": len(sportsbook_legs),
                "prediction_market_lines": len(prediction_legs),
                "matched_prediction_markets": sum(1 for match in matches if match.matched),
            },
            "leagues": leagues,
            "sources": sources,
            "sportsbook_lines": [_leg_payload(leg) for leg in sportsbook_legs[:limit]],
            "prediction_market_lines": [_leg_payload(leg) for leg in prediction_legs[:limit]],
            "matches": [_match_payload(match) for match in matches[:limit]],
        }
    except Exception as exc:
        logger.exception("unified board failed")
        return JSONResponse(status_code=502, content={"error": str(exc)})


@app.get("/v1/simulations/match")
def simulate_match(event_id: str | None = None, simulations: int = 5000, seed: int = 42):
    service = HeadcrackAIService.from_env()
    legs = service.store.latest_legs()
    if not legs:
        return JSONResponse(status_code=404, content={"error": "No persisted legs available. Ingest or fetch lines first."})
    grouped = group_legs_by_match([leg for leg in legs if not _is_prediction_market(leg)])
    if not grouped:
        return JSONResponse(status_code=404, content={"error": "No sportsbook match legs available to simulate."})
    if event_id:
        match_legs = [leg for leg in legs if leg.market.event_id == event_id and not _is_prediction_market(leg)]
        if not match_legs:
            return JSONResponse(status_code=404, content={"error": f"No match legs found for event_id {event_id!r}."})
    else:
        match_legs = next(iter(grouped.values()))
    prediction_legs = [
        leg
        for leg in legs
        if _is_prediction_market(leg) and leg.market.canonical_event_id == match_legs[0].market.canonical_event_id
    ]
    result = simulate_match_from_legs(
        match_legs,
        simulations=max(100, min(simulations, 50_000)),
        seed=seed,
        prediction_legs=prediction_legs,
    )
    return asdict(result)


@app.get("/v1/simulations/parlay")
def simulate_suggested_parlay(
    band: str = "small",
    preset: str = "balanced",
    simulations: int = 5000,
    seed: int = 42,
    min_edge: float = -0.02,
):
    service = HeadcrackAIService.from_env()
    legs = [leg for leg in service.store.latest_legs() if not _is_prediction_market(leg)]
    if not legs:
        return JSONResponse(status_code=404, content={"error": "No sportsbook legs available to simulate."})
    suggestions = suggest_parlays(legs, band=band, count=1, min_edge=min_edge, preset=preset)
    if not suggestions:
        return JSONResponse(status_code=404, content={"error": "No parlay suggestion matched those filters."})
    parlay = suggestions[0]
    result = simulate_parlay(
        parlay,
        all_event_legs=legs,
        simulations=max(100, min(simulations, 50_000)),
        seed=seed,
    )
    return {
        "parlay": _parlay_payload(parlay),
        "simulation": result,
    }


@app.get("/v1/soccer/fetch")
def fetch_soccer(league: str = "soccer_epl", sportsbook: str | None = None):
    service = HeadcrackAIService.from_env()
    try:
        legs = service.fetch_live_legs(sport_key=league, sportsbook=sportsbook)
        return {
            "league": league,
            "lines": len(legs),
            "matches": len({leg.market.event_id for leg in legs}),
        }
    except Exception as exc:
        logger.exception("fetch failed")
        return JSONResponse(status_code=502, content={"error": str(exc)})


def _service_with_prediction_override(include_prediction_markets: bool | None) -> HeadcrackAIService:
    service = HeadcrackAIService.from_env()
    if include_prediction_markets is None:
        return service
    config = replace(service.config, enable_prediction_markets=include_prediction_markets)
    return HeadcrackAIService(config=config, store=service.store)


def _is_prediction_market(leg: BetLeg) -> bool:
    return leg.market.venue_type == VenueType.PREDICTION_MARKET or leg.market.sportsbook.lower() in {
        "kalshi",
        "polymarket",
    }


def _leg_payload(leg: BetLeg) -> dict:
    return {
        "market_id": leg.market.market_id,
        "event_id": leg.market.event_id,
        "label": leg.market.label,
        "sport": leg.market.sport.value,
        "market_type": leg.market.market_type.value,
        "venue": leg.market.sportsbook,
        "venue_type": leg.market.venue_type.value,
        "odds": leg.market.odds.value,
        "implied_probability": round(leg.implied_probability, 4),
        "model_probability": round(leg.model_probability, 4),
        "edge": round(leg.edge, 4),
        "team": leg.market.team,
        "player": leg.market.player,
        "threshold": leg.market.threshold,
        "canonical_event_id": leg.market.canonical_event_id,
        "canonical_outcome_id": leg.market.canonical_outcome_id,
        "liquidity": leg.market.liquidity,
        "source_url": leg.market.source_url,
    }


def _match_payload(match) -> dict:
    return {
        "sportsbook_market_id": match.sportsbook_leg.market.market_id,
        "prediction_market_id": match.prediction_leg.market.market_id,
        "sportsbook_label": match.sportsbook_leg.market.label,
        "prediction_label": match.prediction_leg.market.label,
        "score": match.score,
        "matched": match.matched,
    }


def _parlay_payload(parlay: Parlay) -> dict:
    return {
        "venue": parlay.venue or parlay.sportsbook,
        "preset": parlay.preset,
        "band": parlay.target_band,
        "stake": parlay.stake,
        "decimal_odds": round(parlay.decimal_odds, 3),
        "expected_value": round(parlay.expected_value, 3),
        "adjusted_probability": round(parlay.adjusted_probability, 4),
        "legs": [_leg_payload(leg) for leg in parlay.legs],
    }


def main():
    import uvicorn

    from ..settings import get_settings

    settings = get_settings()
    uvicorn.run("headcrack_ai.api.app:app", host=settings.api_host, port=settings.api_port, reload=False)


if __name__ == "__main__":
    main()
