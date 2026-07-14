from datetime import datetime, timezone

from headcrack_ai.models import AmericanOdds, BetLeg, Market, MarketType, Prediction, Sport
from headcrack_ai.services import SourceStatus
from headcrack_ai.telegram_bot import TELEGRAM_MESSAGE_LIMIT, TelegramBot, _split_message


class FakeApi:
    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


class FakeService:
    def __init__(self, pack):
        self.pack = pack
        self.refreshes = 0

    def refresh_all_sources(self, include_player_props=True):
        self.refreshes += 1
        return self.pack


def _leg(index: int, *, player: str | None = None) -> BetLeg:
    market_type = MarketType.PLAYER_SHOTS if player else MarketType.MONEYLINE
    market = Market(
        market_id=f"m{index}",
        sport=Sport.SOCCER,
        event_id="france-spain",
        label=f"{player} over 1.5 shots" if player else "France to win",
        market_type=market_type,
        sportsbook="fanduel",
        odds=AmericanOdds(120 + index),
        team="France",
        opponent="Spain",
        player=player,
        threshold=1.5 if player else None,
        starts_at=datetime.now(timezone.utc),
        metadata={
            "home_team": "France",
            "away_team": "Spain",
            "league": "World Cup",
            "outcome_name": "Over" if player else "France",
        },
    )
    return BetLeg(
        market=market,
        prediction=Prediction(
            market_id=market.market_id,
            model_probability=0.58,
            model_name="test_model",
        ),
    )


def _bot():
    legs = [_leg(1), _leg(2, player="Kylian Mbappe"), _leg(3, player="Ousmane Dembele")]
    pack = {
        "sportsbook_legs": legs,
        "prediction_legs": [],
        "match_results": [],
        "leagues": ["World Cup"],
        "sources": [SourceStatus("Sportsbooks", "live", "3 lines", 3)],
    }
    api = FakeApi()
    return TelegramBot(FakeService(pack), api, frozenset({"123"})), api


def test_bot_lists_games_props_and_status():
    bot, _ = _bot()
    assert "1 matches" in bot.handle_command("/status")
    assert "France vs Spain" in bot.handle_command("/games")
    props = bot.handle_command("/props 1")
    assert "Top player props" in props
    assert props.count("<b>1.") == 1


def test_bot_rejects_unknown_chat_and_accepts_allowlisted_chat():
    bot, api = _bot()
    bot.handle_update({"message": {"chat": {"id": 999}, "text": "/status"}})
    assert api.sent == []
    bot.handle_update({"message": {"chat": {"id": 123}, "text": "/help"}})
    assert api.sent and api.sent[0][0] == "123"


def test_simulation_usage_is_actionable():
    bot, _ = _bot()
    assert "Use /games" in bot.handle_command("/simulate")
    assert "Build slips" in bot.handle_command("/simparlay 1")


def test_message_split_respects_telegram_limit():
    message = ("line of text\n" * 600).strip()
    parts = _split_message(message)
    assert len(parts) > 1
    assert all(len(part) <= TELEGRAM_MESSAGE_LIMIT for part in parts)
