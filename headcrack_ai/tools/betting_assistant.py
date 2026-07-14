from __future__ import annotations

import json
import urllib.request
from typing import Any

from ..explain import build_card_brief, explain_pick_rationale
from ..llm_explain import OpenAINarrator, TemplateNarrator, SYSTEM_PROMPT
from ..models import BetLeg
from ..optimizer import build_card
from ..plain_language import format_american_odds, format_chance, value_verdict
from .ev_finder import find_positive_ev
from .projections import build_match_projections, format_projection_card


class BettingAssistant:
    """Grounded AI betting assistant — template offline, optional LLM when configured."""

    def __init__(self, narrator: Any | None = None) -> None:
        self._narrator = narrator

    def answer(
        self,
        question: str,
        legs: list[BetLeg],
        budget: float = 20.0,
        min_edge: float = -0.02,
    ) -> str:
        question = question.strip()
        if not question:
            return "Ask me about today's board — best bets, parlays, matchups, or +EV plays."

        brief = build_card_brief(legs, budget=budget, min_edge=min_edge) if legs else None
        template_reply = self._template_answer(question, legs, brief)

        narrator = self._narrator or OpenAINarrator.from_env()
        if narrator is None or not isinstance(narrator, OpenAINarrator):
            return template_reply

        facts = self._grounding_facts(legs, brief)
        try:
            return self._llm_answer(narrator, question, facts, template_reply)
        except Exception:
            return template_reply

    def _llm_answer(
        self, narrator: OpenAINarrator, question: str, facts: dict[str, Any], fallback: str
    ) -> str:
        payload = {
            "model": narrator.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                    + " Answer the user's betting question using ONLY the JSON facts. "
                    "If facts are insufficient, say what data is missing.",
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nFacts:\n{json.dumps(facts, indent=2)}",
                },
            ],
            "temperature": 0.35,
        }
        request = urllib.request.Request(
            f"{narrator.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {narrator.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=narrator.timeout) as response:  # nosec B310
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()

    def _grounding_facts(self, legs: list[BetLeg], brief: dict[str, Any] | None) -> dict[str, Any]:
        ev = find_positive_ev(legs, min_edge=0.01, limit=8) if legs else []
        projections = build_match_projections(legs)[:5] if legs else []
        return {
            "lines_loaded": len(legs),
            "brief": brief,
            "top_ev": [
                {
                    "pick": leg.market.label,
                    "book": leg.market.sportsbook,
                    "odds": leg.market.odds.value,
                    "edge": round(leg.edge, 4),
                    "model_probability": round(leg.model_probability, 4),
                    "why": explain_pick_rationale(leg),
                }
                for leg in ev
            ],
            "projections": [
                {
                    "match": p["match"],
                    "home_xg": p["home_xg"],
                    "away_xg": p["away_xg"],
                    "home_win": p["home_win"],
                    "draw": p["draw"],
                    "away_win": p["away_win"],
                }
                for p in projections
            ],
        }

    def _template_answer(self, question: str, legs: list[BetLeg], brief: dict[str, Any] | None) -> str:
        q = question.lower()

        if not legs:
            return (
                "I don't have lines loaded yet. Head to **Odds Screen** or **Live Odds**, "
                "fetch today's soccer, then ask again."
            )

        if any(word in q for word in ("best", "top", "value", "pick", "bet")):
            return self._best_bets_reply(legs, brief)

        if "parlay" in q or "slip" in q or "combo" in q:
            return self._parlay_reply(legs, brief)

        if any(word in q for word in ("projection", "xg", "matchup", "simulate", "score")):
            return self._projection_reply(legs, question)

        if any(word in q for word in ("ev", "edge", "expected value", "+ev")):
            return self._ev_reply(legs)

        if any(word in q for word in ("why", "explain", "rationale")):
            return self._why_reply(legs)

        if brief:
            narrator = TemplateNarrator()
            return narrator.narrate(brief["card_summary"])

        return (
            "I can break down **best bets**, **parlays**, **match projections**, or **+EV plays**. "
            "Try: 'What are the best +EV bets today?' or 'Break down Argentina vs Switzerland.'"
        )

    def _best_bets_reply(self, legs: list[BetLeg], brief: dict[str, Any] | None) -> str:
        lines = ["**Top model-backed picks right now:**", ""]
        ranked = find_positive_ev(legs, min_edge=0.0, limit=5)
        if not ranked:
            lines.append("Nothing stands out as clear value on this board.")
            return "\n".join(lines)
        for leg in ranked:
            lines.append(
                f"- **{leg.market.label}** ({leg.market.sportsbook}, {format_american_odds(leg.market.odds.value)}) — "
                f"{value_verdict(leg.edge)}, model {format_chance(leg.model_probability)}"
            )
            lines.append(f"  {explain_pick_rationale(leg)}")
        if brief and brief.get("warnings"):
            lines.extend(["", "**Heads up:**"] + [f"- {w}" for w in brief["warnings"]])
        lines.append("\n*No guarantees — bet responsibly.*")
        return "\n".join(lines)

    def _parlay_reply(self, legs: list[BetLeg], brief: dict[str, Any] | None) -> str:
        card = build_card(legs, budget=20.0, min_edge=-0.02)
        lines = ["**Parlay ideas by payout band:**", ""]
        for idea in (brief or {}).get("parlay_ideas", []):
            lines.append(
                f"- **{idea['band']}**: ${idea['stake']:.0f} → ${idea['payout']:.0f} "
                f"({idea['chance']:.0%}) — {', '.join(idea['picks'][:4])}"
            )
        if not (brief or {}).get("parlay_ideas"):
            lines.append("No parlays fit cleanly today without forcing longshots.")
        return "\n".join(lines)

    def _projection_reply(self, legs: list[BetLeg], question: str) -> str:
        projections = build_match_projections(legs)
        if not projections:
            return "No match projections available for the loaded lines."
        team = self._extract_team_query(question, legs)
        if team:
            projections = [p for p in projections if team in p["match"].lower()] or projections[:1]
        return "\n\n".join(format_projection_card(p) for p in projections[:3])

    def _ev_reply(self, legs: list[BetLeg]) -> str:
        ev = find_positive_ev(legs, min_edge=0.02, limit=10)
        if not ev:
            return "No strong +EV spots at 2%+ edge on this board. Try lowering your edge filter."
        lines = ["**+EV Finder results (2%+ edge):**", ""]
        for leg in ev:
            lines.append(
                f"- {leg.market.label} @ {leg.market.sportsbook} — "
                f"edge {leg.edge:+.1%}, EV ${leg.ev_per_dollar:+.2f}/$1"
            )
        return "\n".join(lines)

    def _why_reply(self, legs: list[BetLeg]) -> str:
        ranked = sorted(legs, key=lambda leg: leg.edge, reverse=True)[:3]
        lines = ["**Why the model likes these:**", ""]
        for leg in ranked:
            lines.append(f"- **{leg.market.label}** — {explain_pick_rationale(leg)}")
        return "\n".join(lines)

    def _extract_team_query(self, question: str, legs: list[BetLeg]) -> str:
        q = question.lower()
        teams: set[str] = set()
        for leg in legs:
            if leg.market.team:
                teams.add(leg.market.team.lower())
            meta = leg.market.metadata
            for key in ("home_team", "away_team"):
                if meta.get(key):
                    teams.add(str(meta[key]).lower())
        for team in sorted(teams, key=len, reverse=True):
            if team in q:
                return team
        return ""
