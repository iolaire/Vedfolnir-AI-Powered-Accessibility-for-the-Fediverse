// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Admin Job Management JavaScript
 * Handles admin job management interface functionality including context switching,
 * job actions, and real-time updates.
 */

// Global state
let adminJobManagement = {
    autoRefreshInterval: null,
    autoRefreshActive: false,
    currentAdminMode: true,
    websocket: null
};

/**
 * Initialize admin job management interface
 */
function initializeJobManagement() {
    console.log('Initializing admin job management...');
    
    // Initialize context switcher if available
    if (window.adminContextSwitcher) {
        adminJobManagement.currentAdminMode = window.adminContextSwitcher.getCurrentMode();
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize WebSocket connection for real-time updates
    initializeWebSocket();
    
    // Load initial data
    refreshJobData();
    
    console.log('Admin job management initialized');
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Listen for admin mode changes
    window.addEventListener('adminModeChanged', function(event) {
        adminJobManagement.currentAdminMode = event.detail.adminMode;
        handleAdminModeChange(event.detail.adminMode);
    });
    
    // Listen for job updates
    window.addEventListener('jobUpdated', function(event) {
        handleJobUpdate(event.detail);
    });
    
    // Listen for notifications
    window.addEventListener('adminNotification', function(event) {
        handleAdminNotification(event.detail);
    });
}

/**
 * Initialize WebSocket connection for real-time updates
 */
function initializeWebSocket() {
    try {
        // Use unified WebSocket connection instead of creating new one
        if (window.VedfolnirWS && window.VedfolnirWS.socket) {
            adminJobManagement.websocket = window.VedfolnirWS.socket;
            setupJobWebSocketHandlers();
            console.log('Admin job management using unified WebSocket connection');
            updateConnectionStatus(true);
        } else {
            // Wait for unified WebSocket to be available
            const checkForWebSocket = () => {
                if (window.VedfolnirWS && window.VedfolnirWS.socket) {
                    adminJobManagement.websocket = window.VedfolnirWS.socket;
                    setupJobWebSocketHandlers();
                    console.log('Admin job management connected to unified WebSocket');
                    updateConnectionStatus(true);
                } else {
                    setTimeout(checkForWebSocket, 100);
                }
            };
            checkForWebSocket();
        }
        
    } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
        updateConnectionStatus(false);
    }
}

function setupJobWebSocketHandlers() {
    if (!adminJobManagement.websocket) return;
    
    adminJobManagement.websocket.on('connect', function() {
        console.log('Admin job management WebSocket connected');
        updateConnectionStatus(true);
    });
    
    adminJobManagement.websocket.on('job_update', function(data) {
        handleWebSocketMessage(data);
    });
    
    adminJobManagement.websocket.on('disconnect', function() {
        console.log('Admin job management WebSocket disconnected');
        updateConnectionStatus(false);
    });
    
    adminJobManagement.websocket.on('error', function(error) {
        console.error('Admin job management WebSocket error:', error);
        updateConnectionStatus(false);
    });
}

/**
 * Handle WebSocket messages
 */
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'job_update':
            updateJobInList(data.job);
            break;
        case 'job_completed':
            handleJobCompletion(data.job);
            break;
        case 'job_failed':
            handleJobFailure(data.job);
            break;
        case 'system_alert':
            handleSystemAlert(data.alert);
            break;
        default:
            console.log('Unknown WebSocket message type:', data.type);
    }
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connectionStatus');
    if (indicator) {
        if (connected) {
            indicator.className = 'real-time-indicator';
            indicator.title = 'Real-time updates active';
        } else {
            indicator.className = 'real-time-indicator disconnected';
            indicator.title = 'Connection lost - using fallback refresh';
        }
    }
}

/**
 * Handle admin mode changes
 */
function handleAdminModeChange(adminMode) {
    const adminSection = document.getElementById('adminJobSection');
    const contextWarningText = document.getElementById('contextWarningText');
    
    if (adminMode) {
        if (adminSection) adminSection.style.display = 'block';
        if (contextWarningText) {
            contextWarningText.innerHTML = 'You are currently in <strong>Administrator</strong> mode. Administrative actions will affect all users and be logged as admin interventions.';
        }
    } else {
        if (adminSection) adminSection.style.display = 'none';
        if (contextWarningText) {
            contextWarningText.innerHTML = 'You are currently in <strong>Personal</strong> mode. You can only manage your own jobs in this mode.';
        }
    }
    
    // Refresh data for new context
    refreshJobData();
}

/**
 * Refresh job data
 */
function refreshJobData() {
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('admin_mode', adminJobManagement.currentAdminMode);
    
    fetch(currentUrl.href, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Failed to refresh job data');
    })
    .then(data => {
        updateJobLists(data);
        updateJobStats(data.job_stats);
    })
    .catch(error => {
        console.error('Error refreshing job data:', error);
        if (window.errorHandler) {
            window.errorHandler.showNotification('Failed to refresh job data', 'warning');
        }
    });
}

/**
 * Update job lists with new data
 */
function updateJobLists(data) {
    // Update admin jobs list
    if (data.admin_jobs) {
        updateAdminJobsList(data.admin_jobs);
    }
    
    // Update personal jobs list
    if (data.personal_jobs) {
        updatePersonalJobsList(data.personal_jobs);
    }
}

/**
 * Update admin jobs list
 */
function updateAdminJobsList(jobs) {
    const container = document.getElementById('adminJobsList');
    if (!container) return;
    
    if (jobs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <h5>No Jobs Requiring Admin Management</h5>
                <p>All jobs are running normally. Check back if users report issues.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = jobs.map(job => renderAdminJobCard(job)).join('');
}

/**
 * Update personal jobs list
 */
function updatePersonalJobsList(jobs) {
    const container = document.getElementById('personalJobsList');
    if (!container) return;
    
    if (jobs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-person-plus"></i>
                <h5>No Personal Jobs</h5>
                <p>You haven't started any caption generation jobs yet.</p>
                <a href="/caption_generation" class="btn btn-primary">
                    <i class="bi bi-plus-circle"></i> Start Your First Job
                </a>
            </div>
        `;
        return;
    }
    
    container.innerHTML = jobs.map(job => renderPersonalJobCard(job)).join('');
}

/**
 * Render admin job card
 */
function renderAdminJobCard(job) {
    const statusColor = getStatusColor(job.status);
    const progressPercentage = job.progress_percentage || 0;
    
    return `
        <div class="job-card admin-managed" data-job-id="${job.task_id}" data-job-type="admin">
            <div class="row">
                <div class="col-md-8">
                    <div class="d-flex align-items-center mb-2">
                        <h6 class="mb-0">
                            <code class="small">${job.task_id.substring(0, 8)}...</code>
                            <span class="badge bg-${statusColor}">${job.status}</span>
                            ${job.admin_managed ? '<span class="admin-action-badge">ADMIN MANAGED</span>' : ''}
                        </h6>
                    </div>
                    <div class="row">
                        <div class="col-sm-6">
                            <small><strong>User:</strong> ${job.username} (${job.user_email})</small><br>
                            <small><strong>Platform:</strong> ${job.platform_name} (${job.platform_type})</small>
                        </div>
                        <div class="col-sm-6">
                            <small><strong>Started:</strong> ${formatDateTime(job.created_at)}</small><br>
                            <small><strong>Progress:</strong> ${progressPercentage}% - ${job.current_step}</small>
                        </div>
                    </div>
                    ${job.admin_notes ? `
                        <div class="mt-2">
                            <small class="text-muted">
                                <i class="bi bi-sticky"></i> <strong>Admin Notes:</strong> ${job.admin_notes}
                            </small>
                        </div>
                    ` : ''}
                </div>
                <div class="col-md-4">
                    <div class="job-actions">
                        ${renderAdminJobActions(job)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Render personal job card
 */
function renderPersonalJobCard(job) {
    const statusColor = getStatusColor(job.status);
    const progressPercentage = job.progress_percentage || 0;
    
    return `
        <div class="job-card personal-managed" data-job-id="${job.task_id}" data-job-type="personal">
            <div class="row">
                <div class="col-md-8">
                    <div class="d-flex align-items-center mb-2">
                        <h6 class="mb-0">
                            <code class="small">${job.task_id.substring(0, 8)}...</code>
                            <span class="badge bg-${statusColor}">${job.status}</span>
                            <span class="personal-action-badge">YOUR JOB</span>
                        </h6>
                    </div>
                    <div class="row">
                        <div class="col-sm-6">
                            <small><strong>Platform:</strong> ${job.platform_name} (${job.platform_type})</small><br>
                            <small><strong>Settings:</strong> ${job.max_posts || 'Default'} posts, ${job.processing_delay || 'Default'}s delay</small>
                        </div>
                        <div class="col-sm-6">
                            <small><strong>Started:</strong> ${formatDateTime(job.created_at)}</small><br>
                            <small><strong>Progress:</strong> ${progressPercentage}% - ${job.current_step}</small>
                        </div>
                    </div>
                    ${job.results ? `
                        <div class="mt-2">
                            <small class="text-success">
                                <i class="bi bi-check-circle"></i> ${job.results.captions_generated || 0} captions generated, 
                                ${job.results.images_processed || 0} images processed
                            </small>
                        </div>
                    ` : ''}
                </div>
                <div class="col-md-4">
                    <div class="job-actions">
                        ${renderPersonalJobActions(job)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Render admin job actions
 */
function renderAdminJobActions(job) {
    let actions = [];
    
    if (['running', 'queued'].includes(job.status)) {
        actions.push(`
            <button class="btn btn-outline-danger btn-sm" 
                    data-action="admin-cancel-job" data-task-id="${job.task_id}" data-username="${job.username}"
                    title="Cancel Job (Admin Action)">
                <i class="bi bi-stop-circle"></i> Cancel
            </button>
        `);
        actions.push(`
            <button class="btn btn-outline-warning btn-sm" 
                    data-action="set-priority" data-task-id="${job.task_id}" data-priority="high"
                    title="Set High Priority">
                <i class="bi bi-arrow-up-circle"></i> Priority
            </button>
        `);
    }
    
    if (job.status === 'failed') {
        actions.push(`
            <button class="btn btn-outline-success btn-sm" 
                    data-action="admin-restart-job" data-task-id="${job.task_id}"
                    title="Restart Job (Admin Action)">
                <i class="bi bi-arrow-clockwise"></i> Restart
            </button>
        `);
    }
    
    actions.push(`
        <button class="btn btn-outline-info btn-sm" 
                data-action="view-job-details" data-task-id="${job.task_id}" data-is-admin="true"
                title="View Details">
            <i class="bi bi-eye"></i> Details
        </button>
    `);
    
    actions.push(`
        <button class="btn btn-outline-secondary btn-sm" 
                data-action="add-admin-notes" data-task-id="${job.task_id}"
                title="Add Admin Notes">
            <i class="bi bi-sticky"></i> Notes
        </button>
    `);
    
    return actions.join('');
}

/**
 * Render personal job actions
 */
function renderPersonalJobActions(job) {
    let actions = [];
    
    if (['running', 'queued'].includes(job.status)) {
        actions.push(`
            <button class="btn btn-outline-danger btn-sm" 
                    data-action="personal-cancel-job" data-task-id="${job.task_id}"
                    title="Cancel Your Job">
                <i class="bi bi-stop-circle"></i> Cancel
            </button>
        `);
    }
    
    if (job.status === 'failed') {
        actions.push(`
            <button class="btn btn-outline-success btn-sm" 
                    data-action="personal-retry-job" data-task-id="${job.task_id}"
                    title="Retry Your Job">
                <i class="bi bi-arrow-clockwise"></i> Retry
            </button>
        `);
    }
    
    if (job.status === 'completed') {
        actions.push(`
            <a href="/review" class="btn btn-outline-primary btn-sm"
               title="Review Generated Captions">
                <i class="bi bi-eye-fill"></i> Review
            </a>
        `);
    }
    
    actions.push(`
        <button class="btn btn-outline-info btn-sm" 
                data-action="view-job-details" data-task-id="${job.task_id}" data-is-admin="false"
                title="View Details">
            <i class="bi bi-eye"></i> Details
        </button>
    `);
    
    return actions.join('');
}

/**
 * Update job statistics
 */
function updateJobStats(stats) {
    const elements = {
        'totalActiveJobs': stats.total_active || 0,
        'personalActiveJobs': stats.personal_active || 0,
        'adminManagedJobs': stats.admin_managed || 0,
        'queuedJobs': stats.queued || 0
    };
    
    Object.keys(elements).forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = elements[id];
        }
    });
}

/**
 * Update individual job in list
 */
function updateJobInList(job) {
    const jobCard = document.querySelector(`[data-job-id="${job.task_id}"]`);
    if (jobCard) {
        const jobType = jobCard.getAttribute('data-job-type');
        if (jobType === 'admin') {
            jobCard.outerHTML = renderAdminJobCard(job);
        } else {
            jobCard.outerHTML = renderPersonalJobCard(job);
        }
    }
}

/**
 * Handle job completion
 */
function handleJobCompletion(job) {
    updateJobInList(job);
    
    // Show notification if it's a job we're managing
    if (window.adminNotificationSystem) {
        window.adminNotificationSystem.addNotification({
            title: 'Job Completed',
            message: `Job ${job.task_id.substring(0, 8)}... completed successfully`,
            type: 'job_completed',
            severity: 'success',
            job_id: job.task_id
        });
    }
}

/**
 * Handle job failure
 */
function handleJobFailure(job) {
    updateJobInList(job);
    
    // Show notification
    if (window.adminNotificationSystem) {
        window.adminNotificationSystem.addNotification({
            title: 'Job Failed',
            message: `Job ${job.task_id.substring(0, 8)}... failed: ${job.error_message || 'Unknown error'}`,
            type: 'job_failed',
            severity: 'warning',
            job_id: job.task_id
        });
    }
}

/**
 * Handle system alerts
 */
function handleSystemAlert(alert) {
    if (window.adminNotificationSystem) {
        window.adminNotificationSystem.addNotification({
            title: alert.title || 'System Alert',
            message: alert.message,
            type: 'system_alert',
            severity: alert.severity || 'warning'
        });
    }
}

/**
 * Handle admin notifications
 */
function handleAdminNotification(notification) {
    if (window.adminNotificationSystem) {
        window.adminNotificationSystem.addNotification(notification);
    }
}

/**
 * Get status color for badges
 */
function getStatusColor(status) {
    const colorMap = {
        'running': 'primary',
        'queued': 'secondary',
        'completed': 'success',
        'failed': 'danger',
        'cancelled': 'warning'
    };
    return colorMap[status] || 'secondary';
}

/**
 * Format datetime for display
 */
function formatDateTime(dateString) {
    if (!dateString) return 'Unknown';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (error) {
        return 'Invalid date';
    }
}

/**
 * Toggle auto-refresh
 */
function toggleAutoRefresh() {
    if (adminJobManagement.autoRefreshActive) {
        // Stop adaptive polling if available
        if (window.adaptivePollingManager) {
            window.adaptivePollingManager.stopPolling('admin-job-refresh');
            console.log('Stopped adaptive polling for admin job refresh');
        }
        
        // Stop traditional polling
        clearInterval(adminJobManagement.autoRefreshInterval);
        adminJobManagement.autoRefreshActive = false;
        document.getElementById('autoRefreshIcon').className = 'bi bi-play-circle';
        document.getElementById('autoRefreshText').textContent = 'Start Auto-refresh';
    } else {
        // Use adaptive polling if available
        if (window.adaptivePollingManager) {
            console.log('Using AdaptivePollingManager for admin job refresh');
            
            window.adaptivePollingManager.startPolling('admin-job-refresh', {
                type: 'admin_job_management',
                priority: 2, // Medium priority
                callback: (status) => {
                    // Refresh job data
                    refreshJobData();
                }
            });
            
            adminJobManagement.autoRefreshActive = true;
            document.getElementById('autoRefreshIcon').className = 'bi bi-pause-circle';
            document.getElementById('autoRefreshText').textContent = 'Stop Auto-refresh (Adaptive)';
        } else {
            // Fallback to traditional polling
            console.log('Using traditional polling for admin job refresh');
            adminJobManagement.autoRefreshInterval = setInterval(refreshJobData, 30000); // 30 seconds
            adminJobManagement.autoRefreshActive = true;
            document.getElementById('autoRefreshIcon').className = 'bi bi-pause-circle';
            document.getElementById('autoRefreshText').textContent = 'Stop Auto-refresh';
        }
    }
}

// Export functions for global access
window.adminJobManagement = adminJobManagement;
window.initializeJobManagement = initializeJobManagement;
window.refreshJobData = refreshJobData;
window.toggleAutoRefresh = toggleAutoRefresh;