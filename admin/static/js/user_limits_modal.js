// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * User Limits Modal JavaScript
 * Handles user search, selection, and limits configuration
 */

let searchTimeout;
let selectedUser = null;

/**
 * Get CSRF token from meta tag
 */
function getCSRFToken() {
    try {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (!csrfMeta) {
            console.error('CSRF token not found in page meta tags');
            return '';
        }
        const token = csrfMeta.getAttribute('content');
        if (!token) {
            console.error('CSRF token meta tag found but content is empty');
            return '';
        }
        return token;
    } catch (error) {
        console.error('Error getting CSRF token:', error);
        return '';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initializeUserLimitsModal();
});

// Global function to show the user limits modal (called from dashboard button)
function showUserLimitsModal() {
    const modal = new bootstrap.Modal(document.getElementById('userLimitsModal'));
    modal.show();
}

function initializeUserLimitsModal() {
    const userSearch = document.getElementById('userSearch');
    const userSearchResults = document.getElementById('userSearchResults');
    
    if (userSearch) {
        // Add event listeners for user search
        userSearch.addEventListener('input', handleUserSearch);
        userSearch.addEventListener('focus', handleUserSearchFocus);
        userSearch.addEventListener('blur', handleUserSearchBlur);
        
        // Close search results when clicking outside
        document.addEventListener('click', function(e) {
            if (!userSearch.contains(e.target) && !userSearchResults.contains(e.target)) {
                hideSearchResults();
            }
        });
    }
    
    // Initialize modal event listeners
    const userLimitsModal = document.getElementById('userLimitsModal');
    if (userLimitsModal) {
        userLimitsModal.addEventListener('hidden.bs.modal', resetModal);
    }
}

function handleUserSearch(e) {
    const query = e.target.value.trim();
    
    // Clear previous timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    // Debounce search
    searchTimeout = setTimeout(() => {
        if (query.length >= 2) {
            searchUsers(query);
        } else {
            hideSearchResults();
            showDefaultUsersList();
        }
    }, 300);
}

function handleUserSearchFocus(e) {
    const query = e.target.value.trim();
    if (query.length >= 2) {
        showSearchResults();
    }
}

function handleUserSearchBlur(e) {
    // Delay hiding to allow clicking on results
    setTimeout(() => {
        if (!document.activeElement || !document.getElementById('userSearchResults').contains(document.activeElement)) {
            hideSearchResults();
        }
    }, 150);
}

async function searchUsers(query) {
    try {
        showSearchLoading();
        
        const response = await fetch(`/admin/api/users/search?q=${encodeURIComponent(query)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            displaySearchResults(data.users);
        } else {
            showSearchError(data.error || 'Failed to search users');
        }
        
    } catch (error) {
        console.error('Error searching users:', error);
        showSearchError('Failed to search users. Please try again.');
    }
}

function displaySearchResults(users) {
    const resultsContainer = document.getElementById('userSearchResults');
    const usersList = document.getElementById('usersList');
    
    if (users.length === 0) {
        resultsContainer.innerHTML = `
            <div class="dropdown-item-text text-muted">
                <i class="bi bi-search"></i> No users found
            </div>
        `;
    } else {
        resultsContainer.innerHTML = users.map(user => `
            <button type="button" class="dropdown-item d-flex justify-content-between align-items-center" 
                    onclick="selectUserFromSearch(${user.id}, '${escapeHtml(user.username)}', '${escapeHtml(user.email)}', '${user.role}')">
                <div>
                    <strong>${escapeHtml(user.username)}</strong>
                    <br><small class="text-muted">${escapeHtml(user.email)}</small>
                </div>
                <span class="badge bg-${getRoleBadgeClass(user.role)}">${user.role}</span>
            </button>
        `).join('');
    }
    
    showSearchResults();
    
    // Also update the main users list
    usersList.innerHTML = users.map(user => createUserListItem(user)).join('');
}

function selectUserFromSearch(userId, username, email, role) {
    hideSearchResults();
    document.getElementById('userSearch').value = `${username} (${email})`;
    selectUser(userId, username, email, role);
}

async function selectUser(userId, username, email, role) {
    selectedUser = { id: userId, username, email, role };
    
    // Update UI to show selected user
    document.getElementById('selectedUserId').value = userId;
    document.getElementById('selectedUserName').textContent = username;
    document.getElementById('selectedUserEmail').textContent = email;
    
    // Show the form and buttons
    document.getElementById('userLimitsForm').style.display = 'block';
    document.getElementById('noUserSelected').style.display = 'none';
    document.getElementById('saveUserLimits').style.display = 'inline-block';
    document.getElementById('resetUserLimits').style.display = 'inline-block';
    
    // Load current user limits
    await loadUserLimits(userId);
}

async function loadUserLimits(userId) {
    try {
        showFormLoading(true);
        
        const response = await fetch(`/admin/api/users/${userId}/limits`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.limits) {
            populateFormWithLimits(data.limits);
        } else {
            // Use default limits if none exist
            populateFormWithDefaults();
        }
        
    } catch (error) {
        console.error('Error loading user limits:', error);
        showAlert('Failed to load user limits. Using default values.', 'warning');
        populateFormWithDefaults();
    } finally {
        showFormLoading(false);
    }
}

function populateFormWithLimits(limits) {
    document.getElementById('maxConcurrentJobs').value = limits.max_concurrent_jobs || 2;
    document.getElementById('maxDailyJobs').value = limits.max_daily_jobs || 10;
    document.getElementById('maxImagesPerJob').value = limits.max_images_per_job || 50;
    document.getElementById('jobPriority').value = limits.default_priority || 'normal';
    document.getElementById('jobTimeoutMinutes').value = limits.job_timeout_minutes || 30;
    document.getElementById('cooldownMinutes').value = limits.cooldown_minutes || 5;
    
    // Permissions
    document.getElementById('canCreateJobs').checked = limits.can_create_jobs !== false;
    document.getElementById('canCancelOwnJobs').checked = limits.can_cancel_own_jobs !== false;
    document.getElementById('canViewJobHistory').checked = limits.can_view_job_history !== false;
    document.getElementById('canRetryFailedJobs').checked = limits.can_retry_failed_jobs !== false;
    
    // Notes
    document.getElementById('userNotes').value = limits.admin_notes || '';
}

function populateFormWithDefaults() {
    document.getElementById('maxConcurrentJobs').value = 2;
    document.getElementById('maxDailyJobs').value = 10;
    document.getElementById('maxImagesPerJob').value = 50;
    document.getElementById('jobPriority').value = 'normal';
    document.getElementById('jobTimeoutMinutes').value = 30;
    document.getElementById('cooldownMinutes').value = 5;
    
    // Permissions - all enabled by default
    document.getElementById('canCreateJobs').checked = true;
    document.getElementById('canCancelOwnJobs').checked = true;
    document.getElementById('canViewJobHistory').checked = true;
    document.getElementById('canRetryFailedJobs').checked = true;
    
    // Clear notes
    document.getElementById('userNotes').value = '';
}

async function saveUserLimits() {
    if (!selectedUser) {
        showAlert('No user selected', 'error');
        return;
    }
    
    const formData = {
        max_concurrent_jobs: parseInt(document.getElementById('maxConcurrentJobs').value),
        max_daily_jobs: parseInt(document.getElementById('maxDailyJobs').value),
        max_images_per_job: parseInt(document.getElementById('maxImagesPerJob').value),
        default_priority: document.getElementById('jobPriority').value,
        job_timeout_minutes: parseInt(document.getElementById('jobTimeoutMinutes').value),
        cooldown_minutes: parseInt(document.getElementById('cooldownMinutes').value),
        can_create_jobs: document.getElementById('canCreateJobs').checked,
        can_cancel_own_jobs: document.getElementById('canCancelOwnJobs').checked,
        can_view_job_history: document.getElementById('canViewJobHistory').checked,
        can_retry_failed_jobs: document.getElementById('canRetryFailedJobs').checked,
        admin_notes: document.getElementById('userNotes').value.trim()
    };
    
    try {
        showSaveLoading(true);
        
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken()
        };
        
        const response = await fetch(`/admin/api/users/${selectedUser.id}/limits`, {
            method: 'PUT',
            headers: headers,
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`Limits updated successfully for ${selectedUser.username}`, 'success');
            
            // Close modal after short delay
            setTimeout(() => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('userLimitsModal'));
                if (modal) {
                    modal.hide();
                }
            }, 1500);
        } else {
            showAlert(data.error || 'Failed to save user limits', 'error');
        }
        
    } catch (error) {
        console.error('Error saving user limits:', error);
        showAlert('Failed to save user limits. Please try again.', 'error');
    } finally {
        showSaveLoading(false);
    }
}

function resetUserLimits() {
    if (!selectedUser) {
        return;
    }
    
    if (confirm(`Reset limits for ${selectedUser.username} to default values?`)) {
        populateFormWithDefaults();
        showAlert('Limits reset to default values', 'info');
    }
}

// Utility functions
function showSearchResults() {
    document.getElementById('userSearchResults').style.display = 'block';
}

function hideSearchResults() {
    document.getElementById('userSearchResults').style.display = 'none';
}

function showSearchLoading() {
    document.getElementById('userSearchResults').innerHTML = `
        <div class="dropdown-item-text text-center">
            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
            Searching users...
        </div>
    `;
    showSearchResults();
}

function showSearchError(message) {
    document.getElementById('userSearchResults').innerHTML = `
        <div class="dropdown-item-text text-danger">
            <i class="bi bi-exclamation-triangle"></i> ${escapeHtml(message)}
        </div>
    `;
    showSearchResults();
}

function showDefaultUsersList() {
    document.getElementById('usersList').innerHTML = `
        <div class="text-center text-muted py-3">
            <i class="bi bi-search"></i>
            <p class="mb-0">Start typing to search for users</p>
        </div>
    `;
}

function showFormLoading(show) {
    const form = document.getElementById('limitsConfigForm');
    const inputs = form.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        input.disabled = show;
    });
    
    if (show) {
        form.style.opacity = '0.6';
    } else {
        form.style.opacity = '1';
    }
}

function showSaveLoading(show) {
    const saveBtn = document.getElementById('saveUserLimits');
    const resetBtn = document.getElementById('resetUserLimits');
    
    if (show) {
        saveBtn.disabled = true;
        resetBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
    } else {
        saveBtn.disabled = false;
        resetBtn.disabled = false;
        saveBtn.innerHTML = '<i class="bi bi-save"></i> Save Limits';
    }
}

function resetModal() {
    selectedUser = null;
    
    // Reset form
    document.getElementById('userSearch').value = '';
    document.getElementById('userLimitsForm').style.display = 'none';
    document.getElementById('noUserSelected').style.display = 'block';
    document.getElementById('saveUserLimits').style.display = 'none';
    document.getElementById('resetUserLimits').style.display = 'none';
    
    // Reset search results
    hideSearchResults();
    showDefaultUsersList();
}

function createUserListItem(user) {
    return `
        <div class="user-item p-2 border-bottom" style="cursor: pointer;" 
             onclick="selectUser(${user.id}, '${escapeHtml(user.username)}', '${escapeHtml(user.email)}', '${user.role}')">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${escapeHtml(user.username)}</strong>
                    <br><small class="text-muted">${escapeHtml(user.email)}</small>
                </div>
                <div>
                    <span class="badge bg-${getRoleBadgeClass(user.role)}">${user.role}</span>
                    <br><small class="text-muted">${user.is_active ? 'Active' : 'Inactive'}</small>
                </div>
            </div>
        </div>
    `;
}

function getRoleBadgeClass(role) {
    switch (role) {
        case 'admin': return 'danger';
        case 'reviewer': return 'warning';
        case 'viewer': return 'secondary';
        default: return 'secondary';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showAlert(message, type = 'info') {
    // Try to use the existing admin alert system
    if (typeof window.showAdminAlert === 'function') {
        window.showAdminAlert(message, type);
    } else if (document.querySelector('.alert-container')) {
        // Create Bootstrap alert if container exists
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.alert-container') || document.querySelector('main');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    } else {
        // Fallback to browser alert
        alert(message);
    }
}