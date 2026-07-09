from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from .models import BetLeg, BetRecord, Market, Prediction, ResultStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    market_id TEXT PRIMARY KEY,
    sport TEXT NOT NULL,
    event_id TEXT NOT NULL,
    label TEXT NOT NULL,
    market_type TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    odds INTEGER NOT NULL,
    team TEXT,
    opponent TEXT,
    player TEXT,
    threshold REAL,
    starts_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    model_probability REAL NOT NULL,
    model_name TEXT NOT NULL,
    confidence REAL NOT NULL,
    features_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (market_id) REFERENCES markets(market_id)
);

CREATE TABLE IF NOT EXISTS bet_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(market_id)
);

CREATE TABLE IF NOT EXISTS bet_records (
    bet_id TEXT PRIMARY KEY,
    stake REAL NOT NULL,
    decimal_odds REAL NOT NULL,
    status TEXT NOT NULL,
    payout REAL NOT NULL DEFAULT 0,
    placed_at TEXT NOT NULL,
    legs_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    odds INTEGER NOT NULL,
    implied_probability REAL NOT NULL,
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_markets_event_id ON markets(event_id);
CREATE INDEX IF NOT EXISTS idx_markets_sportsbook ON markets(sportsbook);
CREATE INDEX IF NOT EXISTS idx_predictions_market_id ON predictions(market_id);
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_market_id ON odds_snapshots(market_id);
"""


class SQLiteStore:
    def __init__(self, database_url: str | Path = "headcrack_ai.sqlite3") -> None:
        self.path = Path(str(database_url).replace("sqlite:///", ""))
        self.path.parent.mkdir(parents=True, exist_ok=True) if self.path.parent != Path(".") else None

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def upsert_market(self, market: Market) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO markets (
                    market_id, sport, event_id, label, market_type, sportsbook, odds,
                    team, opponent, player, threshold, starts_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(market_id) DO UPDATE SET
                    sport=excluded.sport,
                    event_id=excluded.event_id,
                    label=excluded.label,
                    market_type=excluded.market_type,
                    sportsbook=excluded.sportsbook,
                    odds=excluded.odds,
                    team=excluded.team,
                    opponent=excluded.opponent,
                    player=excluded.player,
                    threshold=excluded.threshold,
                    starts_at=excluded.starts_at,
                    metadata_json=excluded.metadata_json
                """,
                (
                    market.market_id,
                    market.sport.value,
                    market.event_id,
                    market.label,
                    market.market_type.value,
                    market.sportsbook,
                    market.odds.value,
                    market.team,
                    market.opponent,
                    market.player,
                    market.threshold,
                    market.starts_at.isoformat() if market.starts_at else None,
                    json.dumps(market.metadata),
                ),
            )
            conn.execute(
                """
                INSERT INTO odds_snapshots (market_id, sportsbook, odds, implied_probability)
                VALUES (?, ?, ?, ?)
                """,
                (market.market_id, market.sportsbook, market.odds.value, market.odds.implied_probability),
            )

    def insert_prediction(self, prediction: Prediction) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO predictions (
                    market_id, model_probability, model_name, confidence, features_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    prediction.market_id,
                    prediction.model_probability,
                    prediction.model_name,
                    prediction.confidence,
                    json.dumps(prediction.features),
                    prediction.created_at.isoformat(),
                ),
            )

    def save_leg(self, leg: BetLeg) -> None:
        self.upsert_market(leg.market)
        self.insert_prediction(leg.prediction)
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO bet_legs (market_id, tags) VALUES (?, ?)",
                (leg.market.market_id, "|".join(leg.tags)),
            )

    def save_legs(self, legs: list[BetLeg]) -> None:
        for leg in legs:
            self.save_leg(leg)

    def save_bet_record(self, record: BetRecord) -> None:
        legs_payload = [
            {
                "market_id": leg.market.market_id,
                "label": leg.market.label,
                "odds": leg.market.odds.value,
                "model_probability": leg.model_probability,
                "tags": list(leg.tags),
            }
            for leg in record.legs
        ]
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO bet_records (bet_id, stake, decimal_odds, status, payout, placed_at, legs_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bet_id) DO UPDATE SET
                    stake=excluded.stake,
                    decimal_odds=excluded.decimal_odds,
                    status=excluded.status,
                    payout=excluded.payout,
                    placed_at=excluded.placed_at,
                    legs_json=excluded.legs_json
                """,
                (
                    record.bet_id,
                    record.stake,
                    record.decimal_odds,
                    record.status.value,
                    record.payout,
                    record.placed_at.isoformat(),
                    json.dumps(legs_payload),
                ),
            )

    def update_bet_result(self, bet_id: str, status: ResultStatus, payout: float = 0.0) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE bet_records SET status = ?, payout = ? WHERE bet_id = ?",
                (status.value, payout, bet_id),
            )

    def value_board(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    m.market_id,
                    m.label,
                    m.sport,
                    m.event_id,
                    m.market_type,
                    m.sportsbook,
                    m.odds,
                    p.model_probability,
                    p.confidence,
                    p.model_name,
                    (p.model_probability - CASE
                        WHEN m.odds > 0 THEN 100.0 / (m.odds + 100.0)
                        ELSE ABS(m.odds) / (ABS(m.odds) + 100.0)
                    END) AS edge
                FROM markets m
                JOIN predictions p ON p.market_id = m.market_id
                ORDER BY edge DESC, p.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
