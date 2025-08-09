// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// Navigation JavaScript for platform switching and context

document.addEventListener('DOMContentLoaded', function() {
    // Initialize platform switching functionality
    initializePlatformSwitching();
});

function initializePlatformSwitching() {
    // Add event listeners for platform switching
    const platformDropdown = document.getElementById('platformsDropdown');
    if (platformDropdown) {
        // Add loading state management
        platformDropdown.addEventListener('show.bs.dropdown', function() {
            // Could add dynamic loading of platform status here
        });
    }
}

function quickSwitchPlatform(platformId, platformName) {
    // Check if we're on the caption generation page and warn about active tasks
    if (window.location.pathname === '/caption_generation') {
        const activeTaskStatus = document.getElementById('active-task-status');
        if (activeTaskStatus && activeTaskStatus.classList.contains('running')) {
            const confirmed = confirm(
                `You have an active caption generation task running. ` +
                `Switching platforms will cancel this task. ` +
                `Are you sure you want to continue?`
            );
            if (!confirmed) {
                return;
            }
        }
    }
    
    // Show loading state on the dropdown toggle
    const platformDropdownToggle = document.getElementById('platformsDropdown');
    const originalContent = platformDropdownToggle.innerHTML;
    
    platformDropdownToggle.innerHTML = `
        <div class="spinner-border spinner-border-sm" role="status">
            <span class="visually-hidden">Switching...</span>
        </div>
        <span class="ms-2">Switching...</span>
    `;
    
    // Close the dropdown
    const dropdown = bootstrap.Dropdown.getInstance(platformDropdownToggle);
    if (dropdown) {
        dropdown.hide();
    }
    
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // Make the API call to switch platforms
    fetch(`/api/switch_platform/${platformId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Show success message briefly
            showNavigationAlert('success', 'Switched to ' + platformName);
            
            // Reload the page to update all platform context
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            // Restore original content and show error
            platformDropdownToggle.innerHTML = originalContent;
            showNavigationAlert('danger', result.error || 'Failed to switch platform');
        }
    })
    .catch(error => {
        console.error('Error switching platform:', encodeURIComponent(error.toString()));
        
        // Restore original content and show error
        platformDropdownToggle.innerHTML = originalContent;
        showNavigationAlert('danger', 'Network error occurred while switching platform');
    });
}

function showNavigationAlert(type, message) {
    // Create a temporary alert at the top of the page
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = `
        top: 70px;
        right: 20px;
        z-index: 1060;
        min-width: 300px;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    `;
    // Safely set text content to prevent XSS
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');
    
    alertDiv.appendChild(messageSpan);
    alertDiv.appendChild(closeButton);
    
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 4000);
}

// Platform status checking (optional enhancement)
function checkPlatformStatus(platformId) {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    return fetch(`/api/test_platform/${platformId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken || ''
        }
    })
    .then(response => response.json())
    .then(result => result.success)
    .catch(() => false);
}

// Update platform status indicators
function updatePlatformStatusIndicators() {
    const platformElements = document.querySelectorAll('[data-platform-id]');
    
    platformElements.forEach(async (element) => {
        const platformId = element.dataset.platformId;
        const statusIndicator = element.querySelector('.platform-context-indicator');
        
        if (statusIndicator) {
            try {
                const isOnline = await checkPlatformStatus(platformId);
                statusIndicator.classList.remove('inactive', 'error');
                if (!isOnline) {
                    statusIndicator.classList.add('inactive');
                }
            } catch (error) {
                statusIndicator.classList.remove('inactive');
                statusIndicator.classList.add('error');
            }
        }
    });
}

// Initialize status checking on page load (optional)
// updatePlatformStatusIndicators();