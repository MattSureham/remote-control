#!/usr/bin/env python3
"""
Remote Control Host Server - Internet Edition
Supports both LAN and Internet (relay) modes
"""

import os
import io
import base64
import threading
import time
import json
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
from mss import mss
from PIL import Image
import pynput
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# ============= CONFIGURATION =============
# Mode: 'lan' or 'relay'
MODE = os.getenv('MODE', 'lan')  # 'lan' or 'relay'

# LAN mode settings
HOST = "0.0.0.0"
PORT = 8080

# Relay mode settings
RELAY_URL = os.getenv('RELAY_URL', '')  # e.g., 'wss://your-relay-server.com'
SESSION_ID = os.getenv('SESSION_ID', '')  # Unique session ID

# Common settings
PASSWORD = os.getenv('PASSWORD', 'admin123')
SCREEN_QUALITY = int(os.getenv('SCREEN_QUALITY', '30'))
SCREEN_INTERVAL = float(os.getenv('SCREEN_INTERVAL', '0.1'))

# ============= APP SETUP =============
app = Flask(__name__)
app.config['SECRET_KEY'] = 'remote-control-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Controllers
mouse = MouseController()
keyboard = KeyboardController()
sct = mss()
monitor = sct.monitors[1]

# State
authenticated = False
running = True


def capture_screen():
    """Capture screen and send to client"""
    global running
    
    while running:
        if authenticated:
            try:
                img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                
                # Resize for performance
                width, height = pil_img.size
                new_width = int(width * 0.6)
                new_height = int(height * 0.6)
                pil_img = pil_img.resize((new_width, new_height))
                
                # Convert to JPEG
                buffer = io.BytesIO()
                pil_img.save(buffer, format='JPEG', quality=SCREEN_QUALITY)
                img_str = base64.b64encode(buffer.getvalue()).decode()
                
                if MODE == 'lan':
                    socketio.emit('screen', {'image': img_str})
                else:
                    # Send via relay
                    socketio.emit('screen_data', {
                        'session_id': SESSION_ID,
                        'data': {'image': img_str}
                    })
                
            except Exception as e:
                print(f"Capture error: {e}")
        
        time.sleep(SCREEN_INTERVAL)


def mouse_move(x, y):
    try:
        width = monitor['width']
        height = monitor['height']
        
        with mss() as sct_temp:
            img = sct_temp.grab(monitor)
            cap_width = img.width
            cap_height = img.height
        
        scale_x = cap_width / width
        scale_y = cap_height / height
        
        mouse.position = (x * scale_x, y * scale_y)
        return True
    except Exception as e:
        return False


def mouse_click(button='left', action='click'):
    try:
        btn = Button.left if button == 'left' else Button.right
        if action == 'press':
            mouse.press(btn)
        elif action == 'release':
            mouse.release(btn)
        else:
            mouse.click(btn)
        return True
    except:
        return False


def mouse_scroll(direction='down'):
    try:
        delta = 100 if direction == 'down' else -100
        mouse.scroll(0, delta)
        return True
    except:
        return False


def keyboard_type(text):
    try:
        keyboard.type(text)
        return True
    except:
        return False


def keyboard_press(key):
    try:
        key_map = {
            'enter': Key.enter, 'space': Key.space,
            'backspace': Key.backspace, 'tab': Key.tab,
            'esc': Key.esc, 'ctrl': Key.ctrl_l,
            'alt': Key.alt_l, 'shift': Key.shift_l,
        }
        if key.lower() in key_map:
            keyboard.press(key_map[key.lower()])
            keyboard.release(key_map[key.lower()])
        else:
            keyboard.press(key)
            keyboard.release(key)
        return True
    except:
        return False


# HTML Template (same as before)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Remote Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a; color: #fff; overflow: hidden; height: 100vh; }
        
        #login-screen { position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex; align-items: center; justify-content: center; z-index: 1000; }
        
        .login-box { background: rgba(255,255,255,0.95); padding: 40px; border-radius: 20px;
            text-align: center; color: #333; }
        .login-box h1 { margin-bottom: 20px; }
        .login-box input { width: 200px; padding: 12px; margin: 10px 0;
            border: 1px solid #ddd; border-radius: 8px; font-size: 16px; }
        .login-box button { width: 200px; padding: 12px; background: #667eea; color: white;
            border: none; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        
        #main-screen { display: none; height: 100vh; flex-direction: column; }
        #toolbar { background: #2a2a2a; padding: 10px 20px; display: flex;
            align-items: center; gap: 15px; border-bottom: 1px solid #444; }
        #toolbar button { padding: 8px 16px; background: #444; color: white;
            border: none; border-radius: 6px; cursor: pointer; }
        #toolbar button:hover { background: #555; }
        #status { color: #888; font-size: 14px; }
        #screen-container { flex: 1; position: relative; overflow: hidden; cursor: crosshair; }
        #screen { width: 100%; height: 100%; object-fit: contain; }
    </style>
</head>
<body>
    <div id="login-screen">
        <div class="login-box">
            <h1>🔐 Remote Control</h1>
            <input type="password" id="password" placeholder="Enter Password">
            <button onclick="login()">Connect</button>
            <p id="login-error" style="color: red; margin-top: 10px; display: none;">Wrong password</p>
        </div>
    </div>
    
    <div id="main-screen">
        <div id="toolbar">
            <span id="status">Connecting...</span>
            <button onclick="toggleFullscreen()">⛶ Fullscreen</button>
            <span id="session-info" style="margin-left: auto; color: #666; font-size: 12px;"></span>
        </div>
        <div id="screen-container">
            <img id="screen" alt="Screen">
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        const socket = io();
        let clipboardMode = false;
        
        // Mode from server
        const MODE = '{{ mode }}';
        
        function login() {
            const password = document.getElementById('password').value;
            socket.emit('auth', {password: password});
        }
        
        socket.on('auth_result', function(data) {
            if (data.success) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('main-screen').style.display = 'flex';
                document.getElementById('status').textContent = 'Connected ✓';
            } else {
                document.getElementById('login-error').style.display = 'block';
            }
        });
        
        socket.on('screen', function(data) {
            document.getElementById('screen').src = 'data:image/jpeg;base64,' + data.image;
        });
        
        socket.on('screen_update', function(data) {
            document.getElementById('screen').src = 'data:image/jpeg;base64,' + data.image;
        });
        
        const screen = document.getElementById('screen');
        let mouseX = 0, mouseY = 0;
        
        screen.addEventListener('mousemove', function(e) {
            const rect = screen.getBoundingClientRect();
            mouseX = e.clientX - rect.left;
            mouseY = e.clientY - rect.top;
            socket.emit('mouse_move', {x: mouseX, y: mouseY});
        });
        
        screen.addEventListener('click', function(e) {
            if (clipboardMode) {
                navigator.clipboard.readText().then(text => {
                    socket.emit('keyboard_type', {text: text});
                });
            } else {
                socket.emit('mouse_click', {button: 'left'});
            }
        });
        
        screen.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            socket.emit('mouse_click', {button: 'right'});
        });
        
        screen.addEventListener('wheel', function(e) {
            e.preventDefault();
            socket.emit('mouse_scroll', {direction: e.deltaY > 0 ? 'down' : 'up'});
        });
        
        document.addEventListener('keydown', function(e) {
            if (document.getElementById('login-screen').style.display !== 'none') return;
            if (e.key.length === 1) {
                socket.emit('keyboard_type', {text: e.key});
            } else {
                socket.emit('keyboard_press', {key: e.key});
            }
        });
        
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        }
        
        socket.on('connect', function() {
            document.getElementById('status').textContent = 'Connecting...';
            // Register as controller in relay mode
            {{ 'const sessionId = "{{ session_id }}"; if(sessionId) socket.emit("register", {type: "controller", session_id: sessionId});' if mode == 'relay' else '' }}
        });
        
        socket.on('disconnect', function() {
            document.getElementById('status').textContent = 'Disconnected';
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, mode=MODE, session_id=SESSION_ID)


@app.route('/auth', methods=['POST'])
def auth():
    global authenticated
    data = request.json
    if data.get('password') == PASSWORD:
        authenticated = True
        return jsonify({'success': True})
    return jsonify({'success': False})


# WebSocket events
@socketio.on('auth')
def handle_auth(data):
    global authenticated
    if data.get('password') == PASSWORD:
        authenticated = True
        emit('auth_result', {'success': True})
    else:
        emit('auth_result', {'success': False})


@socketio.on('mouse_move')
def handle_mouse_move(data):
    if authenticated:
        mouse_move(data['x'], data['y'])


@socketio.on('mouse_click')
def handle_mouse_click(data):
    if authenticated:
        mouse_click(data.get('button', 'left'))


@socketio.on('mouse_scroll')
def handle_mouse_scroll(data):
    if authenticated:
        mouse_scroll(data.get('direction', 'down'))


@socketio.on('keyboard_type')
def handle_keyboard_type(data):
    if authenticated:
        keyboard_type(data['text'])


@socketio.on('keyboard_press')
def handle_keyboard_press(data):
    if authenticated:
        keyboard_press(data['key'])


# Relay mode events
@socketio.on('register')
def handle_register(data):
    if data.get('type') == 'controller':
        print(f"Controller connected via relay")


@socketio.on('screen_data')
def handle_screen_data(data):
    if authenticated:
        socketio.emit('screen_update', data.get('data'))


def main():
    global running
    
    # Start screen capture
    screen_thread = threading.Thread(target=capture_screen, daemon=True)
    screen_thread.start()
    
    print(f"=" * 50)
    print(f"Remote Control Host - {MODE.upper()} Mode")
    print(f"=" * 50)
    print(f"Password: {PASSWORD}")
    print(f"Quality: {SCREEN_QUALITY}%")
    print(f"Interval: {SCREEN_INTERVAL}s")
    
    if MODE == 'lan':
        print(f"URL: http://localhost:{PORT}")
    else:
        print(f"Relay: {RELAY_URL}")
        print(f"Session ID: {SESSION_ID}")
    
    print("=" * 50)
    
    try:
        socketio.run(app, host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False


if __name__ == '__main__':
    main()
