// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * CSP-Compliant Event Handlers
 * Replaces inline event handlers with proper JavaScript event listeners
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Generic click handlers
    setupGenericClickHandlers();
    
    // Form change handlers
    setupFormChangeHandlers();
    
    // Platform management handlers
    setupPlatformManagementHandlers();
    
    // Caption generation handlers
    setupCaptionGenerationHandlers();
    
    // Profile management handlers
    setupProfileHandlers();
    
    // Admin job management handlers
    setupAdminJobHandlers();
    
    // Error page handlers
    setupErrorPageHandlers();
});

function setupGenericClickHandlers() {
    // Reload page buttons
    document.querySelectorAll('[data-action="reload"]').forEach(button => {
        button.addEventListener('click', function() {
            window.location.reload();
        });
    });
    
    // Go back buttons
    document.querySelectorAll('[data-action="go-back"]').forEach(button => {
        button.addEventListener('click', function() {
            window.history.back();
        });
    });
    
    // Copy to clipboard buttons
    document.querySelectorAll('[data-action="copy-clipboard"]').forEach(button => {
        button.addEventListener('click', function() {
            const text = this.getAttribute('data-copy-text');
            copyToClipboard(text);
        });
    });
}

function setupFormChangeHandlers() {
    // Auto-submit forms on select change
    document.querySelectorAll('select[data-auto-submit="true"]').forEach(select => {
        select.addEventListener('change', function() {
            this.form.submit();
        });
    });
}f
unction setupPlatformManagementHandlers() {
    // Switch platform buttons
    document.querySelectorAll('[data-action="switch-platform"]').forEach(button => {
        button.addEventListener('click', function() {
            const platformId = this.getAttribute('data-platform-id');
            const platformName = this.getAttribute('data-platform-name');
            switchPlatform(platformId, platformName);
        });
    });
    
    // Edit platform buttons
    document.querySelectorAll('[data-action="edit-platform"]').forEach(button => {
        button.addEventListener('click', function() {
            const platformId = this.getAttribute('data-platform-id');
            editPlatform(platformId);
        });
    });
    
    // Test connection buttons
    document.querySelectorAll('[data-action="test-connection"]').forEach(button => {
        button.addEventListener('click', function() {
            const platformId = this.getAttribute('data-platform-id');
            const platformName = this.getAttribute('data-platform-name');
            testConnection(platformId, platformName);
        });
    });
    
    // Delete platform buttons
    document.querySelectorAll('[data-action="delete-platform"]').forEach(button => {
        button.addEventListener('click', function() {
            const platformId = this.getAttribute('data-platform-id');
            const platformName = this.getAttribute('data-platform-name');
            deletePlatform(platformId, platformName);
        });
    });
    
    // Confirm platform deletion
    document.querySelectorAll('[data-action="confirm-platform-deletion"]').forEach(button => {
        button.addEventListener('click', function() {
            confirmPlatformDeletion();
        });
    });
}

function setupCaptionGenerationHandlers() {
    // Cancel task buttons
    document.querySelectorAll('[data-action="cancel-task"]').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            cancelTask(taskId);
        });
    });
    
    // Filter tasks buttons
    document.querySelectorAll('[data-action="filter-tasks"]').forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');
            filterTasks(filter);
        });
    });
    
    // Retry task buttons
    document.querySelectorAll('[data-action="retry-task"]').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            retryTask(taskId);
        });
    });
    
    // Show error details buttons
    document.querySelectorAll('[data-action="show-error-details"]').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            showErrorDetails(taskId);
        });
    });
    
    // Cancel generation buttons
    document.querySelectorAll('[data-action="cancel-generation"]').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            cancelGeneration(taskId);
        });
    });
    
    // Task item click handlers
    document.querySelectorAll('.task-item.clickable').forEach(item => {
        item.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            // Add your task details view logic here
            console.log('Task clicked:', taskId);
        });
    });
}

function setupProfileHandlers() {
    // Toggle edit mode buttons
    document.querySelectorAll('[data-action="toggle-edit-mode"]').forEach(button => {
        button.addEventListener('click', function() {
            toggleEditMode();
        });
    });
}

function setupAdminJobHandlers() {
    // Load job details buttons
    document.querySelectorAll('[data-action="load-job-details"]').forEach(button => {
        button.addEventListener('click', function() {
            const jobId = this.getAttribute('data-job-id');
            loadJobDetails(jobId);
        });
    });
}

function setupErrorPageHandlers() {
    // Error page specific handlers are already covered by generic handlers
    // using data-action attributes
}// 
Utility functions (these should already exist in your codebase)
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            console.log('Text copied to clipboard');
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            console.log('Text copied to clipboard (fallback)');
        } catch (err) {
            console.error('Failed to copy text (fallback): ', err);
        }
        document.body.removeChild(textArea);
    }
}

// Placeholder functions - these should be implemented based on your existing code
function switchPlatform(platformId, platformName) {
    console.log('Switch platform:', platformId, platformName);
    // Implement your platform switching logic
}

function editPlatform(platformId) {
    console.log('Edit platform:', platformId);
    // Implement your platform editing logic
}

function testConnection(platformId, platformName) {
    console.log('Test connection:', platformId, platformName);
    // Implement your connection testing logic
}

function deletePlatform(platformId, platformName) {
    console.log('Delete platform:', platformId, platformName);
    // Implement your platform deletion logic
}

function confirmPlatformDeletion() {
    console.log('Confirm platform deletion');
    // Implement your platform deletion confirmation logic
}

function cancelTask(taskId) {
    console.log('Cancel task:', taskId);
    // Implement your task cancellation logic
}

function filterTasks(filter) {
    console.log('Filter tasks:', filter);
    // Implement your task filtering logic
}

function retryTask(taskId) {
    console.log('Retry task:', taskId);
    // Implement your task retry logic
}

function showErrorDetails(taskId) {
    console.log('Show error details:', taskId);
    // Implement your error details display logic
}

function cancelGeneration(taskId) {
    console.log('Cancel generation:', taskId);
    // Implement your generation cancellation logic
}

function toggleEditMode() {
    console.log('Toggle edit mode');
    // Implement your edit mode toggle logic
}

function loadJobDetails(jobId) {
    console.log('Load job details:', jobId);
    // Implement your job details loading logic
}