#!/usr/bin/env python3
"""
Relay Server for Remote Control
Run this on a server with public IP (VPS)

Usage:
    pip install flask flask-socketio eventlet
    python relay_server.py
"""

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Sessions storage
sessions = {}


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on('register')
def handle_register(data):
    """Host or controller registers"""
    session_type = data.get('type')  # 'host' or 'controller'
    session_id = data.get('session_id')
    
    if session_type == 'host':
        sessions[session_id] = {
            'host_sid': request.sid,
            'controller_sid': None
        }
        join_room(session_id)
        print(f"Host registered: {session_id}")
        emit('registered', {'type': 'host'}, room=request.sid)
    
    elif session_type == 'controller':
        if session_id in sessions:
            sessions[session_id]['controller_sid'] = request.sid
            join_room(session_id)
            print(f"Controller connected to: {session_id}")
            emit('connected', room=session_id)
        else:
            emit('error', {'message': 'Session not found'}, room=request.sid)


@socketio.on('screen_data')
def handle_screen(data):
    """Forward screen data from host to controller"""
    session_id = data.get('session_id')
    if session_id in sessions:
        controller = sessions[session_id].get('controller_sid')
        if controller:
            emit('screen', data.get('data'), room=controller)


@socketio.on('input_event')
def handle_input(data):
    """Forward input from controller to host"""
    session_id = data.get('session_id')
    if session_id in sessions:
        host = sessions[session_id].get('host_sid')
        if host:
            emit('input_event', data.get('event'), room=host)


@socketio.on('disconnect')
def handle_disconnect():
    # Clean up sessions
    for session_id, session in sessions.items():
        if session.get('host_sid') == request.sid:
            print(f"Host disconnected: {session_id}")
            if session.get('controller_sid'):
                emit('host_disconnected', room=session['controller_sid'])
            del sessions[session_id]
        elif session.get('controller_sid') == request.sid:
            print(f"Controller disconnected: {session_id}")
            if session.get('host_sid'):
                emit('controller_disconnected', room=session['host_sid'])
            session['controller_sid'] = None


from flask import request

if __name__ == '__main__':
    print("=" * 50)
    print("Remote Control Relay Server")
    print("=" * 50)
    print("Start this on a server with public IP")
    print("Then configure hosts to connect to:")
    print("  RELAY_URL = 'wss://your-server.com'")
    print("  SESSION_ID = 'your-session-id'")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=8081, debug=True)
