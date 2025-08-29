// Copyright (C) 2025 iolaire mcfadden.
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
