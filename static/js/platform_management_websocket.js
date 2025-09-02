// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Platform Management WebSocket Integration
 * 
 * Replaces legacy alert-based notifications with real-time WebSocket notifications
 * for platform management operations including connection, switching, testing, and configuration.
 */

class PlatformManagementWebSocket {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        // Platform operation tracking
        this.activeOperations = new Map();
        
        // Initialize WebSocket connection
        this.initializeWebSocket();
        
        // Initialize page notification integrator
        this.initializePageNotifications();
        
        console.log('Platform Management WebSocket initialized');
    }
    
    initializeWebSocket() {
        try {
            // Use existing WebSocket connection if available
            if (window.socket && window.socket.connected) {
                this.socket = window.socket;
                this.connected = true;
                this.setupEventHandlers();
                console.log('Using existing WebSocket connection for platform management');
                return;
            }
            
            // Use unified WebSocket connection
            if (window.VedfolnirWS && window.VedfolnirWS.socket) {
                this.socket = window.VedfolnirWS.socket;
                this.setupConnectionHandlers();
                this.setupEventHandlers();
                console.log('Platform management using unified WebSocket connection');
            } else {
                // Wait for unified WebSocket to be available
                const checkForWebSocket = () => {
                    if (window.VedfolnirWS && window.VedfolnirWS.socket) {
                        this.socket = window.VedfolnirWS.socket;
                        this.setupConnectionHandlers();
                        this.setupEventHandlers();
                        console.log('Platform management connected to unified WebSocket');
                    } else {
                        setTimeout(checkForWebSocket, 100);
                    }
                };
                checkForWebSocket();
            }
            
        } catch (error) {
            console.error('Failed to initialize WebSocket for platform management:', error);
            this.handleConnectionError(error);
        }
    }
    
    setupConnectionHandlers() {
        this.socket.on('connect', () => {
            this.connected = true;
            this.reconnectAttempts = 0;
            console.log('Platform management WebSocket connected');
            
            // Join platform management room
            this.socket.emit('join_room', {
                room: 'platform_management',
                page_type: 'platform_management'
            });
        });
        
        this.socket.on('disconnect', (reason) => {
            this.connected = false;
            console.log('Platform management WebSocket disconnected:', reason);
            
            if (reason === 'io server disconnect') {
                // Server initiated disconnect, try to reconnect
                this.attemptReconnect();
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Platform management WebSocket connection error:', error);
            this.handleConnectionError(error);
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log('Platform management WebSocket reconnected after', attemptNumber, 'attempts');
            this.connected = true;
            this.reconnectAttempts = 0;
        });
    }
    
    setupEventHandlers() {
        // Platform status notifications
        this.socket.on('platform_status', (data) => {
            this.handlePlatformStatus(data);
        });
        
        // Platform connection notifications
        this.socket.on('platform_connection', (data) => {
            this.handlePlatformConnection(data);
        });
        
        // Platform error notifications
        this.socket.on('platform_error', (data) => {
            this.handlePlatformError(data);
        });
        
        // System notifications (maintenance, etc.)
        this.socket.on('system_notification', (data) => {
            this.handleSystemNotification(data);
        });
        
        // Generic notification handler
        this.socket.on('notification', (data) => {
            this.handleGenericNotification(data);
        });
    }
    
    initializePageNotifications() {
        // Initialize page notification integrator if available
        if (window.PageNotificationIntegrator) {
            this.pageIntegrator = new window.PageNotificationIntegrator('platform_management');
            console.log('Page notification integrator initialized for platform management');
        } else {
            console.warn('PageNotificationIntegrator not available, using fallback notifications');
        }
    }
    
    handlePlatformStatus(data) {
        console.log('Platform status notification:', data);
        
        try {
            // Update platform status indicators in UI
            if (data.platform_name && data.status) {
                this.updatePlatformStatusIndicator(data.platform_name, data.status);
            }
            
            // Show notification
            this.showNotification(data);
            
            // Handle specific status changes
            if (data.status === 'active' && data.operation_type === 'switch_platform') {
                // Platform switch successful - may need page refresh
                setTimeout(() => {
                    if (data.requires_refresh !== false) {
                        window.location.reload();
                    }
                }, 1500);
            }
            
        } catch (error) {
            console.error('Error handling platform status notification:', error);
        }
    }
    
    handlePlatformConnection(data) {
        console.log('Platform connection notification:', data);
        
        try {
            // Show notification
            this.showNotification(data);
            
            // Handle specific connection events
            if (data.operation_type === 'add_platform' && data.success) {
                // Platform added successfully
                if (data.is_first_platform) {
                    // First platform - redirect to dashboard
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 2000);
                } else {
                    // Additional platform - refresh platform management
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                }
            } else if (data.operation_type === 'edit_platform' && data.success) {
                // Platform edited successfully - refresh page
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else if (data.operation_type === 'delete_platform' && data.success) {
                // Platform deleted successfully - refresh page
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            }
            
        } catch (error) {
            console.error('Error handling platform connection notification:', error);
        }
    }
    
    handlePlatformError(data) {
        console.log('Platform error notification:', data);
        
        try {
            // Show error notification
            this.showNotification(data);
            
            // Handle authentication errors
            if (data.error_type === 'authentication' || data.operation_type === 'platform_auth_error') {
                // Show action button for credential update
                this.showActionNotification(data);
            }
            
        } catch (error) {
            console.error('Error handling platform error notification:', error);
        }
    }
    
    handleSystemNotification(data) {
        console.log('System notification:', data);
        
        try {
            // Show system notification
            this.showNotification(data);
            
            // Handle maintenance mode notifications
            if (data.maintenance_active) {
                this.handleMaintenanceMode(data);
            }
            
        } catch (error) {
            console.error('Error handling system notification:', error);
        }
    }
    
    handleGenericNotification(data) {
        console.log('Generic notification:', data);
        
        try {
            // Show generic notification
            this.showNotification(data);
            
        } catch (error) {
            console.error('Error handling generic notification:', error);
        }
    }
    
    showNotification(data) {
        // Use page integrator if available
        if (this.pageIntegrator && this.pageIntegrator.renderNotification) {
            this.pageIntegrator.renderNotification(data);
            return;
        }
        
        // Fallback to legacy notification system
        this.showLegacyNotification(data);
    }
    
    showLegacyNotification(data) {
        // Fallback notification display for compatibility
        const type = this.mapNotificationType(data.type);
        const message = data.message || data.title || 'Notification';
        
        // Use existing showAlert function if available
        if (typeof showAlert === 'function') {
            showAlert(type, message);
        } else {
            // Create simple notification
            this.createSimpleNotification(type, message);
        }
    }
    
    showActionNotification(data) {
        // Show notification with action button
        if (data.action_url && data.action_text) {
            const notification = this.createActionableNotification(data);
            this.displayNotification(notification);
        } else {
            this.showNotification(data);
        }
    }
    
    createActionableNotification(data) {
        const type = this.mapNotificationType(data.type);
        const message = data.message || data.title || 'Notification';
        
        // Create notification with action button
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show animate-slide-in`;
        
        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        
        const actionButton = document.createElement('a');
        actionButton.href = data.action_url;
        actionButton.className = 'btn btn-sm btn-outline-primary ms-2';
        actionButton.textContent = data.action_text;
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        
        alertDiv.appendChild(messageSpan);
        alertDiv.appendChild(actionButton);
        alertDiv.appendChild(closeButton);
        
        return alertDiv;
    }
    
    createSimpleNotification(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show animate-slide-in`;
        
        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        
        alertDiv.appendChild(messageSpan);
        alertDiv.appendChild(closeButton);
        
        this.displayNotification(alertDiv);
    }
    
    displayNotification(alertDiv) {
        // Insert notification at top of container
        const container = document.querySelector('.container-fluid') || document.body;
        if (container.firstChild) {
            container.insertBefore(alertDiv, container.firstChild);
        } else {
            container.appendChild(alertDiv);
        }
        
        // Scroll to top to show notification
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Auto-dismiss after appropriate time
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.classList.add('fade');
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.remove();
                    }
                }, 300);
            }
        }, 7000);
    }
    
    updatePlatformStatusIndicator(platformName, status) {
        // Find platform cards and update status indicators
        const platformCards = document.querySelectorAll('.platform-connection-card');
        
        platformCards.forEach(card => {
            const nameElement = card.querySelector('.card-title span.fw-bold');
            if (nameElement && nameElement.textContent.trim() === platformName) {
                const statusBadge = card.querySelector('.platform-status .badge');
                if (statusBadge) {
                    this.updateStatusBadge(statusBadge, status);
                }
            }
        });
    }
    
    updateStatusBadge(badge, status) {
        // Reset badge classes
        badge.className = 'badge';
        
        // Apply new status
        switch (status) {
            case 'active':
                badge.classList.add('bg-success');
                badge.innerHTML = '<i class="bi bi-check-circle"></i> Active';
                break;
            case 'inactive':
                badge.classList.add('bg-warning');
                badge.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Connection Issue';
                break;
            case 'error':
                badge.classList.add('bg-danger');
                badge.innerHTML = '<i class="bi bi-x-circle"></i> Error';
                break;
            case 'testing':
                badge.classList.add('bg-info');
                badge.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Testing...';
                break;
            default:
                badge.classList.add('bg-secondary');
                badge.innerHTML = '<i class="bi bi-question-circle"></i> Unknown';
        }
    }
    
    handleMaintenanceMode(data) {
        // Show maintenance mode banner if not already shown
        if (!document.querySelector('.maintenance-banner')) {
            this.showMaintenanceBanner(data);
        }
        
        // Disable platform operation buttons
        this.disablePlatformOperations();
    }
    
    showMaintenanceBanner(data) {
        const banner = document.createElement('div');
        banner.className = 'alert alert-warning maintenance-banner';
        banner.innerHTML = `
            <i class="bi bi-tools"></i>
            <strong>Maintenance Mode:</strong> Platform operations are temporarily disabled.
            ${data.maintenance_info && data.maintenance_info.reason ? 
                `<br><small>Reason: ${data.maintenance_info.reason}</small>` : ''}
        `;
        
        const container = document.querySelector('.container-fluid');
        if (container && container.firstChild) {
            container.insertBefore(banner, container.firstChild);
        }
    }
    
    disablePlatformOperations() {
        // Disable platform operation buttons during maintenance
        const operationButtons = document.querySelectorAll(
            'button[onclick*="switchPlatform"], ' +
            'button[onclick*="testConnection"], ' +
            'button[onclick*="editPlatform"], ' +
            'button[onclick*="deletePlatform"]'
        );
        
        operationButtons.forEach(button => {
            button.disabled = true;
            button.title = 'Disabled during maintenance';
        });
        
        // Disable add platform button
        const addButton = document.querySelector('[data-bs-target="#addPlatformModal"]');
        if (addButton) {
            addButton.disabled = true;
            addButton.title = 'Disabled during maintenance';
        }
    }
    
    mapNotificationType(type) {
        // Map notification types to Bootstrap alert classes
        const typeMap = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'info'
        };
        
        return typeMap[type] || 'info';
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached for platform management WebSocket');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Attempting to reconnect platform management WebSocket (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.connected) {
                this.socket.connect();
            }
        }, delay);
    }
    
    handleConnectionError(error) {
        console.error('Platform management WebSocket connection error:', error);
        
        // Show connection error notification
        this.showLegacyNotification({
            type: 'warning',
            message: 'Real-time notifications temporarily unavailable. Operations will still work normally.'
        });
    }
    
    // Public methods for integration with existing platform management functions
    
    notifyOperationStart(operationType, platformName) {
        const operationId = `${operationType}_${Date.now()}`;
        this.activeOperations.set(operationId, {
            type: operationType,
            platform: platformName,
            startTime: Date.now()
        });
        
        // Emit operation start event
        if (this.connected) {
            this.socket.emit('platform_operation_start', {
                operation_id: operationId,
                operation_type: operationType,
                platform_name: platformName
            });
        }
        
        return operationId;
    }
    
    notifyOperationComplete(operationId, success, message) {
        const operation = this.activeOperations.get(operationId);
        if (operation) {
            // Emit operation complete event
            if (this.connected) {
                this.socket.emit('platform_operation_complete', {
                    operation_id: operationId,
                    operation_type: operation.type,
                    platform_name: operation.platform,
                    success: success,
                    message: message,
                    duration: Date.now() - operation.startTime
                });
            }
            
            this.activeOperations.delete(operationId);
        }
    }
    
    isConnected() {
        return this.connected;
    }
    
    getActiveOperations() {
        return Array.from(this.activeOperations.values());
    }
}

// Initialize platform management WebSocket when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on platform management page
    if (window.location.pathname === '/platform_management' || 
        document.querySelector('[data-page-type="platform_management"]')) {
        
        window.platformWebSocket = new PlatformManagementWebSocket();
        console.log('Platform Management WebSocket integration initialized');
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PlatformManagementWebSocket;
} else {
    window.PlatformManagementWebSocket = PlatformManagementWebSocket;
}