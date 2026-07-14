from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from ..logging_config import get_logger
from .builders import build_player_shot_features, build_team_form_features  # noqa: F401
from .registry import REGISTRY, list_features

logger = get_logger(__name__)


def materialize_match_features(match_external_id: str, window: int = 5) -> dict[str, Any]:
    """Build all registered features for a match."""
    features: dict[str, float] = {}
    for name in list_features():
        spec = REGISTRY[name]
        if name == "team_form":
            features.update(spec.builder(match_external_id, window=window))
        elif name == "player_shots":
            continue  # player features need player_name — built per market
    payload = {
        "match_external_id": match_external_id,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "features": features,
        "features_hash": _hash_features(features),
    }
    logger.info("Materialized %s features for match %s", len(features), match_external_id)
    return payload


def materialize_player_market_features(player_name: str, match_external_id: str, window: int = 5) -> dict[str, Any]:
    base = materialize_match_features(match_external_id, window=window)
    shot_feats = REGISTRY["player_shots"].builder(player_name, window=window)
    all_feats = {**base["features"], **shot_feats}
    return {
        **base,
        "player": player_name,
        "features": all_feats,
        "features_hash": _hash_features(all_feats),
    }


def _hash_features(features: dict[str, float]) -> str:
    blob = json.dumps(features, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
