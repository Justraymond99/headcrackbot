"""Integration module to connect WebSocket server with existing services."""
import threading
import logging
from typing import Optional
from websocket_server import (
    start_websocket_server,
    broadcast_new_picks,
    broadcast_new_parlays,
    broadcast_odds_update,
    broadcast_line_movement,
    broadcast_game_status_update,
    broadcast_performance_update,
    broadcast_pick_result,
    broadcast_system_message
)

logger = logging.getLogger(__name__)


class WebSocketIntegration:
    """Integrate WebSocket server with existing services."""
    
    def __init__(self, port: int = 5000):
        """
        Initialize WebSocket integration.
        
        Args:
            port: Port to run WebSocket server on
        """
        self.port = port
        self.server_thread = None
        self.running = False
    
    def start_server(self, host: str = '0.0.0.0', port: Optional[int] = None):
        """Start WebSocket server in background thread."""
        if self.running:
            logger.warning("WebSocket server already running")
            return
        
        port = port or self.port
        
        def run_server():
            try:
                start_websocket_server(host=host, port=port, debug=False)
            except Exception as e:
                logger.error(f"WebSocket server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        logger.info(f"WebSocket server started on {host}:{port}")
    
    def stop_server(self):
        """Stop WebSocket server."""
        self.running = False
        # Server will stop when main thread exits (daemon thread)
        logger.info("WebSocket server stopped")


# Global instance
websocket_integration = WebSocketIntegration()


def start_websocket_background(port: int = 5000):
    """Start WebSocket server in background (convenience function)."""
    websocket_integration.start_server(port=port)


def get_websocket_broadcaster():
    """Get broadcaster functions for use in other modules."""
    return {
        'new_picks': broadcast_new_picks,
        'new_parlays': broadcast_new_parlays,
        'odds_update': broadcast_odds_update,
        'line_movement': broadcast_line_movement,
        'game_status': broadcast_game_status_update,
        'performance': broadcast_performance_update,
        'pick_result': broadcast_pick_result,
        'system_message': broadcast_system_message
    }

