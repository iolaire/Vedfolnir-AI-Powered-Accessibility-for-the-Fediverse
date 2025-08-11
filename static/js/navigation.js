// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// Navigation JavaScript for platform switching and context

// Global state for race condition prevention
let platformSwitchInProgress = false;
let platformSwitchDebounceTimer = null;
let originalPlatformState = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize platform switching functionality
    initializePlatformSwitching();
    
    // Listen for session state changes from other tabs
    window.addEventListener('sessionStateChanged', handleSessionStateChange);
    window.addEventListener('platformSwitched', handlePlatformSwitched);
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
    // Prevent multiple simultaneous switches with debouncing
    if (platformSwitchInProgress) {
        console.log('Platform switch already in progress, ignoring request');
        return;
    }
    
    // Clear any existing debounce timer
    if (platformSwitchDebounceTimer) {
        clearTimeout(platformSwitchDebounceTimer);
    }
    
    // Debounce rapid clicks
    platformSwitchDebounceTimer = setTimeout(() => {
        performPlatformSwitch(platformId, platformName);
    }, 100);
}

function performPlatformSwitch(platformId, platformName) {
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
    
    // Set switch in progress flag
    platformSwitchInProgress = true;
    
    // Store original platform state for potential reversion
    storeOriginalPlatformState();
    
    // Optimistically update UI immediately
    updatePlatformUI(platformId, platformName);
    
    // Notify other tabs about the switch
    if (window.sessionSync) {
        window.sessionSync.notifyPlatformSwitch(platformId, platformName);
    }
    
    // Show loading state on the dropdown toggle
    const platformDropdownToggle = document.getElementById('platformsDropdown');
    showPlatformSwitchLoading(platformDropdownToggle);
    
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
            
            // Sync session state across tabs
            if (window.sessionSync) {
                window.sessionSync.syncSessionState();
            }
            
            // Reload the page to update all platform context
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            // Revert optimistic UI update
            revertPlatformUI();
            showPlatformError(result.error || 'Failed to switch platform');
        }
    })
    .catch(error => {
        console.error('Error switching platform:', error);
        
        // Revert optimistic UI update
        revertPlatformUI();
        showPlatformError('Network error occurred while switching platform');
    })
    .finally(() => {
        // Reset switch in progress flag
        platformSwitchInProgress = false;
        
        // Restore platform dropdown
        restorePlatformDropdown();
    });
}

function showNavigationAlert(type, message) {
    // Use global error handler if available
    if (window.errorHandler) {
        window.errorHandler.showNotification(message, type, 4000);
        return;
    }
    
    // Fallback to local implementation
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

// Store original platform state for reverting
function storeOriginalPlatformState() {
    const platformDropdown = document.getElementById('platformsDropdown');
    if (platformDropdown && !originalPlatformState) {
        const platformIcon = platformDropdown.querySelector('.platform-icon');
        const platformNameEl = platformDropdown.querySelector('.platform-name');
        originalPlatformState = {
            icon: platformIcon ? platformIcon.className : '',
            name: platformNameEl ? platformNameEl.textContent : '',
            html: platformDropdown.innerHTML
        };
    }
}

function updatePlatformUI(platformId, platformName) {
    // Update platform dropdown
    const platformDropdown = document.getElementById('platformsDropdown');
    if (platformDropdown) {
        const platformIcon = platformDropdown.querySelector('.platform-icon');
        const platformNameEl = platformDropdown.querySelector('.platform-name');
        
        if (platformIcon && platformNameEl) {
            // Update icon based on platform type (simplified)
            platformIcon.className = 'platform-icon bi bi-globe';
            platformNameEl.textContent = platformName;
        }
    }
    
    // Update current platform displays
    const currentPlatformElements = document.querySelectorAll('[data-current-platform]');
    currentPlatformElements.forEach(element => {
        element.textContent = platformName;
        element.setAttribute('data-platform-id', platformId);
    });
    
    console.log(`Optimistically updated UI for platform: ${platformName}`);
}

function revertPlatformUI() {
    if (!originalPlatformState) {
        return;
    }
    
    const platformDropdown = document.getElementById('platformsDropdown');
    if (platformDropdown) {
        // Restore the original HTML content
        platformDropdown.innerHTML = originalPlatformState.html;
    }
    
    console.log('Reverted platform UI to original state');
    originalPlatformState = null;
}

function showPlatformSwitchLoading(platformDropdownToggle) {
    if (platformDropdownToggle) {
        const loadingContent = `
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Switching...</span>
            </div>
            <span class="ms-2">Switching...</span>
        `;
        platformDropdownToggle.innerHTML = loadingContent;
    }
}

function restorePlatformDropdown() {
    // The dropdown will be restored either by revertPlatformUI() on error
    // or by page reload on success, so no action needed here
}

function showPlatformError(message) {
    // Use global error handler if available
    if (window.errorHandler) {
        window.errorHandler.showNotification(message, 'danger');
        return;
    }
    
    // Fallback to local implementation
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    errorDiv.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 1060;
        min-width: 300px;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    `;
    
    errorDiv.innerHTML = `
        <i class="bi bi-exclamation-triangle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(errorDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

// Handle session state changes from other tabs
function handleSessionStateChange(event) {
    const sessionState = event.detail;
    if (sessionState.platform) {
        updatePlatformUI(sessionState.platform.id, sessionState.platform.name);
    }
}

// Handle platform switch events from other tabs
function handlePlatformSwitched(event) {
    const switchEvent = event.detail;
    console.log(`Platform switched in another tab: ${switchEvent.platformName}`);
    
    // Update UI to match the switch
    updatePlatformUI(switchEvent.platformId, switchEvent.platformName);
}

// Initialize status checking on page load (optional)
// updatePlatformStatusIndicators();