# WebSocket Real-Time Updates Guide

## 🚀 Overview

Your system now supports **real-time WebSocket updates** for:
- ✅ New picks as they're generated
- ✅ New parlay suggestions
- ✅ Odds updates
- ✅ Line movements
- ✅ Game status changes
- ✅ Performance updates
- ✅ Pick results

## 📋 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies:
- `flask-socketio` - WebSocket server
- `python-socketio` - WebSocket client
- `eventlet` - Async support

### 2. Enable WebSocket Server

Add to your `.env` file:

```bash
ENABLE_WEBSOCKET=true
WEBSOCKET_PORT=5000
```

### 3. Start the Scheduler

The WebSocket server starts automatically with the scheduler:

```bash
python enhanced_scheduler.py
```

The server will run on `http://localhost:5000` (or your configured port).

## 🔌 Client Connection

### Python Client

```python
from websocket_client import WebSocketClient

# Create client
client = WebSocketClient('http://localhost:5000')

# Define callbacks
def on_new_picks(picks):
    print(f"Received {len(picks)} new picks!")
    for pick in picks:
        print(f"  - {pick['selection']} ({pick['bet_type']})")

# Register callbacks
client.on('on_new_picks', on_new_picks)
client.on('on_new_parlays', on_new_parlays)
client.on('on_line_movement', on_line_movement)

# Connect and wait
client.connect()
client.wait()
```

### JavaScript/HTML Client

Open `websocket_dashboard.html` in your browser, or use Socket.IO:

```javascript
const socket = io('http://localhost:5000');

socket.on('connect', () => {
    console.log('Connected!');
    
    // Subscribe to events
    socket.emit('subscribe', {
        events: ['new_picks', 'new_parlays', 'line_movement']
    });
});

socket.on('new_picks', (data) => {
    console.log('New picks:', data.picks);
});

socket.on('new_parlays', (data) => {
    console.log('New parlays:', data.parlays_by_sport);
});
```

## 📡 Available Events

### 1. `new_picks`
Emitted when new hourly picks are generated.

```json
{
    "picks": [...],
    "count": 5,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 2. `new_parlays`
Emitted when new parlay suggestions are generated.

```json
{
    "parlays_by_sport": {
        "NBA": [...],
        "NFL": [...]
    },
    "sports": ["NBA", "NFL"],
    "timestamp": "2024-01-01T12:30:00Z"
}
```

### 3. `odds_update`
Emitted when odds are updated for a game.

```json
{
    "game_id": 123,
    "odds": {...},
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 4. `line_movement`
Emitted when favorable line movements are detected.

```json
{
    "movement": {
        "description": "...",
        "old_odds": -110,
        "new_odds": -105
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 5. `game_status`
Emitted when game status changes (scheduled → live → finished).

```json
{
    "game_id": 123,
    "status": "live",
    "score": {...},
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 6. `performance_update`
Emitted when performance summaries are generated.

```json
{
    "performance": {
        "win_rate": 0.65,
        "roi": 0.15,
        ...
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 7. `pick_result`
Emitted when a pick result is determined (win/loss).

```json
{
    "pick_id": 456,
    "result": "win",
    "payout": 50.00,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 8. `system_message`
Emitted for system notifications.

```json
{
    "message": "Hourly picks sent successfully",
    "level": "success",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 9. `stats_update`
Emitted periodically (every minute) with current stats.

```json
{
    "scheduled_games": 25,
    "live_games": 3,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🎯 Dashboard

Open `websocket_dashboard.html` in your browser for a real-time dashboard showing:
- Connection status
- Latest picks
- Latest parlays
- Line movements
- System messages
- Statistics

## 🔧 Configuration

### Environment Variables

```bash
# Enable WebSocket server
ENABLE_WEBSOCKET=true

# WebSocket port
WEBSOCKET_PORT=5000

# CORS origins (comma-separated)
WEBSOCKET_CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Running Standalone

You can also run the WebSocket server standalone:

```bash
python websocket_server.py
```

## 📱 Integration Examples

### React Component

```javascript
import { useEffect, useState } from 'react';
import io from 'socket.io-client';

function PicksDashboard() {
    const [picks, setPicks] = useState([]);
    
    useEffect(() => {
        const socket = io('http://localhost:5000');
        
        socket.on('new_picks', (data) => {
            setPicks(data.picks);
        });
        
        return () => socket.close();
    }, []);
    
    return (
        <div>
            {picks.map(pick => (
                <div key={pick.id}>
                    {pick.selection} - {pick.bet_type}
                </div>
            ))}
        </div>
    );
}
```

### Mobile App (React Native)

```javascript
import io from 'socket.io-client';

const socket = io('http://your-server:5000');

socket.on('new_picks', (data) => {
    // Show notification
    // Update UI
});
```

## 🚨 Troubleshooting

### Connection Failed
- Check if server is running
- Verify port is not blocked
- Check firewall settings

### No Updates Received
- Verify you subscribed to events
- Check server logs
- Verify events are being emitted

### CORS Errors
- Configure `WEBSOCKET_CORS_ORIGINS`
- Or set to `*` for development

## 📊 Deployment

### Railway/Render

The WebSocket server runs alongside the scheduler. Just enable it:

```bash
ENABLE_WEBSOCKET=true
WEBSOCKET_PORT=5000
```

### Separate Server

You can run WebSocket server separately:

```bash
# Terminal 1: Main scheduler
python enhanced_scheduler.py

# Terminal 2: WebSocket server (if not auto-started)
python websocket_server.py
```

## 🎉 Benefits

- ✅ **Real-time updates** - No polling needed
- ✅ **Live dashboard** - See picks as they're generated
- ✅ **Efficient** - Only sends updates when needed
- ✅ **Scalable** - Supports multiple clients
- ✅ **Easy integration** - Simple client API

Your system now has real-time capabilities! 🚀

