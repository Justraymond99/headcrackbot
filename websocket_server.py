"""WebSocket server for real-time updates on picks, odds, and game status."""
import logging
from flask import Flask, request
from flask_socketio import SocketIO, emit
from datetime import datetime
from typing import Dict, List, Optional
import json
import threading
import time
from models import Game, PlayerProp, SessionLocal
from config import DATABASE_URL

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hourly-picks-websocket-secret-key-change-in-production'
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Allow all origins for development
    async_mode='threading',
    logger=True,
    engineio_logger=True
)

# Store connected clients
connected_clients = set()

@app.route('/')
def index():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Hourly Picks WebSocket Server",
        "connected_clients": len(connected_clients),
        "timestamp": datetime.utcnow().isoformat()
    }

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    client_id = request.sid
    connected_clients.add(client_id)
    logger.info(f"Client connected: {client_id} (Total: {len(connected_clients)})")
    
    # Send welcome message
    emit('connected', {
        'message': 'Connected to Hourly Picks WebSocket Server',
        'client_id': client_id,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Send current status
    send_current_status(client_id)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    client_id = request.sid
    connected_clients.discard(client_id)
    logger.info(f"Client disconnected: {client_id} (Total: {len(connected_clients)})")

@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle client subscription to specific events."""
    client_id = request.sid
    event_types = data.get('events', [])
    logger.info(f"Client {client_id} subscribed to: {event_types}")
    
    emit('subscribed', {
        'events': event_types,
        'message': f'Subscribed to {len(event_types)} event types'
    })

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Handle client unsubscription."""
    client_id = request.sid
    event_types = data.get('events', [])
    logger.info(f"Client {client_id} unsubscribed from: {event_types}")
    
    emit('unsubscribed', {
        'events': event_types,
        'message': f'Unsubscribed from {len(event_types)} event types'
    })

def send_current_status(client_id: str):
    """Send current system status to a client."""
    try:
        session = SessionLocal()
        
        # Get current games
        games = session.query(Game).filter(
            Game.status == "scheduled"
        ).limit(10).all()
        
        game_count = session.query(Game).filter(
            Game.status == "scheduled"
        ).count()
        
        session.close()
        
        socketio.emit('status', {
            'games_scheduled': game_count,
            'recent_games': len(games),
            'server_time': datetime.utcnow().isoformat()
        }, room=client_id)
        
    except Exception as e:
        logger.error(f"Error sending status: {e}")

# Event broadcasting functions
def broadcast_new_picks(picks: List[Dict]):
    """Broadcast new picks to all connected clients."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('new_picks', {
            'picks': picks,
            'count': len(picks),
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"Broadcasted {len(picks)} new picks to {len(connected_clients)} clients")
    except Exception as e:
        logger.error(f"Error broadcasting picks: {e}")

def broadcast_new_parlays(parlays_by_sport: Dict[str, List[Dict]]):
    """Broadcast new parlay picks."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('new_parlays', {
            'parlays_by_sport': parlays_by_sport,
            'sports': list(parlays_by_sport.keys()),
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"Broadcasted parlays for {len(parlays_by_sport)} sports to {len(connected_clients)} clients")
    except Exception as e:
        logger.error(f"Error broadcasting parlays: {e}")

def broadcast_odds_update(game_id: int, odds_data: Dict):
    """Broadcast odds update for a specific game."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('odds_update', {
            'game_id': game_id,
            'odds': odds_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.debug(f"Broadcasted odds update for game {game_id}")
    except Exception as e:
        logger.error(f"Error broadcasting odds update: {e}")

def broadcast_line_movement(movement: Dict):
    """Broadcast line movement alert."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('line_movement', {
            'movement': movement,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"Broadcasted line movement to {len(connected_clients)} clients")
    except Exception as e:
        logger.error(f"Error broadcasting line movement: {e}")

def broadcast_game_status_update(game_id: int, status: str, score: Optional[Dict] = None):
    """Broadcast game status change."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('game_status', {
            'game_id': game_id,
            'status': status,
            'score': score,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.debug(f"Broadcasted game status update for game {game_id}: {status}")
    except Exception as e:
        logger.error(f"Error broadcasting game status: {e}")

def broadcast_performance_update(performance_data: Dict):
    """Broadcast performance summary update."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('performance_update', {
            'performance': performance_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"Broadcasted performance update to {len(connected_clients)} clients")
    except Exception as e:
        logger.error(f"Error broadcasting performance: {e}")

def broadcast_pick_result(pick_id: int, result: str, payout: Optional[float] = None):
    """Broadcast pick result (win/loss)."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('pick_result', {
            'pick_id': pick_id,
            'result': result,
            'payout': payout,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"Broadcasted pick result: {pick_id} - {result}")
    except Exception as e:
        logger.error(f"Error broadcasting pick result: {e}")

def broadcast_system_message(message: str, level: str = 'info'):
    """Broadcast system message to all clients."""
    if not connected_clients:
        return
    
    try:
        socketio.emit('system_message', {
            'message': message,
            'level': level,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"Broadcasted system message: {message}")
    except Exception as e:
        logger.error(f"Error broadcasting system message: {e}")

# Background thread for periodic updates
def broadcast_periodic_updates():
    """Periodically broadcast system status updates."""
    while True:
        try:
            time.sleep(60)  # Update every minute
            
            if connected_clients:
                # Broadcast current stats
                session = SessionLocal()
                scheduled_count = session.query(Game).filter(
                    Game.status == "scheduled"
                ).count()
                live_count = session.query(Game).filter(
                    Game.status == "live"
                ).count()
                session.close()
                
                socketio.emit('stats_update', {
                    'scheduled_games': scheduled_count,
                    'live_games': live_count,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")
            time.sleep(60)

# Start background thread
update_thread = threading.Thread(target=broadcast_periodic_updates, daemon=True)
update_thread.start()

def start_websocket_server(host='0.0.0.0', port=5000, debug=False):
    """Start the WebSocket server."""
    logger.info(f"Starting WebSocket server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    # Run the WebSocket server
    start_websocket_server(port=5000, debug=True)

