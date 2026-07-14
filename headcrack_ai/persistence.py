from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import require_sqlite_url
from .models import AmericanOdds, BetLeg, BetRecord, Market, MarketType, Prediction, ResultStatus, Sport, VenueType

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
    venue_type TEXT NOT NULL DEFAULT 'sportsbook',
    canonical_event_id TEXT,
    canonical_outcome_id TEXT,
    quoted_at TEXT,
    bid REAL,
    ask REAL,
    liquidity REAL,
    source_url TEXT,
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

CREATE TABLE IF NOT EXISTS market_results (
    market_id TEXT PRIMARY KEY,
    outcome TEXT NOT NULL,
    settled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_markets_event_id ON markets(event_id);
CREATE INDEX IF NOT EXISTS idx_markets_sportsbook ON markets(sportsbook);
CREATE INDEX IF NOT EXISTS idx_predictions_market_id ON predictions(market_id);
CREATE INDEX IF NOT EXISTS idx_predictions_market_created ON predictions(market_id, created_at, id);
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_market_id ON odds_snapshots(market_id);
"""


class SQLiteStore:
    def __init__(self, database_url: str | Path = "headcrack_ai.sqlite3") -> None:
        database_url = require_sqlite_url(str(database_url))
        self.path = Path(database_url.replace("sqlite:///", ""))
        self.path.parent.mkdir(parents=True, exist_ok=True) if self.path.parent != Path(".") else None

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Add venue columns safely on existing SQLite databases."""
        cols = {row[1] for row in conn.execute("PRAGMA table_info(markets)").fetchall()}
        alterations = [
            ("venue_type", "TEXT NOT NULL DEFAULT 'sportsbook'"),
            ("canonical_event_id", "TEXT"),
            ("canonical_outcome_id", "TEXT"),
            ("quoted_at", "TEXT"),
            ("bid", "REAL"),
            ("ask", "REAL"),
            ("liquidity", "REAL"),
            ("source_url", "TEXT"),
        ]
        for name, ddl in alterations:
            if name not in cols:
                conn.execute(f"ALTER TABLE markets ADD COLUMN {name} {ddl}")

    def save_legs(self, legs: list[BetLeg]) -> None:
        if not legs:
            return
        with self.connect() as conn:
            for leg in legs:
                self._upsert_market_conn(conn, leg.market)
                self._insert_prediction_conn(conn, leg.prediction)
                tags = "|".join(leg.tags)
                conn.execute(
                    """
                    INSERT INTO bet_legs (market_id, tags)
                    SELECT ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM bet_legs
                        WHERE market_id = ? AND tags = ?
                    )
                    """,
                    (leg.market.market_id, tags, leg.market.market_id, tags),
                )

    def _upsert_market_conn(self, conn: sqlite3.Connection, market: Market) -> None:
        from .models import venue_type_for_name

        venue = market.venue_type.value if getattr(market, "venue_type", None) else venue_type_for_name(market.sportsbook).value
        conn.execute(
            """
            INSERT INTO markets (
                market_id, sport, event_id, label, market_type, sportsbook, odds,
                team, opponent, player, threshold, starts_at, metadata_json,
                venue_type, canonical_event_id, canonical_outcome_id, quoted_at,
                bid, ask, liquidity, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                metadata_json=excluded.metadata_json,
                venue_type=excluded.venue_type,
                canonical_event_id=excluded.canonical_event_id,
                canonical_outcome_id=excluded.canonical_outcome_id,
                quoted_at=excluded.quoted_at,
                bid=excluded.bid,
                ask=excluded.ask,
                liquidity=excluded.liquidity,
                source_url=excluded.source_url
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
                venue,
                getattr(market, "canonical_event_id", None),
                getattr(market, "canonical_outcome_id", None),
                market.quoted_at.isoformat() if getattr(market, "quoted_at", None) else None,
                getattr(market, "bid", None),
                getattr(market, "ask", None),
                getattr(market, "liquidity", None),
                getattr(market, "source_url", None),
            ),
        )
        conn.execute(
            """
            INSERT INTO odds_snapshots (market_id, sportsbook, odds, implied_probability)
            VALUES (?, ?, ?, ?)
            """,
            (market.market_id, market.sportsbook, market.odds.value, market.odds.implied_probability),
        )

    def _insert_prediction_conn(self, conn: sqlite3.Connection, prediction: Prediction) -> None:
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
        self.save_legs([leg])

    def upsert_market(self, market: Market) -> None:
        with self.connect() as conn:
            self._upsert_market_conn(conn, market)

    def insert_prediction(self, prediction: Prediction) -> None:
        with self.connect() as conn:
            self._insert_prediction_conn(conn, prediction)

    def save_bet_record(self, record: BetRecord) -> None:
        legs_payload = [
            {
                "market_id": leg.market.market_id,
                "label": leg.market.label,
                "sport": leg.market.sport.value,
                "market_type": leg.market.market_type.value,
                "sportsbook": leg.market.sportsbook,
                "odds": leg.market.odds.value,
                "decimal_odds": leg.decimal_odds,
                "model_probability": leg.model_probability,
                "implied_probability": leg.implied_probability,
                "confidence": leg.prediction.confidence,
                "model_name": leg.prediction.model_name,
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

    def all_bet_records(self) -> list[dict]:
        """Return persisted bet records with parsed legs, newest first."""
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT bet_id, stake, decimal_odds, status, payout, placed_at, legs_json
                FROM bet_records
                ORDER BY placed_at DESC, bet_id DESC
                """
            ).fetchall()
        records: list[dict] = []
        for row in rows:
            record = dict(row)
            record["legs"] = json.loads(record.pop("legs_json") or "[]")
            records.append(record)
        return records

    def record_market_result(self, market_id: str, outcome: ResultStatus) -> None:
        """Record the real-world outcome of a single market for tracking/calibration."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO market_results (market_id, outcome, settled_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(market_id) DO UPDATE SET
                    outcome=excluded.outcome,
                    settled_at=excluded.settled_at
                """,
                (market_id, outcome.value),
            )

    def market_results(self) -> dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT market_id, outcome FROM market_results").fetchall()
        return {row["market_id"]: row["outcome"] for row in rows}

    def calibration_rows(self) -> list[dict]:
        """Join each market's latest prediction with its recorded outcome."""
        with self.connect() as conn:
            rows = conn.execute(
                """
                WITH ranked_predictions AS (
                    SELECT
                        p.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY p.market_id
                            ORDER BY p.created_at DESC, p.id DESC
                        ) AS prediction_rank
                    FROM predictions p
                )
                SELECT
                    r.market_id,
                    r.outcome,
                    p.model_probability,
                    p.model_name,
                    p.confidence
                FROM market_results r
                JOIN ranked_predictions p
                    ON p.market_id = r.market_id AND p.prediction_rank = 1
                WHERE r.outcome IN ('won', 'lost')
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def settle_bets_from_market_results(self) -> int:
        """Settle pending bets from recorded market outcomes.

        A leg's outcome comes from ``market_results``. A void leg is treated as a
        push and excluded from the parlay: the effective payout odds are the
        product of the surviving winning legs. A bet is settled only once every
        leg has a recorded result. Returns the number of bets newly settled.
        """
        outcomes = self.market_results()
        settled_count = 0
        for record in self.all_bet_records():
            if record["status"] != ResultStatus.PENDING.value:
                continue
            legs = record["legs"]
            leg_outcomes = [outcomes.get(leg["market_id"]) for leg in legs]
            if any(outcome is None for outcome in leg_outcomes):
                continue  # Not every leg has settled yet.

            if any(outcome == ResultStatus.LOST.value for outcome in leg_outcomes):
                self.update_bet_result(record["bet_id"], ResultStatus.LOST, payout=0.0)
                settled_count += 1
                continue

            surviving = [
                leg
                for leg, outcome in zip(legs, leg_outcomes)
                if outcome == ResultStatus.WON.value
            ]
            if not surviving:
                # Every leg pushed: refund the stake.
                self.update_bet_result(record["bet_id"], ResultStatus.VOID, payout=record["stake"])
                settled_count += 1
                continue

            effective_odds = 1.0
            for leg in surviving:
                effective_odds *= float(leg.get("decimal_odds", 1.0))
            payout = round(record["stake"] * effective_odds, 2)
            self.update_bet_result(record["bet_id"], ResultStatus.WON, payout=payout)
            settled_count += 1
        return settled_count

    def value_board(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                WITH ranked_predictions AS (
                    SELECT
                        p.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY p.market_id
                            ORDER BY p.created_at DESC, p.id DESC
                        ) AS prediction_rank
                    FROM predictions p
                ),
                latest_predictions AS (
                    SELECT *
                    FROM ranked_predictions
                    WHERE prediction_rank = 1
                )
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
                JOIN latest_predictions p ON p.market_id = m.market_id
                ORDER BY edge DESC, p.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def latest_legs(self, limit: int = 250) -> list[BetLeg]:
        """Hydrate latest persisted market + prediction rows for API simulations."""
        with self.connect() as conn:
            rows = conn.execute(
                """
                WITH ranked_predictions AS (
                    SELECT
                        p.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY p.market_id
                            ORDER BY p.created_at DESC, p.id DESC
                        ) AS prediction_rank
                    FROM predictions p
                ),
                latest_tags AS (
                    SELECT market_id, tags
                    FROM bet_legs
                    WHERE id IN (
                        SELECT MAX(id)
                        FROM bet_legs
                        GROUP BY market_id
                    )
                )
                SELECT
                    m.*,
                    p.model_probability,
                    p.model_name,
                    p.confidence,
                    p.features_json,
                    p.created_at AS prediction_created_at,
                    COALESCE(t.tags, '') AS tags
                FROM markets m
                JOIN ranked_predictions p
                    ON p.market_id = m.market_id AND p.prediction_rank = 1
                LEFT JOIN latest_tags t ON t.market_id = m.market_id
                ORDER BY p.created_at DESC, m.market_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        legs: list[BetLeg] = []
        for row in rows:
            metadata = json.loads(row["metadata_json"] or "{}")
            features = json.loads(row["features_json"] or "{}")
            starts_at = _parse_datetime(row["starts_at"])
            quoted_at = _parse_datetime(row["quoted_at"])
            prediction_created_at = _parse_datetime(row["prediction_created_at"])
            market = Market(
                market_id=row["market_id"],
                sport=Sport(row["sport"]),
                event_id=row["event_id"],
                label=row["label"],
                market_type=MarketType(row["market_type"]),
                sportsbook=row["sportsbook"],
                odds=AmericanOdds(int(row["odds"])),
                team=row["team"],
                opponent=row["opponent"],
                player=row["player"],
                threshold=row["threshold"],
                starts_at=starts_at,
                metadata=metadata,
                venue_type=VenueType(row["venue_type"]),
                canonical_event_id=row["canonical_event_id"],
                canonical_outcome_id=row["canonical_outcome_id"],
                quoted_at=quoted_at,
                bid=row["bid"],
                ask=row["ask"],
                liquidity=row["liquidity"],
                source_url=row["source_url"],
            )
            prediction = Prediction(
                market_id=row["market_id"],
                model_probability=float(row["model_probability"]),
                model_name=row["model_name"],
                confidence=float(row["confidence"]),
                features=features,
                created_at=prediction_created_at or datetime.now(timezone.utc),
            )
            tags = tuple(tag for tag in str(row["tags"] or "").split("|") if tag)
            legs.append(BetLeg(market=market, prediction=prediction, tags=tags))
        return legs

    def line_movements(self, min_implied_move: float = 0.015, limit: int = 75) -> list[dict]:
        """Biggest implied-probability swings between earliest and latest snapshot."""
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.market_id,
                    m.label,
                    m.sportsbook,
                    m.event_id,
                    MIN(s.implied_probability) AS low_implied,
                    MAX(s.implied_probability) AS high_implied,
                    COUNT(*) AS snapshots,
                    MIN(s.captured_at) AS first_seen,
                    MAX(s.captured_at) AS last_seen,
                    (
                        SELECT odds FROM odds_snapshots s2
                        WHERE s2.market_id = s.market_id
                        ORDER BY s2.captured_at ASC LIMIT 1
                    ) AS open_odds,
                    (
                        SELECT odds FROM odds_snapshots s2
                        WHERE s2.market_id = s.market_id
                        ORDER BY s2.captured_at DESC LIMIT 1
                    ) AS current_odds
                FROM odds_snapshots s
                JOIN markets m ON m.market_id = s.market_id
                GROUP BY s.market_id
                HAVING snapshots > 1
                   AND (high_implied - low_implied) >= ?
                ORDER BY (high_implied - low_implied) DESC
                LIMIT ?
                """,
                (min_implied_move, limit),
            ).fetchall()
        results: list[dict] = []
        for row in rows:
            item = dict(row)
            item["move"] = round(item["high_implied"] - item["low_implied"], 4)
            results.append(item)
        return results


def _parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
