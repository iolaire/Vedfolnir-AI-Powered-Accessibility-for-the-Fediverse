// Admin-specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize admin functionality
    initializeAdminDashboard();
    initializeConfirmDialogs();
    initializeAutoRefresh();
});

function initializeAdminDashboard() {
    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

function initializeConfirmDialogs() {
    // Add confirmation dialogs to dangerous actions
    const dangerousButtons = document.querySelectorAll('[data-confirm]');
    
    dangerousButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Check if user has admin privileges before allowing dangerous actions
            if (!document.body.hasAttribute('data-admin-user')) {
                e.preventDefault();
                alert('Access denied. Admin privileges required.');
                return false;
            }
            
            // Check if user has admin privileges before allowing dangerous actions
            if (!document.body.hasAttribute('data-admin-user')) {
                e.preventDefault();
                alert('Access denied. Admin privileges required.');
                return false;
            }
            
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

function initializeAutoRefresh() {
    // Auto-refresh certain admin pages
    const refreshPages = ['/admin/monitoring', '/admin/health'];
    const currentPath = window.location.pathname;
    
    if (refreshPages.some(path => currentPath.includes(path))) {
        // Refresh every 30 seconds
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                refreshPageData();
            }
        }, 30000);
    }
}

function refreshPageData() {
    // Refresh dynamic content without full page reload
    const refreshElements = document.querySelectorAll('[data-refresh]');
    
    refreshElements.forEach(element => {
        const url = element.getAttribute('data-refresh');
        if (url) {
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateElement(element, data);
                    }
                })
                .catch(error => {
                    console.error('Error refreshing data:', error);
                });
        }
    });
}

function updateElement(element, data) {
    // Update element content based on data
    if (data.text) {
        element.textContent = data.text;
    }
    // Removed innerHTML assignment to prevent code injection
}

// Utility functions for admin operations
function showLoading(element) {
    element.classList.add('loading');
    const spinner = document.createElement('span');
    spinner.className = 'spinner-border spinner-border-sm me-2';
    element.prepend(spinner);
}

function hideLoading(element) {
    element.classList.remove('loading');
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.remove();
    }
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('main');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}