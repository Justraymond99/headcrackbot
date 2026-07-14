from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ..logging_config import get_logger
from ..models import BetLeg
from .models import IngestRun, League, Match, OddsSnapshot, Team, init_warehouse
from .session import session_scope

logger = get_logger(__name__)


def _get_or_create_league(session, key: str, name: str) -> League:
    row = session.execute(select(League).where(League.key == key)).scalar_one_or_none()
    if row:
        return row
    row = League(key=key, name=name)
    session.add(row)
    session.flush()
    return row


def _get_or_create_team(session, name: str, league_id: int | None = None) -> Team:
    row = session.execute(select(Team).where(Team.name == name)).scalar_one_or_none()
    if row:
        return row
    row = Team(name=name, league_id=league_id)
    session.add(row)
    session.flush()
    return row


def ingest_odds_legs(legs: list[BetLeg], league_key: str, league_name: str) -> int:
    """Persist live odds legs into the warehouse."""
    init_warehouse()
    written = 0
    with session_scope() as session:
        run = IngestRun(source=f"odds_api:{league_key}", status="running")
        session.add(run)
        session.flush()
        league = _get_or_create_league(session, league_key, league_name)
        try:
            for leg in legs:
                meta = leg.market.metadata
                home = meta.get("home_team") or "Home"
                away = meta.get("away_team") or "Away"
                home_team = _get_or_create_team(session, str(home), league.id)
                away_team = _get_or_create_team(session, str(away), league.id)
                external_id = leg.market.event_id
                match = session.execute(
                    select(Match).where(Match.external_id == external_id)
                ).scalar_one_or_none()
                if not match:
                    match = Match(
                        external_id=external_id,
                        league_id=league.id,
                        home_team_id=home_team.id,
                        away_team_id=away_team.id,
                    )
                    session.add(match)
                    session.flush()
                session.add(
                    OddsSnapshot(
                        market_id=leg.market.market_id,
                        match_external_id=external_id,
                        sportsbook=leg.market.sportsbook,
                        market_type=leg.market.market_type.value,
                        label=leg.market.label,
                        odds_american=leg.market.odds.value,
                        implied_probability=leg.implied_probability,
                        captured_at=datetime.now(timezone.utc),
                    )
                )
                written += 1
            run.status = "success"
            run.rows_written = written
            run.finished_at = datetime.now(timezone.utc)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            logger.exception("Warehouse odds ingest failed")
            raise
    return written


def ingest_player_logs_from_json(rows: list[dict[str, Any]]) -> int:
    from .models import Player, PlayerMatchStat

    init_warehouse()
    written = 0
    with session_scope() as session:
        for row in rows:
            player = session.execute(
                select(Player).where(Player.name == row["player"])
            ).scalar_one_or_none()
            if not player:
                player = Player(name=row["player"])
                session.add(player)
                session.flush()
            match = session.execute(
                select(Match).where(Match.external_id == str(row.get("event_id", row["game_date"])))
            ).scalar_one_or_none()
            if not match:
                home = _get_or_create_team(session, row.get("team") or "Unknown")
                away = _get_or_create_team(session, row.get("opponent") or "Opponent")
                match = Match(
                    external_id=str(row.get("event_id", row["game_date"])),
                    home_team_id=home.id,
                    away_team_id=away.id,
                )
                session.add(match)
                session.flush()
            existing = session.execute(
                select(PlayerMatchStat).where(
                    PlayerMatchStat.match_id == match.id,
                    PlayerMatchStat.player_id == player.id,
                )
            ).scalar_one_or_none()
            if existing:
                continue
            session.add(
                PlayerMatchStat(
                    match_id=match.id,
                    player_id=player.id,
                    minutes=float(row.get("minutes", 90)),
                    shots=float(row.get("shots", 0)),
                    shots_on_target=float(row.get("shots_on_target", 0)),
                    goals=float(row.get("goals", 0)),
                    assists=float(row.get("assists", 0)),
                )
            )
            written += 1
    return written
