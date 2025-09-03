// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Database Session Cross-Tab Synchronization
 * 
 * This module provides cross-tab session synchronization using database sessions
 * as the single source of truth. It replaces Flask session synchronization.
 */

class DatabaseSessionSync {
    constructor() {
        this.tabId = this.generateTabId();
        this.syncInterval = 30000; // 30 seconds
        this.heartbeatInterval = 60000; // 1 minute
        this.lastSyncTime = null;
        this.lastHeartbeatTime = null;
        this.isOnline = navigator.onLine;
        this.currentSessionState = null;
        
        // Bind methods
        this.handleStorageEvent = this.handleStorageEvent.bind(this);
        this.handleOnlineStatusChange = this.handleOnlineStatusChange.bind(this);
        this.handleBeforeUnload = this.handleBeforeUnload.bind(this);
        
        this.setupEventListeners();
        this.startSyncTimer();
        this.startHeartbeatTimer();
        
        console.log(`[SessionSync] Initialized for tab ${this.tabId}`);
    }
    
    generateTabId() {
        return 'tab_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    setupEventListeners() {
        // Listen for storage events (cross-tab communication)
        window.addEventListener('storage', this.handleStorageEvent);
        
        // Listen for online/offline status changes
        window.addEventListener('online', this.handleOnlineStatusChange);
        window.addEventListener('offline', this.handleOnlineStatusChange);
        
        // Listen for tab close/refresh
        window.addEventListener('beforeunload', this.handleBeforeUnload);
        
        // Listen for visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                // Tab became visible, sync immediately
                this.syncSessionState();
            }
        });
    }
    
    async syncSessionState() {
        if (!this.isOnline) {
            console.log('[SessionSync] Offline, skipping sync');
            return;
        }
        
        try {
            const response = await fetch('/api/session/state', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                if (response.status === 302) {
                    // Handle redirect (likely authentication required)
                    console.log('[SessionSync] Authentication required, session may be expired');
                    this.handleSessionExpiration();
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.handleSessionStateUpdate(data);
                this.lastSyncTime = Date.now();
            } else {
                console.error('[SessionSync] Session state API error:', data.error || 'Unknown error');
            }
            
        } catch (error) {
            console.error('[SessionSync] Failed to sync session state:', error);
            
            if (error.message.includes('401') || error.message.includes('403')) {
                this.handleSessionExpiration();
            }
        }
    }
    
    handleSessionStateUpdate(sessionData) {
        const previousState = this.currentSessionState;
        this.currentSessionState = sessionData;
        
        // Store session state in localStorage for cross-tab sync
        const syncData = {
            tabId: this.tabId,
            timestamp: Date.now(),
            sessionState: sessionData,
            eventType: 'session_update'
        };
        
        try {
            localStorage.setItem('vedfolnir_session_sync', JSON.stringify(syncData));
        } catch (error) {
            console.warn('[SessionSync] Failed to store sync data:', error);
        }
        
        // Check for significant changes
        if (previousState) {
            this.checkForSessionChanges(previousState, sessionData);
        }
        
        // Update UI if needed
        this.updateSessionUI(sessionData);
    }
    
    checkForSessionChanges(previousState, currentState) {
        // Check for authentication changes
        if (previousState.authenticated !== currentState.authenticated) {
            if (!currentState.authenticated) {
                this.handleSessionExpiration();
                return;
            }
        }
        
        // Check for platform changes
        const prevPlatform = previousState.platform;
        const currPlatform = currentState.platform;
        
        if (prevPlatform && currPlatform && prevPlatform.id !== currPlatform.id) {
            this.handlePlatformSwitch(currPlatform);
        }
        
        // Check for user changes (shouldn't happen but good to check)
        const prevUser = previousState.user;
        const currUser = currentState.user;
        
        if (prevUser && currUser && prevUser.id !== currUser.id) {
            console.warn('[SessionSync] User changed, reloading page');
            window.location.reload();
        }
    }
    
    handlePlatformSwitch(newPlatform) {
        console.log(`[SessionSync] Platform switched to: ${newPlatform.name}`);
        
        // Update platform UI elements
        this.updatePlatformUI(newPlatform);
        
        // Dispatch custom event for other components
        this.dispatchSessionEvent('platform_switch', {
            platform: newPlatform,
            tabId: this.tabId
        });
        
        // Show notification
        this.showNotification(`Switched to ${newPlatform.name}`, 'info');
    }
    
    handleSessionExpiration() {
        console.log('[SessionSync] Session expired, redirecting to login');
        
        // Clear local session data
        this.clearLocalSessionData();
        
        // Show notification
        this.showNotification('Your session has expired. Please log in again.', 'warning');
        
        // Redirect to login after a short delay
        setTimeout(() => {
            const currentUrl = window.location.pathname + window.location.search;
            const loginUrl = `/login${currentUrl !== '/login' ? '?next=' + encodeURIComponent(currentUrl) : ''}`;
            window.location.href = loginUrl;
        }, 2000);
    }
    
    handleStorageEvent(event) {
        if (event.key !== 'vedfolnir_session_sync') {
            return;
        }
        
        try {
            const syncData = JSON.parse(event.newValue);
            
            // Ignore events from this tab
            if (syncData.tabId === this.tabId) {
                return;
            }
            
            console.log(`[SessionSync] Received sync event from tab ${syncData.tabId}:`, syncData.eventType);
            
            // Handle different event types
            switch (syncData.eventType) {
                case 'session_update':
                    this.handleRemoteSessionUpdate(syncData.sessionState);
                    break;
                case 'logout':
                    this.handleRemoteLogout();
                    break;
                case 'platform_switch':
                    this.handleRemotePlatformSwitch(syncData.platform);
                    break;
            }
            
        } catch (error) {
            console.error('[SessionSync] Failed to parse storage event:', error);
        }
    }
    
    handleRemoteSessionUpdate(sessionState) {
        // Update current state without triggering another sync
        this.currentSessionState = sessionState;
        this.updateSessionUI(sessionState);
    }
    
    handleRemoteLogout() {
        console.log('[SessionSync] Remote logout detected');
        this.clearLocalSessionData();
        window.location.href = '/login';
    }
    
    handleRemotePlatformSwitch(platform) {
        console.log(`[SessionSync] Remote platform switch to: ${platform.name}`);
        this.updatePlatformUI(platform);
        this.showNotification(`Platform switched to ${platform.name}`, 'info');
    }
    
    updateSessionUI(sessionData) {
        // Update user info in UI
        if (sessionData.authenticated && sessionData.user) {
            this.updateUserUI(sessionData.user);
        }
        
        // Update platform info in UI
        if (sessionData.platform) {
            this.updatePlatformUI(sessionData.platform);
        }
    }
    
    updateUserUI(user) {
        // Update user name displays
        const userElements = document.querySelectorAll('[data-user-name]');
        userElements.forEach(el => {
            el.textContent = user.username;
        });
        
        // Update user email displays
        const emailElements = document.querySelectorAll('[data-user-email]');
        emailElements.forEach(el => {
            el.textContent = user.email;
        });
    }
    
    updatePlatformUI(platform) {
        // Update platform name displays
        const platformElements = document.querySelectorAll('[data-platform-name]');
        platformElements.forEach(el => {
            el.textContent = platform.name;
        });
        
        // Update platform type displays
        const typeElements = document.querySelectorAll('[data-platform-type]');
        typeElements.forEach(el => {
            el.textContent = platform.platform_type;
        });
        
        // Update platform selection dropdowns
        const selectElements = document.querySelectorAll('select[name="platform_id"]');
        selectElements.forEach(select => {
            select.value = platform.id;
        });
        
        // Update active platform indicators
        const indicators = document.querySelectorAll('[data-platform-id]');
        indicators.forEach(indicator => {
            const isActive = indicator.dataset.platformId == platform.id;
            indicator.classList.toggle('active', isActive);
            indicator.classList.toggle('selected', isActive);
        });
    }
    
    async sendHeartbeat() {
        if (!this.isOnline) {
            return;
        }
        
        try {
            const response = await fetch('/api/session/heartbeat', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.active) {
                    this.lastHeartbeatTime = Date.now();
                } else if (!data.active) {
                    this.handleSessionExpiration();
                }
            }
            
        } catch (error) {
            console.error('[SessionSync] Heartbeat failed:', error);
        }
    }
    
    notifyLogout() {
        const syncData = {
            tabId: this.tabId,
            timestamp: Date.now(),
            eventType: 'logout'
        };
        
        try {
            localStorage.setItem('vedfolnir_session_sync', JSON.stringify(syncData));
        } catch (error) {
            console.warn('[SessionSync] Failed to notify logout:', error);
        }
    }
    
    notifyPlatformSwitch(platform) {
        const syncData = {
            tabId: this.tabId,
            timestamp: Date.now(),
            eventType: 'platform_switch',
            platform: platform
        };
        
        try {
            localStorage.setItem('vedfolnir_session_sync', JSON.stringify(syncData));
        } catch (error) {
            console.warn('[SessionSync] Failed to notify platform switch:', error);
        }
    }
    
    clearLocalSessionData() {
        try {
            localStorage.removeItem('vedfolnir_session_sync');
        } catch (error) {
            console.warn('[SessionSync] Failed to clear local session data:', error);
        }
        
        this.currentSessionState = null;
    }
    
    showNotification(message, type = 'info') {
        // Create a simple notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px; right: 20px; z-index: 1060;
            min-width: 300px;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        `;
        
        notification.innerHTML = `
            <i class="bi bi-info-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    dispatchSessionEvent(eventType, data) {
        const event = new CustomEvent('sessionSync', {
            detail: {
                type: eventType,
                data: data,
                tabId: this.tabId
            }
        });
        
        window.dispatchEvent(event);
    }
    
    handleOnlineStatusChange() {
        this.isOnline = navigator.onLine;
        console.log(`[SessionSync] Online status: ${this.isOnline}`);
        
        if (this.isOnline) {
            // Sync immediately when coming back online
            this.syncSessionState();
        }
    }
    
    handleBeforeUnload() {
        // Clean up when tab is closing
        console.log(`[SessionSync] Tab ${this.tabId} closing`);
    }
    
    startSyncTimer() {
        setInterval(() => {
            this.syncSessionState();
        }, this.syncInterval);
        
        // Initial sync
        this.syncSessionState();
    }
    
    startHeartbeatTimer() {
        // Heartbeat disabled due to CSRF issues
        // TODO: Fix CSRF exemption for heartbeat endpoint
        console.log('[SessionSync] Heartbeat disabled');
    }
    
    destroy() {
        // Clean up event listeners
        window.removeEventListener('storage', this.handleStorageEvent);
        window.removeEventListener('online', this.handleOnlineStatusChange);
        window.removeEventListener('offline', this.handleOnlineStatusChange);
        window.removeEventListener('beforeunload', this.handleBeforeUnload);
        
        console.log(`[SessionSync] Destroyed for tab ${this.tabId}`);
    }
}

// Initialize session sync when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if user is authenticated
    if (document.body.dataset.authenticated === 'true') {
        window.sessionSync = new DatabaseSessionSync();
        
        // Make it available globally for other scripts
        window.vedfolnir = window.vedfolnir || {};
        window.vedfolnir.sessionSync = window.sessionSync;
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DatabaseSessionSync;
}