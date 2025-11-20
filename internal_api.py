"""Internal REST API for dashboard."""
from flask import Flask, jsonify, request
from typing import Dict, List
from models import Game, Parlay, Leg, SessionLocal
from research_engine import ResearchEngine
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/api/games', methods=['GET'])
def get_games():
    """Get games API endpoint."""
    session = SessionLocal()
    try:
        sport = request.args.get('sport')
        status = request.args.get('status', 'scheduled')
        
        query = session.query(Game).filter_by(status=status)
        if sport:
            query = query.filter_by(sport=sport)
        
        games = query.all()
        
        return jsonify([{
            "id": g.id,
            "sport": g.sport,
            "home_team": g.home_team,
            "away_team": g.away_team,
            "fighter1": g.fighter1,
            "fighter2": g.fighter2,
            "game_date": g.game_date.isoformat(),
            "home_moneyline": g.home_moneyline,
            "away_moneyline": g.away_moneyline
        } for g in games])
    finally:
        session.close()


@app.route('/api/parlays', methods=['GET'])
def get_parlays():
    """Get parlays API endpoint."""
    session = SessionLocal()
    try:
        status = request.args.get('status')
        
        query = session.query(Parlay)
        if status:
            query = query.filter_by(status=status)
        
        parlays = query.all()
        
        return jsonify([{
            "id": p.id,
            "name": p.name,
            "sport": p.sport,
            "odds": p.combined_odds,
            "stake": p.stake,
            "payout": p.payout,
            "result": p.result,
            "confidence": p.confidence_rating
        } for p in parlays])
    finally:
        session.close()


@app.route('/api/generate-parlays', methods=['POST'])
def generate_parlays_api():
    """Generate parlays API endpoint."""
    session = SessionLocal()
    try:
        data = request.json
        sports = data.get('sports', ['NBA', 'NFL'])
        max_parlays = data.get('max_parlays', 10)
        
        engine = ResearchEngine()
        games = session.query(Game).filter(
            Game.sport.in_(sports),
            Game.status == "scheduled"
        ).all()
        
        parlays = engine.generate_parlays(games, max_parlays)
        
        return jsonify([{
            "num_legs": p['num_legs'],
            "odds": p['combined_odds'],
            "ev": p['expected_value'],
            "confidence": p['confidence_rating']
        } for p in parlays])
    finally:
        session.close()


def run_api(host='127.0.0.1', port=5000, debug=False):
    """Run the API server."""
    app.run(host=host, port=port, debug=debug)

