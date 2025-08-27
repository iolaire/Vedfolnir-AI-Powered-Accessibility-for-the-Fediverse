// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Admin Dashboard JavaScript
 * Handles real-time job monitoring, WebSocket connections, and admin controls
 */

let websocket = null;
let autoRefreshInterval = null;
let isAutoRefreshEnabled = false;
let selectedJobs = new Set();

/**
 * Initialize the admin dashboard
 */
function initializeDashboard() {
    console.log('Initializing admin dashboard...');

    // Load initial data
    refreshDashboard();

    // Set up event listeners
    setupEventListeners();

    // Initialize tooltips
    initializeTooltips();
}

/**
 * Set up event listeners for dashboard interactions
 */
function setupEventListeners() {
    // Emergency stop confirmation checkbox
    const emergencyCheckbox = document.getElementById('confirmEmergencyStop');
    const emergencyButton = document.getElementById('executeEmergencyStop');

    if (emergencyCheckbox && emergencyButton) {
        emergencyCheckbox.addEventListener('change', function () {
            emergencyButton.disabled = !this.checked;
        });
    }

    // Emergency reason textarea
    const emergencyReason = document.getElementById('emergencyReason');
    if (emergencyReason) {
        emergencyReason.addEventListener('input', function () {
            const checkbox = document.getElementById('confirmEmergencyStop');
            const button = document.getElementById('executeEmergencyStop');
            if (checkbox && button) {
                button.disabled = !checkbox.checked || this.value.trim().length < 10;
            }
        });
    }
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Connect to WebSocket for real-time updates using Socket.IO
 */
function connectWebSocket() {
    // Check if Socket.IO is available
    if (typeof io === 'undefined') {
        console.error('Socket.IO library not loaded. WebSocket functionality disabled.');
        updateConnectionStatus(false);
        showNotification('Socket.IO library not available - real-time updates disabled', 'warning');
        return;
    }
    
    try {
        console.log('Initializing Socket.IO connection...');
        
        // Initialize Socket.IO connection with better configuration
        websocket = io({
            transports: ['polling', 'websocket'], // Allow both transports
            upgrade: true, // Allow upgrade to WebSocket if available
            timeout: 10000, // 10 second timeout
            forceNew: false, // Allow connection reuse
            reconnection: true, // Enable auto-reconnection
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            maxHttpBufferSize: 1e6,
            pingTimeout: 60000,
            pingInterval: 25000,
            withCredentials: true, // Include cookies for authentication
            extraHeaders: {
                // Include CSRF token if available
                'X-CSRF-Token': getCSRFToken()
            }
        });

        websocket.on('connect', function() {
            console.log('✅ WebSocket connected successfully');
            updateConnectionStatus(true);
            showNotification('Real-time updates connected', 'success');
            
            // Join admin dashboard room
            console.log('Joining admin dashboard room...');
            websocket.emit('join_admin_dashboard');
        });

        websocket.on('disconnect', function(reason) {
            console.log('❌ WebSocket disconnected:', reason);
            updateConnectionStatus(false);
            showNotification(`Real-time updates disconnected: ${reason}`, 'warning');
        });

        websocket.on('admin_dashboard_joined', function(data) {
            console.log('✅ Joined admin dashboard:', data.message);
            showNotification('Joined admin dashboard for real-time updates', 'info');
        });

        websocket.on('system_metrics_update', function(data) {
            console.log('📊 System metrics update received:', data);
            handleWebSocketMessage(data);
        });

        websocket.on('job_update', function(data) {
            console.log('🔄 Job update received:', data);
            handleWebSocketMessage(data);
        });

        websocket.on('admin_alert', function(data) {
            console.log('🚨 Admin alert received:', data);
            handleWebSocketMessage(data);
        });

        websocket.on('error', function(error) {
            console.error('❌ WebSocket error:', error);
            updateConnectionStatus(false);
            showNotification(`WebSocket error: ${error}`, 'error');
        });

        websocket.on('connect_error', function(error) {
            console.error('❌ WebSocket connection error:', error);
            updateConnectionStatus(false);
            showNotification(`Connection error: ${error.message || error}`, 'error');
        });

        websocket.on('reconnect', function(attemptNumber) {
            console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts`);
            updateConnectionStatus(true);
            showNotification('Real-time updates reconnected', 'success');
        });

        websocket.on('reconnect_attempt', function(attemptNumber) {
            console.log(`🔄 WebSocket reconnection attempt ${attemptNumber}`);
            showNotification(`Reconnecting... (attempt ${attemptNumber})`, 'info');
        });

        websocket.on('reconnect_error', function(error) {
            console.error('❌ WebSocket reconnection error:', error);
        });

        websocket.on('reconnect_failed', function() {
            console.error('❌ WebSocket reconnection failed after maximum attempts');
            updateConnectionStatus(false);
            showNotification('Failed to reconnect - real-time updates disabled', 'error');
        });

    } catch (error) {
        console.error('❌ Failed to connect WebSocket:', error);
        updateConnectionStatus(false);
        showNotification(`Failed to initialize WebSocket: ${error.message}`, 'error');
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'job_update':
            updateJobInTable(data.job);
            break;
        case 'system_metrics':
            updateSystemMetrics(data.metrics);
            break;
        case 'alert':
            addAlert(data.alert);
            break;
        case 'job_completed':
            handleJobCompletion(data.job);
            break;
        case 'job_failed':
            handleJobFailure(data.job);
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
            indicator.classList.remove('disconnected');
            indicator.title = 'Real-time updates active';
        } else {
            indicator.classList.add('disconnected');
            indicator.title = 'Connection lost - using periodic refresh';
        }
    }
}

/**
 * Check if WebSocket is connected
 */
function isWebSocketConnected() {
    return websocket && websocket.readyState === WebSocket.OPEN;
}

/**
 * Refresh the entire dashboard
 */
function refreshDashboard() {
    console.log('Refreshing dashboard...');

    Promise.all([
        refreshSystemMetrics(),
        refreshActiveJobs(),
        refreshAlerts()
    ]).then(() => {
        console.log('Dashboard refresh complete');
    }).catch(error => {
        console.error('Dashboard refresh failed:', error);
        showNotification('Failed to refresh dashboard', 'error');
    });
}

/**
 * Refresh system metrics
 */
async function refreshSystemMetrics() {
    try {
        console.log('Fetching system metrics...');
        const response = await fetch('/admin/api/system-metrics');
        console.log('System metrics response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('System metrics data:', data);

        if (data.success) {
            updateSystemMetrics(data.metrics);
        } else {
            console.error('System metrics API returned success=false:', data.error);
            throw new Error(data.error || 'API returned success=false');
        }
    } catch (error) {
        console.error('Failed to refresh system metrics:', error);
        showNotification(`Failed to refresh system metrics: ${error.message}`, 'error');
    }
}

/**
 * Update system metrics display
 */
function updateSystemMetrics(metrics) {
    const elements = {
        'activeJobsCount': metrics.active_jobs || 0,
        'completedTodayCount': metrics.completed_today || 0,
        'failedJobsCount': metrics.failed_jobs || 0,
        'systemLoadValue': `${metrics.system_load || 0}%`
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

/**
 * Refresh active jobs table
 */
async function refreshActiveJobs() {
    try {
        const response = await fetch('/admin/api/jobs/active');
        const data = await response.json();

        if (data.success) {
            updateActiveJobsTable(data.jobs);
        }
    } catch (error) {
        console.error('Failed to refresh active jobs:', error);
    }
}

/**
 * Update active jobs table
 */
function updateActiveJobsTable(jobs) {
    const tbody = document.getElementById('activeJobsBody');
    if (!tbody) return;

    if (jobs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted py-4">
                    <i class="bi bi-inbox"></i> No active jobs at this time
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = jobs.map(job => createJobRow(job)).join('');
}

/**
 * Create a job table row
 */
function createJobRow(job) {
    const statusClass = getStatusBadgeClass(job.status);
    const progressPercentage = job.progress_percentage || 0;

    return `
        <tr data-job-id="${job.task_id}">
            <td>
                <input type="checkbox" class="job-checkbox" value="${job.task_id}" 
                       onchange="updateSelectedJobs()">
            </td>
            <td>
                <code class="small">${job.task_id.substring(0, 8)}...</code>
            </td>
            <td>
                <strong>${escapeHtml(job.username)}</strong>
                <br><small class="text-muted">${escapeHtml(job.user_email)}</small>
            </td>
            <td>
                <span class="badge bg-secondary">${escapeHtml(job.platform_type)}</span>
                <br><small>${escapeHtml(job.platform_name)}</small>
            </td>
            <td>
                <span class="badge job-status-badge ${statusClass}">
                    ${job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                </span>
            </td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar" role="progressbar" 
                         style="width: ${progressPercentage}%"
                         aria-valuenow="${progressPercentage}" 
                         aria-valuemin="0" aria-valuemax="100">
                        ${progressPercentage}%
                    </div>
                </div>
                <small class="text-muted">${escapeHtml(job.current_step || 'Initializing')}</small>
            </td>
            <td>
                <small>${formatTime(job.created_at)}</small>
            </td>
            <td>
                <small>${job.estimated_completion || 'Calculating...'}</small>
            </td>
            <td>
                ${createJobActionButtons(job)}
            </td>
        </tr>
    `;
}

/**
 * Get CSS class for status badge
 */
function getStatusBadgeClass(status) {
    const classes = {
        'running': 'bg-primary',
        'queued': 'bg-secondary',
        'completed': 'bg-success',
        'failed': 'bg-danger',
        'cancelled': 'bg-warning'
    };
    return classes[status] || 'bg-warning';
}

/**
 * Create action buttons for a job
 */
function createJobActionButtons(job) {
    let buttons = '';

    if (['running', 'queued'].includes(job.status)) {
        buttons += `
            <button class="btn btn-outline-danger btn-sm" 
                    onclick="cancelJob('${job.task_id}', '${escapeHtml(job.username)}')"
                    title="Cancel Job">
                <i class="bi bi-stop-circle"></i>
            </button>
            <button class="btn btn-outline-warning btn-sm" 
                    onclick="setPriority('${job.task_id}', 'high')"
                    title="Set High Priority">
                <i class="bi bi-arrow-up-circle"></i>
            </button>
        `;
    }

    if (job.status === 'failed') {
        buttons += `
            <button class="btn btn-outline-success btn-sm" 
                    onclick="restartJob('${job.task_id}')"
                    title="Restart Job">
                <i class="bi bi-arrow-clockwise"></i>
            </button>
        `;
    }

    buttons += `
        <button class="btn btn-outline-info btn-sm" 
                onclick="viewJobDetails('${job.task_id}')"
                title="View Details">
            <i class="bi bi-eye"></i>
        </button>
    `;

    return `<div class="job-controls">${buttons}</div>`;
}

/**
 * Update a specific job in the table
 */
function updateJobInTable(job) {
    const row = document.querySelector(`tr[data-job-id="${job.task_id}"]`);
    if (row) {
        const newRow = createJobRow(job);
        row.outerHTML = newRow;
    } else {
        // Job not in table, refresh the entire table
        refreshActiveJobs();
    }
}

/**
 * Handle job completion
 */
function handleJobCompletion(job) {
    updateJobInTable(job);
    showNotification(`Job ${job.task_id.substring(0, 8)} completed successfully`, 'success');
}

/**
 * Handle job failure
 */
function handleJobFailure(job) {
    updateJobInTable(job);
    showNotification(`Job ${job.task_id.substring(0, 8)} failed: ${job.error_message}`, 'error');
}

/**
 * Cancel a job
 */
async function cancelJob(taskId, username) {
    const reason = prompt(`Enter reason for cancelling ${username}'s job:`);
    if (!reason) return;

    try {
        const response = await fetch(`/admin/api/jobs/${taskId}/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ reason })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Job cancelled successfully', 'success');
            refreshActiveJobs();
        } else {
            showNotification(`Failed to cancel job: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to cancel job:', error);
        showNotification('Failed to cancel job', 'error');
    }
}

/**
 * Set job priority
 */
async function setPriority(taskId, priority) {
    try {
        const response = await fetch(`/admin/api/jobs/${taskId}/priority`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ priority })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(`Job priority set to ${priority}`, 'success');
            refreshActiveJobs();
        } else {
            showNotification(`Failed to set priority: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to set priority:', error);
        showNotification('Failed to set priority', 'error');
    }
}

/**
 * Restart a failed job
 */
async function restartJob(taskId) {
    if (!confirm('Are you sure you want to restart this job?')) return;

    try {
        const response = await fetch(`/admin/api/jobs/${taskId}/restart`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Job restarted successfully', 'success');
            refreshActiveJobs();
        } else {
            showNotification(`Failed to restart job: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to restart job:', error);
        showNotification('Failed to restart job', 'error');
    }
}

/**
 * View job details
 */
async function viewJobDetails(taskId) {
    try {
        const response = await fetch(`/admin/api/jobs/${taskId}/details`);
        const data = await response.json();

        if (data.success) {
            showJobDetailsModal(data.job);
        } else {
            showNotification(`Failed to load job details: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to load job details:', error);
        showNotification('Failed to load job details', 'error');
    }
}

/**
 * Show job details modal
 */
function showJobDetailsModal(job) {
    const modal = document.getElementById('jobDetailsModal');
    const content = document.getElementById('jobDetailsContent');
    const template = document.getElementById('jobDetailsTemplate');

    if (!modal || !content || !template) return;

    // Clone template and populate with job data
    const clone = template.content.cloneNode(true);

    // Populate job details
    clone.querySelector('.job-id').textContent = job.task_id;
    clone.querySelector('.job-user').textContent = `${job.username} (${job.user_email})`;
    clone.querySelector('.job-platform').textContent = `${job.platform_name} (${job.platform_type})`;
    clone.querySelector('.job-status').textContent = job.status;
    clone.querySelector('.job-status').className = `badge ${getStatusBadgeClass(job.status)}`;
    clone.querySelector('.job-priority').textContent = job.priority || 'normal';
    clone.querySelector('.job-created').textContent = formatDateTime(job.created_at);
    clone.querySelector('.job-started').textContent = formatDateTime(job.started_at);
    clone.querySelector('.job-duration').textContent = job.duration || 'N/A';

    // Progress information
    const progressBar = clone.querySelector('.job-progress');
    const progressPercentage = job.progress_percentage || 0;
    progressBar.style.width = `${progressPercentage}%`;
    progressBar.setAttribute('aria-valuenow', progressPercentage);
    clone.querySelector('.job-progress-text').textContent = `${progressPercentage}% complete`;

    clone.querySelector('.job-current-step').textContent = job.current_step || 'Initializing';
    clone.querySelector('.job-images-processed').textContent = `${job.images_processed || 0} / ${job.total_images || 0}`;
    clone.querySelector('.job-estimated-completion').textContent = job.estimated_completion || 'Calculating...';

    // Settings
    const settingsDiv = clone.querySelector('.job-settings');
    if (job.settings) {
        settingsDiv.innerHTML = Object.entries(job.settings)
            .map(([key, value]) => `<strong>${key}:</strong> ${value}`)
            .join('<br>');
    }

    // Processing log
    const logDiv = clone.querySelector('.job-log');
    if (job.processing_log && job.processing_log.length > 0) {
        logDiv.innerHTML = job.processing_log
            .map(entry => `<div><small class="text-muted">${formatTime(entry.timestamp)}</small> ${entry.message}</div>`)
            .join('');
    } else {
        logDiv.innerHTML = '<div class="text-muted">No log entries available</div>';
    }

    // Error information
    if (job.error_message) {
        const errorSection = clone.querySelector('.job-error-section');
        const errorDetails = clone.querySelector('.job-error-details');
        errorSection.style.display = 'block';
        errorDetails.innerHTML = `
            <strong>Error:</strong> ${escapeHtml(job.error_message)}<br>
            ${job.error_details ? `<strong>Details:</strong> ${escapeHtml(job.error_details)}` : ''}
        `;
    }

    // Admin notes
    const notesTextarea = clone.querySelector('.job-admin-notes');
    notesTextarea.value = job.admin_notes || '';
    notesTextarea.setAttribute('data-job-id', job.task_id);

    // Replace modal content
    content.innerHTML = '';
    content.appendChild(clone);

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Toggle auto-refresh
 */
function toggleAutoRefresh() {
    const button = document.getElementById('autoRefreshText');
    const icon = document.getElementById('autoRefreshIcon');

    if (isAutoRefreshEnabled) {
        // Stop auto-refresh
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        isAutoRefreshEnabled = false;
        button.textContent = 'Start Auto-refresh';
        icon.className = 'bi bi-play-circle';
    } else {
        // Start auto-refresh
        autoRefreshInterval = setInterval(refreshDashboard, 10000); // 10 seconds
        isAutoRefreshEnabled = true;
        button.textContent = 'Stop Auto-refresh';
        icon.className = 'bi bi-pause-circle';
    }
}

/**
 * Refresh alerts
 */
async function refreshAlerts() {
    try {
        const response = await fetch('/admin/api/alerts');
        const data = await response.json();

        if (data.success) {
            updateAlertsDisplay(data.alerts);
        }
    } catch (error) {
        console.error('Failed to refresh alerts:', error);
    }
}

/**
 * Update alerts display
 */
function updateAlertsDisplay(alerts) {
    const alertsList = document.getElementById('alertsList');
    if (!alertsList) return;

    if (alerts.length === 0) {
        alertsList.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="bi bi-check-circle"></i> No active alerts
            </div>
        `;
        return;
    }

    alertsList.innerHTML = alerts.map(alert => `
        <div class="alert-item alert-${alert.severity}" data-alert-id="${alert.id}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${escapeHtml(alert.title)}</strong>
                    <p class="mb-1">${escapeHtml(alert.message)}</p>
                    <small class="text-muted">${formatDateTime(alert.created_at)}</small>
                </div>
                <button class="btn btn-sm btn-outline-secondary" 
                        onclick="acknowledgeAlert('${alert.id}')"
                        title="Acknowledge">
                    <i class="bi bi-check"></i>
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Add a new alert
 */
function addAlert(alert) {
    const alertsList = document.getElementById('alertsList');
    if (!alertsList) return;

    // Remove "no alerts" message if present
    const noAlertsMsg = alertsList.querySelector('.text-center');
    if (noAlertsMsg) {
        noAlertsMsg.remove();
    }

    // Add new alert at the top
    const alertHtml = `
        <div class="alert-item alert-${alert.severity}" data-alert-id="${alert.id}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${escapeHtml(alert.title)}</strong>
                    <p class="mb-1">${escapeHtml(alert.message)}</p>
                    <small class="text-muted">${formatDateTime(alert.created_at)}</small>
                </div>
                <button class="btn btn-sm btn-outline-secondary" 
                        onclick="acknowledgeAlert('${alert.id}')"
                        title="Acknowledge">
                    <i class="bi bi-check"></i>
                </button>
            </div>
        </div>
    `;

    alertsList.insertAdjacentHTML('afterbegin', alertHtml);
}

/**
 * Acknowledge an alert
 */
async function acknowledgeAlert(alertId) {
    try {
        const response = await fetch(`/admin/api/alerts/${alertId}/acknowledge`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            // Remove alert from display
            const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
            if (alertElement) {
                alertElement.remove();
            }

            // Check if no alerts remain
            const alertsList = document.getElementById('alertsList');
            if (alertsList && alertsList.children.length === 0) {
                alertsList.innerHTML = `
                    <div class="text-center text-muted py-3">
                        <i class="bi bi-check-circle"></i> No active alerts
                    </div>
                `;
            }
        } else {
            showNotification(`Failed to acknowledge alert: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to acknowledge alert:', error);
        showNotification('Failed to acknowledge alert', 'error');
    }
}

/**
 * Show bulk actions modal
 */
function showBulkActions() {
    const selectedCount = selectedJobs.size;
    if (selectedCount === 0) {
        showNotification('Please select at least one job', 'warning');
        return;
    }

    document.getElementById('selectedJobsCount').textContent = selectedCount;
    const modal = new bootstrap.Modal(document.getElementById('bulkActionsModal'));
    modal.show();
}

/**
 * Update bulk action form based on selected action
 */
function updateBulkActionForm() {
    const action = document.getElementById('bulkAction').value;
    const executeButton = document.getElementById('executeBulkAction');

    // Hide all forms
    document.querySelectorAll('.bulk-action-form').forEach(form => {
        form.style.display = 'none';
    });

    // Show relevant form
    if (action) {
        const formId = action + 'ActionForm';
        const form = document.getElementById(formId);
        if (form) {
            form.style.display = 'block';
        }
        executeButton.disabled = false;
    } else {
        executeButton.disabled = true;
    }
}

/**
 * Toggle all job selection
 */
function toggleAllJobSelection() {
    const selectAll = document.getElementById('selectAllJobs');
    const checkboxes = document.querySelectorAll('.job-checkbox');

    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });

    updateSelectedJobs();
}

/**
 * Update selected jobs set
 */
function updateSelectedJobs() {
    selectedJobs.clear();

    document.querySelectorAll('.job-checkbox:checked').forEach(checkbox => {
        selectedJobs.add(checkbox.value);
    });

    // Update select all checkbox state
    const selectAll = document.getElementById('selectAllJobs');
    const checkboxes = document.querySelectorAll('.job-checkbox');
    const checkedBoxes = document.querySelectorAll('.job-checkbox:checked');

    if (checkedBoxes.length === 0) {
        selectAll.indeterminate = false;
        selectAll.checked = false;
    } else if (checkedBoxes.length === checkboxes.length) {
        selectAll.indeterminate = false;
        selectAll.checked = true;
    } else {
        selectAll.indeterminate = true;
        selectAll.checked = false;
    }
}

/**
 * Save system configuration
 */
async function saveSystemConfig() {
    const config = {
        max_concurrent_jobs: parseInt(document.getElementById('maxConcurrentJobs').value),
        job_timeout_minutes: parseInt(document.getElementById('jobTimeoutMinutes').value),
        max_retries: parseInt(document.getElementById('maxRetries').value),
        alert_threshold: parseInt(document.getElementById('alertThreshold').value)
    };

    try {
        const response = await fetch('/admin/api/config', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            showNotification('System configuration saved successfully', 'success');
        } else {
            showNotification(`Failed to save configuration: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to save configuration:', error);
        showNotification('Failed to save configuration', 'error');
    }
}

/**
 * Utility functions
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleTimeString();
}

function formatDateTime(timestamp) {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
}

function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Export functions for global access
window.initializeDashboard = initializeDashboard;
window.connectWebSocket = connectWebSocket;
window.refreshDashboard = refreshDashboard;
window.toggleAutoRefresh = toggleAutoRefresh;
window.cancelJob = cancelJob;
window.setPriority = setPriority;
window.restartJob = restartJob;
window.viewJobDetails = viewJobDetails;
window.showBulkActions = showBulkActions;
window.updateBulkActionForm = updateBulkActionForm;
window.toggleAllJobSelection = toggleAllJobSelection;
window.updateSelectedJobs = updateSelectedJobs;
window.acknowledgeAlert = acknowledgeAlert;
window.saveSystemConfig = saveSystemConfig;
// Additional functions for modal functionality

/**
 * Show user limits modal
 */
function showUserLimitsModal() {
    const modal = new bootstrap.Modal(document.getElementById('userLimitsModal'));
    loadUsersList();
    modal.show();
}

/**
 * Load users list for limits configuration
 */
async function loadUsersList() {
    try {
        const response = await fetch('/admin/api/users');
        const data = await response.json();

        if (data.success) {
            populateUsersList(data.users);
        }
    } catch (error) {
        console.error('Failed to load users list:', error);
    }
}

/**
 * Populate users list in modal
 */
function populateUsersList(users) {
    const usersList = document.getElementById('usersList');
    const template = document.getElementById('userListItemTemplate');

    if (!usersList || !template) return;

    usersList.innerHTML = '';

    users.forEach(user => {
        const clone = template.content.cloneNode(true);

        clone.querySelector('.user-name').textContent = user.username;
        clone.querySelector('.user-email').textContent = user.email;
        clone.querySelector('.user-role').textContent = user.role;
        clone.querySelector('.user-role').className = `badge ${getRoleBadgeClass(user.role)}`;
        clone.querySelector('.user-status').textContent = user.is_active ? 'Active' : 'Inactive';

        const userItem = clone.querySelector('.user-item');
        userItem.setAttribute('data-user-id', user.id);
        userItem.setAttribute('data-username', user.username);
        userItem.setAttribute('data-email', user.email);

        usersList.appendChild(clone);
    });
}

/**
 * Get CSS class for user role badge
 */
function getRoleBadgeClass(role) {
    const classes = {
        'admin': 'bg-danger',
        'reviewer': 'bg-primary',
        'viewer': 'bg-secondary'
    };
    return classes[role] || 'bg-secondary';
}

/**
 * Select a user for limits configuration
 */
function selectUser(userElement) {
    // Remove previous selection
    document.querySelectorAll('.user-item').forEach(item => {
        item.classList.remove('bg-light');
    });

    // Highlight selected user
    userElement.classList.add('bg-light');

    // Get user data
    const userId = userElement.getAttribute('data-user-id');
    const username = userElement.getAttribute('data-username');
    const email = userElement.getAttribute('data-email');

    // Show user limits form
    document.getElementById('selectedUserId').value = userId;
    document.getElementById('selectedUserName').textContent = username;
    document.getElementById('selectedUserEmail').textContent = email;

    document.getElementById('userLimitsForm').style.display = 'block';
    document.getElementById('noUserSelected').style.display = 'none';
    document.getElementById('resetUserLimits').style.display = 'inline-block';
    document.getElementById('saveUserLimits').style.display = 'inline-block';

    // Load current limits for user
    loadUserLimits(userId);
}

/**
 * Load current limits for a user
 */
async function loadUserLimits(userId) {
    try {
        const response = await fetch(`/admin/api/users/${userId}/limits`);
        const data = await response.json();

        if (data.success) {
            populateUserLimitsForm(data.limits);
        }
    } catch (error) {
        console.error('Failed to load user limits:', error);
    }
}

/**
 * Populate user limits form with current values
 */
function populateUserLimitsForm(limits) {
    document.getElementById('maxConcurrentJobs').value = limits.max_concurrent_jobs || 2;
    document.getElementById('maxDailyJobs').value = limits.max_daily_jobs || 10;
    document.getElementById('maxImagesPerJob').value = limits.max_images_per_job || 50;
    document.getElementById('jobPriority').value = limits.default_priority || 'normal';
    document.getElementById('jobTimeoutMinutes').value = limits.job_timeout_minutes || 30;
    document.getElementById('cooldownMinutes').value = limits.cooldown_minutes || 5;

    document.getElementById('canCreateJobs').checked = limits.can_create_jobs !== false;
    document.getElementById('canCancelOwnJobs').checked = limits.can_cancel_own_jobs !== false;
    document.getElementById('canViewJobHistory').checked = limits.can_view_job_history !== false;
    document.getElementById('canRetryFailedJobs').checked = limits.can_retry_failed_jobs !== false;

    document.getElementById('userNotes').value = limits.admin_notes || '';
}

/**
 * Save user limits
 */
async function saveUserLimits() {
    const userId = document.getElementById('selectedUserId').value;
    if (!userId) return;

    const limits = {
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
        admin_notes: document.getElementById('userNotes').value
    };

    try {
        const response = await fetch(`/admin/api/users/${userId}/limits`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(limits)
        });

        const data = await response.json();

        if (data.success) {
            showNotification('User limits saved successfully', 'success');
        } else {
            showNotification(`Failed to save limits: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to save user limits:', error);
        showNotification('Failed to save user limits', 'error');
    }
}

/**
 * Reset user limits to defaults
 */
function resetUserLimits() {
    if (!confirm('Reset user limits to system defaults?')) return;

    populateUserLimitsForm({
        max_concurrent_jobs: 2,
        max_daily_jobs: 10,
        max_images_per_job: 50,
        default_priority: 'normal',
        job_timeout_minutes: 30,
        cooldown_minutes: 5,
        can_create_jobs: true,
        can_cancel_own_jobs: true,
        can_view_job_history: true,
        can_retry_failed_jobs: true,
        admin_notes: ''
    });
}

/**
 * Filter users list
 */
function filterUsers() {
    const searchTerm = document.getElementById('userSearch').value.toLowerCase();
    const userItems = document.querySelectorAll('.user-item');

    userItems.forEach(item => {
        const username = item.querySelector('.user-name').textContent.toLowerCase();
        const email = item.querySelector('.user-email').textContent.toLowerCase();

        if (username.includes(searchTerm) || email.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}



/**
 * Load current system activity
 */
async function loadSystemActivity() {
    try {
        const response = await fetch('/admin/api/system-activity');
        const data = await response.json();

        if (data.success) {
            updateSystemActivity(data.activity);
        }
    } catch (error) {
        console.error('Failed to load system activity:', error);
    }
}

/**
 * Update system activity display
 */
function updateSystemActivity(activity) {
    document.getElementById('activeJobsCount').textContent = activity.active_jobs || 0;
    document.getElementById('queuedJobsCount').textContent = activity.queued_jobs || 0;
    document.getElementById('connectedUsersCount').textContent = activity.connected_users || 0;
    document.getElementById('systemLoadPercent').textContent = `${activity.system_load || 0}%`;
}

/**
 * Pause system jobs
 */
async function pauseSystem() {
    const reason = document.getElementById('maintenanceReason').value;
    if (!reason.trim()) {
        showNotification('Please enter a reason for maintenance', 'warning');
        return;
    }

    try {
        const response = await fetch('/admin/api/system/pause', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ reason })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('systemStatus').textContent = 'Paused';
            document.getElementById('systemStatus').className = 'badge bg-warning';
            document.getElementById('pauseSystemBtn').style.display = 'none';
            document.getElementById('resumeSystemBtn').style.display = 'block';

            addMaintenanceLogEntry(`System paused: ${reason}`);
            showNotification('System paused successfully', 'success');
        } else {
            showNotification(`Failed to pause system: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to pause system:', error);
        showNotification('Failed to pause system', 'error');
    }
}

/**
 * Resume system jobs
 */
async function resumeSystem() {
    try {
        const response = await fetch('/admin/api/system/resume', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('systemStatus').textContent = 'Active';
            document.getElementById('systemStatus').className = 'badge bg-success';
            document.getElementById('pauseSystemBtn').style.display = 'block';
            document.getElementById('resumeSystemBtn').style.display = 'none';

            addMaintenanceLogEntry('System resumed');
            showNotification('System resumed successfully', 'success');
        } else {
            showNotification(`Failed to resume system: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to resume system:', error);
        showNotification('Failed to resume system', 'error');
    }
}

/**
 * Add entry to maintenance log
 */
function addMaintenanceLogEntry(message) {
    const logDiv = document.getElementById('maintenanceLog');
    if (!logDiv) return;

    const timestamp = new Date().toLocaleString();
    const entry = document.createElement('div');
    entry.innerHTML = `<small class="text-muted">${timestamp}</small> ${message}`;

    // Remove "no activities" message if present
    const noActivities = logDiv.querySelector('.text-muted');
    if (noActivities && noActivities.textContent.includes('No maintenance activities')) {
        noActivities.remove();
    }

    logDiv.insertBefore(entry, logDiv.firstChild);
}

/**
 * Show emergency stop modal
 */
function showEmergencyStop() {
    const modal = new bootstrap.Modal(document.getElementById('emergencyStopModal'));
    modal.show();
}

/**
 * Execute emergency stop
 */
async function executeEmergencyStop() {
    const reason = document.getElementById('emergencyReason').value;
    const confirmed = document.getElementById('confirmEmergencyStop').checked;

    if (!reason.trim() || reason.length < 10) {
        showNotification('Please provide a detailed reason (minimum 10 characters)', 'warning');
        return;
    }

    if (!confirmed) {
        showNotification('Please confirm that you understand the consequences', 'warning');
        return;
    }

    try {
        const response = await fetch('/admin/api/system/emergency-stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ reason })
        });

        const data = await response.json();

        if (data.success) {
            // Close modals
            bootstrap.Modal.getInstance(document.getElementById('emergencyStopModal')).hide();
            bootstrap.Modal.getInstance(document.getElementById('systemMaintenanceModal')).hide();

            // Update system status
            document.getElementById('systemStatus').textContent = 'Emergency Stop';
            document.getElementById('systemStatus').className = 'badge bg-danger';

            showNotification('Emergency stop executed', 'warning');

            // Refresh dashboard
            setTimeout(refreshDashboard, 2000);
        } else {
            showNotification(`Failed to execute emergency stop: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to execute emergency stop:', error);
        showNotification('Failed to execute emergency stop', 'error');
    }
}

/**
 * Maintenance task functions
 */
async function clearStuckJobs() {
    if (!confirm('Clear all stuck jobs? This action cannot be undone.')) return;

    try {
        const response = await fetch('/admin/api/maintenance/clear-stuck-jobs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            addMaintenanceLogEntry(`Cleared ${data.count} stuck jobs`);
            showNotification(`Cleared ${data.count} stuck jobs`, 'success');
            refreshActiveJobs();
        } else {
            showNotification(`Failed to clear stuck jobs: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to clear stuck jobs:', error);
        showNotification('Failed to clear stuck jobs', 'error');
    }
}

async function cleanupOldLogs() {
    if (!confirm('Clean up old logs? This will remove logs older than 30 days.')) return;

    try {
        const response = await fetch('/admin/api/maintenance/cleanup-logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            addMaintenanceLogEntry(`Cleaned up ${data.count} old log entries`);
            showNotification(`Cleaned up ${data.count} old log entries`, 'success');
        } else {
            showNotification(`Failed to cleanup logs: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to cleanup logs:', error);
        showNotification('Failed to cleanup logs', 'error');
    }
}

async function optimizeDatabase() {
    if (!confirm('Optimize database? This may take a few minutes.')) return;

    try {
        const response = await fetch('/admin/api/maintenance/optimize-database', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            addMaintenanceLogEntry('Database optimization completed');
            showNotification('Database optimization completed', 'success');
        } else {
            showNotification(`Failed to optimize database: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to optimize database:', error);
        showNotification('Failed to optimize database', 'error');
    }
}

async function refreshSystemCache() {
    try {
        const response = await fetch('/admin/api/maintenance/refresh-cache', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            addMaintenanceLogEntry('System cache refreshed');
            showNotification('System cache refreshed', 'success');
        } else {
            showNotification(`Failed to refresh cache: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to refresh cache:', error);
        showNotification('Failed to refresh cache', 'error');
    }
}

async function runHealthCheck() {
    try {
        const response = await fetch('/admin/api/maintenance/health-check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });

        const data = await response.json();

        if (data.success) {
            addMaintenanceLogEntry(`Health check completed: ${data.status}`);
            showNotification(`Health check completed: ${data.status}`, 'success');
        } else {
            showNotification(`Health check failed: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to run health check:', error);
        showNotification('Failed to run health check', 'error');
    }
}

/**
 * Export system report
 */
async function exportSystemReport() {
    try {
        const response = await fetch('/admin/api/reports/system-report', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `system-report-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showNotification('System report exported successfully', 'success');
        } else {
            showNotification('Failed to export system report', 'error');
        }
    } catch (error) {
        console.error('Failed to export system report:', error);
        showNotification('Failed to export system report', 'error');
    }
}

/**
 * Export maintenance report
 */
async function exportMaintenanceReport() {
    try {
        const response = await fetch('/admin/api/reports/maintenance-report', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `maintenance-report-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showNotification('Maintenance report exported successfully', 'success');
        } else {
            showNotification('Failed to export maintenance report', 'error');
        }
    } catch (error) {
        console.error('Failed to export maintenance report:', error);
        showNotification('Failed to export maintenance report', 'error');
    }
}

/**
 * Reset system configuration to defaults
 */
function resetSystemConfig() {
    if (!confirm('Reset system configuration to defaults?')) return;

    document.getElementById('maxConcurrentJobs').value = 5;
    document.getElementById('jobTimeoutMinutes').value = 30;
    document.getElementById('maxRetries').value = 3;
    document.getElementById('alertThreshold').value = 80;
}

/**
 * Save job notes from job details modal
 */
async function saveJobNotes() {
    const textarea = document.querySelector('.job-admin-notes');
    if (!textarea) return;

    const taskId = textarea.getAttribute('data-job-id');
    const notes = textarea.value;

    try {
        const response = await fetch(`/admin/api/jobs/${taskId}/notes`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ notes })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Job notes saved successfully', 'success');
        } else {
            showNotification(`Failed to save notes: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Failed to save job notes:', error);
        showNotification('Failed to save job notes', 'error');
    }
}

// Export additional functions for global access
window.showUserLimitsModal = showUserLimitsModal;
window.selectUser = selectUser;
window.saveUserLimits = saveUserLimits;
window.resetUserLimits = resetUserLimits;
window.filterUsers = filterUsers;

window.pauseSystem = pauseSystem;
window.resumeSystem = resumeSystem;
window.showEmergencyStop = showEmergencyStop;
window.executeEmergencyStop = executeEmergencyStop;
window.clearStuckJobs = clearStuckJobs;
window.cleanupOldLogs = cleanupOldLogs;
window.optimizeDatabase = optimizeDatabase;
window.refreshSystemCache = refreshSystemCache;
window.runHealthCheck = runHealthCheck;
window.exportSystemReport = exportSystemReport;
window.exportMaintenanceReport = exportMaintenanceReport;
window.resetSystemConfig = resetSystemConfig;
window.saveJobNotes = saveJobNotes;