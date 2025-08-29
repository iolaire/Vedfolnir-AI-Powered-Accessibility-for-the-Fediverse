#!/usr/bin/env python3
"""
WebSocket Session Fix

Enables proper session handling for WebSocket connections by:
1. Allowing WebSocket connections to access Flask session data
2. Configuring SocketIO to use session cookies
3. Enabling authentication for admin WebSocket connections
"""

import os

def fix_websocket_session_handling():
    """Fix WebSocket session handling configuration"""
    
    # Update environment to enable session handling
    env_updates = {
        'SOCKETIO_REQUIRE_AUTH': 'true',
        'SOCKETIO_SESSION_VALIDATION': 'true',
        'SOCKETIO_CORS_CREDENTIALS': 'true',
        'SOCKETIO_WITH_CREDENTIALS': 'true'
    }
    
    # Read current .env
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    # Update lines
    updated_lines = []
    updated_keys = set()
    
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            if key in env_updates:
                updated_lines.append(f"{key}={env_updates[key]}\n")
                updated_keys.add(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Add missing keys
    for key, value in env_updates.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back
    with open('.env', 'w') as f:
        f.writelines(updated_lines)
    
    print("✅ Updated WebSocket session configuration")

if __name__ == '__main__':
    fix_websocket_session_handling()
