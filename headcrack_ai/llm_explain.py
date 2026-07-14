from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .models import BetLeg, Parlay
from .plain_language import (
    describe_edge,
    describe_ev_per_dollar,
    format_american_odds,
    format_chance,
    parlay_chance_in_words,
    payout_band_label,
    value_verdict,
)

SYSTEM_PROMPT = (
    "You are Headcrack AI, a friendly sports betting helper. Explain picks in plain "
    "English that anyone can understand. Avoid jargon like EV, implied probability, "
    "or Kelly. Never promise guaranteed profit."
)


def _leg_summary(leg: BetLeg) -> dict[str, Any]:
    return {
        "label": leg.market.label,
        "odds": leg.market.odds.value,
        "model_probability": round(leg.model_probability, 4),
        "implied_probability": round(leg.implied_probability, 4),
        "edge": round(leg.edge, 4),
        "ev_per_dollar": round(leg.ev_per_dollar, 4),
        "tags": list(leg.tags),
    }


def _parlay_summary(parlay: Parlay) -> dict[str, Any]:
    return {
        "stake": round(parlay.stake, 2),
        "payout": round(parlay.gross_payout, 2),
        "adjusted_probability": round(parlay.adjusted_probability, 4),
        "expected_value": round(parlay.expected_value, 2),
        "correlation_score": round(parlay.correlation_score, 2),
        "risk_score": round(parlay.risk_score, 2),
        "legs": [_leg_summary(leg) for leg in parlay.legs],
    }


def summarize_card(card: dict[str, list[Parlay]]) -> dict[str, Any]:
    """Build a JSON-serializable snapshot of a card for narration."""
    summary: dict[str, Any] = {"bands": {}}
    best_single: dict[str, Any] | None = None
    for band, parlays in card.items():
        summary["bands"][band] = [_parlay_summary(parlay) for parlay in parlays[:3]]
        for parlay in parlays:
            for leg in parlay.legs:
                candidate = _leg_summary(leg)
                if best_single is None or candidate["ev_per_dollar"] > best_single["ev_per_dollar"]:
                    best_single = candidate
    summary["best_single"] = best_single
    return summary


@runtime_checkable
class CardNarrator(Protocol):
    def narrate(self, summary: dict[str, Any]) -> str: ...


class TemplateNarrator:
    """Deterministic, offline narrator. No network, always available."""

    def narrate(self, summary: dict[str, Any]) -> str:
        lines: list[str] = ["**Here's our read on today's picks.**", ""]

        best = summary.get("best_single")
        if best:
            lines.append(
                f"**Best single bet:** {best['label']} at {format_american_odds(best['odds'])}. "
                f"We think {format_chance(best['model_probability'])}, "
                f"the book thinks {format_chance(best['implied_probability'])}. "
                f"{value_verdict(best['edge'])} — {describe_edge(best['edge'])}."
            )
            lines.append("")

        for band, parlays in summary.get("bands", {}).items():
            lines.append(f"**{payout_band_label(band)}**")
            if not parlays:
                lines.append("- Nothing fit this payout range. Sitting out is fine.")
                lines.append("")
                continue
            top = parlays[0]
            leg_labels = ", ".join(leg["label"] for leg in top["legs"])
            outlook = (
                "looks worth a shot on paper"
                if top["expected_value"] > 0
                else "is more of a fun longshot than a value play"
            )
            lines.append(
                f"- Bet ${top['stake']:.2f} to win ${top['payout']:.2f}. "
                f"Chance to hit: {format_chance(top['adjusted_probability'])} "
                f"({parlay_chance_in_words(top['adjusted_probability'])}). "
                f"This slip {outlook}."
            )
            lines.append(f"  Picks: {leg_labels}.")
            if top["correlation_score"] >= 1.0:
                lines.append("  ✅ These picks tell the same story — that's a good sign.")
            elif top["correlation_score"] <= 0:
                lines.append("  ⚠️ These picks clash — be careful with this combo.")
            if top["risk_score"] >= 1.5:
                lines.append("  🎲 High risk — keep the bet small.")
            lines.append("")

        lines.append("*Remember: no pick is guaranteed. Only bet what you can afford to lose.*")
        return "\n".join(lines).strip()


@dataclass
class OpenAINarrator:
    """Optional OpenAI-compatible narrator. Used only when an API key is set."""

    api_key: str
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "OpenAINarrator | None":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            model=os.getenv("HEADCRACK_LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    def narrate(self, summary: dict[str, Any]) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Explain this betting card as a short brief:\n"
                    + json.dumps(summary, indent=2),
                },
            ],
            "temperature": 0.4,
        }
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # nosec B310
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()


def get_default_narrator() -> CardNarrator:
    """Prefer a configured LLM narrator, else fall back to the offline template."""
    return OpenAINarrator.from_env() or TemplateNarrator()


def explain_card_narrative(
    card: dict[str, list[Parlay]],
    narrator: CardNarrator | None = None,
    brief: dict[str, Any] | None = None,
) -> str:
    narrator = narrator or get_default_narrator()
    summary = brief["card_summary"] if brief else summarize_card(card)
    return narrator.narrate(summary)


def explain_brief_narrative(brief: dict[str, Any], narrator: CardNarrator | None = None) -> str:
    """Narrate from grounded card brief facts only."""
    return explain_card_narrative({}, narrator=narrator, brief=brief)
