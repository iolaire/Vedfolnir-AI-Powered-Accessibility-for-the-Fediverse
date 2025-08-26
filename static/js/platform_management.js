// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// Platform Management JavaScript

// Handle maintenance mode responses
function handleMaintenanceResponse(response, operation) {
    if (response.maintenance_active) {
        const maintenanceInfo = response.maintenance_info || {};
        const operationInfo = response.operation_info || {};
        
        let message = `${operationInfo.icon || '🔧'} ${operationInfo.title || 'Service Unavailable'}`;
        
        if (maintenanceInfo.reason) {
            message += `\n\nReason: ${maintenanceInfo.reason}`;
        }
        
        if (operationInfo.description) {
            message += `\n\n${operationInfo.description}`;
        }
        
        if (maintenanceInfo.estimated_completion) {
            const completion = new Date(maintenanceInfo.estimated_completion);
            message += `\n\nExpected completion: ${completion.toLocaleString()}`;
        } else if (maintenanceInfo.estimated_duration) {
            message += `\n\nEstimated duration: ${maintenanceInfo.estimated_duration} minutes`;
        }
        
        if (operationInfo.suggestion) {
            message += `\n\n${operationInfo.suggestion}`;
        }
        
        showAlert('warning', message, 10000); // Show for 10 seconds
        return true;
    }
    return false;
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize add platform form
    const addPlatformForm = document.getElementById('addPlatformForm');
    if (addPlatformForm) {
        addPlatformForm.addEventListener('submit', handleAddPlatform);
        
        // Ensure submit button properly triggers form submission
        const submitButton = addPlatformForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.addEventListener('click', function(e) {
                e.preventDefault();
                const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                addPlatformForm.dispatchEvent(submitEvent);
            });
        }
    }
    
    // Initialize edit platform form
    const editPlatformForm = document.getElementById('editPlatformForm');
    if (editPlatformForm) {
        editPlatformForm.addEventListener('submit', handleEditPlatform);
    }
    
    // Initialize delete confirmation checkbox
    const confirmDeletionCheckbox = document.getElementById('confirmDeletion');
    const confirmDeleteButton = document.getElementById('confirmDeleteButton');
    
    if (confirmDeletionCheckbox && confirmDeleteButton) {
        confirmDeletionCheckbox.addEventListener('change', function() {
            confirmDeleteButton.disabled = !this.checked;
        });
    }
});

function handleAddPlatform(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const spinner = submitButton.querySelector('.spinner-border');
    const formData = new FormData(form);

    // Convert FormData to JSON and validate
    const data = {};
    for (let [key, value] of formData.entries()) {
        console.log(`  ${key}: ${value}`);
        if (key !== 'test_connection') {
            data[key] = value ? value.trim() : '';
        }
    }
    
    // Explicitly handle test_connection checkbox
    const testConnectionCheckbox = form.querySelector('#testConnection');
    data.test_connection = testConnectionCheckbox ? testConnectionCheckbox.checked : false;
    
    // Client-side validation
    const validationErrors = validatePlatformForm(data);
    if (validationErrors.length > 0) {
        showAlert('danger', 'Validation errors: ' + validationErrors.join('; '));
        return;
    }
    
    // Show loading state
    submitButton.disabled = true;
    spinner.classList.remove('d-none');
    
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    fetch('/api/add_platform', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken || ''
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showAlert('success', result.message);
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addPlatformModal'));
            modal.hide();
            
            // Mark platform context for refresh
            if (window.markPlatformContextForRefresh) {
                window.markPlatformContextForRefresh();
            }
            
            // If this was the first platform, redirect to dashboard instead of platform management
            const redirectUrl = result.is_first_platform ? '/' : '/platform_management';
            const redirectMessage = result.is_first_platform ? 'Redirecting to dashboard...' : 'Redirecting to platform management...';
            
            if (result.is_first_platform) {
                if (result.requires_refresh) {
                    showAlert('info', 'First platform added successfully! Please refresh the page if you experience any issues. ' + redirectMessage);
                } else {
                    showAlert('info', 'First platform added successfully! ' + redirectMessage);
                }
            }
            
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, result.is_first_platform ? 1500 : 1000);
        } else {
            // Check if this is a maintenance mode response
            if (!handleMaintenanceResponse(result, 'add_platform')) {
                showAlert('danger', result.error || 'Failed to add platform connection');
            }
        }
    })
    .catch(error => {
        showAlert('danger', 'Network error occurred while adding platform: ' + (error.message || 'Unknown error'));
    })
    .finally(() => {
        // Hide loading state
        submitButton.disabled = false;
        spinner.classList.add('d-none');
    });
}

function validatePlatformForm(data) {
    const errors = [];
    
    // Validate required fields
    const requiredFields = ['name', 'platform_type', 'instance_url', 'access_token'];
    for (const field of requiredFields) {
        if (!data[field]) {
            errors.push(`${field.replace('_', ' ')} is required`);
        }
    }
    
    // Validate name length
    if (data.name && (data.name.length < 1 || data.name.length > 100)) {
        errors.push('Platform name must be between 1 and 100 characters');
    }
    
    // Validate platform type
    if (data.platform_type && !['pixelfed', 'mastodon'].includes(data.platform_type.toLowerCase())) {
        errors.push('Platform type must be either Pixelfed or Mastodon');
    }
    
    // Validate instance URL format
    if (data.instance_url) {
        try {
            const url = new URL(data.instance_url);
            if (!['http:', 'https:'].includes(url.protocol)) {
                errors.push('Instance URL must use HTTP or HTTPS protocol');
            }
        } catch (e) {
            errors.push('Instance URL format is invalid');
        }
        
        if (data.instance_url.length > 500) {
            errors.push('Instance URL must be less than 500 characters');
        }
    }
    
    // Validate access token
    if (data.access_token && data.access_token.length < 10) {
        errors.push('Access token appears to be too short (minimum 10 characters)');
    }
    
    // Validate username length if provided
    if (data.username && data.username.length > 200) {
        errors.push('Username must be less than 200 characters');
    }
    
    // Mastodon validation removed - only access token required
    
    return errors;
}

function editPlatform(platformId) {
    // Get platform data from the page
    const platformCard = document.querySelector(`[data-platform-id="${platformId}"]`);
    if (!platformCard) {
        // If we can't find the card, fetch the data from the server
        fetchPlatformData(platformId);
        return;
    }
    
    // For now, we'll fetch the data from the server since we need all details
    fetchPlatformData(platformId);
}

function fetchPlatformData(platformId) {
    showLoadingModal('Loading platform data...');
    
    fetch(`/api/get_platform/${platformId}`)
    .then(response => response.json())
    .then(result => {
        hideLoadingModal();
        if (result.success) {
            populateEditForm(result.platform);
            const modal = new bootstrap.Modal(document.getElementById('editPlatformModal'));
            modal.show();
        } else {
            showAlert('danger', result.error || 'Failed to load platform data');
        }
    })
    .catch(error => {
        hideLoadingModal();
        console.error('Error:', encodeURIComponent(error.toString()));
        showAlert('danger', 'Network error occurred while loading platform data');
    });
}

function populateEditForm(platform) {
    document.getElementById('editPlatformId').value = platform.id;
    document.getElementById('editPlatformName').value = platform.name;
    document.getElementById('editPlatformType').value = platform.platform_type;
    document.getElementById('editInstanceUrl').value = platform.instance_url;
    document.getElementById('editUsername').value = platform.username || '';
    document.getElementById('editAccessToken').value = platform.access_token || '';
    
    // Mastodon fields handling removed - no longer needed
}

function handleEditPlatform(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const spinner = submitButton.querySelector('.spinner-border');
    const formData = new FormData(form);
    const platformId = document.getElementById('editPlatformId').value;
    
    // Convert FormData to JSON and validate
    const data = {};
    for (let [key, value] of formData.entries()) {
        if (key !== 'platform_id' && key !== 'test_connection' && value && value.trim()) {
            data[key] = value.trim();
        }
    }
    
    // Explicitly handle test_connection checkbox
    const testConnectionCheckbox = form.querySelector('#editTestConnection');
    data.test_connection = testConnectionCheckbox ? testConnectionCheckbox.checked : false;
    
    // Client-side validation
    const validationErrors = validatePlatformForm(data);
    if (validationErrors.length > 0) {
        showAlert('danger', 'Validation errors: ' + validationErrors.join('; '));
        return;
    }
    
    // Show loading state
    submitButton.disabled = true;
    spinner.classList.remove('d-none');
    
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    fetch(`/api/edit_platform/${platformId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken || ''
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showAlert('success', result.message);
            // Close modal and refresh page
            const modal = bootstrap.Modal.getInstance(document.getElementById('editPlatformModal'));
            modal.hide();
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            // Check if this is a maintenance mode response
            if (!handleMaintenanceResponse(result, 'edit_platform')) {
                showAlert('danger', result.error || 'Failed to update platform connection');
            }
        }
    })
    .catch(error => {
        console.error('Error:', encodeURIComponent(error.toString()));
        showAlert('danger', 'Network error occurred while updating platform');
    })
    .finally(() => {
        // Hide loading state
        submitButton.disabled = false;
        spinner.classList.add('d-none');
    });
}

function switchPlatform(platformId, platformName) {
    showLoadingModal(`Switching to ${platformName}...`);
    
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    fetch(`/api/switch_platform/${platformId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        hideLoadingModal();
        if (result.success) {
            showAlert('success', `Successfully switched to ${platformName}. Refreshing page...`);
            // Update UI immediately before reload
            updateCurrentPlatformDisplay(result.platform);
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            // Check if this is a maintenance mode response
            if (!handleMaintenanceResponse(result, 'switch_platform')) {
                showAlert('danger', result.error || 'Failed to switch platform');
            }
        }
    })
    .catch(error => {
        hideLoadingModal();
        console.error('Error:', encodeURIComponent(error.toString()));
        showAlert('danger', 'Network error occurred while switching platform');
    });
}

function testConnection(platformId, platformName) {
    const testButton = document.querySelector(`button[onclick="testConnection(${platformId}, '${platformName}')"]`);
    const originalText = testButton ? testButton.innerHTML : '';
    
    if (testButton) {
        testButton.disabled = true;
        testButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Testing...';
    }
    
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    fetch(`/api/test_platform/${platformId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showAlert('success', `✅ Connection test successful for ${platformName}: ${result.message}`);
            // Update platform status indicator if exists
            updatePlatformStatus(platformId, 'active');
        } else {
            // Check if this is a maintenance mode response
            if (!handleMaintenanceResponse(result, 'test_platform')) {
                showAlert('warning', `⚠️ Connection test failed for ${platformName}: ${result.message}`);
                updatePlatformStatus(platformId, 'inactive');
            }
        }
    })
    .catch(error => {
        console.error('Error:', encodeURIComponent(error.toString()));
        showAlert('danger', `❌ Network error while testing ${encodeURIComponent(platformName)}: Unable to reach the platform`);
        updatePlatformStatus(platformId, 'error');
    })
    .finally(() => {
        if (testButton) {
            testButton.disabled = false;
            testButton.innerHTML = originalText;
        }
    });
}

// Global variable to store platform data for deletion
let platformToDelete = null;

function deletePlatform(platformId, platformName) {
    // First, get the platform data to show in the confirmation modal
    showLoadingModal('Loading platform information...');
    
    fetch(`/api/get_platform/${platformId}`)
    .then(response => response.json())
    .then(result => {
        hideLoadingModal();
        if (result.success) {
            platformToDelete = result.platform;
            showDeleteConfirmationModal(result.platform);
        } else {
            showAlert('danger', result.error || 'Failed to load platform information');
        }
    })
    .catch(error => {
        hideLoadingModal();
        console.error('Error:', encodeURIComponent(error.toString()));
        showAlert('danger', 'Network error occurred while loading platform information');
    });
}

function showDeleteConfirmationModal(platform) {
    // Populate the modal with platform information
    document.getElementById('deletePlatformName').textContent = platform.name;
    document.getElementById('deletePlatformType').textContent = platform.platform_type.charAt(0).toUpperCase() + platform.platform_type.slice(1);
    document.getElementById('deletePlatformUrl').textContent = platform.instance_url;
    document.getElementById('deletePlatformUsername').textContent = platform.username ? `@${platform.username}` : 'No username specified';
    
    // Show warning if this is the default platform
    const defaultWarning = document.getElementById('deleteDefaultWarning');
    if (platform.is_default) {
        defaultWarning.classList.remove('d-none');
    } else {
        defaultWarning.classList.add('d-none');
    }
    
    // Reset the confirmation checkbox and button
    const confirmCheckbox = document.getElementById('confirmDeletion');
    const confirmButton = document.getElementById('confirmDeleteButton');
    confirmCheckbox.checked = false;
    confirmButton.disabled = true;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('deletePlatformModal'));
    modal.show();
}

function confirmPlatformDeletion() {
    if (!platformToDelete) {
        showAlert('danger', 'No platform selected for deletion');
        return;
    }
    
    const confirmButton = document.getElementById('confirmDeleteButton');
    const spinner = confirmButton.querySelector('.spinner-border');
    
    // Show loading state
    confirmButton.disabled = true;
    spinner.classList.remove('d-none');
    
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    fetch(`/api/delete_platform/${platformToDelete.id}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Hide the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deletePlatformModal'));
            modal.hide();
            
            showAlert('success', result.message);
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showAlert('danger', result.error || 'Failed to delete platform connection');
        }
    })
    .catch(error => {
        console.error('Error:', encodeURIComponent(error.toString()));
        showAlert('danger', 'Network error occurred while deleting platform');
    })
    .finally(() => {
        // Hide loading state
        confirmButton.disabled = false;
        spinner.classList.add('d-none');
        platformToDelete = null;
    });
}

function showLoadingModal(message) {
    const loadingModal = document.getElementById('loadingModal');
    const loadingMessage = document.getElementById('loadingMessage');
    
    if (loadingMessage) {
        loadingMessage.textContent = message;
    }
    
    const modal = new bootstrap.Modal(loadingModal);
    modal.show();
}

function hideLoadingModal() {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal) {
        const modal = bootstrap.Modal.getInstance(loadingModal);
        if (modal) {
            modal.hide();
        }
    }
}

function showAlert(type, message) {
    // Sanitize inputs to prevent XSS
    const sanitizedType = type.replace(/[^a-zA-Z-]/g, '');
    const sanitizedMessage = document.createTextNode(message).textContent;
    
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${sanitizedType} alert-dismissible fade show animate-slide-in`;
    
    // Create message element safely
    const messageSpan = document.createElement('span');
    messageSpan.textContent = sanitizedMessage;
    
    // Create close button safely
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');
    
    alertDiv.appendChild(messageSpan);
    alertDiv.appendChild(closeButton);
    
    // Insert at the top of the container or body if container not found
    const container = document.querySelector('.container-fluid') || document.body;
    if (container.firstChild) {
        container.insertBefore(alertDiv, container.firstChild);
    } else {
        container.appendChild(alertDiv);
    }
    
    // Scroll to top to show alert
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Auto-dismiss after appropriate time for better UX
    const dismissTime = type === 'info' ? 10000 : 7000;
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.classList.add('fade');
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 300);
        }
    }, dismissTime);
}

// Helper function to update current platform display
function updateCurrentPlatformDisplay(platform) {
    const currentPlatformCard = document.querySelector('.card .card-body');
    if (currentPlatformCard && platform) {
        // Update the current platform display immediately
        const platformIcon = currentPlatformCard.querySelector('.platform-icon i');
        const platformName = currentPlatformCard.querySelector('h6');
        const platformDetails = currentPlatformCard.querySelector('p');
        
        if (platformIcon) {
            platformIcon.className = `bi bi-${platform.platform_type === 'mastodon' ? 'mastodon' : 'image'} fs-2 text-primary`;
        }
        if (platformName) {
            platformName.textContent = platform.name;
        }
        if (platformDetails) {
            platformDetails.innerHTML = `${platform.platform_type.charAt(0).toUpperCase() + platform.platform_type.slice(1)} - ${platform.instance_url}`;
        }
    }
}

// Helper function to update platform status indicators
function updatePlatformStatus(platformId, status) {
    const platformCard = document.querySelector(`[data-platform-id="${platformId}"]`);
    if (!platformCard) return;
    
    const statusBadge = platformCard.querySelector('.platform-status .badge');
    if (statusBadge) {
        statusBadge.className = 'badge';
        switch (status) {
            case 'active':
                statusBadge.classList.add('bg-success');
                statusBadge.innerHTML = '<i class="bi bi-check-circle"></i> Active';
                break;
            case 'inactive':
                statusBadge.classList.add('bg-warning');
                statusBadge.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Connection Issue';
                break;
            case 'error':
                statusBadge.classList.add('bg-danger');
                statusBadge.innerHTML = '<i class="bi bi-x-circle"></i> Error';
                break;
        }
    }
}