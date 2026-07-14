from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .persistence import SQLiteStore

FEATURE_SCHEMA = """
CREATE TABLE IF NOT EXISTS player_game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player TEXT NOT NULL,
    team TEXT,
    opponent TEXT,
    event_id TEXT,
    game_date TEXT NOT NULL,
    minutes REAL NOT NULL DEFAULT 90,
    shots REAL NOT NULL DEFAULT 0,
    shots_on_target REAL NOT NULL DEFAULT 0,
    goals REAL NOT NULL DEFAULT 0,
    assists REAL NOT NULL DEFAULT 0,
    is_home INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player, game_date, event_id)
);

CREATE TABLE IF NOT EXISTS team_game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team TEXT NOT NULL,
    opponent TEXT,
    event_id TEXT,
    game_date TEXT NOT NULL,
    goals_for REAL NOT NULL DEFAULT 0,
    goals_against REAL NOT NULL DEFAULT 0,
    shots_for REAL NOT NULL DEFAULT 0,
    shots_against REAL NOT NULL DEFAULT 0,
    corners_for REAL NOT NULL DEFAULT 0,
    corners_against REAL NOT NULL DEFAULT 0,
    is_home INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team, game_date, event_id)
);

CREATE INDEX IF NOT EXISTS idx_player_logs_player ON player_game_logs(player, game_date);
CREATE INDEX IF NOT EXISTS idx_team_logs_team ON team_game_logs(team, game_date);
"""

LEAGUE_AVG_SHOTS_ALLOWED = 12.0


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _to_bool_int(value: Any, default: int = 1) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "home", "h"} else 0
    return 1 if value else 0


@dataclass
class FeatureStore:
    store: SQLiteStore

    def initialize(self) -> None:
        with self.store.connect() as conn:
            conn.executescript(FEATURE_SCHEMA)

    def add_player_log(self, row: dict[str, Any]) -> None:
        with self.store.connect() as conn:
            conn.execute(
                """
                INSERT INTO player_game_logs
                    (player, team, opponent, event_id, game_date, minutes, shots,
                     shots_on_target, goals, assists, is_home)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player, game_date, event_id) DO UPDATE SET
                    team=excluded.team, opponent=excluded.opponent, minutes=excluded.minutes,
                    shots=excluded.shots, shots_on_target=excluded.shots_on_target,
                    goals=excluded.goals, assists=excluded.assists, is_home=excluded.is_home
                """,
                (
                    str(row["player"]),
                    row.get("team") or None,
                    row.get("opponent") or None,
                    str(row.get("event_id") or ""),
                    str(row["game_date"]),
                    _to_float(row.get("minutes"), 90.0),
                    _to_float(row.get("shots")),
                    _to_float(row.get("shots_on_target")),
                    _to_float(row.get("goals")),
                    _to_float(row.get("assists")),
                    _to_bool_int(row.get("is_home")),
                ),
            )

    def add_team_log(self, row: dict[str, Any]) -> None:
        with self.store.connect() as conn:
            conn.execute(
                """
                INSERT INTO team_game_logs
                    (team, opponent, event_id, game_date, goals_for, goals_against,
                     shots_for, shots_against, corners_for, corners_against, is_home)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team, game_date, event_id) DO UPDATE SET
                    opponent=excluded.opponent, goals_for=excluded.goals_for,
                    goals_against=excluded.goals_against, shots_for=excluded.shots_for,
                    shots_against=excluded.shots_against, corners_for=excluded.corners_for,
                    corners_against=excluded.corners_against, is_home=excluded.is_home
                """,
                (
                    str(row["team"]),
                    row.get("opponent") or None,
                    str(row.get("event_id") or ""),
                    str(row["game_date"]),
                    _to_float(row.get("goals_for")),
                    _to_float(row.get("goals_against")),
                    _to_float(row.get("shots_for")),
                    _to_float(row.get("shots_against")),
                    _to_float(row.get("corners_for")),
                    _to_float(row.get("corners_against")),
                    _to_bool_int(row.get("is_home")),
                ),
            )

    def ingest_player_logs(self, rows: Iterable[dict[str, Any]]) -> int:
        count = 0
        for row in rows:
            self.add_player_log(row)
            count += 1
        return count

    def ingest_team_logs(self, rows: Iterable[dict[str, Any]]) -> int:
        count = 0
        for row in rows:
            self.add_team_log(row)
            count += 1
        return count

    def player_shot_features(
        self,
        player: str,
        window: int = 10,
        before_date: str | None = None,
    ) -> dict[str, float] | None:
        """Rolling shot features from a player's most recent games."""
        query = "SELECT minutes, shots, shots_on_target FROM player_game_logs WHERE player = ?"
        params: list[Any] = [player]
        if before_date:
            query += " AND game_date < ?"
            params.append(before_date)
        query += " ORDER BY game_date DESC LIMIT ?"
        params.append(window)
        with self.store.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        if not rows:
            return None

        games = len(rows)
        total_minutes = sum(r["minutes"] for r in rows) or 1.0
        total_shots = sum(r["shots"] for r in rows)
        total_sot = sum(r["shots_on_target"] for r in rows)
        return {
            "games": games,
            "avg_shots": round(total_shots / games, 3),
            "avg_shots_on_target": round(total_sot / games, 3),
            "avg_minutes": round(total_minutes / games, 2),
            "shots_per_90": round(total_shots / total_minutes * 90.0, 3),
            "shots_on_target_per_90": round(total_sot / total_minutes * 90.0, 3),
        }

    def opponent_shots_allowed(self, team: str, window: int = 10, before_date: str | None = None) -> float | None:
        """Average shots a team concedes; used to adjust a player's expected shots."""
        query = "SELECT shots_against FROM team_game_logs WHERE team = ?"
        params: list[Any] = [team]
        if before_date:
            query += " AND game_date < ?"
            params.append(before_date)
        query += " ORDER BY game_date DESC LIMIT ?"
        params.append(window)
        with self.store.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        if not rows:
            return None
        return round(sum(r["shots_against"] for r in rows) / len(rows), 3)

    def team_offensive_rate(self, team: str, window: int = 10, before_date: str | None = None) -> float | None:
        """Average goals a team scores — used for live match xG estimates."""
        query = "SELECT goals_for FROM team_game_logs WHERE team = ?"
        params: list[Any] = [team]
        if before_date:
            query += " AND game_date < ?"
            params.append(before_date)
        query += " ORDER BY game_date DESC LIMIT ?"
        params.append(window)
        with self.store.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        if not rows:
            return None
        return round(sum(r["goals_for"] for r in rows) / len(rows), 3)


def _load_rows(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text())
        if isinstance(payload, dict):
            payload = payload.get("logs") or payload.get("rows") or []
        return list(payload)
    if suffix == ".csv":
        with path.open(newline="") as f:
            return list(csv.DictReader(f))
    raise ValueError("Input must be .csv or .json")


def load_player_logs(store: SQLiteStore, path: str | Path) -> int:
    feature_store = FeatureStore(store)
    feature_store.initialize()
    return feature_store.ingest_player_logs(_load_rows(path))


def load_team_logs(store: SQLiteStore, path: str | Path) -> int:
    feature_store = FeatureStore(store)
    feature_store.initialize()
    return feature_store.ingest_team_logs(_load_rows(path))
