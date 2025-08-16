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

// Utility functions
window.Vedfolnir = {
    // Show toast notification
    showToast: function(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container') || createToastContainer();
        const toast = document.createElement('div');
        
        // Sanitize type parameter to prevent CSS injection
        const sanitizedType = ['primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark'].includes(type) ? type : 'info';
        
        toast.className = `toast align-items-center text-white bg-${sanitizedType} border-0`;
        toast.setAttribute('role', 'alert');
        
        // Sanitize message to prevent XSS
        const sanitizedMessage = this.sanitizeHtml(message);
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${sanitizedMessage}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },
    
    // Confirm dialog with modern styling
    confirm: function(message, callback) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        
        // Sanitize message to prevent XSS
        const sanitizedMessage = this.sanitizeHtml(message);
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header border-0">
                        <h5 class="modal-title">Confirm Action</h5>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0">${sanitizedMessage}</p>
                    </div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirmBtn">Confirm</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        
        modal.querySelector('#confirmBtn').addEventListener('click', () => {
            callback(true);
            bsModal.hide();
        });
        
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
        
        bsModal.show();
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

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
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