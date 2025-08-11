// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Session Synchronization Module
 * Handles cross-tab session state synchronization and platform context management
 */

class SessionSync {
    constructor() {
        this.storageKey = 'vedfolnir_session_state';
        this.lastSyncTime = Date.now();
        this.syncInterval = 30000; // 30 seconds - reduced frequency for better performance
        this.validationInterval = 60000; // 1 minute - periodic session validation
        this.isInitialized = false;
        this.isOnline = navigator.onLine;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.tabId = this.generateTabId();
        
        // Performance optimization flags
        this.syncInProgress = false;
        this.lastSessionState = null;
        this.debounceTimer = null;
        this.performanceMetrics = {
            syncCount: 0,
            syncErrors: 0,
            avgSyncTime: 0,
            lastSyncDuration: 0
        };
        
        // Bind methods to preserve context
        this.handleStorageChange = this.handleStorageChange.bind(this);
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
        this.handleOnlineChange = this.handleOnlineChange.bind(this);
        this.syncSessionState = this.syncSessionState.bind(this);
        this.validateSession = this.validateSession.bind(this);
    }
    
    /**
     * Initialize session synchronization
     */
    init() {
        if (this.isInitialized) {
            return;
        }
        
        console.log(`Initializing session synchronization for tab ${this.tabId}`);
        
        // Check if we should initialize session sync (only on authenticated pages)
        if (!this.shouldInitializeSync()) {
            console.log('Skipping session sync initialization - not on authenticated page');
            return;
        }
        
        // Listen for storage changes from other tabs
        window.addEventListener('storage', this.handleStorageChange);
        
        // Listen for visibility changes to sync when tab becomes active
        document.addEventListener('visibilitychange', this.handleVisibilityChange);
        
        // Listen for online/offline changes
        window.addEventListener('online', this.handleOnlineChange);
        window.addEventListener('offline', this.handleOnlineChange);
        
        // Periodic sync to catch any missed updates
        this.syncTimer = setInterval(this.syncSessionState, this.syncInterval);
        
        // Periodic session validation
        this.validationTimer = setInterval(this.validateSession, this.validationInterval);
        
        // Initial sync (with a small delay to let the page load)
        setTimeout(() => {
            this.syncSessionState();
        }, 1000);
        
        this.isInitialized = true;
    }
    
    /**
     * Clean up event listeners and timers
     */
    destroy() {
        if (!this.isInitialized) {
            return;
        }
        
        console.log(`Destroying session sync for tab ${this.tabId}`);
        
        window.removeEventListener('storage', this.handleStorageChange);
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        window.removeEventListener('online', this.handleOnlineChange);
        window.removeEventListener('offline', this.handleOnlineChange);
        
        if (this.syncTimer) {
            clearInterval(this.syncTimer);
        }
        
        if (this.validationTimer) {
            clearInterval(this.validationTimer);
        }
        
        this.isInitialized = false;
    }
    
    /**
     * Handle storage changes from other tabs
     */
    handleStorageChange(event) {
        if (event.key === this.storageKey && event.newValue) {
            try {
                const sessionState = JSON.parse(event.newValue);
                
                // Don't apply changes from our own tab
                if (sessionState.tabId === this.tabId) {
                    return;
                }
                
                console.log(`Received session state update from tab ${sessionState.tabId}`);
                this.applySessionState(sessionState);
            } catch (error) {
                console.error('Error parsing session state from storage:', error);
            }
        } else if (event.key === 'vedfolnir_platform_switch' && event.newValue) {
            try {
                const switchEvent = JSON.parse(event.newValue);
                
                // Don't handle our own platform switch events
                if (switchEvent.tabId === this.tabId) {
                    return;
                }
                
                console.log(`Received platform switch from tab ${switchEvent.tabId}: ${switchEvent.platformName}`);
                this.handlePlatformSwitchEvent(switchEvent);
            } catch (error) {
                console.error('Error parsing platform switch event:', error);
            }
        } else if (event.key === 'vedfolnir_session_expired' && event.newValue) {
            // Handle session expiration broadcast from other tabs
            console.log('Received session expiration notification from another tab');
            this.handleSessionExpired();
        } else if (event.key === 'vedfolnir_logout' && event.newValue) {
            // Handle logout broadcast from other tabs
            console.log('Received logout notification from another tab');
            this.handleLogoutEvent();
        }
    }
    
    /**
     * Handle visibility changes (tab focus/blur)
     */
    handleVisibilityChange() {
        if (!document.hidden) {
            // Tab became visible, sync session state
            console.log(`Tab ${this.tabId} became visible, syncing session state`);
            this.syncSessionState();
        }
    }
    
    /**
     * Handle online/offline changes
     */
    handleOnlineChange() {
        const wasOnline = this.isOnline;
        this.isOnline = navigator.onLine;
        
        if (!wasOnline && this.isOnline) {
            // Just came back online, sync immediately
            console.log(`Tab ${this.tabId} came back online, syncing session state`);
            this.syncSessionState();
        } else if (!this.isOnline) {
            console.log(`Tab ${this.tabId} went offline`);
            
            // Use global error handler if available, otherwise fallback to local method
            if (window.errorHandler) {
                window.errorHandler.showNotification('You are currently offline. Some features may not work.', 'warning', 0);
            } else {
                this.showNotification('You are currently offline. Some features may not work.', 'warning');
            }
        }
    }
    
    /**
     * Sync session state across tabs with performance optimizations
     */
    async syncSessionState() {
        if (!this.isOnline) {
            console.log('Skipping session sync - offline');
            return;
        }
        
        // Skip sync if we're on login page or other public pages
        if (window.location.pathname === '/login' || 
            window.location.pathname === '/register' ||
            window.location.pathname === '/') {
            console.log('Skipping session sync - on public page');
            return;
        }
        
        // Prevent concurrent sync operations
        if (this.syncInProgress) {
            console.log('Sync already in progress, skipping');
            return;
        }
        
        this.syncInProgress = true;
        const syncStartTime = performance.now();
        
        try {
            // Get current session state from server
            const response = await fetch('/api/session_state', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                // Check if response is actually JSON
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error(`Expected JSON response, got ${contentType}`);
                }
                
                const sessionState = await response.json();
                
                // Check if state actually changed to avoid unnecessary updates
                if (this.hasSessionStateChanged(sessionState)) {
                    // Update local storage to notify other tabs
                    localStorage.setItem(this.storageKey, JSON.stringify({
                        ...sessionState,
                        timestamp: Date.now(),
                        tabId: this.tabId
                    }));
                    
                    // Apply state to current tab
                    this.applySessionState(sessionState);
                    
                    // Store last state for comparison
                    this.lastSessionState = sessionState;
                    
                    console.log(`Session state synced successfully for tab ${this.tabId}`);
                } else {
                    console.log('Session state unchanged, skipping update');
                }
                
                this.lastSyncTime = Date.now();
                this.retryCount = 0; // Reset retry count on success
                
                // Update performance metrics
                this.updatePerformanceMetrics(syncStartTime, true);
                
            } else if (response.status === 401) {
                // Session expired, redirect to login
                this.handleSessionExpired();
            } else if (response.status === 302) {
                // Redirect response (likely to login page)
                console.log('Received redirect response, user may not be authenticated');
                this.handleSessionExpired();
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error(`Error syncing session state for tab ${this.tabId}:`, error);
            this.updatePerformanceMetrics(syncStartTime, false);
            this.handleSyncError(error);
        } finally {
            this.syncInProgress = false;
        }
    }
    
    /**
     * Validate session with server periodically
     */
    async validateSession() {
        if (!this.isOnline) {
            return;
        }
        
        // Skip validation if we're on login page or other public pages
        if (window.location.pathname === '/login' || 
            window.location.pathname === '/register' ||
            window.location.pathname === '/') {
            return;
        }
        
        try {
            const response = await fetch('/api/session_state', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (response.status === 401) {
                this.handleSessionExpired();
            } else if (response.status === 302) {
                // Redirect response (likely to login page)
                this.handleSessionExpired();
            } else if (!response.ok) {
                console.warn(`Session validation failed: ${response.status}`);
            }
        } catch (error) {
            console.error('Error validating session:', error);
        }
    }
    
    /**
     * Handle sync errors with retry logic
     */
    handleSyncError(error) {
        this.retryCount++;
        
        // Use global error handler if available
        if (window.errorHandler) {
            window.errorHandler.handleAsyncError(error, 'session sync');
        }
        
        if (this.retryCount <= this.maxRetries) {
            const retryDelay = Math.min(1000 * Math.pow(2, this.retryCount - 1), 10000);
            console.log(`Retrying session sync in ${retryDelay}ms (attempt ${this.retryCount}/${this.maxRetries})`);
            
            setTimeout(() => {
                this.syncSessionState();
            }, retryDelay);
        } else {
            console.error('Max retry attempts reached for session sync');
            
            if (window.errorHandler) {
                window.errorHandler.showNotification('Unable to sync session state. Please refresh the page.', 'danger');
            } else {
                this.showNotification('Unable to sync session state. Please refresh the page.', 'danger');
            }
            
            this.retryCount = 0; // Reset for next sync cycle
        }
    }
    
    /**
     * Apply session state to current tab
     */
    applySessionState(sessionState) {
        // Update platform context in UI
        this.updatePlatformContext(sessionState.platform);
        
        // Update user context
        this.updateUserContext(sessionState.user);
        
        // Update page-specific elements based on platform availability
        this.updatePageElements(sessionState.platform);
        
        // Emit custom event for other components to listen to
        window.dispatchEvent(new CustomEvent('sessionStateChanged', {
            detail: sessionState
        }));
    }
    
    /**
     * Update page-specific elements based on platform context
     */
    updatePageElements(platform) {
        // Show/hide platform-required features
        const platformRequiredElements = document.querySelectorAll('.platform-required');
        platformRequiredElements.forEach(element => {
            if (platform) {
                element.classList.remove('d-none');
                element.style.display = '';
            } else {
                element.classList.add('d-none');
                element.style.display = 'none';
            }
        });
        
        // Update platform-specific messages
        const platformMessages = document.querySelectorAll('[data-platform-message]');
        platformMessages.forEach(element => {
            const messageType = element.getAttribute('data-platform-message');
            if (messageType === 'no-platform' && !platform) {
                element.style.display = 'block';
            } else if (messageType === 'has-platform' && platform) {
                element.style.display = 'block';
            } else {
                element.style.display = 'none';
            }
        });
    }
    
    /**
     * Update platform context in UI
     */
    updatePlatformContext(platform) {
        if (!platform) {
            // Handle case where no platform is available
            this.clearPlatformContext();
            return;
        }
        
        // Update platform dropdown text
        const platformDropdown = document.getElementById('platformsDropdown');
        if (platformDropdown) {
            // Update the dropdown text to show current platform
            const dropdownText = platformDropdown.textContent;
            if (dropdownText.includes(':')) {
                platformDropdown.textContent = `Platforms: ${platform.name}`;
            }
        }
        
        // Update current platform display elements
        const currentPlatformElements = document.querySelectorAll('[data-current-platform]');
        currentPlatformElements.forEach(element => {
            element.textContent = platform.name;
            element.setAttribute('data-platform-id', platform.id);
            element.setAttribute('data-platform-type', platform.type);
        });
        
        // Update platform-specific navigation items
        const captionGenerationLink = document.querySelector('a[href*="caption_generation"]');
        if (captionGenerationLink) {
            captionGenerationLink.style.display = platform ? 'block' : 'none';
        }
        
        // Update any platform-dependent content
        const platformDependentElements = document.querySelectorAll('[data-requires-platform]');
        platformDependentElements.forEach(element => {
            element.style.display = platform ? 'block' : 'none';
        });
    }
    
    /**
     * Clear platform context from UI
     */
    clearPlatformContext() {
        // Update platform dropdown
        const platformDropdown = document.getElementById('platformsDropdown');
        if (platformDropdown) {
            platformDropdown.textContent = 'Platforms';
        }
        
        // Clear current platform display
        const currentPlatformElements = document.querySelectorAll('[data-current-platform]');
        currentPlatformElements.forEach(element => {
            element.textContent = 'No Platform';
            element.removeAttribute('data-platform-id');
            element.removeAttribute('data-platform-type');
        });
        
        // Hide platform-dependent content
        const platformDependentElements = document.querySelectorAll('[data-requires-platform]');
        platformDependentElements.forEach(element => {
            element.style.display = 'none';
        });
    }
    
    /**
     * Update user context in UI
     */
    updateUserContext(user) {
        if (!user) {
            return;
        }
        
        // Update user display elements
        const userElements = document.querySelectorAll('[data-user-info]');
        userElements.forEach(element => {
            const infoType = element.getAttribute('data-user-info');
            if (infoType === 'username' && user.username) {
                element.textContent = user.username;
            } else if (infoType === 'email' && user.email) {
                element.textContent = user.email;
            }
        });
    }
    
    /**
     * Handle session expiration
     */
    handleSessionExpired() {
        // Broadcast to other tabs first
        this.broadcastSessionExpired();
        
        // Clear local storage
        localStorage.removeItem(this.storageKey);
        
        // Show notification
        this.showNotification('Your session has expired. Please log in again.', 'warning');
        
        // Emit custom event
        window.dispatchEvent(new CustomEvent('sessionExpired', {
            detail: { timestamp: Date.now() }
        }));
        
        // Redirect to login after a short delay
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }
    
    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 1060;
            min-width: 300px;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        `;
        
        notification.innerHTML = `
            ${message}
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
    
    /**
     * Generate unique tab ID
     */
    generateTabId() {
        return 'tab_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now().toString(36);
    }
    
    /**
     * Check if session sync should be initialized on this page
     */
    shouldInitializeSync() {
        // Don't initialize on public pages
        const publicPages = ['/login', '/register', '/'];
        if (publicPages.includes(window.location.pathname)) {
            return false;
        }
        
        // Check if there's a CSRF token (indicates authenticated page)
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (!csrfToken) {
            return false;
        }
        
        // Check if there are user-specific elements on the page
        const userElements = document.querySelectorAll('[data-user-info], .navbar-nav .dropdown');
        if (userElements.length === 0) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Get unique tab ID
     */
    getTabId() {
        return this.tabId;
    }
    
    /**
     * Notify other tabs of platform switch
     */
    notifyPlatformSwitch(platformId, platformName) {
        const switchEvent = {
            type: 'platform_switch',
            platformId: platformId,
            platformName: platformName,
            timestamp: Date.now(),
            tabId: this.tabId
        };
        
        console.log(`Broadcasting platform switch to other tabs: ${platformName}`);
        localStorage.setItem('vedfolnir_platform_switch', JSON.stringify(switchEvent));
        
        // Remove the event after a short time to prevent stale events
        setTimeout(() => {
            localStorage.removeItem('vedfolnir_platform_switch');
        }, 1000);
    }
    
    /**
     * Handle platform switch event from another tab
     */
    handlePlatformSwitchEvent(switchEvent) {
        // Update UI to reflect platform switch
        this.updatePlatformContext({
            id: switchEvent.platformId,
            name: switchEvent.platformName
        });
        
        // Show notification
        this.showNotification(`Platform switched to ${switchEvent.platformName}`, 'info');
        
        // Emit custom event
        window.dispatchEvent(new CustomEvent('platformSwitched', {
            detail: switchEvent
        }));
    }
    
    /**
     * Broadcast session expiration to other tabs
     */
    broadcastSessionExpired() {
        const expiredEvent = {
            type: 'session_expired',
            timestamp: Date.now(),
            tabId: this.tabId
        };
        
        console.log('Broadcasting session expiration to other tabs');
        localStorage.setItem('vedfolnir_session_expired', JSON.stringify(expiredEvent));
        
        // Remove after short time
        setTimeout(() => {
            localStorage.removeItem('vedfolnir_session_expired');
        }, 1000);
    }
    
    /**
     * Broadcast logout to other tabs
     */
    broadcastLogout() {
        const logoutEvent = {
            type: 'logout',
            timestamp: Date.now(),
            tabId: this.tabId
        };
        
        console.log('Broadcasting logout to other tabs');
        localStorage.setItem('vedfolnir_logout', JSON.stringify(logoutEvent));
        
        // Remove after short time
        setTimeout(() => {
            localStorage.removeItem('vedfolnir_logout');
        }, 1000);
    }
    
    /**
     * Handle logout event from another tab
     */
    handleLogoutEvent() {
        // Clear local session data
        localStorage.removeItem(this.storageKey);
        
        // Show notification
        this.showNotification('You have been logged out from another tab.', 'info');
        
        // Redirect to login
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }
    
    /**
     * Broadcast session state update to other tabs
     */
    broadcastSessionState(sessionState) {
        const broadcastData = {
            ...sessionState,
            timestamp: Date.now(),
            tabId: this.tabId
        };
        
        localStorage.setItem(this.storageKey, JSON.stringify(broadcastData));
    }
    
    /**
     * Check if session state has actually changed
     */
    hasSessionStateChanged(newState) {
        if (!this.lastSessionState) {
            return true;
        }
        
        // Compare key fields that matter for UI updates
        const keyFields = ['user.id', 'platform.id', 'platform.name', 'platform.type', 'session_id'];
        
        for (const field of keyFields) {
            const oldValue = this.getNestedValue(this.lastSessionState, field);
            const newValue = this.getNestedValue(newState, field);
            
            if (oldValue !== newValue) {
                console.log(`Session state changed: ${field} changed from ${oldValue} to ${newValue}`);
                return true;
            }
        }
        
        // Also check if platform availability changed (null to object or vice versa)
        const oldPlatform = this.lastSessionState.platform;
        const newPlatform = newState.platform;
        
        if ((oldPlatform === null) !== (newPlatform === null)) {
            console.log('Platform availability changed');
            return true;
        }
        
        return false;
    }
    
    /**
     * Get nested object value by dot notation
     */
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : null;
        }, obj);
    }
    
    /**
     * Update performance metrics
     */
    updatePerformanceMetrics(startTime, success) {
        const duration = performance.now() - startTime;
        
        this.performanceMetrics.syncCount++;
        this.performanceMetrics.lastSyncDuration = duration;
        
        if (success) {
            // Update average sync time (exponential moving average)
            const alpha = 0.1; // Smoothing factor
            this.performanceMetrics.avgSyncTime = 
                (alpha * duration) + ((1 - alpha) * this.performanceMetrics.avgSyncTime);
        } else {
            this.performanceMetrics.syncErrors++;
        }
    }
    
    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        return {
            ...this.performanceMetrics,
            errorRate: this.performanceMetrics.syncCount > 0 ? 
                (this.performanceMetrics.syncErrors / this.performanceMetrics.syncCount) * 100 : 0,
            tabId: this.tabId,
            isOnline: this.isOnline,
            lastSyncTime: this.lastSyncTime
        };
    }
    
    /**
     * Debounced sync to prevent excessive API calls
     */
    debouncedSync(delay = 1000) {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        this.debounceTimer = setTimeout(() => {
            this.syncSessionState();
        }, delay);
    }
}

// Global session sync instance
let sessionSync = null;

// Initialize session sync when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    sessionSync = new SessionSync();
    sessionSync.init();
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (sessionSync) {
        sessionSync.destroy();
    }
});

// Export for use in other modules
window.SessionSync = SessionSync;
window.sessionSync = sessionSync;