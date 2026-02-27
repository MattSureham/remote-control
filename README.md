# Remote Control Tool

Personal remote desktop control tool - self-hosted.

## Overview

```
┌──────────────────┐      WebSocket       ┌──────────────────┐
│  Controller      │◄─────────────────────►│  Host Server     │
│  (Browser)       │      (LAN/Internet)  │  (Target PC)     │
└──────────────────┘                       └──────────────────┘
```

## Two Modes

### Mode 1: LAN (Local Network)
For devices on the same WiFi/network.

```bash
# Start host
MODE=lan python host/server.py

# Access from browser
http://<host-ip>:8080
```

### Mode 2: Internet (Relay)
For devices on different networks via relay server.

```
┌──────────┐      Internet      ┌────────────┐      Internet      ┌──────────┐
│  Host    │◄────────────────►│   Relay    │◄────────────────►│Controller│
│ (target) │                  │  (VPS)     │                  │   (you)  │
└──────────┘                  └────────────┘                  └──────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. LAN Mode (Same Network)

```bash
cd host
python server.py
# Open http://localhost:8080
```

### 3. Internet Mode (Different Networks)

#### Step A: Set up Relay Server (on VPS)

```bash
cd relay
pip install flask flask-socketio eventlet
python relay_server.py
```

#### Step B: Configure Host

```bash
# On target computer
MODE=relay \
RELAY_URL=wss://your-vps.com \
SESSION_ID=my-pc-123 \
python host/server.py
```

#### Step C: Access

Open relay URL in browser:
```
https://your-vps.com:8081
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PASSWORD` | Access password | `admin123` |
| `MODE` | `lan` or `relay` | `lan` |
| `PORT` | Server port | `8080` |
| `SCREEN_QUALITY` | JPEG quality 1-100 | `30` |
| `SCREEN_INTERVAL` | Capture interval (sec) | `0.1` |

### Relay Server

```bash
# On your VPS
export RELAY_URL=wss://your-domain.com
python relay_server.py
```

### Host (Internet Mode)

```bash
# On target computer
export MODE=relay
export RELAY_URL=wss://your-relay-server.com
export SESSION_ID=unique-session-id
export PASSWORD=your-password
python host/server.py
```

## Features

- 🎥 Screen streaming (MJPEG)
- 🖱️ Mouse control (move, click, scroll)
- ⌨️ Keyboard input
- 🔐 Password protection
- 📱 Responsive web UI
- 🔄 Real-time updates
- 🌐 LAN + Internet modes

## Project Structure

```
remote-control/
├── README.md
├── requirements.txt
├── host/
│   ├── server.py          # Main server (LAN + Relay)
│   └── requirements.txt
└── relay/
    └── relay_server.py   # Relay server for internet
```

## Security Notes

- Change default password in production
- Use HTTPS/WSS for internet mode
- Password protect your relay server
- Don't expose to untrusted networks

## License

MIT
