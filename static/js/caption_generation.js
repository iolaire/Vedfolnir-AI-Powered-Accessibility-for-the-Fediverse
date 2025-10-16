// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Enhanced Caption Generation UI with Unified Notification System
 * Provides improved job management, error handling, and user experience
 * Integrated with WebSocket-based real-time notifications
 */

class CaptionGenerationUI {
    constructor() {
        this.currentTaskId = null;
        this.progressPollingInterval = null;
        this.taskStartTime = null;
        this.websocketConnected = false;
        this.notificationIntegrator = null;
        
        this.init();
    }
    
    init() {
        // Get current task ID from template
        const taskIdElement = document.querySelector('[data-current-task-id]');
        if (taskIdElement) {
            this.currentTaskId = taskIdElement.dataset.currentTaskId;
        }
        
        // Initialize progress bar from data attribute
        this.initializeProgressBar();
        
        this.setupEventListeners();
        this.initializeNotificationSystem();
        this.initializeProgressMonitoring();
        this.initializeTaskFilters();
    }
    
    initializeProgressBar() {
        const progressBar = document.getElementById('progress-bar');
        if (progressBar && progressBar.dataset.progressWidth) {
            // Use the new progress bar utility for initialization
            if (window.progressBarUtils) {
                window.progressBarUtils.initializeProgressBar(progressBar);
            } else {
                // Fallback to direct CSS custom property setting
                progressBar.style.setProperty('--progress-width', progressBar.dataset.progressWidth);
            }
        }
    }
    
    initializeNotificationSystem() {
        // Initialize page notification integrator for caption processing
        if (window.PageNotificationIntegrator) {
            this.notificationIntegrator = new window.PageNotificationIntegrator('caption-processing', 'user');
            
            // Register WebSocket event handlers for caption processing
            this.notificationIntegrator.registerEventHandlers({
                'caption_progress': (data) => this.handleCaptionProgressNotification(data),
                'caption_status': (data) => this.handleCaptionStatusNotification(data),
                'caption_complete': (data) => this.handleCaptionCompleteNotification(data),
                'caption_error': (data) => this.handleCaptionErrorNotification(data),
                'system_maintenance': (data) => this.handleMaintenanceNotification(data),
                'notification': (data) => this.handleGeneralNotification(data)
            });
            
            // Initialize WebSocket connection
            this.notificationIntegrator.initialize();
            
            // Monitor connection status
            this.notificationIntegrator.onConnectionChange((connected) => {
                this.websocketConnected = connected;
                this.updateConnectionStatus(connected);
            });
            
            console.log('Caption processing notification system initialized');
            
            // Setup notification action handlers for caption generation
            document.addEventListener('notificationAction', (event) => {
                const { action, notificationId, notification } = event.detail;
                
                switch (action) {
                    case 'review':
                        this.goToReview();
                        break;
                    case 'new_task':
                        this.startNewTask();
                        break;
                    case 'retry':
                        if (this.currentTaskId) {
                            this.retryTask(this.currentTaskId);
                        }
                        break;
                    case 'details':
                        if (this.currentTaskId) {
                            this.showErrorDetails(this.currentTaskId);
                        }
                        break;
                    default:
                        console.log('Unknown caption generation notification action:', action);
                }
            });
        } else {
            console.warn('PageNotificationIntegrator not available, falling back to polling');
        }
    }
    
    setupEventListeners() {
        // Caption generation form
        const captionForm = document.getElementById('caption-generation-form');
        if (captionForm) {
            captionForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
        
        // Page visibility change handling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.cleanupProgressMonitoring();
            } else if (this.currentTaskId && !this.progressPollingInterval) {
                this.initializeProgressMonitoring();
            }
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.cleanupProgressMonitoring();
        });
    }
    
    async handleFormSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const formData = new FormData(form);
        const submitBtn = document.getElementById('start-generation-btn');
        
        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
        
        try {
            const response = await window.csrfHandler.secureFetch(form.action, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentTaskId = data.task_id;
                this.taskStartTime = new Date();
                this.showAlert(data.message, 'success');
                
                // Refresh page to show active task
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                this.showAlert(data.error, 'danger');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-play-circle"></i> Start Caption Generation';
            }
        } catch (error) {
            console.error('Error:', error);
            this.showAlert('An error occurred while starting caption generation.', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-play-circle"></i> Start Caption Generation';
        }
    }
    
    initializeProgressMonitoring() {
        if (!this.currentTaskId) {
            console.log('No active task, skipping progress monitoring');
            return;
        }
        
        console.log('Starting progress monitoring for task:', this.currentTaskId);
        
        // Use WebSocket notifications if available, otherwise fall back to polling
        if (this.websocketConnected && this.notificationIntegrator) {
            console.log('Using WebSocket-based progress monitoring');
            // WebSocket notifications will handle progress updates
            // Keep minimal polling as backup
            this.startBackupPolling();
        } else {
            console.log('Using polling-based progress monitoring');
            this.startProgressPolling();
        }
    }
    
    handleCaptionProgressNotification(data) {
        console.log('Received caption progress notification:', data);
        
        if (data.task_id && data.task_id !== this.currentTaskId) {
            return; // Not for current task
        }
        
        // Update progress from WebSocket notification
        this.updateProgressFromNotification(data);
        
        // Show progress notification if significant milestone
        if (data.show_notification) {
            this.notificationIntegrator.showNotification({
                type: 'progress',
                title: data.title || 'Caption Generation Progress',
                message: data.message || `Processing: ${data.progress_percent || 0}%`,
                progress: data.progress_percent || 0,
                autoHide: data.auto_hide !== false,
                persistent: data.persistent === true,
                category: 'caption',
                data: {
                    task_id: data.task_id,
                    progress_percent: data.progress_percent,
                    current_step: data.current_step,
                    estimated_completion: data.estimated_completion,
                    processing_rate: data.processing_rate
                }
            });
        }
    }
    
    handleCaptionStatusNotification(data) {
        console.log('Received caption status notification:', data);
        
        if (data.task_id && data.task_id !== this.currentTaskId) {
            return; // Not for current task
        }
        
        // Update task status
        this.updateTaskStatus(data.status, data.message);
        
        // Show status notification
        this.notificationIntegrator.showNotification({
            type: data.status === 'running' ? 'info' : 'success',
            title: 'Caption Generation Status',
            message: data.message || `Task status: ${data.status}`,
            autoHide: true,
            category: 'caption'
        });
    }
    
    handleCaptionCompleteNotification(data) {
        console.log('Received caption complete notification:', data);
        
        if (data.task_id && data.task_id !== this.currentTaskId) {
            return; // Not for current task
        }
        
        // Handle task completion
        this.handleTaskCompletion(data);
        
        // Show completion notification with enhanced action buttons
        this.notificationIntegrator.showNotification({
            type: 'success',
            title: 'Caption Generation Complete!',
            message: data.message || `Generated ${data.captions_generated || 0} captions for ${data.images_processed || 0} images.`,
            autoHide: false,
            persistent: true,
            category: 'caption',
            actions: data.actions || [
                {
                    text: 'Review Captions',
                    action: () => this.goToReview(),
                    primary: true
                },
                {
                    text: 'Start New Task',
                    action: () => this.startNewTask()
                }
            ],
            data: {
                task_id: data.task_id,
                captions_generated: data.captions_generated,
                images_processed: data.images_processed,
                processing_time: data.processing_time,
                success_rate: data.success_rate
            }
        });
        
        // Stop progress monitoring
        this.stopProgressPolling();
    }
    
    handleCaptionErrorNotification(data) {
        console.log('Received caption error notification:', data);
        
        if (data.task_id && data.task_id !== this.currentTaskId) {
            return; // Not for current task
        }
        
        // Handle task error
        this.handleTaskError(data);
        
        // Show enhanced error notification with retry options and recovery suggestions
        this.notificationIntegrator.showNotification({
            type: 'error',
            title: 'Caption Generation Failed',
            message: data.message || 'An error occurred during caption generation.',
            autoHide: false,
            persistent: true,
            category: 'caption',
            actions: data.actions || [
                {
                    text: 'Retry Task',
                    action: () => this.retryTask(data.task_id),
                    primary: true
                },
                {
                    text: 'View Details',
                    action: () => this.showErrorDetails(data.task_id)
                }
            ],
            data: {
                task_id: data.task_id,
                error_message: data.error_message,
                error_category: data.error_category,
                recovery_suggestions: data.recovery_suggestions || []
            }
        });
        
        // Show recovery suggestions if available
        if (data.recovery_suggestions && data.recovery_suggestions.length > 0) {
            this.showRecoverySuggestions(data.recovery_suggestions);
        }
        
        // Stop progress monitoring
        this.stopProgressPolling();
    }
    
    handleMaintenanceNotification(data) {
        console.log('Received maintenance notification:', data);
        
        // Show maintenance notification
        this.notificationIntegrator.showNotification({
            type: 'warning',
            title: 'System Maintenance',
            message: data.message || 'System maintenance is in progress. Caption generation may be temporarily unavailable.',
            autoHide: false,
            category: 'maintenance',
            persistent: true
        });
        
        // If maintenance affects caption processing, pause current operations
        if (data.affects_caption_processing && this.currentTaskId) {
            this.pauseTaskForMaintenance(data);
        }
    }
    
    handleGeneralNotification(data) {
        console.log('Received general notification:', data);
        
        // Show general notification
        this.notificationIntegrator.showNotification({
            type: data.type || 'info',
            title: data.title || 'Notification',
            message: data.message,
            autoHide: data.auto_hide !== false,
            category: data.category || 'system'
        });
    }
    
    startProgressPolling() {
        // Use AdaptivePollingManager if available
        if (window.adaptivePollingManager && this.currentTaskId) {
            console.log('Using AdaptivePollingManager for progress polling');
            
            window.adaptivePollingManager.startPolling(this.currentTaskId, {
                type: 'caption_generation',
                priority: 1, // High priority for active task
                callback: (status) => {
                    this.updateProgressFromStatus(status);
                    
                    // Check if task is completed
                    if (status.status === 'completed') {
                        this.handleTaskCompletion(status);
                    } else if (status.status === 'failed') {
                        this.handleTaskError(status);
                    } else if (status.status === 'cancelled') {
                        this.handleTaskCancellation(status);
                    }
                }
            });
            
            return;
        }
        
        // Fallback to traditional polling
        console.log('Using traditional polling (AdaptivePollingManager not available)');
        
        // Clear any existing interval
        if (this.progressPollingInterval) {
            clearInterval(this.progressPollingInterval);
        }
        
        // Poll every 2 seconds for progress updates
        this.progressPollingInterval = setInterval(async () => {
            if (!this.currentTaskId) {
                this.stopProgressPolling();
                return;
            }
            
            try {
                const response = await fetch(`/caption/api/status/${this.currentTaskId}`);
                const data = await response.json();
                
                if (data.success && data.status) {
                    this.updateProgressFromStatus(data.status);
                    
                    // Check if task is completed
                    if (data.status.status === 'completed') {
                        this.handleTaskCompletion(data.status);
                        this.stopProgressPolling();
                    } else if (data.status.status === 'failed') {
                        this.handleTaskError(data.status);
                        this.stopProgressPolling();
                    } else if (data.status.status === 'cancelled') {
                        this.handleTaskCancellation(data.status);
                        this.stopProgressPolling();
                    }
                } else {
                    console.log('No status data available for task:', this.currentTaskId);
                }
            } catch (error) {
                console.error('Error polling for progress:', error);
                
                // Show connection error notification if WebSocket is not available
                if (!this.websocketConnected && this.notificationIntegrator) {
                    this.notificationIntegrator.showNotification({
                        type: 'warning',
                        title: 'Connection Issue',
                        message: 'Having trouble getting progress updates. Retrying...',
                        autoHide: true,
                        category: 'system'
                    });
                }
            }
        }, 2000);
    }
    
    startBackupPolling() {
        // Use AdaptivePollingManager for backup polling if available
        if (window.adaptivePollingManager && this.currentTaskId) {
            console.log('Using AdaptivePollingManager for backup polling');
            
            window.adaptivePollingManager.startPolling(this.currentTaskId, {
                type: 'caption_generation',
                priority: 3, // Low priority for backup polling
                callback: (status) => {
                    // Only update if WebSocket is not connected
                    if (!this.websocketConnected) {
                        this.updateProgressFromStatus(status);
                    }
                }
            });
            
            return;
        }
        
        // Fallback to traditional backup polling
        console.log('Using traditional backup polling');
        
        // Lighter polling when WebSocket is available (every 10 seconds as backup)
        if (this.progressPollingInterval) {
            clearInterval(this.progressPollingInterval);
        }
        
        this.progressPollingInterval = setInterval(async () => {
            if (!this.currentTaskId || this.websocketConnected) {
                return; // Skip if no task or WebSocket is handling updates
            }
            
            try {
                const response = await fetch(`/caption/api/status/${this.currentTaskId}`);
                const data = await response.json();
                
                if (data.success && data.status) {
                    this.updateProgressFromStatus(data.status);
                }
            } catch (error) {
                console.error('Error in backup polling:', error);
            }
        }, 10000);
    }
    
    updateProgressFromNotification(data) {
        const progressData = {
            task_id: data.task_id,
            progress_percent: data.progress_percent || 0,
            current_step: data.current_step || data.message || 'Processing',
            details: data.details || {}
        };
        
        this.updateProgress(progressData);
        
        // Update additional WebSocket-specific data
        if (data.estimated_completion) {
            const estimatedCompletion = document.getElementById('estimated-completion');
            if (estimatedCompletion) {
                estimatedCompletion.textContent = data.estimated_completion;
            }
        }
        
        if (data.processing_rate) {
            const processingRate = document.getElementById('processing-rate');
            if (processingRate) {
                processingRate.textContent = data.processing_rate;
            }
        }
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('websocket-status');
        if (statusIndicator) {
            statusIndicator.className = connected ? 'text-success' : 'text-warning';
            statusIndicator.textContent = connected ? 'Connected' : 'Reconnecting...';
        }
        
        // Show connection status notification
        if (this.notificationIntegrator) {
            if (connected) {
                this.notificationIntegrator.showNotification({
                    type: 'success',
                    title: 'Connection Restored',
                    message: 'Real-time updates are now available.',
                    autoHide: true,
                    category: 'system'
                });
            } else {
                this.notificationIntegrator.showNotification({
                    type: 'warning',
                    title: 'Connection Lost',
                    message: 'Attempting to reconnect for real-time updates...',
                    autoHide: true,
                    category: 'system'
                });
            }
        }
    }
    
    updateTaskStatus(status, message) {
        const statusDiv = document.getElementById('active-task-status');
        if (statusDiv) {
            // Update status class
            statusDiv.className = `task-status ${status}`;
            
            // Update status text
            const statusText = statusDiv.querySelector('.text-capitalize');
            if (statusText) {
                statusText.textContent = status;
            }
            
            // Update current step if message provided
            if (message) {
                const currentStep = document.getElementById('current-step');
                if (currentStep) {
                    currentStep.textContent = message;
                }
            }
        }
    }
    
    pauseTaskForMaintenance(maintenanceData) {
        // Show maintenance pause notification
        this.notificationIntegrator.showNotification({
            type: 'warning',
            title: 'Task Paused for Maintenance',
            message: `Caption generation has been paused due to system maintenance. ${maintenanceData.message || ''}`,
            autoHide: false,
            category: 'maintenance',
            persistent: true,
            actions: [
                {
                    text: 'View Maintenance Details',
                    action: () => this.showMaintenanceDetails(maintenanceData)
                }
            ]
        });
        
        // Update UI to show paused state
        const currentStep = document.getElementById('current-step');
        if (currentStep) {
            currentStep.textContent = 'Paused for maintenance';
        }
        
        // Stop progress polling during maintenance
        this.stopProgressPolling();
    }
    
    showMaintenanceDetails(maintenanceData) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-tools text-warning"></i>
                            System Maintenance
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning">
                            <h6><i class="bi bi-info-circle"></i> Maintenance Information</h6>
                            <p>${maintenanceData.message || 'System maintenance is currently in progress.'}</p>
                        </div>
                        
                        ${maintenanceData.estimated_duration ? `
                        <div class="alert alert-info">
                            <h6><i class="bi bi-clock"></i> Estimated Duration</h6>
                            <p>${maintenanceData.estimated_duration} minutes</p>
                        </div>
                        ` : ''}
                        
                        <div class="alert alert-success">
                            <h6><i class="bi bi-lightbulb"></i> What You Can Do</h6>
                            <ul class="mb-0">
                                <li>Your current task progress has been saved</li>
                                <li>Caption generation will resume automatically after maintenance</li>
                                <li>You can safely close this page and return later</li>
                                <li>Check back in a few minutes for updates</li>
                            </ul>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x"></i> Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up modal after it's hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }
    
    showRecoverySuggestions(suggestions) {
        if (!suggestions || suggestions.length === 0) {
            return;
        }
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-lightbulb text-info"></i>
                            Recovery Suggestions
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <h6><i class="bi bi-info-circle"></i> Suggested Actions</h6>
                            <p>Here are some suggestions to resolve the issue:</p>
                        </div>
                        
                        <ul class="list-group list-group-flush">
                            ${suggestions.map(suggestion => `
                                <li class="list-group-item">
                                    <i class="bi bi-arrow-right text-primary"></i>
                                    ${suggestion}
                                </li>
                            `).join('')}
                        </ul>
                        
                        <div class="alert alert-warning mt-3">
                            <h6><i class="bi bi-exclamation-triangle"></i> Need More Help?</h6>
                            <p class="mb-0">If these suggestions don't resolve the issue, you can contact support or check the system status page.</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="captionUI.retryTask('${this.currentTaskId}')">
                            <i class="bi bi-arrow-clockwise"></i> Try Again
                        </button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x"></i> Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up modal after it's hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }
    
    stopProgressPolling() {
        // Stop AdaptivePollingManager polling if available
        if (window.adaptivePollingManager && this.currentTaskId) {
            window.adaptivePollingManager.stopPolling(this.currentTaskId);
            console.log('Stopped adaptive polling for task:', this.currentTaskId);
        }
        
        // Also stop traditional polling as fallback
        if (this.progressPollingInterval) {
            clearInterval(this.progressPollingInterval);
            this.progressPollingInterval = null;
            console.log('Stopped traditional progress polling');
        }
    }
    
    cleanupProgressMonitoring() {
        this.stopProgressPolling();
    }
    
    updateProgressFromStatus(status) {
        const progressData = {
            task_id: status.task_id,
            progress_percent: status.progress_percent || 0,
            current_step: status.current_step || 'Processing',
            details: status.progress_details || {}
        };
        
        this.updateProgress(progressData);
    }
    
    updateProgress(data) {
        if (data.task_id && data.task_id !== this.currentTaskId) return;
        
        const progressBar = document.getElementById('progress-bar');
        const currentStep = document.getElementById('current-step');
        
        // Use the new progress bar utility for updates
        if (progressBar && window.progressBarUtils) {
            window.progressBarUtils.updateProgressBar(progressBar, data.progress_percent, {
                updateText: true,
                updateAriaValue: true,
                animate: true
            });
        } else if (progressBar) {
            // Fallback to direct CSS custom property setting
            progressBar.style.setProperty('--progress-width', data.progress_percent + '%');
            progressBar.setAttribute('aria-valuenow', data.progress_percent);
            
            const progressText = document.getElementById('progress-text');
            if (progressText) {
                progressText.textContent = data.progress_percent + '%';
            }
        }
        
        if (currentStep) {
            currentStep.textContent = data.current_step || 'Processing';
        }
        
        // Update detailed progress information
        this.updateDetailedProgress(data);
    }
    
    updateDetailedProgress(data) {
        if (!data.details) return;
        
        const imagesProcessed = document.getElementById('images-processed');
        const processingRate = document.getElementById('processing-rate');
        const estimatedCompletion = document.getElementById('estimated-completion');
        
        // Update images processed
        if (imagesProcessed && data.details.images_processed) {
            imagesProcessed.textContent = data.details.images_processed;
        }
        
        // Calculate and update processing rate
        if (processingRate && data.details.images_processed && this.taskStartTime) {
            const now = new Date();
            const elapsedMinutes = (now - this.taskStartTime) / (1000 * 60);
            
            if (elapsedMinutes > 0) {
                const rate = (data.details.images_processed / elapsedMinutes).toFixed(1);
                processingRate.textContent = `${rate} images/min`;
            }
        }
        
        // Calculate and update estimated completion
        if (estimatedCompletion && data.details.total_posts && data.details.current_post && this.taskStartTime) {
            const now = new Date();
            const elapsedMs = now - this.taskStartTime;
            const progress = data.details.current_post / data.details.total_posts;
            
            if (progress > 0) {
                const totalEstimatedMs = elapsedMs / progress;
                const remainingMs = totalEstimatedMs - elapsedMs;
                
                if (remainingMs > 0) {
                    const remainingMinutes = Math.ceil(remainingMs / (1000 * 60));
                    estimatedCompletion.textContent = `~${remainingMinutes} minutes`;
                } else {
                    estimatedCompletion.textContent = 'Almost done';
                }
            }
        }
    }
    
    handleTaskCompletion(status) {
        if (status.task_id !== this.currentTaskId) return;
        
        const statusDiv = document.getElementById('active-task-status');
        if (statusDiv) {
            statusDiv.className = 'task-status completed';
            
            const currentStep = document.getElementById('current-step');
            if (currentStep) {
                currentStep.textContent = 'Completed';
            }
            
            const progressBar = document.getElementById('progress-bar');
            if (progressBar && window.progressBarUtils) {
                // Use the utility function for completion
                window.progressBarUtils.completeProgressBar(progressBar, {
                    customClass: 'bg-success'
                });
            } else if (progressBar) {
                // Fallback to direct CSS custom property setting
                progressBar.style.setProperty('--progress-width', '100%');
                progressBar.className = 'progress-bar progress-bar-dynamic bg-success';
                
                const progressText = document.getElementById('progress-text');
                if (progressText) {
                    progressText.textContent = '100%';
                }
            }
            
            // Add review button to the status div
            const reviewButtonHtml = `
                <div class="mt-2">
                    <button type="button" class="btn btn-sm btn-success" onclick="captionUI.goToReview()">
                        <i class="bi bi-eye"></i> Review Generated Captions
                    </button>
                </div>
            `;
            statusDiv.innerHTML += reviewButtonHtml;
        }
        
        // Show completion alert with results if available
        let completionMessage = 'Caption generation completed successfully!';
        if (status.results) {
            completionMessage += ` Generated ${status.results.captions_generated || 0} captions for ${status.results.images_processed || 0} images.`;
        }
        
        this.showCompletionAlert(completionMessage, status.task_id);
        
        // Automatically redirect to review interface after a short delay
        this.scheduleReviewRedirect(status.task_id);
    }
    
    handleTaskError(status) {
        if (status.task_id !== this.currentTaskId) return;
        
        const statusDiv = document.getElementById('active-task-status');
        if (statusDiv) {
            statusDiv.className = 'task-status failed';
            
            const currentStep = document.getElementById('current-step');
            if (currentStep) {
                currentStep.textContent = 'Failed';
            }
            
            // Add retry button to the status div
            const retryButtonHtml = `
                <div class="mt-2">
                    <button type="button" class="btn btn-sm btn-primary me-2" onclick="captionUI.retryTask('${status.task_id}')">
                        <i class="bi bi-arrow-clockwise"></i> Retry Task
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-info" onclick="captionUI.showErrorDetails('${status.task_id}')">
                        <i class="bi bi-info-circle"></i> View Details
                    </button>
                </div>
            `;
            statusDiv.innerHTML += retryButtonHtml;
        }
        
        // Show enhanced error alert with recovery suggestions
        this.showEnhancedErrorAlert(status.error_message || 'Unknown error', status.task_id);
    }
    
    handleTaskCancellation(status) {
        if (status.task_id !== this.currentTaskId) return;
        
        const statusDiv = document.getElementById('active-task-status');
        if (statusDiv) {
            statusDiv.className = 'task-status cancelled';
            
            const currentStep = document.getElementById('current-step');
            if (currentStep) {
                currentStep.textContent = 'Cancelled';
            }
        }
        
        this.showAlert('Caption generation was cancelled.', 'warning');
    }
    
    async scheduleReviewRedirect(taskId) {
        try {
            // Get redirect information from the server
            const response = await window.csrfHandler.secureFetch(`/api/caption_generation/redirect_info/${taskId}`);
            const data = await response.json();
            
            if (data.success && data.redirect_info) {
                const redirectInfo = data.redirect_info;
                
                // Show redirect notification
                this.showRedirectNotification(redirectInfo);
                
                // Auto-redirect after 5 seconds unless user cancels
                this.autoRedirectTimeout = setTimeout(() => {
                    window.location.href = redirectInfo.redirect_url;
                }, 5000);
            } else {
                // Fallback to batch review page
                this.showRedirectNotification({
                    redirect_url: '/review/batches',
                    total_images: 'unknown'
                });
                
                this.autoRedirectTimeout = setTimeout(() => {
                    window.location.href = '/review/batches';
                }, 5000);
            }
        } catch (error) {
            console.error('Error getting redirect info:', error);
            // Fallback redirect
            setTimeout(() => {
                window.location.href = '/review/batches';
            }, 3000);
        }
    }
    
    showRedirectNotification(redirectInfo) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
        
        const imageText = redirectInfo.total_images !== 'unknown' 
            ? `${redirectInfo.total_images} images` 
            : 'your captions';
        
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-arrow-right-circle me-2"></i>
                <div class="flex-grow-1">
                    <strong>Ready for Review!</strong><br>
                    <small>Redirecting to review ${imageText} in <span id="redirect-countdown">5</span> seconds...</small>
                </div>
            </div>
            <div class="mt-2">
                <button type="button" class="btn btn-sm btn-primary me-2" onclick="captionUI.redirectNow('${redirectInfo.redirect_url}')">
                    <i class="bi bi-eye"></i> Review Now
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="captionUI.cancelRedirect()">
                    <i class="bi bi-x"></i> Cancel
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Start countdown
        let countdown = 5;
        this.countdownInterval = setInterval(() => {
            countdown--;
            const countdownElement = document.getElementById('redirect-countdown');
            if (countdownElement) {
                countdownElement.textContent = countdown;
            }
            
            if (countdown <= 0) {
                clearInterval(this.countdownInterval);
            }
        }, 1000);
        
        // Auto-remove notification after redirect
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 6000);
    }
    
    redirectNow(url) {
        this.cancelRedirect();
        window.location.href = url;
    }
    
    cancelRedirect() {
        if (this.autoRedirectTimeout) {
            clearTimeout(this.autoRedirectTimeout);
            this.autoRedirectTimeout = null;
        }
        
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
        
        // Remove notification
        const notification = document.querySelector('.alert.position-fixed');
        if (notification) {
            notification.remove();
        }
        
        // Refresh page after a short delay
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    }
    
    showCompletionAlert(message, taskId) {
        // Use unified notification system
        if (window.Vedfolnir && window.Vedfolnir.showNotification) {
            return window.Vedfolnir.showNotification(message, 'success', {
                title: 'Caption Generation Complete!',
                persistent: true,
                actions: [
                    {
                        label: 'Review Captions',
                        type: 'primary',
                        action: 'review'
                    },
                    {
                        label: 'Start New Task',
                        type: 'secondary',
                        action: 'new_task'
                    }
                ]
            });
        } else {
            // Fallback to legacy alert display
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success alert-dismissible fade show';
            alertDiv.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="flex-grow-1">
                        <h6><i class="bi bi-check-circle"></i> Caption Generation Complete!</h6>
                        <p class="mb-2">${message}</p>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-sm btn-outline-success" onclick="captionUI.goToReview()">
                                <i class="bi bi-eye"></i> Review Captions
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-success" onclick="captionUI.startNewTask()">
                                <i class="bi bi-plus-circle"></i> Start New Task
                            </button>
                        </div>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            const container = document.querySelector('.container');
            if (container) {
                container.insertBefore(alertDiv, container.firstChild);
                
                // Auto-redirect to review after 5 seconds if user doesn't interact
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        this.goToReview();
                    }
                }, 5000);
            }
        }
    }
    
    showEnhancedErrorAlert(errorMessage, taskId) {
        // Use unified notification system
        if (window.Vedfolnir && window.Vedfolnir.showNotification) {
            return window.Vedfolnir.showNotification(errorMessage, 'error', {
                title: 'Caption Generation Failed',
                duration: 10000,
                actions: [
                    {
                        label: 'Retry',
                        type: 'primary',
                        action: 'retry'
                    },
                    {
                        label: 'Details',
                        type: 'secondary',
                        action: 'details'
                    }
                ]
            });
        } else {
            // Fallback to legacy alert display
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="flex-grow-1">
                        <h6><i class="bi bi-exclamation-triangle"></i> Caption Generation Failed</h6>
                        <p class="mb-2">${errorMessage}</p>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-sm btn-outline-light" onclick="captionUI.retryTask('${taskId}')">
                                <i class="bi bi-arrow-clockwise"></i> Retry
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-light" onclick="captionUI.showErrorDetails('${taskId}')">
                                <i class="bi bi-info-circle"></i> Details
                            </button>
                        </div>
                    </div>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            const container = document.querySelector('.container');
            if (container) {
                container.insertBefore(alertDiv, container.firstChild);
                
                // Auto-dismiss after 10 seconds (longer for error messages)
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.remove();
                    }
                }, 10000);
            }
        }
    }
    
    showAlert(message, type) {
        // Use unified notification system
        if (window.Vedfolnir && window.Vedfolnir.showNotification) {
            const notificationType = type === 'danger' ? 'error' : type;
            return window.Vedfolnir.showNotification(message, notificationType, {
                duration: 5000
            });
        } else {
            // Fallback to legacy alert display
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            const container = document.querySelector('.container');
            if (container) {
                container.insertBefore(alertDiv, container.firstChild);
                
                // Auto-dismiss after 5 seconds
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.remove();
                    }
                }, 5000);
            }
        }
    }
    
    // Task management methods
    
    cancelTask(taskId) {
        this.showCancellationDialog(taskId);
    }
    
    showCancellationDialog(taskId) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-exclamation-triangle text-warning"></i>
                            Cancel Caption Generation
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p><strong>Are you sure you want to cancel this caption generation task?</strong></p>
                        <p class="text-muted">
                            <i class="bi bi-info-circle"></i>
                            This action cannot be undone. Any progress made will be lost, but you can start a new task at any time.
                        </p>
                        <div class="alert alert-warning">
                            <small>
                                <i class="bi bi-lightbulb"></i>
                                <strong>Tip:</strong> If the task seems stuck, cancelling and restarting often resolves the issue.
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x"></i> Keep Running
                        </button>
                        <button type="button" class="btn btn-danger" onclick="captionUI.confirmCancelTask('${taskId}')" data-bs-dismiss="modal">
                            <i class="bi bi-stop-circle"></i> Cancel Task
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up modal after it's hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }
    
    async confirmCancelTask(taskId) {
        const cancelBtn = document.querySelector(`button[onclick*="cancelTask('${taskId}')"]`);
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Cancelling...';
        }
        
        try {
            const response = await window.csrfHandler.secureFetch(`/api/caption_generation/cancel/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(data.message, 'success');
            } else {
                this.showAlert(data.error, 'danger');
                // Re-enable cancel button on error
                if (cancelBtn) {
                    cancelBtn.disabled = false;
                    cancelBtn.innerHTML = '<i class="bi bi-x-circle"></i> Cancel';
                }
            }
        } catch (error) {
            console.error('Error:', error);
            this.showAlert('An error occurred while cancelling the task.', 'danger');
            // Re-enable cancel button on error
            if (cancelBtn) {
                cancelBtn.disabled = false;
                cancelBtn.innerHTML = '<i class="bi bi-x-circle"></i> Cancel';
            }
        }
    }
    
    async retryTask(taskId) {
        if (!confirm('Retry this failed task with the same settings?')) {
            return;
        }
        
        const retryBtn = document.querySelector(`button[onclick*="retryTask('${taskId}')"]`);
        if (retryBtn) {
            retryBtn.disabled = true;
            retryBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>';
        }
        
        try {
            const response = await window.csrfHandler.secureFetch(`/api/caption_generation/retry/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Task retry started successfully!', 'success');
                // Refresh page to show new active task
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                this.showAlert(data.error || 'Failed to retry task', 'danger');
                if (retryBtn) {
                    retryBtn.disabled = false;
                    retryBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
                }
            }
        } catch (error) {
            console.error('Error:', error);
            this.showAlert('An error occurred while retrying the task.', 'danger');
            if (retryBtn) {
                retryBtn.disabled = false;
                retryBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
            }
        }
    }
    
    async showErrorDetails(taskId) {
        try {
            const response = await window.csrfHandler.secureFetch(`/api/caption_generation/error_details/${taskId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showErrorDetailsModal(data.error_details);
            } else {
                this.showAlert('Could not load error details', 'warning');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showAlert('An error occurred while loading error details.', 'danger');
        }
    }
    
    showErrorDetailsModal(errorDetails) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-exclamation-circle text-danger"></i>
                            Error Details & Recovery Suggestions
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-danger">
                            <h6><i class="bi bi-bug"></i> Error Message</h6>
                            <p class="mb-0">${errorDetails.message || 'Unknown error occurred'}</p>
                        </div>
                        
                        ${errorDetails.category ? `
                        <div class="alert alert-info">
                            <h6><i class="bi bi-info-circle"></i> Error Category</h6>
                            <p class="mb-0">${errorDetails.category}</p>
                        </div>
                        ` : ''}
                        
                        ${errorDetails.recovery_suggestions && errorDetails.recovery_suggestions.length > 0 ? `
                        <div class="alert alert-success">
                            <h6><i class="bi bi-lightbulb"></i> Recovery Suggestions</h6>
                            <ul class="mb-0">
                                ${errorDetails.recovery_suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        
                        <div class="alert alert-warning">
                            <h6><i class="bi bi-question-circle"></i> Need Help?</h6>
                            <p class="mb-2">If you continue to experience issues:</p>
                            <ul class="mb-0">
                                <li>Check your platform connection settings</li>
                                <li>Verify your internet connection</li>
                                <li>Try reducing the number of posts to process</li>
                                <li>Contact support if the problem persists</li>
                            </ul>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x"></i> Close
                        </button>
                        <button type="button" class="btn btn-primary" onclick="window.open('/docs/troubleshooting.html', '_blank')">
                            <i class="bi bi-book"></i> View Troubleshooting Guide
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up modal after it's hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }
    
    // Task history filtering
    
    initializeTaskFilters() {
        // Set default filter to 'all'
        const allFilterBtn = document.getElementById('filter-all');
        if (allFilterBtn) {
            allFilterBtn.classList.add('active');
        }
    }
    
    filterTasks(status) {
        const taskItems = document.querySelectorAll('.task-item');
        const filterButtons = document.querySelectorAll('[id^="filter-"]');
        
        // Update button states
        filterButtons.forEach(btn => btn.classList.remove('active'));
        document.getElementById(`filter-${status}`).classList.add('active');
        
        // Filter task items
        taskItems.forEach(item => {
            if (status === 'all' || item.dataset.status === status) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    // Navigation methods
    
    goToReview() {
        window.location.href = '/review/batches';
    }
    
    startNewTask() {
        window.location.reload();
    }
}

// Initialize the caption generation UI when the page loads
let captionUI;
document.addEventListener('DOMContentLoaded', function() {
    captionUI = new CaptionGenerationUI();
});

// Global functions for backward compatibility
function cancelTask(taskId) {
    if (captionUI) captionUI.cancelTask(taskId);
}

function retryTask(taskId) {
    if (captionUI) captionUI.retryTask(taskId);
}

function showErrorDetails(taskId) {
    if (captionUI) captionUI.showErrorDetails(taskId);
}

function filterTasks(status) {
    if (captionUI) captionUI.filterTasks(status);
}