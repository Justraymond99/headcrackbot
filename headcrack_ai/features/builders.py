from __future__ import annotations

from sqlalchemy import select

from ..warehouse.models import Match, PlayerMatchStat, TeamMatchStat
from ..warehouse.session import session_scope
from .registry import register, FeatureSpec


def _team_form(team_id: int, window: int = 5) -> dict[str, float]:
    with session_scope() as session:
        rows = session.execute(
            select(TeamMatchStat)
            .where(TeamMatchStat.team_id == team_id)
            .order_by(TeamMatchStat.id.desc())
            .limit(window)
        ).scalars().all()
    if not rows:
        return {"games": 0.0, "avg_goals_for": 1.3, "avg_goals_against": 1.1, "avg_shots_for": 12.0}
    n = len(rows)
    return {
        "games": float(n),
        "avg_goals_for": sum(r.goals_for for r in rows) / n,
        "avg_goals_against": sum(r.goals_against for r in rows) / n,
        "avg_shots_for": sum(r.shots_for for r in rows) / n,
    }


def build_team_form_features(match_external_id: str, window: int = 5) -> dict[str, float]:
    with session_scope() as session:
        match = session.execute(
            select(Match).where(Match.external_id == match_external_id)
        ).scalar_one_or_none()
    if not match:
        return {}
    home = _team_form(match.home_team_id, window)
    away = _team_form(match.away_team_id, window)
    return {f"home_{k}": v for k, v in home.items()} | {f"away_{k}": v for k, v in away.items()}


def build_player_shot_features(player_name: str, window: int = 5) -> dict[str, float]:
    from ..warehouse.models import Player

    with session_scope() as session:
        player = session.execute(select(Player).where(Player.name == player_name)).scalar_one_or_none()
        if not player:
            return {}
        rows = session.execute(
            select(PlayerMatchStat)
            .where(PlayerMatchStat.player_id == player.id)
            .order_by(PlayerMatchStat.id.desc())
            .limit(window)
        ).scalars().all()
    if not rows:
        return {}
    n = len(rows)
    total_min = sum(r.minutes for r in rows) or 1.0
    total_shots = sum(r.shots for r in rows)
    return {
        "player_games": float(n),
        "player_avg_shots": total_shots / n,
        "player_shots_per_90": total_shots / total_min * 90.0,
    }


register(FeatureSpec("team_form", "v1", "Rolling team goals and shots", build_team_form_features))
register(FeatureSpec("player_shots", "v1", "Rolling player shot rates", build_player_shot_features))
