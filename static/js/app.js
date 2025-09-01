// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// Vedfolnir - Enhanced Application JavaScript
// This file provides global functionality and UI enhancements

document.addEventListener('DOMContentLoaded', function() {
    console.log('Vedfolnir application initialized');
    
    // Initialize all UI enhancements
    initializeTooltips();
    initializeAlerts();
    initializeFormEnhancements();
    initializeLoadingStates();
    initializeKeyboardShortcuts();
    initializeMaintenanceMonitoring();
    
    // Add smooth scrolling
    document.documentElement.style.scrollBehavior = 'smooth';
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            delay: { show: 500, hide: 100 }
        });
    });
}

// Enhanced alert handling with auto-dismiss
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        // Auto-dismiss success and info alerts after 5 seconds
        if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
        
        // Add slide-in animation
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            alert.style.transition = 'all 0.3s ease-in-out';
            alert.style.opacity = '1';
            alert.style.transform = 'translateY(0)';
        }, 100);
    });
}

// Form enhancements
function initializeFormEnhancements() {
    // Character counters for textareas
    const textareas = document.querySelectorAll('textarea[maxlength]');
    textareas.forEach(textarea => {
        const maxLength = parseInt(textarea.getAttribute('maxlength'));
        const counter = document.createElement('div');
        counter.className = 'char-counter mt-1 text-end';
        textarea.parentNode.appendChild(counter);
        
        function updateCounter() {
            const remaining = maxLength - textarea.value.length;
            counter.textContent = `${textarea.value.length}/${maxLength} characters`;
            
            // Color coding
            counter.className = 'char-counter mt-1 text-end';
            if (remaining < 50) {
                counter.classList.add('text-danger');
            } else if (remaining < 100) {
                counter.classList.add('text-warning');
            } else {
                counter.classList.add('text-muted');
            }
        }
        
        textarea.addEventListener('input', updateCounter);
        updateCounter(); // Initial count
    });
    
    // Form validation feedback
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            form.classList.add('was-validated');
        });
    });
}

// Loading states for buttons
function initializeLoadingStates() {
    const buttons = document.querySelectorAll('button[type="submit"], .btn-loading');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.form && this.form.checkValidity && !this.form.checkValidity()) {
                return; // Don't show loading for invalid forms
            }
            
            const originalText = this.innerHTML;
            const loadingText = this.dataset.loadingText || 'Loading...';
            
            this.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>${loadingText}`;
            this.disabled = true;
            
            // Reset after 10 seconds as fallback
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 10000);
        });
    });
}

// Global keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Only handle shortcuts when not in input fields
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // Global shortcuts
        if (event.ctrlKey || event.metaKey) {
            switch(event.key) {
                case '/':
                    event.preventDefault();
                    // Focus search if available
                    const searchInput = document.querySelector('input[type="search"], input[placeholder*="search" i]');
                    if (searchInput) {
                        searchInput.focus();
                    }
                    break;
                case 'k':
                    event.preventDefault();
                    // Quick navigation (could open a command palette)
                    showQuickNavigation();
                    break;
            }
        }
        
        // Escape key to close modals/dropdowns
        if (event.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                modal.hide();
            }
        }
    });
}

// Quick navigation helper
function showQuickNavigation() {
    // Create a simple quick navigation overlay
    const nav = document.createElement('div');
    nav.className = 'position-fixed top-50 start-50 translate-middle bg-white shadow-lg rounded p-4';
    nav.style.zIndex = '9999';
    nav.style.minWidth = '300px';
    
    nav.innerHTML = `
        <h6 class="mb-3">Quick Navigation</h6>
        <div class="list-group list-group-flush">
            <a href="/" class="list-group-item list-group-item-action">
                <i class="bi bi-house me-2"></i>Dashboard
            </a>
            <a href="/review" class="list-group-item list-group-item-action">
                <i class="bi bi-eye me-2"></i>Review Images
            </a>
            <a href="/batch_review" class="list-group-item list-group-item-action">
                <i class="bi bi-stack me-2"></i>Batch Review
            </a>
        </div>
        <div class="text-center mt-3">
            <small class="text-muted">Press Escape to close</small>
        </div>
    `;
    
    document.body.appendChild(nav);
    
    // Close on escape or click outside
    function closeNav(event) {
        if (event.key === 'Escape' || !nav.contains(event.target)) {
            nav.remove();
            document.removeEventListener('keydown', closeNav);
            document.removeEventListener('click', closeNav);
        }
    }
    
    setTimeout(() => {
        document.addEventListener('keydown', closeNav);
        document.addEventListener('click', closeNav);
    }, 100);
}

// Unified Notification System Integration
window.Vedfolnir = {
    // Initialize unified notification system
    notificationRenderer: null,
    
    // Initialize notification system
    initNotificationSystem: function() {
        if (!this.notificationRenderer && window.NotificationUIRenderer) {
            this.notificationRenderer = new window.NotificationUIRenderer('vedfolnir-notifications', {
                position: 'top-right',
                maxNotifications: 5,
                autoHide: true,
                defaultDuration: 5000
            });
            console.log('Unified notification system initialized');
        }
    },
    
    // Show notification using unified system
    showNotification: function(message, type = 'info', options = {}) {
        this.initNotificationSystem();
        
        if (this.notificationRenderer) {
            return this.notificationRenderer.renderNotification({
                type: type === 'danger' ? 'error' : type, // Map Bootstrap types
                message: message,
                title: options.title,
                duration: options.duration,
                persistent: options.persistent,
                actions: options.actions
            });
        } else {
            // Fallback to console if unified system not available
            console.log(`Notification (${type}): ${message}`);
        }
    },
    
    // Legacy showToast method - redirects to unified system
    showToast: function(message, type = 'info') {
        return this.showNotification(message, type);
    },
    
    // Confirm dialog using unified notification system
    confirm: function(message, callback, options = {}) {
        this.initNotificationSystem();
        
        if (this.notificationRenderer) {
            return this.notificationRenderer.renderNotification({
                type: 'warning',
                title: options.title || 'Confirm Action',
                message: message,
                persistent: true,
                actions: [
                    {
                        label: 'Cancel',
                        type: 'secondary',
                        action: 'cancel'
                    },
                    {
                        label: 'Confirm',
                        type: 'primary',
                        action: 'confirm'
                    }
                ]
            });
        } else {
            // Fallback to native confirm
            const result = confirm(message);
            if (callback) callback(result);
            return result;
        }
    },
    
    // HTML sanitization utility
    sanitizeHtml: function(str) {
        if (typeof str !== 'string') {
            return '';
        }
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};

// Initialize unified notification system on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Vedfolnir notification system
    if (window.Vedfolnir) {
        window.Vedfolnir.initNotificationSystem();
        
        // Setup notification action handlers
        document.addEventListener('notificationAction', function(event) {
            const { action, notificationId, notification } = event.detail;
            
            switch (action) {
                case 'confirm':
                    // Handle confirmation actions
                    console.log('Notification confirmed:', notificationId);
                    break;
                case 'cancel':
                    // Handle cancellation actions
                    console.log('Notification cancelled:', notificationId);
                    break;
                case 'dismiss':
                    // Handle dismiss actions
                    console.log('Notification dismissed:', notificationId);
                    break;
                default:
                    console.log('Unknown notification action:', action);
            }
        });
    }
});

// Maintenance mode monitoring
function initializeMaintenanceMonitoring() {
    let maintenanceAlert = null;
    let lastMaintenanceStatus = null;
    
    function checkMaintenanceStatus() {
        fetch('/api/maintenance/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    const isMaintenanceMode = data.maintenance_mode;
                    const maintenanceReason = data.maintenance_reason;
                    
                    // Check if maintenance status changed
                    if (lastMaintenanceStatus !== isMaintenanceMode) {
                        lastMaintenanceStatus = isMaintenanceMode;
                        
                        if (isMaintenanceMode) {
                            showMaintenanceAlert(maintenanceReason);
                        } else {
                            hideMaintenanceAlert();
                        }
                    }
                }
            })
            .catch(error => {
                // Silently handle maintenance status check errors
                // This prevents console spam when the API is temporarily unavailable
                if (console.debug) {
                    console.debug('Maintenance status check failed (this is normal during startup):', error.message);
                }
            });
    }
    
    function showMaintenanceAlert(reason) {
        // Remove existing alert if present
        hideMaintenanceAlert();
        
        // Use unified notification system
        if (window.Vedfolnir && window.Vedfolnir.showNotification) {
            const reasonText = reason ? ` Reason: ${reason}` : '';
            maintenanceAlert = window.Vedfolnir.showNotification(
                `System Maintenance Mode Active${reasonText}`,
                'warning',
                {
                    title: 'System Maintenance',
                    persistent: true,
                    actions: [
                        {
                            label: 'Dismiss',
                            type: 'secondary',
                            action: 'dismiss'
                        }
                    ]
                }
            );
        } else {
            // Fallback to legacy alert display
            maintenanceAlert = document.createElement('div');
            maintenanceAlert.className = 'alert alert-warning alert-dismissible fade show position-fixed';
            maintenanceAlert.style.cssText = `
                top: 0;
                left: 0;
                right: 0;
                z-index: 9999;
                margin: 0;
                border-radius: 0;
                border: none;
                border-bottom: 3px solid #f0ad4e;
            `;
            
            const reasonText = reason ? ` Reason: ${reason}` : '';
            maintenanceAlert.innerHTML = `
                <div class="container-fluid">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        <strong>System Maintenance Mode Active</strong>
                        <span class="ms-2">${reasonText}</span>
                        <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
                    </div>
                </div>
            `;
            
            document.body.insertBefore(maintenanceAlert, document.body.firstChild);
            document.body.style.paddingTop = maintenanceAlert.offsetHeight + 'px';
            
            maintenanceAlert.addEventListener('closed.bs.alert', function() {
                document.body.style.paddingTop = '';
                maintenanceAlert = null;
            });
        }
        
        console.log('Maintenance mode alert displayed:', reason ? ` Reason: ${reason}` : '');
    }
    
    function hideMaintenanceAlert() {
        if (maintenanceAlert) {
            // If using unified system, dismiss by ID
            if (window.Vedfolnir && window.Vedfolnir.notificationRenderer && typeof maintenanceAlert === 'string') {
                window.Vedfolnir.notificationRenderer.dismissNotification(maintenanceAlert);
            } else if (maintenanceAlert.nodeType) {
                // Legacy DOM element cleanup
                const bsAlert = bootstrap.Alert.getInstance(maintenanceAlert);
                if (bsAlert) {
                    bsAlert.close();
                } else {
                    maintenanceAlert.remove();
                    document.body.style.paddingTop = '';
                }
            }
            maintenanceAlert = null;
        }
    }
    
    // Initial check
    checkMaintenanceStatus();
    
    // Poll every 30 seconds
    setInterval(checkMaintenanceStatus, 30000);
}

// Performance monitoring
if ('performance' in window) {
    window.addEventListener('load', function() {
        setTimeout(function() {
            const perfData = performance.getEntriesByType('navigation')[0];
            if (perfData.loadEventEnd - perfData.loadEventStart > 3000) {
                console.warn('Page load time is slow:', perfData.loadEventEnd - perfData.loadEventStart, 'ms');
            }
        }, 0);
    });
}