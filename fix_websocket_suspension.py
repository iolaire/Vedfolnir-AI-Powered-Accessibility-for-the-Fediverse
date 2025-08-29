# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix WebSocket Suspension Issues

This script fixes the WebSocket "closed due to suspension" error by correcting
timeout values and implementing proper keep-alive mechanisms.
"""

import os
import sys
from dotenv import load_dotenv

def fix_websocket_timeouts():
    """Fix WebSocket timeout configuration in .env file"""
    
    print("🔧 Fixing WebSocket suspension issues...")
    
    # Load current environment
    load_dotenv()
    
    # Read current .env file
    env_path = '.env'
    if not os.path.exists(env_path):
        print("❌ .env file not found")
        return False
    
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Fix timeout values (convert from milliseconds to seconds)
    fixes_applied = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Fix ping timeout (should be in seconds for SocketIO server config)
        if line.startswith('SOCKETIO_PING_TIMEOUT=60000'):
            lines[i] = 'SOCKETIO_PING_TIMEOUT=60\n'
            fixes_applied.append('SOCKETIO_PING_TIMEOUT: 60000ms → 60s')
        
        # Fix ping interval (should be in seconds for SocketIO server config)
        elif line.startswith('SOCKETIO_PING_INTERVAL=25000'):
            lines[i] = 'SOCKETIO_PING_INTERVAL=25\n'
            fixes_applied.append('SOCKETIO_PING_INTERVAL: 25000ms → 25s')
        
        # Fix client timeout (keep in milliseconds but reduce for better responsiveness)
        elif line.startswith('SOCKETIO_TIMEOUT=30000'):
            lines[i] = 'SOCKETIO_TIMEOUT=20000\n'
            fixes_applied.append('SOCKETIO_TIMEOUT: 30000ms → 20000ms')
        
        # Add keep-alive settings if missing
        elif line.startswith('# Client Configuration (development-optimized)'):
            # Check if keep-alive settings exist
            keep_alive_exists = any('SOCKETIO_FORCE_NEW' in l for l in lines)
            if not keep_alive_exists:
                # Insert keep-alive settings after this comment
                insert_lines = [
                    'SOCKETIO_FORCE_NEW=false\n',
                    'SOCKETIO_UPGRADE=true\n',
                    'SOCKETIO_REMEMBER_UPGRADE=true\n',
                    'SOCKETIO_WITH_CREDENTIALS=true\n',
                    '\n'
                ]
                lines[i+1:i+1] = insert_lines
                fixes_applied.append('Added keep-alive settings')
    
    # Write back the fixed .env file
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    if fixes_applied:
        print("✅ Applied fixes:")
        for fix in fixes_applied:
            print(f"   • {fix}")
        return True
    else:
        print("ℹ️  No fixes needed - timeouts already correct")
        return False

def create_websocket_keepalive_script():
    """Create a client-side keep-alive script for admin pages"""
    
    script_content = '''// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Keep-Alive Manager
 * 
 * Prevents WebSocket suspension by implementing proper keep-alive mechanisms
 * and handling browser suspension events.
 */

class WebSocketKeepAlive {
    constructor(socket) {
        this.socket = socket;
        this.keepAliveInterval = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isPageVisible = true;
        
        this.setupKeepAlive();
        this.setupVisibilityHandling();
        this.setupReconnectionLogic();
    }
    
    setupKeepAlive() {
        // Send ping every 20 seconds to prevent suspension
        this.keepAliveInterval = setInterval(() => {
            if (this.socket && this.socket.connected && this.isPageVisible) {
                this.socket.emit('ping', { timestamp: Date.now() });
                console.log('🏓 WebSocket keep-alive ping sent');
            }
        }, 20000);
        
        // Handle pong responses
        this.socket.on('pong', (data) => {
            console.log('🏓 WebSocket keep-alive pong received');
            this.reconnectAttempts = 0; // Reset reconnect attempts on successful ping
        });
    }
    
    setupVisibilityHandling() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.isPageVisible = !document.hidden;
            
            if (this.isPageVisible) {
                console.log('📱 Page became visible - resuming WebSocket');
                this.resumeConnection();
            } else {
                console.log('📱 Page became hidden - WebSocket may be suspended by browser');
            }
        });
        
        // Handle page focus/blur
        window.addEventListener('focus', () => {
            this.isPageVisible = true;
            this.resumeConnection();
        });
        
        window.addEventListener('blur', () => {
            // Don't immediately mark as invisible on blur
            // Browser may still keep connection active
        });
    }
    
    setupReconnectionLogic() {
        this.socket.on('disconnect', (reason) => {
            console.log(`🔌 WebSocket disconnected: ${reason}`);
            
            if (reason === 'transport close' || reason === 'transport error') {
                console.log('🔄 Attempting to reconnect due to transport issue...');
                this.attemptReconnection();
            }
        });
        
        this.socket.on('connect', () => {
            console.log('✅ WebSocket reconnected successfully');
            this.reconnectAttempts = 0;
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('❌ WebSocket connection error:', error);
            this.attemptReconnection();
        });
    }
    
    resumeConnection() {
        if (!this.socket.connected && this.reconnectAttempts < this.maxReconnectAttempts) {
            console.log('🔄 Resuming WebSocket connection...');
            this.socket.connect();
        }
    }
    
    attemptReconnection() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
        
        console.log(`🔄 Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.socket.connected) {
                this.socket.connect();
            }
        }, delay);
    }
    
    destroy() {
        if (this.keepAliveInterval) {
            clearInterval(this.keepAliveInterval);
            this.keepAliveInterval = null;
        }
    }
}

// Auto-initialize for any existing Socket.IO connections
if (typeof io !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        // Wait for Socket.IO to be available
        setTimeout(() => {
            if (window.socket && window.socket.connected) {
                window.webSocketKeepAlive = new WebSocketKeepAlive(window.socket);
                console.log('🚀 WebSocket keep-alive initialized');
            }
        }, 1000);
    });
}

// Export for manual initialization
window.WebSocketKeepAlive = WebSocketKeepAlive;
'''
    
    # Create static/js directory if it doesn't exist
    os.makedirs('static/js', exist_ok=True)
    
    # Write the keep-alive script
    with open('static/js/websocket-keepalive.js', 'w') as f:
        f.write(script_content)
    
    print("✅ Created WebSocket keep-alive script: static/js/websocket-keepalive.js")

def update_admin_templates():
    """Update admin templates to include the keep-alive script"""
    
    # Find admin template files
    admin_template_dirs = ['admin/templates', 'templates']
    templates_updated = []
    
    for template_dir in admin_template_dirs:
        if not os.path.exists(template_dir):
            continue
            
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html') and ('admin' in file.lower() or 'dashboard' in file.lower()):
                    template_path = os.path.join(root, file)
                    
                    # Read template content
                    with open(template_path, 'r') as f:
                        content = f.read()
                    
                    # Check if keep-alive script is already included
                    if 'websocket-keepalive.js' in content:
                        continue
                    
                    # Add keep-alive script before closing </body> tag
                    if '</body>' in content:
                        keepalive_script = '''    <!-- WebSocket Keep-Alive Script -->
    <script src="{{ url_for('static', filename='js/websocket-keepalive.js') }}"></script>
</body>'''
                        content = content.replace('</body>', keepalive_script)
                        
                        # Write back the updated template
                        with open(template_path, 'w') as f:
                            f.write(content)
                        
                        templates_updated.append(template_path)
    
    if templates_updated:
        print("✅ Updated admin templates with keep-alive script:")
        for template in templates_updated:
            print(f"   • {template}")
    else:
        print("ℹ️  No admin templates found or already updated")

def main():
    """Main function to fix WebSocket suspension issues"""
    
    print("🔧 WebSocket Suspension Fix Tool")
    print("=" * 50)
    
    # Step 1: Fix timeout configuration
    print("\n1. Fixing WebSocket timeout configuration...")
    timeout_fixed = fix_websocket_timeouts()
    
    # Step 2: Create keep-alive script
    print("\n2. Creating WebSocket keep-alive script...")
    create_websocket_keepalive_script()
    
    # Step 3: Update admin templates
    print("\n3. Updating admin templates...")
    update_admin_templates()
    
    print("\n" + "=" * 50)
    print("🎉 WebSocket suspension fix complete!")
    
    if timeout_fixed:
        print("\n⚠️  IMPORTANT: Restart the web application to apply timeout fixes:")
        print("   1. Stop the current web app (Ctrl+C)")
        print("   2. Start it again: python web_app.py")
    
    print("\n📋 What was fixed:")
    print("   • Corrected ping timeout and interval values")
    print("   • Added client-side keep-alive mechanism")
    print("   • Implemented browser suspension handling")
    print("   • Added automatic reconnection logic")
    
    print("\n🔍 If issues persist, check:")
    print("   • Browser developer console for WebSocket errors")
    print("   • Server logs for connection issues")
    print("   • Network connectivity and firewall settings")

if __name__ == '__main__':
    main()