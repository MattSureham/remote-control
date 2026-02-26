#!/usr/bin/env python3
"""
Remote Control Host Server
Runs on the computer you want to control
"""

import os
import io
import base64
import threading
import time
import json
from flask import Flask, render_template_string, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from mss import mss
from PIL import Image
import pynput
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# Configuration
HOST = "0.0.0.0"
PORT = 8080
PASSWORD = "admin123"  # Change this!
SCREEN_QUALITY = 50  # JPEG quality 1-100
SCREEN_INTERVAL = 0.05  # Screen capture interval (seconds)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'remote-control-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Controllers
mouse = MouseController()
keyboard = KeyboardController()

# Screen capture
sct = mss()
monitor = sct.monitors[1]  # Primary monitor

# State
authenticated = False
screen_thread = None
running = True


def capture_screen():
    """Capture screen and send to client"""
    global running
    
    while running:
        if authenticated:
            try:
                # Capture screen
                img = sct.grab(monitor)
                
                # Convert to PIL Image
                pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                
                # Resize for performance
                width, height = pil_img.size
                new_width = int(width * 0.8)
                new_height = int(height * 0.8)
                pil_img = pil_img.resize((new_width, new_height))
                
                # Convert to JPEG
                buffer = io.BytesIO()
                pil_img.save(buffer, format='JPEG', quality=SCREEN_QUALITY)
                img_str = base64.b64encode(buffer.getvalue()).decode()
                
                # Send via WebSocket
                socketio.emit('screen', {'image': img_str})
                
            except Exception as e:
                print(f"Capture error: {e}")
        
        time.sleep(SCREEN_INTERVAL)


def mouse_move(x, y):
    """Move mouse to position"""
    try:
        # Scale coordinates based on screen size
        width = monitor['width']
        height = monitor['height']
        
        # Get current screen size from capture
        with mss() as sct_temp:
            img = sct_temp.grab(monitor)
            cap_width = img.width
            cap_height = img.height
        
        # Scale coordinates
        scale_x = cap_width / width
        scale_y = cap_height / height
        
        mouse.position = (x * scale_x, y * scale_y)
        return True
    except Exception as e:
        print(f"Mouse move error: {e}")
        return False


def mouse_click(button='left', action='click'):
    """Click mouse button"""
    try:
        btn = Button.left if button == 'left' else Button.right
        
        if action == 'press':
            mouse.press(btn)
        elif action == 'release':
            mouse.release(btn)
        else:  # click
            mouse.click(btn)
        return True
    except Exception as e:
        print(f"Mouse click error: {e}")
        return False


def mouse_scroll(direction='down'):
    """Scroll mouse"""
    try:
        delta = 100 if direction == 'down' else -100
        mouse.scroll(0, delta)
        return True
    except Exception as e:
        print(f"Scroll error: {e}")
        return False


def keyboard_type(text):
    """Type text"""
    try:
        keyboard.type(text)
        return True
    except Exception as e:
        print(f"Keyboard type error: {e}")
        return False


def keyboard_press(key):
    """Press special key"""
    try:
        # Handle special keys
        key_map = {
            'enter': Key.enter,
            'space': Key.space,
            'backspace': Key.backspace,
            'tab': Key.tab,
            'esc': Key.esc,
            'ctrl': Key.ctrl_l,
            'alt': Key.alt_l,
            'shift': Key.shift_l,
        }
        
        if key.lower() in key_map:
            keyboard.press(key_map[key.lower()])
            keyboard.release(key_map[key.lower()])
        else:
            keyboard.press(key)
            keyboard.release(key)
        return True
    except Exception as e:
        print(f"Keyboard press error: {e}")
        return False


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Remote Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a; 
            color: #fff;
            overflow: hidden;
            height: 100vh;
        }
        
        #login-screen {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        
        .login-box {
            background: rgba(255,255,255,0.95);
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            color: #333;
        }
        
        .login-box h1 { margin-bottom: 20px; }
        
        .login-box input {
            width: 200px;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        
        .login-box button {
            width: 200px;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        
        #main-screen {
            display: none;
            height: 100vh;
            flex-direction: column;
        }
        
        #toolbar {
            background: #2a2a2a;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            border-bottom: 1px solid #444;
        }
        
        #toolbar button {
            padding: 8px 16px;
            background: #444;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }
        
        #toolbar button:hover { background: #555; }
        
        #toolbar button.active { background: #667eea; }
        
        #status { color: #888; font-size: 14px; }
        
        #screen-container {
            flex: 1;
            position: relative;
            overflow: hidden;
            cursor: crosshair;
        }
        
        #screen {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        #info {
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <!-- Login Screen -->
    <div id="login-screen">
        <div class="login-box">
            <h1>🔐 Remote Control</h1>
            <input type="password" id="password" placeholder="Enter Password">
            <button onclick="login()">Connect</button>
            <p id="login-error" style="color: red; margin-top: 10px; display: none;">Wrong password</p>
        </div>
    </div>
    
    <!-- Main Screen -->
    <div id="main-screen">
        <div id="toolbar">
            <span id="status">Connecting...</span>
            <button onclick="toggleFullscreen()">⛶ Fullscreen</button>
            <button onclick="requestScreenshot()">📷 Screenshot</button>
            <button id="clipboard-btn" onclick="clipboardMode()">📋 Clipboard</button>
        </div>
        <div id="screen-container">
            <img id="screen" alt="Screen">
            <div id="info"></div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        const socket = io();
        let mouseX = 0, mouseY = 0;
        let clipboardMode = false;
        
        // Login
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
        
        // Screen updates
        socket.on('screen', function(data) {
            document.getElementById('screen').src = 'data:image/jpeg;base64,' + data.image;
            document.getElementById('info').textContent = new Date().toLocaleTimeString();
        });
        
        // Mouse events
        const screen = document.getElementById('screen');
        
        screen.addEventListener('mousemove', function(e) {
            const rect = screen.getBoundingClientRect();
            mouseX = e.clientX - rect.left;
            mouseY = e.clientY - rect.top;
            
            if (!clipboardMode) {
                socket.emit('mouse_move', {x: mouseX, y: mouseY});
            }
        });
        
        screen.addEventListener('click', function(e) {
            if (clipboardMode) {
                // Read clipboard
                navigator.clipboard.readText().then(text => {
                    socket.emit('keyboard_type', {text: text});
                });
            } else {
                socket.emit('mouse_click', {button: 'left'});
            }
        });
        
        screen.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            if (!clipboardMode) {
                socket.emit('mouse_click', {button: 'right'});
            }
        });
        
        screen.addEventListener('wheel', function(e) {
            e.preventDefault();
            socket.emit('mouse_scroll', {direction: e.deltaY > 0 ? 'down' : 'up'});
        });
        
        // Keyboard events
        document.addEventListener('keydown', function(e) {
            if (document.getElementById('login-screen').style.display !== 'none') return;
            
            if (e.ctrlKey && e.key === 'v' && clipboardMode) {
                navigator.clipboard.readText().then(text => {
                    socket.emit('keyboard_type', {text: text});
                });
            } else if (e.key.length === 1) {
                socket.emit('keyboard_type', {text: e.key});
            } else {
                socket.emit('keyboard_press', {key: e.key});
            }
        });
        
        // Functions
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        }
        
        function requestScreenshot() {
            socket.emit('request_screenshot');
        }
        
        function clipboardMode() {
            clipboardMode = !clipboardMode;
            document.getElementById('clipboard-btn').classList.toggle('active', clipboardMode);
            if (clipboardMode) {
                alert('Clipboard mode ON: Click to paste, Ctrl+V to paste');
            }
        }
        
        // Connection
        socket.on('connect', function() {
            document.getElementById('status').textContent = 'Connecting...';
        });
        
        socket.on('disconnect', function() {
            document.getElementById('status').textContent = 'Disconnected';
        });
    </script>
</body>
</html>
'''


# Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


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


@socketio.on('request_screenshot')
def handle_screenshot():
    if authenticated:
        # Capture and send immediately
        img = sct.grab(monitor)
        pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        buffer = io.BytesIO()
        pil_img.save(buffer, format='JPEG', quality=90)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        emit('screen', {'image': img_str})


def main():
    global screen_thread, running
    
    # Start screen capture thread
    screen_thread = threading.Thread(target=capture_screen, daemon=True)
    screen_thread.start()
    
    print(f"Remote Control Host starting on http://{HOST}:{PORT}")
    print(f"Password: {PASSWORD}")
    print("Press Ctrl+C to stop")
    
    try:
        socketio.run(app, host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False


if __name__ == '__main__':
    main()
