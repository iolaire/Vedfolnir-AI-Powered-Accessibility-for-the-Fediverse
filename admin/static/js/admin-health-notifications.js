// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Admin Health Notifications Client Library
 * 
 * Provides real-time system health monitoring and notifications for admin dashboard
 * via WebSocket integration with the unified notification system.
 * 
 * Requirements: 4.1, 4.2, 4.4, 4.5, 8.1, 8.3
 */

class AdminHealthNotifications {
    constructor(options = {}) {
        this.options = {
            namespace: '/admin',
            autoConnect: true,
            reconnectAttempts: 5,
            reconnectDelay: 2000,
            healthUpdateInterval: 30000, // 30 seconds
            alertDisplayDuration: 10000, // 10 seconds
            ...options
        };
        
        this.socket = null;
        this.connected = false;
        this.monitoringActive = false;
        this.reconnectCount = 0;
        this.healthUpdateTimer = null;
        this.activeAlerts = new Map();
        
        // Event callbacks
        this.callbacks = {
            onConnect: [],
            onDisconnect: [],
            onHealthUpdate: [],
            onHealthAlert: [],
            onMonitoringStatusChange: [],
            onError: []
        };
        
        // Initialize if auto-connect is enabled
        if (this.options.autoConnect) {
            this.initialize();
        }
    }
    
    /**
     * Initialize WebSocket connection and event handlers
     */
    initialize() {
        try {
            // Check if Socket.IO is available
            // Use unified WebSocket connection instead of creating new one
            if (window.VedfolnirWS && window.VedfolnirWS.socket) {
                this.socket = window.VedfolnirWS.socket;
                this.setupEventHandlers();
                this.connected = true;
                console.log('Admin health notifications using unified WebSocket connection');
                return true;
            }
            
            // Wait for unified WebSocket to be available
            const checkForWebSocket = () => {
                if (window.VedfolnirWS && window.VedfolnirWS.socket) {
                    this.socket = window.VedfolnirWS.socket;
                    this.setupEventHandlers();
                    this.connected = true;
                    console.log('Admin health notifications connected to unified WebSocket');
                } else {
                    setTimeout(checkForWebSocket, 100);
                }
            };
            
            checkForWebSocket();
            console.log('Admin health notifications initialized');
            return true;
            
        } catch (error) {
            console.error('Failed to initialize admin health notifications:', error);
            this.triggerCallback('onError', { error: error.message });
            return false;
        }
    }
    
    /**
     * Set up WebSocket event handlers
     */
    setupEventHandlers() {
        if (!this.socket) return;
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to admin health monitoring');
            this.connected = true;
            this.reconnectCount = 0;
            this.triggerCallback('onConnect', { connected: true });
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from admin health monitoring:', reason);
            this.connected = false;
            this.triggerCallback('onDisconnect', { reason });
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Admin health monitoring connection error:', error);
            this.reconnectCount++;
            this.triggerCallback('onError', { error: error.message, reconnectCount: this.reconnectCount });
        });
        
        // Health monitoring events
        this.socket.on('health_monitoring_status', (data) => {
            console.log('Health monitoring status:', data);
            this.monitoringActive = data.monitoring_active || false;
            
            if (data.initial_health) {
                this.triggerCallback('onHealthUpdate', data.initial_health);
            }
        });
        
        this.socket.on('health_update', (data) => {
            console.log('Health update received:', data);
            if (data.success && data.health_status) {
                this.triggerCallback('onHealthUpdate', data.health_status);
            }
        });
        
        this.socket.on('health_notification', (data) => {
            console.log('Health notification received:', data);
            this.handleHealthNotification(data);
        });
        
        this.socket.on('health_alert', (data) => {
            console.log('Health alert received:', data);
            this.handleHealthAlert(data);
        });
        
        this.socket.on('health_monitoring_status_change', (data) => {
            console.log('Health monitoring status changed:', data);
            this.monitoringActive = data.monitoring_active || false;
            this.triggerCallback('onMonitoringStatusChange', data);
        });
        
        // Configuration events
        this.socket.on('health_config_updated', (data) => {
            console.log('Health configuration updated:', data);
            if (data.success) {
                this.showNotification('Configuration Updated', 'Health monitoring settings have been updated', 'success');
            } else {
                this.showNotification('Configuration Error', data.error || 'Failed to update configuration', 'error');
            }
        });
        
        // Alert acknowledgment events
        this.socket.on('alert_acknowledged', (data) => {
            console.log('Alert acknowledged:', data);
            this.removeAlert(data.alert_id);
        });
        
        this.socket.on('alert_acknowledgment_broadcast', (data) => {
            console.log('Alert acknowledgment broadcast:', data);
            this.removeAlert(data.alert_id);
        });
        
        // Error events
        this.socket.on('error', (data) => {
            console.error('Admin health monitoring error:', data);
            this.triggerCallback('onError', data);
        });
    }
    
    /**
     * Connect to WebSocket
     */
    connect() {
        // Connection is handled by unified WebSocket system
        if (this.socket && this.socket.connected) {
            this.connected = true;
            console.log('Admin health notifications already connected via unified WebSocket');
        } else {
            console.log('Waiting for unified WebSocket connection...');
        }
    }
    
    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        if (this.socket && this.connected) {
            this.socket.disconnect();
        }
        
        // Clear health update timer
        if (this.healthUpdateTimer) {
            clearInterval(this.healthUpdateTimer);
            this.healthUpdateTimer = null;
        }
    }
    
    /**
     * Request immediate health update
     */
    requestHealthUpdate(forceUpdate = false) {
        if (this.socket && this.connected) {
            this.socket.emit('request_health_update', { force_update: forceUpdate });
        } else {
            console.warn('Cannot request health update - not connected');
        }
    }
    
    /**
     * Start health monitoring
     */
    startMonitoring() {
        if (this.socket && this.connected) {
            this.socket.emit('start_health_monitoring');
        } else {
            console.warn('Cannot start monitoring - not connected');
        }
    }
    
    /**
     * Stop health monitoring
     */
    stopMonitoring() {
        if (this.socket && this.connected) {
            this.socket.emit('stop_health_monitoring');
        } else {
            console.warn('Cannot stop monitoring - not connected');
        }
    }
    
    /**
     * Configure health alerts
     */
    configureAlerts(config) {
        if (this.socket && this.connected) {
            this.socket.emit('configure_health_alerts', config);
        } else {
            console.warn('Cannot configure alerts - not connected');
        }
    }
    
    /**
     * Get current health status
     */
    getHealthStatus() {
        if (this.socket && this.connected) {
            this.socket.emit('get_health_status');
        } else {
            console.warn('Cannot get health status - not connected');
        }
    }
    
    /**
     * Acknowledge health alert
     */
    acknowledgeAlert(alertId) {
        if (this.socket && this.connected) {
            this.socket.emit('acknowledge_health_alert', { alert_id: alertId });
        } else {
            console.warn('Cannot acknowledge alert - not connected');
        }
    }
    
    /**
     * Handle health notification
     */
    handleHealthNotification(data) {
        try {
            // Determine notification type and priority
            const type = this.getNotificationType(data.type, data.priority);
            const title = data.title || 'System Health Notification';
            const message = data.message || 'System health update received';
            
            // Show notification
            this.showNotification(title, message, type, data);
            
            // Trigger callback
            this.triggerCallback('onHealthUpdate', data);
            
        } catch (error) {
            console.error('Error handling health notification:', error);
        }
    }
    
    /**
     * Handle health alert
     */
    handleHealthAlert(data) {
        try {
            const alertId = data.id || `alert_${Date.now()}`;
            const type = this.getAlertType(data.priority);
            const title = data.title || 'System Health Alert';
            const message = data.message || 'System health issue detected';
            
            // Store alert
            this.activeAlerts.set(alertId, data);
            
            // Show alert with acknowledgment option
            this.showAlert(alertId, title, message, type, data);
            
            // Trigger callback
            this.triggerCallback('onHealthAlert', data);
            
        } catch (error) {
            console.error('Error handling health alert:', error);
        }
    }
    
    /**
     * Show notification
     */
    showNotification(title, message, type = 'info', data = null) {
        try {
            // Create notification element
            const notification = this.createNotificationElement(title, message, type, false, data);
            
            // Add to page
            this.addNotificationToPage(notification);
            
            // Auto-remove after duration
            setTimeout(() => {
                this.removeNotificationElement(notification);
            }, this.options.alertDisplayDuration);
            
        } catch (error) {
            console.error('Error showing notification:', error);
        }
    }
    
    /**
     * Show alert with acknowledgment
     */
    showAlert(alertId, title, message, type = 'warning', data = null) {
        try {
            // Create alert element
            const alert = this.createNotificationElement(title, message, type, true, data, alertId);
            
            // Add to page
            this.addNotificationToPage(alert);
            
        } catch (error) {
            console.error('Error showing alert:', error);
        }
    }
    
    /**
     * Remove alert
     */
    removeAlert(alertId) {
        try {
            // Remove from active alerts
            this.activeAlerts.delete(alertId);
            
            // Remove from page
            const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
            if (alertElement) {
                this.removeNotificationElement(alertElement);
            }
            
        } catch (error) {
            console.error('Error removing alert:', error);
        }
    }
    
    /**
     * Create notification element
     */
    createNotificationElement(title, message, type, showAcknowledge, data, alertId) {
        const alertClass = this.getBootstrapAlertClass(type);
        const icon = this.getNotificationIcon(type);
        
        const element = document.createElement('div');
        element.className = `alert ${alertClass} alert-dismissible fade show position-fixed admin-health-notification`;
        element.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px; min-width: 300px;';
        
        if (alertId) {
            element.setAttribute('data-alert-id', alertId);
        }
        
        let acknowledgeButton = '';
        if (showAcknowledge && alertId) {
            acknowledgeButton = `
                <button type="button" class="btn btn-sm btn-outline-secondary me-2" onclick="adminHealthNotifications.acknowledgeAlert('${alertId}')">
                    <i class="bi bi-check-circle"></i> Acknowledge
                </button>
            `;
        }
        
        element.innerHTML = `
            <div class="d-flex align-items-start">
                <i class="${icon} me-2 mt-1"></i>
                <div class="flex-grow-1">
                    <strong>${this.escapeHtml(title)}</strong>
                    <div class="small mt-1">${this.escapeHtml(message)}</div>
                    ${data && data.system_health_data ? this.formatHealthData(data.system_health_data) : ''}
                </div>
            </div>
            <div class="mt-2 d-flex justify-content-end">
                ${acknowledgeButton}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        return element;
    }
    
    /**
     * Add notification to page
     */
    addNotificationToPage(element) {
        // Create container if it doesn't exist
        let container = document.getElementById('admin-health-notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'admin-health-notifications-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; pointer-events: none;';
            document.body.appendChild(container);
        }
        
        // Enable pointer events for this notification
        element.style.pointerEvents = 'auto';
        
        // Add to container
        container.appendChild(element);
        
        // Limit number of notifications
        const notifications = container.children;
        if (notifications.length > 5) {
            container.removeChild(notifications[0]);
        }
    }
    
    /**
     * Remove notification element
     */
    removeNotificationElement(element) {
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }
    
    /**
     * Format health data for display
     */
    formatHealthData(healthData) {
        if (!healthData || typeof healthData !== 'object') {
            return '';
        }
        
        let formatted = '<div class="small text-muted mt-1">';
        
        if (healthData.resource && healthData.usage) {
            formatted += `${healthData.resource.toUpperCase()}: ${healthData.usage.toFixed(1)}%`;
        }
        
        if (healthData.error_rate !== undefined) {
            formatted += `Error Rate: ${healthData.error_rate.toFixed(1)}%`;
        }
        
        if (healthData.stuck_jobs_count) {
            formatted += `Stuck Jobs: ${healthData.stuck_jobs_count}`;
        }
        
        formatted += '</div>';
        
        return formatted;
    }
    
    /**
     * Get notification type from data
     */
    getNotificationType(type, priority) {
        if (priority === 'critical') return 'error';
        if (priority === 'high') return 'warning';
        if (type === 'error') return 'error';
        if (type === 'warning') return 'warning';
        if (type === 'success') return 'success';
        return 'info';
    }
    
    /**
     * Get alert type from priority
     */
    getAlertType(priority) {
        if (priority === 'critical') return 'error';
        if (priority === 'high') return 'warning';
        return 'info';
    }
    
    /**
     * Get Bootstrap alert class
     */
    getBootstrapAlertClass(type) {
        switch (type) {
            case 'error': return 'alert-danger';
            case 'warning': return 'alert-warning';
            case 'success': return 'alert-success';
            case 'info':
            default: return 'alert-info';
        }
    }
    
    /**
     * Get notification icon
     */
    getNotificationIcon(type) {
        switch (type) {
            case 'error': return 'bi bi-exclamation-triangle-fill text-danger';
            case 'warning': return 'bi bi-exclamation-triangle text-warning';
            case 'success': return 'bi bi-check-circle-fill text-success';
            case 'info':
            default: return 'bi bi-info-circle text-info';
        }
    }
    
    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Add event callback
     */
    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }
    
    /**
     * Remove event callback
     */
    off(event, callback) {
        if (this.callbacks[event]) {
            const index = this.callbacks[event].indexOf(callback);
            if (index > -1) {
                this.callbacks[event].splice(index, 1);
            }
        }
    }
    
    /**
     * Trigger event callback
     */
    triggerCallback(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${event} callback:`, error);
                }
            });
        }
    }
    
    /**
     * Get connection status
     */
    isConnected() {
        return this.connected;
    }
    
    /**
     * Get monitoring status
     */
    isMonitoringActive() {
        return this.monitoringActive;
    }
    
    /**
     * Cleanup resources
     */
    cleanup() {
        this.disconnect();
        
        // Remove notification container
        const container = document.getElementById('admin-health-notifications-container');
        if (container) {
            container.remove();
        }
        
        // Clear callbacks
        Object.keys(this.callbacks).forEach(key => {
            this.callbacks[key] = [];
        });
    }
}

// Global instance for easy access
let adminHealthNotifications = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on admin pages
    if (document.body.classList.contains('admin-page') || 
        window.location.pathname.startsWith('/admin')) {
        
        adminHealthNotifications = new AdminHealthNotifications({
            autoConnect: true,
            healthUpdateInterval: 30000,
            alertDisplayDuration: 15000
        });
        
        // Make globally available
        window.adminHealthNotifications = adminHealthNotifications;
        
        console.log('Admin health notifications ready');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (adminHealthNotifications) {
        adminHealthNotifications.cleanup();
    }
});