// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Debug Helper for Vedfolnir
 * Provides debugging utilities for WebSocket connections
 */

window.WebSocketDebug = {
    
    /**
     * Check WebSocket environment and configuration
     */
    checkEnvironment: function() {
        console.log('=== WebSocket Environment Check ===');
        
        // Check Socket.IO availability
        if (typeof io !== 'undefined') {
            console.log('✅ Socket.IO library loaded');
            console.log('   Version:', io.version || 'Unknown');
        } else {
            console.error('❌ Socket.IO library not loaded');
            return false;
        }
        
        // Check VedfolnirWS instance
        if (window.VedfolnirWS) {
            console.log('✅ VedfolnirWS instance available');
            console.log('   Connected:', window.VedfolnirWS.isConnected());
            console.log('   Reconnect attempts:', window.VedfolnirWS.reconnectAttempts);
        } else {
            console.error('❌ VedfolnirWS instance not available');
            return false;
        }
        
        // Check page context
        console.log('📍 Page context:');
        console.log('   Path:', window.location.pathname);
        console.log('   Is admin page:', window.location.pathname.startsWith('/admin'));
        
        // Check authentication indicators
        const userElements = document.querySelectorAll('[data-user-id], .user-authenticated, .admin-authenticated');
        const logoutLinks = document.querySelectorAll('a[href*="logout"]');
        console.log('🔐 Authentication indicators:');
        console.log('   User elements found:', userElements.length);
        console.log('   Logout links found:', logoutLinks.length);
        
        // Check WebSocket status element
        const statusElement = document.getElementById('websocket-status');
        if (statusElement) {
            console.log('✅ WebSocket status element found');
            console.log('   Current content:', statusElement.innerHTML);
        } else {
            console.warn('⚠️ WebSocket status element not found');
        }
        
        return true;
    },
    
    /**
     * Test WebSocket connection manually
     */
    testConnection: function() {
        console.log('=== Manual WebSocket Connection Test ===');
        
        if (!window.VedfolnirWS) {
            console.error('❌ VedfolnirWS not available');
            return;
        }
        
        // Disconnect if already connected
        if (window.VedfolnirWS.isConnected()) {
            console.log('🔌 Disconnecting existing connection...');
            window.VedfolnirWS.disconnect();
        }
        
        // Add event listeners for debugging
        window.VedfolnirWS.on('connect', function() {
            console.log('✅ WebSocket connected successfully');
        });
        
        window.VedfolnirWS.on('disconnect', function(reason) {
            console.log('❌ WebSocket disconnected:', reason);
        });
        
        window.VedfolnirWS.on('error', function(error) {
            console.error('❌ WebSocket error:', error);
        });
        
        window.VedfolnirWS.on('auth_required', function(error) {
            console.warn('🔐 Authentication required:', error);
        });
        
        // Attempt connection
        console.log('🔌 Attempting to connect...');
        window.VedfolnirWS.connect();
    },
    
    /**
     * Test Socket.IO endpoint directly
     */
    testEndpoint: function() {
        console.log('=== Socket.IO Endpoint Test ===');
        
        const baseUrl = window.location.origin;
        const testUrl = baseUrl + '/socket.io/?EIO=4&transport=polling';
        
        console.log('🌐 Testing endpoint:', testUrl);
        
        fetch(testUrl, {
            method: 'GET',
            credentials: 'include' // Include cookies for authentication
        })
        .then(response => {
            console.log('📡 Response status:', response.status);
            console.log('📡 Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (response.ok) {
                return response.text();
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        })
        .then(data => {
            console.log('✅ Endpoint accessible');
            console.log('📄 Response data (first 200 chars):', data.substring(0, 200));
        })
        .catch(error => {
            console.error('❌ Endpoint test failed:', error);
        });
    },
    
    /**
     * Show current WebSocket status
     */
    showStatus: function() {
        console.log('=== WebSocket Status ===');
        
        if (!window.VedfolnirWS) {
            console.error('❌ VedfolnirWS not available');
            return;
        }
        
        const ws = window.VedfolnirWS;
        
        console.log('🔌 Connection status:', ws.isConnected());
        console.log('🔄 Reconnect attempts:', ws.reconnectAttempts);
        console.log('⏱️ Reconnect delay:', ws.reconnectDelay);
        console.log('🎯 Max reconnect attempts:', ws.maxReconnectAttempts);
        
        if (ws.socket) {
            console.log('📡 Socket.IO status:');
            console.log('   Connected:', ws.socket.connected);
            console.log('   ID:', ws.socket.id);
            console.log('   Transport:', ws.socket.io.engine.transport.name);
        } else {
            console.log('❌ No Socket.IO instance');
        }
    },
    
    /**
     * Run all diagnostic tests
     */
    runDiagnostics: function() {
        console.log('🔍 Running WebSocket diagnostics...');
        console.log('');
        
        this.checkEnvironment();
        console.log('');
        
        this.showStatus();
        console.log('');
        
        this.testEndpoint();
        console.log('');
        
        console.log('💡 To test connection manually, run: WebSocketDebug.testConnection()');
        console.log('💡 To force reconnect, run: window.VedfolnirWS.connect()');
    }
};

// Auto-run diagnostics on admin pages if in debug mode
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're in debug mode (look for debug indicators)
    const isDebugMode = window.location.search.includes('debug=1') || 
                       localStorage.getItem('websocket_debug') === 'true' ||
                       console.debug !== undefined;
    
    if (window.location.pathname.startsWith('/admin') && isDebugMode) {
        setTimeout(() => {
            console.log('🔍 WebSocket Debug Mode Active');
            console.log('💡 Run WebSocketDebug.runDiagnostics() for full diagnostics');
            console.log('💡 Run WebSocketDebug.testConnection() to test connection');
        }, 3000);
    }
});

// Make debug functions available globally
window.wsDebug = window.WebSocketDebug;