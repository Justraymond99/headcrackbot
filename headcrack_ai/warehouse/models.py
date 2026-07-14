from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class League(Base):
    __tablename__ = "wh_leagues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))


class Team(Base):
    __tablename__ = "wh_teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("wh_leagues.id"))


class Player(Base):
    __tablename__ = "wh_players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("wh_teams.id"))


class Match(Base):
    __tablename__ = "wh_matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("wh_leagues.id"))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("wh_teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("wh_teams.id"))
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    home_goals: Mapped[int | None] = mapped_column(Integer)
    away_goals: Mapped[int | None] = mapped_column(Integer)


class PlayerMatchStat(Base):
    __tablename__ = "wh_player_match_stats"
    __table_args__ = (UniqueConstraint("match_id", "player_id", name="uq_player_match"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("wh_matches.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("wh_players.id"))
    minutes: Mapped[float] = mapped_column(Float, default=90.0)
    shots: Mapped[float] = mapped_column(Float, default=0.0)
    shots_on_target: Mapped[float] = mapped_column(Float, default=0.0)
    goals: Mapped[float] = mapped_column(Float, default=0.0)
    assists: Mapped[float] = mapped_column(Float, default=0.0)


class TeamMatchStat(Base):
    __tablename__ = "wh_team_match_stats"
    __table_args__ = (UniqueConstraint("match_id", "team_id", name="uq_team_match"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("wh_matches.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("wh_teams.id"))
    goals_for: Mapped[float] = mapped_column(Float, default=0.0)
    goals_against: Mapped[float] = mapped_column(Float, default=0.0)
    shots_for: Mapped[float] = mapped_column(Float, default=0.0)
    shots_against: Mapped[float] = mapped_column(Float, default=0.0)
    corners_for: Mapped[float] = mapped_column(Float, default=0.0)
    corners_against: Mapped[float] = mapped_column(Float, default=0.0)


class OddsSnapshot(Base):
    __tablename__ = "wh_odds_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[str] = mapped_column(String(256), index=True)
    match_external_id: Mapped[str] = mapped_column(String(128), index=True)
    sportsbook: Mapped[str] = mapped_column(String(64))
    market_type: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(512))
    odds_american: Mapped[int] = mapped_column(Integer)
    implied_probability: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ModelPrediction(Base):
    __tablename__ = "wh_model_predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[str] = mapped_column(String(256), index=True)
    model_name: Mapped[str] = mapped_column(String(128))
    model_version: Mapped[str] = mapped_column(String(64))
    probability: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    features_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class IngestRun(Base):
    __tablename__ = "wh_ingest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="running")
    rows_written: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


def init_warehouse() -> None:
    from .session import get_engine

    Base.metadata.create_all(get_engine())
