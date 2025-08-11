// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Comprehensive Error Handling and User Feedback System
 * Provides standardized error notifications, offline detection, and user feedback
 */

class ErrorHandler {
    constructor() {
        this.isOnline = navigator.onLine;
        this.notificationQueue = [];
        this.maxNotifications = 3;
        this.defaultTimeout = 5000;
        
        // Bind methods
        this.handleOnlineChange = this.handleOnlineChange.bind(this);
        
        // Initialize
        this.init();
    }
    
    init() {
        // Listen for online/offline changes
        window.addEventListener('online', this.handleOnlineChange);
        window.addEventListener('offline', this.handleOnlineChange);
        
        // Listen for unhandled errors
        window.addEventListener('error', (event) => {
            this.handleGlobalError(event.error, event.filename, event.lineno);
        });
        
        // Listen for unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handlePromiseRejection(event.reason);
        });
        
        console.log('Error handler initialized');
    }
    
    handleOnlineChange() {
        const wasOnline = this.isOnline;
        this.isOnline = navigator.onLine;
        
        if (!wasOnline && this.isOnline) {
            this.showNotification('You are back online!', 'success', 3000);
        } else if (!this.isOnline) {
            this.showNotification('You are currently offline. Some features may not work.', 'warning', 0);
        }
    }
    
    handleGlobalError(error, filename, lineno) {
        console.error('Global error:', error, 'at', filename, ':', lineno);
        
        // Don't show notifications for script loading errors
        if (filename && filename.includes('.js')) {
            return;
        }
        
        this.showNotification('An unexpected error occurred. Please refresh the page if problems persist.', 'danger');
    }
    
    handlePromiseRejection(reason) {
        console.error('Unhandled promise rejection:', reason);
        
        // Handle specific types of promise rejections
        if (reason && reason.name === 'NetworkError') {
            this.handleNetworkError(reason);
        } else {
            this.showNotification('An error occurred while processing your request.', 'warning');
        }
    }
    
    handleNetworkError(error) {
        if (!this.isOnline) {
            this.showNotification('Network request failed - you appear to be offline.', 'warning');
        } else {
            this.showNotification('Network error occurred. Please check your connection.', 'danger');
        }
    }
    
    handleSessionError(error) {
        if (error.status === 401) {
            this.showNotification('Your session has expired. Please log in again.', 'warning');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else if (error.status === 403) {
            this.showNotification('You do not have permission to perform this action.', 'danger');
        } else {
            this.showNotification('Session error occurred. Please refresh the page.', 'warning');
        }
    }
    
    handlePlatformError(error, platformName) {
        let message = `Error with platform ${platformName}: `;
        
        if (error.status === 401) {
            message += 'Authentication failed. Please check your credentials.';
        } else if (error.status === 403) {
            message += 'Access denied. Please check your permissions.';
        } else if (error.status === 404) {
            message += 'Platform not found or unavailable.';
        } else if (error.status >= 500) {
            message += 'Server error. Please try again later.';
        } else {
            message += 'An unexpected error occurred.';
        }
        
        this.showNotification(message, 'danger');
    }
    
    showNotification(message, type = 'info', timeout = null) {
        // Limit number of simultaneous notifications
        if (this.notificationQueue.length >= this.maxNotifications) {
            const oldestNotification = this.notificationQueue.shift();
            if (oldestNotification && oldestNotification.parentNode) {
                oldestNotification.remove();
            }
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: ${20 + (this.notificationQueue.length * 70)}px;
            right: 20px;
            z-index: 1060;
            min-width: 300px;
            max-width: 500px;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            word-wrap: break-word;
        `;
        
        // Add appropriate icon
        let icon = '';
        switch (type) {
            case 'success':
                icon = '<i class="bi bi-check-circle me-2"></i>';
                break;
            case 'warning':
                icon = '<i class="bi bi-exclamation-triangle me-2"></i>';
                break;
            case 'danger':
                icon = '<i class="bi bi-x-circle me-2"></i>';
                break;
            case 'info':
            default:
                icon = '<i class="bi bi-info-circle me-2"></i>';
                break;
        }
        
        notification.innerHTML = `
            ${icon}${this.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Add to queue
        this.notificationQueue.push(notification);
        
        // Add to DOM
        document.body.appendChild(notification);
        
        // Auto-remove after timeout (unless timeout is 0 for persistent notifications)
        const actualTimeout = timeout !== null ? timeout : this.defaultTimeout;
        if (actualTimeout > 0) {
            setTimeout(() => {
                this.removeNotification(notification);
            }, actualTimeout);
        }
        
        // Handle manual dismissal
        const closeButton = notification.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                this.removeNotification(notification);
            });
        }
        
        return notification;
    }
    
    removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.remove();
            
            // Remove from queue
            const index = this.notificationQueue.indexOf(notification);
            if (index > -1) {
                this.notificationQueue.splice(index, 1);
            }
            
            // Reposition remaining notifications
            this.repositionNotifications();
        }
    }
    
    repositionNotifications() {
        this.notificationQueue.forEach((notification, index) => {
            if (notification && notification.parentNode) {
                notification.style.top = `${20 + (index * 70)}px`;
            }
        });
    }
    
    clearAllNotifications() {
        this.notificationQueue.forEach(notification => {
            if (notification && notification.parentNode) {
                notification.remove();
            }
        });
        this.notificationQueue = [];
    }
    
    showConfirmDialog(message, title = 'Confirm') {
        return new Promise((resolve) => {
            // Create modal dialog
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${this.escapeHtml(title)}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${this.escapeHtml(message)}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary confirm-btn">Confirm</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            const bootstrapModal = new bootstrap.Modal(modal);
            
            // Handle confirm
            modal.querySelector('.confirm-btn').addEventListener('click', () => {
                bootstrapModal.hide();
                resolve(true);
            });
            
            // Handle cancel/close
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
                resolve(false);
            });
            
            bootstrapModal.show();
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Utility methods for common error scenarios
    handleFetchError(response, context = '') {
        const contextMsg = context ? ` (${context})` : '';
        
        if (!response.ok) {
            if (response.status === 401) {
                this.handleSessionError({ status: 401 });
            } else if (response.status === 403) {
                this.showNotification(`Access denied${contextMsg}`, 'danger');
            } else if (response.status === 404) {
                this.showNotification(`Resource not found${contextMsg}`, 'warning');
            } else if (response.status >= 500) {
                this.showNotification(`Server error${contextMsg}. Please try again later.`, 'danger');
            } else {
                this.showNotification(`Request failed${contextMsg} (${response.status})`, 'warning');
            }
            return false;
        }
        return true;
    }
    
    handleAsyncError(error, context = '') {
        console.error(`Async error${context ? ' in ' + context : ''}:`, error);
        
        if (error.name === 'NetworkError' || error.message.includes('fetch')) {
            this.handleNetworkError(error);
        } else if (error.status) {
            this.handleFetchError({ ok: false, status: error.status }, context);
        } else {
            this.showNotification(`An error occurred${context ? ' in ' + context : ''}`, 'warning');
        }
    }
}

// Global error handler instance
const errorHandler = new ErrorHandler();

// Export for use in other modules
window.ErrorHandler = ErrorHandler;
window.errorHandler = errorHandler;