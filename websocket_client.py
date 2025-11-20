"""WebSocket client for connecting to the real-time updates server."""
import socketio
import logging
from typing import Callable, Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketClient:
    """Client for connecting to the Hourly Picks WebSocket server."""
    
    def __init__(self, server_url: str = 'http://localhost:5000'):
        """
        Initialize WebSocket client.
        
        Args:
            server_url: URL of the WebSocket server
        """
        self.server_url = server_url
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.connected = False
        self.callbacks = {}
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register default event handlers."""
        
        @self.sio.event
        def connect():
            logger.info("Connected to WebSocket server")
            self.connected = True
            if 'on_connect' in self.callbacks:
                self.callbacks['on_connect']()
        
        @self.sio.event
        def disconnect():
            logger.info("Disconnected from WebSocket server")
            self.connected = False
            if 'on_disconnect' in self.callbacks:
                self.callbacks['on_disconnect']()
        
        @self.sio.on('connected')
        def on_connected(data):
            logger.info(f"Server confirmed connection: {data.get('message')}")
        
        @self.sio.on('new_picks')
        def on_new_picks(data):
            picks = data.get('picks', [])
            logger.info(f"Received {len(picks)} new picks")
            if 'on_new_picks' in self.callbacks:
                self.callbacks['on_new_picks'](picks)
        
        @self.sio.on('new_parlays')
        def on_new_parlays(data):
            parlays = data.get('parlays_by_sport', {})
            logger.info(f"Received parlays for {len(parlays)} sports")
            if 'on_new_parlays' in self.callbacks:
                self.callbacks['on_new_parlays'](parlays)
        
        @self.sio.on('odds_update')
        def on_odds_update(data):
            logger.debug(f"Odds update for game {data.get('game_id')}")
            if 'on_odds_update' in self.callbacks:
                self.callbacks['on_odds_update'](data)
        
        @self.sio.on('line_movement')
        def on_line_movement(data):
            logger.info("Line movement detected")
            if 'on_line_movement' in self.callbacks:
                self.callbacks['on_line_movement'](data)
        
        @self.sio.on('game_status')
        def on_game_status(data):
            logger.debug(f"Game status update: {data.get('status')}")
            if 'on_game_status' in self.callbacks:
                self.callbacks['on_game_status'](data)
        
        @self.sio.on('performance_update')
        def on_performance_update(data):
            logger.info("Performance update received")
            if 'on_performance_update' in self.callbacks:
                self.callbacks['on_performance_update'](data)
        
        @self.sio.on('pick_result')
        def on_pick_result(data):
            logger.info(f"Pick result: {data.get('result')}")
            if 'on_pick_result' in self.callbacks:
                self.callbacks['on_pick_result'](data)
        
        @self.sio.on('system_message')
        def on_system_message(data):
            message = data.get('message', '')
            level = data.get('level', 'info')
            logger.info(f"System message [{level}]: {message}")
            if 'on_system_message' in self.callbacks:
                self.callbacks['on_system_message'](data)
        
        @self.sio.on('stats_update')
        def on_stats_update(data):
            if 'on_stats_update' in self.callbacks:
                self.callbacks['on_stats_update'](data)
        
        @self.sio.on('status')
        def on_status(data):
            if 'on_status' in self.callbacks:
                self.callbacks['on_status'](data)
    
    def connect(self):
        """Connect to the WebSocket server."""
        try:
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.connected:
            self.sio.disconnect()
    
    def subscribe(self, events: List[str]):
        """Subscribe to specific event types."""
        if self.connected:
            self.sio.emit('subscribe', {'events': events})
    
    def unsubscribe(self, events: List[str]):
        """Unsubscribe from specific event types."""
        if self.connected:
            self.sio.emit('unsubscribe', {'events': events})
    
    def on(self, event: str, callback: Callable):
        """Register callback for a specific event."""
        self.callbacks[event] = callback
    
    def wait(self):
        """Wait for events (blocks until disconnect)."""
        self.sio.wait()


# Example usage
if __name__ == '__main__':
    # Create client
    client = WebSocketClient('http://localhost:5000')
    
    # Define callbacks
    def on_new_picks(picks):
        print(f"\n🎯 NEW PICKS RECEIVED: {len(picks)} picks")
        for pick in picks[:3]:  # Show first 3
            print(f"  - {pick.get('selection', 'N/A')} ({pick.get('bet_type', 'unknown')})")
    
    def on_new_parlays(parlays_by_sport):
        print(f"\n🎲 NEW PARLAYS RECEIVED:")
        for sport, parlays in parlays_by_sport.items():
            print(f"  {sport}: {len(parlays)} parlay(s)")
    
    def on_line_movement(data):
        movement = data.get('movement', {})
        print(f"\n📊 LINE MOVEMENT:")
        print(f"  {movement.get('description', 'N/A')}")
    
    def on_system_message(data):
        print(f"\n💬 SYSTEM: {data.get('message')}")
    
    # Register callbacks
    client.on('on_new_picks', on_new_picks)
    client.on('on_new_parlays', on_new_parlays)
    client.on('on_line_movement', on_line_movement)
    client.on('on_system_message', on_system_message)
    
    # Connect and wait
    if client.connect():
        print("Connected! Waiting for updates...")
        client.wait()
    else:
        print("Failed to connect. Is the server running?")

