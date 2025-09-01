// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Legacy Notification Migration Utility
 * 
 * Provides compatibility functions to redirect legacy notification calls
 * to the unified notification system. This ensures that any remaining
 * legacy code continues to work while using the new system.
 */

(function() {
    'use strict';
    
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        
        // Legacy notification function compatibility
        
        // Legacy alert() replacement
        const originalAlert = window.alert;
        window.alert = function(message) {
            if (window.showNotification) {
                return window.showNotification(message, 'info', 'Alert');
            } else {
                return originalAlert(message);
            }
        };
        
        // Legacy notification functions
        window.showAlert = window.showAlert || function(message, type = 'info') {
            if (window.showNotification) {
                return window.showNotification(message, type);
            } else {
                console.warn('Unified notification system not available, falling back to console');
                console.log(`${type.toUpperCase()}: ${message}`);
            }
        };
        
        window.showSuccess = window.showSuccess || function(message, title = 'Success') {
            if (window.showNotification) {
                return window.showNotification(message, 'success', title);
            }
        };
        
        window.showError = window.showError || function(message, title = 'Error') {
            if (window.showNotification) {
                return window.showNotification(message, 'error', title);
            }
        };
        
        window.showWarning = window.showWarning || function(message, title = 'Warning') {
            if (window.showNotification) {
                return window.showNotification(message, 'warning', title);
            }
        };
        
        window.showInfo = window.showInfo || function(message, title = 'Information') {
            if (window.showNotification) {
                return window.showNotification(message, 'info', title);
            }
        };
        
        // Legacy toast functions
        window.showToast = window.showToast || function(message, type = 'info', duration = 5000) {
            if (window.showNotification) {
                return window.showNotification(message, type, null, { duration: duration });
            }
        };
        
        window.toast = window.toast || function(message, options = {}) {
            if (window.showNotification) {
                return window.showNotification(message, options.type || 'info', options.title, options);
            }
        };
        
        // Legacy progress functions
        window.showProgressNotification = window.showProgressNotification || function(taskId, message, percentage = 0) {
            if (window.showProgress) {
                return window.showProgress(taskId, message, percentage);
            }
        };
        
        window.updateProgress = window.updateProgress || function(taskId, percentage, message = null) {
            if (window.showProgress) {
                return window.showProgress(taskId, message || 'Processing...', percentage);
            }
        };
        
        // Legacy admin notification functions
        window.showAdminAlert = window.showAdminAlert || function(message, type = 'warning') {
            if (window.showAdminNotification) {
                return window.showAdminNotification(message, type);
            } else if (window.showNotification) {
                return window.showNotification(message, type, 'Admin Alert');
            }
        };
        
        // Legacy flash message compatibility
        window.flash = window.flash || function(message, category = 'info') {
            const typeMap = {
                'message': 'info',
                'error': 'error',
                'warning': 'warning',
                'success': 'success',
                'danger': 'error'
            };
            
            const type = typeMap[category] || 'info';
            
            if (window.showNotification) {
                return window.showNotification(message, type);
            }
        };
        
        // Legacy jQuery notification compatibility (if jQuery is available)
        if (window.jQuery) {
            jQuery.fn.showNotification = function(message, type = 'info', options = {}) {
                if (window.showNotification) {
                    return window.showNotification(message, type, options.title, options);
                }
                return this;
            };
            
            jQuery.fn.notification = function(options = {}) {
                if (window.showNotification && options.message) {
                    return window.showNotification(options.message, options.type || 'info', options.title, options);
                }
                return this;
            };
        }
        
        // Legacy Bootstrap alert compatibility
        window.showBootstrapAlert = window.showBootstrapAlert || function(message, type = 'info', dismissible = true) {
            if (window.showNotification) {
                return window.showNotification(message, type, null, { 
                    allowDismiss: dismissible,
                    duration: dismissible ? 5000 : 0
                });
            }
        };
        
        // Legacy notification queue functions
        window.queueNotification = window.queueNotification || function(message, type = 'info', delay = 0) {
            setTimeout(function() {
                if (window.showNotification) {
                    window.showNotification(message, type);
                }
            }, delay);
        };
        
        // Legacy notification clearing functions
        window.clearNotifications = window.clearNotifications || function(type = null) {
            if (window.unifiedNotificationRenderer) {
                window.unifiedNotificationRenderer.clearNotifications(type);
            } else if (window.adminNotificationRenderer) {
                window.adminNotificationRenderer.clearNotifications(type);
            }
        };
        
        window.clearAllNotifications = window.clearAllNotifications || function() {
            window.clearNotifications();
        };
        
        // Legacy notification positioning
        window.setNotificationPosition = window.setNotificationPosition || function(position) {
            console.log(`Legacy notification position setting ignored: ${position}. Use unified notification system configuration instead.`);
        };
        
        // Legacy notification configuration
        window.configureNotifications = window.configureNotifications || function(config) {
            console.log('Legacy notification configuration ignored. Use unified notification system configuration instead.', config);
        };
        
        // Migrate any existing legacy notification containers
        migrateLegacyContainers();
        
        // Set up mutation observer to catch dynamically added legacy notifications
        setupLegacyNotificationObserver();
        
        console.log('Legacy notification migration utility loaded');
    });
    
    /**
     * Migrate existing legacy notification containers
     */
    function migrateLegacyContainers() {
        // Find and hide legacy notification containers
        const legacySelectors = [
            '.legacy-notification-container',
            '.old-notification-system',
            '.flash-message-container',
            '.legacy-alert-container',
            '.old-toast-container'
        ];
        
        legacySelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.style.display = 'none';
                element.classList.add('notification-system-legacy');
                
                // Try to extract and migrate any existing notifications
                const notifications = element.querySelectorAll('.alert, .notification, .toast');
                notifications.forEach(notification => {
                    migrateLegacyNotification(notification);
                });
            });
        });
    }
    
    /**
     * Migrate a single legacy notification element
     */
    function migrateLegacyNotification(element) {
        if (!window.showNotification) return;
        
        // Extract message
        const message = element.textContent || element.innerText || '';
        if (!message.trim()) return;
        
        // Determine type from classes
        let type = 'info';
        if (element.classList.contains('alert-success') || element.classList.contains('success')) {
            type = 'success';
        } else if (element.classList.contains('alert-danger') || element.classList.contains('error') || element.classList.contains('danger')) {
            type = 'error';
        } else if (element.classList.contains('alert-warning') || element.classList.contains('warning')) {
            type = 'warning';
        } else if (element.classList.contains('alert-info') || element.classList.contains('info')) {
            type = 'info';
        }
        
        // Show in unified system
        window.showNotification(message.trim(), type, 'Migrated Notification');
        
        // Hide original
        element.style.display = 'none';
    }
    
    /**
     * Set up mutation observer to catch dynamically added legacy notifications
     */
    function setupLegacyNotificationObserver() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if the added node is a legacy notification
                        if (node.classList && (
                            node.classList.contains('alert') ||
                            node.classList.contains('notification') ||
                            node.classList.contains('toast') ||
                            node.classList.contains('legacy-notification')
                        )) {
                            // Small delay to allow the element to be fully rendered
                            setTimeout(() => migrateLegacyNotification(node), 100);
                        }
                        
                        // Check for legacy notifications within the added node
                        const legacyNotifications = node.querySelectorAll && node.querySelectorAll('.alert, .notification, .toast');
                        if (legacyNotifications) {
                            legacyNotifications.forEach(notification => {
                                setTimeout(() => migrateLegacyNotification(notification), 100);
                            });
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
})();