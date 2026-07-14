"""Interactive Telegram interface for Headcrack AI.

The bot uses Telegram's HTTPS long-polling API directly, so it does not need a
webhook or an additional Telegram framework dependency.
"""

from __future__ import annotations

import html
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from .models import BetLeg, Parlay
from .optimizer import LEG_BANDS, PRESETS, suggest_parlays
from .services import HeadcrackAIService
from .simulation import simulate_match_from_legs, simulate_parlay
from .soccer import group_legs_by_match

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096
HELP_TEXT = """<b>HEADCRACK AI</b>

<code>/status</code> — source and board status
<code>/refresh</code> — reload sportsbooks and prediction markets
<code>/games</code> — numbered live match list
<code>/picks [count]</code> — top value opportunities
<code>/props [count]</code> — top individual-player props
<code>/markets [count]</code> — Kalshi/Polymarket contracts
<code>/parlays [band] [preset]</code> — build suggested slips
<code>/simulate &lt;game #&gt;</code> — simulate a listed game
<code>/simparlay &lt;slip #&gt;</code> — simulate a suggested slip

Bands: <code>small</code>, <code>big</code>, <code>nuclear</code>
Presets: <code>balanced</code>, <code>cross_game</code>, <code>same_game</code>, <code>player_props</code>

Examples:
<code>/parlays small player_props</code>
<code>/simulate 2</code>"""


class TelegramApi:
    """Small wrapper around the Telegram Bot API."""

    def __init__(self, token: str, session: requests.Session | None = None):
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = session or requests.Session()

    def call(self, method: str, payload: dict[str, Any] | None = None, timeout: int = 20) -> Any:
        response = self.session.post(
            f"{self.base_url}/{method}",
            json=payload or {},
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise RuntimeError(body.get("description") or f"Telegram {method} failed")
        return body.get("result")

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset
        return self.call("getUpdates", payload, timeout=timeout + 10) or []

    def send_message(self, chat_id: str, text: str) -> None:
        for part in _split_message(text):
            self.call(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": part,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )

    def prepare_polling(self) -> None:
        self.call("deleteWebhook", {"drop_pending_updates": False})
        self.call(
            "setMyCommands",
            {
                "commands": [
                    {"command": "status", "description": "Board and source status"},
                    {"command": "refresh", "description": "Reload all market sources"},
                    {"command": "games", "description": "List live matches"},
                    {"command": "picks", "description": "Top value opportunities"},
                    {"command": "props", "description": "Top player props"},
                    {"command": "markets", "description": "Prediction markets"},
                    {"command": "parlays", "description": "Build suggested parlays"},
                    {"command": "simulate", "description": "Simulate a listed game"},
                    {"command": "simparlay", "description": "Simulate a suggested slip"},
                    {"command": "help", "description": "Show command guide"},
                ]
            },
        )


@dataclass
class TelegramBot:
    service: HeadcrackAIService
    api: TelegramApi
    allowed_chat_ids: frozenset[str]
    poll_timeout: int = 30
    cache_seconds: int = 300
    _pack: dict[str, Any] | None = field(default=None, init=False)
    _pack_time: float = field(default=0.0, init=False)
    _matches: list[tuple[str, list[BetLeg]]] = field(default_factory=list, init=False)
    _parlays: list[Parlay] = field(default_factory=list, init=False)

    @classmethod
    def from_env(cls) -> "TelegramBot":
        service = HeadcrackAIService.from_env()
        config = service.config
        if not config.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        if not config.telegram_allowed_chat_ids:
            raise RuntimeError(
                "Set TELEGRAM_ALLOWED_CHAT_IDS (comma-separated) or TELEGRAM_CHAT_ID "
                "before starting the bot"
            )
        return cls(
            service=service,
            api=TelegramApi(config.telegram_bot_token),
            allowed_chat_ids=frozenset(config.telegram_allowed_chat_ids),
            poll_timeout=config.telegram_poll_timeout,
        )

    def refresh(self) -> dict[str, Any]:
        self._pack = self.service.refresh_all_sources(include_player_props=True)
        self._pack_time = time.monotonic()
        grouped = group_legs_by_match(self._pack["sportsbook_legs"])
        self._matches = list(grouped.items())
        self._parlays = []
        return self._pack

    def board(self) -> dict[str, Any]:
        if self._pack is None or time.monotonic() - self._pack_time >= self.cache_seconds:
            return self.refresh()
        return self._pack

    def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        chat_id = str((message.get("chat") or {}).get("id") or "")
        text = str(message.get("text") or "").strip()
        if not chat_id or not text:
            return
        if chat_id not in self.allowed_chat_ids:
            logger.warning("Rejected Telegram chat id %s", chat_id)
            return
        try:
            reply = self.handle_command(text)
        except Exception:
            logger.exception("Telegram command failed: %s", text.split()[0])
            reply = (
                "That command failed while loading market data. Check the bot logs and "
                "try <code>/refresh</code> again."
            )
        self.api.send_message(chat_id, reply)

    def handle_command(self, text: str) -> str:
        parts = text.split()
        command = parts[0].split("@", 1)[0].lower()
        args = parts[1:]
        if command in {"/start", "/help"}:
            return HELP_TEXT
        if command == "/refresh":
            return self._format_status(self.refresh(), heading="Board refreshed")
        if command == "/status":
            return self._format_status(self.board())
        if command == "/games":
            return self._format_games(self.board())
        if command == "/picks":
            return self._format_legs(self.board()["sportsbook_legs"], args, props_only=False)
        if command == "/props":
            return self._format_legs(self.board()["sportsbook_legs"], args, props_only=True)
        if command == "/markets":
            return self._format_markets(self.board()["prediction_legs"], args)
        if command == "/parlays":
            return self._format_parlays(args)
        if command == "/simulate":
            return self._format_match_sim(args)
        if command == "/simparlay":
            return self._format_parlay_sim(args)
        return "Unknown command. Use <code>/help</code> to see what I can do."

    def _format_status(self, pack: dict[str, Any], heading: str = "Board status") -> str:
        events = len({leg.market.event_id for leg in pack["sportsbook_legs"]})
        lines = [
            f"<b>{heading}</b>",
            f"{events} matches · {len(pack['sportsbook_legs'])} sportsbook lines · "
            f"{len(pack['prediction_legs'])} prediction contracts",
            "",
        ]
        for source in pack["sources"]:
            marker = "🟢" if source.status == "live" else "🟡" if source.status == "stale" else "🔴"
            lines.append(f"{marker} <b>{html.escape(source.name)}</b>: {html.escape(source.detail)}")
        return "\n".join(lines)

    def _format_games(self, pack: dict[str, Any]) -> str:
        if not self._matches:
            grouped = group_legs_by_match(pack["sportsbook_legs"])
            self._matches = list(grouped.items())
        if not self._matches:
            return "No sportsbook matches are available right now."
        lines = ["<b>Live soccer board</b>", "Use <code>/simulate #</code> for a breakdown.", ""]
        for index, (name, legs) in enumerate(self._matches[:30], 1):
            props = sum(1 for leg in legs if leg.market.player)
            lines.append(
                f"<b>{index}.</b> {html.escape(name)}\n"
                f"   {len(legs)} lines · {props} player props"
            )
        return "\n".join(lines)

    def _format_legs(self, legs: list[BetLeg], args: list[str], props_only: bool) -> str:
        count = _bounded_count(args, default=8)
        ranked = [leg for leg in legs if bool(leg.market.player) is props_only]
        ranked.sort(key=lambda leg: (leg.edge, leg.ev_per_dollar), reverse=True)
        title = "Top player props" if props_only else "Top value opportunities"
        if not ranked:
            return f"No {title.lower()} are available right now."
        lines = [f"<b>{title}</b>", ""]
        for index, leg in enumerate(ranked[:count], 1):
            player = f" · {html.escape(leg.market.player)}" if leg.market.player else ""
            lines.append(
                f"<b>{index}. {html.escape(leg.market.label)}</b>{player}\n"
                f"   {html.escape(leg.market.sportsbook)} · {_odds(leg.market.odds.value)} · "
                f"model {leg.model_probability:.1%} · edge {leg.edge:+.1%}"
            )
        return "\n".join(lines)

    def _format_markets(self, legs: list[BetLeg], args: list[str]) -> str:
        count = _bounded_count(args, default=8)
        ranked = sorted(
            legs,
            key=lambda leg: (leg.market.liquidity or 0.0, leg.implied_probability),
            reverse=True,
        )
        if not ranked:
            return "No Kalshi or Polymarket soccer contracts are available right now."
        lines = ["<b>Prediction markets</b>", "Read-only comparison; no order execution.", ""]
        for index, leg in enumerate(ranked[:count], 1):
            liquidity = (
                f" · liq ${leg.market.liquidity:,.0f}" if leg.market.liquidity is not None else ""
            )
            lines.append(
                f"<b>{index}. {html.escape(leg.market.label)}</b>\n"
                f"   {html.escape(leg.market.sportsbook)} · {leg.implied_probability:.1%}{liquidity}"
            )
        return "\n".join(lines)

    def _format_parlays(self, args: list[str]) -> str:
        band = args[0].lower() if args else "small"
        preset = args[1].lower() if len(args) > 1 else "balanced"
        if band not in LEG_BANDS:
            return f"Unknown band. Choose: <code>{'</code>, <code>'.join(LEG_BANDS)}</code>"
        if preset not in PRESETS:
            return f"Unknown preset. Choose: <code>{'</code>, <code>'.join(PRESETS)}</code>"
        pack = self.board()
        self._parlays = suggest_parlays(
            pack["sportsbook_legs"],
            stake=3.0,
            band=band,
            preset=preset,
            count=3,
        )
        if not self._parlays:
            return (
                f"No valid {html.escape(band)} / {html.escape(preset)} slips fit the current "
                "board. Try <code>/parlays small balanced</code>."
            )
        lines = [
            f"<b>Suggested {html.escape(PRESETS[preset]['label'])} slips</b>",
            "Single-sportsbook only. Combined odds are estimates.",
            "",
        ]
        for index, parlay in enumerate(self._parlays, 1):
            lines.append(
                f"<b>Slip {index} · {html.escape(parlay.sportsbook)} · "
                f"{len(parlay.legs)} legs</b>\n"
                f"Est. {_decimal_to_american(parlay.decimal_odds)} · "
                f"model hit {parlay.adjusted_probability:.1%}"
            )
            for leg in parlay.legs:
                lines.append(f"  • {html.escape(leg.market.label)} ({_odds(leg.market.odds.value)})")
            lines.append(f"Simulate: <code>/simparlay {index}</code>\n")
        return "\n".join(lines)

    def _format_match_sim(self, args: list[str]) -> str:
        self.board()
        try:
            index = _parse_index(args, len(self._matches), "Use /games, then /simulate <game #>.")
        except ValueError as exc:
            return html.escape(str(exc))
        name, legs = self._matches[index]
        result = simulate_match_from_legs(
            legs,
            simulations=10_000,
            prediction_legs=self._pack["prediction_legs"] if self._pack else None,
        )
        top_scores = ", ".join(
            f"{score} ({count / result.simulations:.1%})"
            for score, count in list(result.top_scores.items())[:5]
        )
        return (
            f"<b>{html.escape(name)}</b>\n"
            f"xG: {html.escape(result.home_team)} {result.home_xg:.2f} – "
            f"{result.away_xg:.2f} {html.escape(result.away_team)}\n\n"
            f"Home win: <b>{result.home_win:.1%}</b>\n"
            f"Draw: <b>{result.draw:.1%}</b>\n"
            f"Away win: <b>{result.away_win:.1%}</b>\n"
            f"Both teams score: <b>{result.btts:.1%}</b>\n"
            f"Over 2.5 goals: <b>{result.over_2_5:.1%}</b>\n\n"
            f"Top scores: {html.escape(top_scores)}\n"
            f"<i>{result.simulations:,} odds-informed simulations · {html.escape(result.source)}</i>"
        )

    def _format_parlay_sim(self, args: list[str]) -> str:
        try:
            index = _parse_index(
                args,
                len(self._parlays),
                "Build slips with /parlays first, then use /simparlay <slip #>.",
            )
        except ValueError as exc:
            return html.escape(str(exc))
        parlay = self._parlays[index]
        pack = self.board()
        result = simulate_parlay(
            parlay,
            all_event_legs=pack["sportsbook_legs"],
            simulations=8_000,
        )
        lines = [
            f"<b>Slip {index + 1} simulation · {html.escape(parlay.sportsbook)}</b>",
            f"Hit rate: <b>{result['slip_hit_rate']:.1%}</b>",
            f"Fair decimal odds: {result.get('fair_decimal_odds') or '—'}",
            f"Estimated book decimal: {result['estimated_decimal_odds']}",
            f"EV on ${result['stake']:.0f}: <b>${result['expected_value']:+.2f}</b>",
            "",
            "<b>Per-leg simulation</b>",
        ]
        for leg in result["legs"]:
            lines.append(f"• {html.escape(leg['pick'])}: {leg['hit_rate']:.1%}")
        if result.get("most_common_losing_leg"):
            lines.extend(
                [
                    "",
                    f"Most common first miss: {html.escape(result['most_common_losing_leg'])}",
                ]
            )
        lines.append(f"\n<i>{result['simulations']:,} joint simulations</i>")
        return "\n".join(lines)

    def run_forever(self) -> None:
        self.api.prepare_polling()
        offset: int | None = None
        logger.info("Telegram bot polling started; %d chats allowed", len(self.allowed_chat_ids))
        while True:
            try:
                for update in self.api.get_updates(offset, self.poll_timeout):
                    offset = int(update["update_id"]) + 1
                    self.handle_update(update)
            except KeyboardInterrupt:
                logger.info("Telegram bot stopped")
                return
            except requests.RequestException:
                logger.exception("Telegram polling network failure; retrying")
                time.sleep(5)
            except Exception:
                logger.exception("Telegram polling failure; retrying")
                time.sleep(3)


def _split_message(message: str) -> list[str]:
    if len(message) <= TELEGRAM_MESSAGE_LIMIT:
        return [message]
    parts: list[str] = []
    remaining = message
    while len(remaining) > TELEGRAM_MESSAGE_LIMIT:
        split_at = remaining.rfind("\n", 0, TELEGRAM_MESSAGE_LIMIT)
        if split_at < TELEGRAM_MESSAGE_LIMIT // 2:
            split_at = TELEGRAM_MESSAGE_LIMIT
        parts.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        parts.append(remaining)
    return parts


def _bounded_count(args: list[str], default: int) -> int:
    try:
        value = int(args[0]) if args else default
    except ValueError:
        value = default
    return max(1, min(value, 20))


def _parse_index(args: list[str], length: int, usage: str) -> int:
    if not args or not args[0].isdigit():
        raise ValueError(usage)
    index = int(args[0]) - 1
    if index < 0 or index >= length:
        raise ValueError(usage)
    return index


def _odds(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def _decimal_to_american(decimal: float) -> str:
    if decimal >= 2:
        return _odds(round((decimal - 1) * 100))
    return str(round(-100 / (decimal - 1)))


def main() -> None:
    TelegramBot.from_env().run_forever()


if __name__ == "__main__":
    main()
