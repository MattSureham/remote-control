# Remote Control Tool

Personal remote desktop control tool - control any computer from another.

## Overview

```
┌──────────────────┐      WebSocket       ┌──────────────────┐
│  Controller      │◄─────────────────────►│  Host Server     │
│  (Browser)      │      localhost/        │  (Target PC)     │
│                 │      LAN IP            │                  │
└──────────────────┘                       └──────────────────┘
        │                                         │
        ▼                                         ▼
   View screen                               Screen capture
   Mouse control          ──────▶            Mouse simulation
   Keyboard                              Keyboard simulation
   File transfer                          File transfer
```

## Components

- **Host**: Runs on the computer you want to control
- **Controller**: Web-based interface to control the host

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Host (on target computer)

```bash
cd host
python server.py
```

The host will start on `http://0.0.0.0:8080`

### 3. Access Controller

Open your browser and go to:
- Local: `http://localhost:8080`
- LAN: `http://<host-ip>:8080`

### 4. Control

- Move mouse, click, type
- View screen in real-time
- Transfer files

## Features

- 🎥 Screen streaming (MJPEG)
- 🖱️ Mouse control (move, click, scroll)
- ⌨️ Keyboard input
- 📁 File transfer
- 🔒 Simple password protection

## Security

- Password-protected access
- Local/LAN only by default
- No cloud - fully self-hosted

## License

MIT
