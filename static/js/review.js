// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// Vedfolnir JavaScript functionality

// Unified Notification System Integration for Review Page
class ReviewNotificationManager {
    constructor() {
        // Initialize unified notification system
        this.initUnifiedSystem();
    }

    initUnifiedSystem() {
        // Initialize Vedfolnir notification system if available
        if (window.Vedfolnir) {
            window.Vedfolnir.initNotificationSystem();
        }
    }

    showNotification(message, type = 'info', options = {}) {
        // Use unified notification system
        if (window.Vedfolnir && window.Vedfolnir.showNotification) {
            return window.Vedfolnir.showNotification(message, type, options);
        } else {
            // Fallback to console logging
            console.log(`Review Notification (${type}): ${message}`);
        }
    }

    // Legacy method for backward compatibility
    showToast(message, type = 'info') {
        return this.showNotification(message, type);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize unified notification manager
    window.toastManager = new ReviewNotificationManager();
    
    // Find all Approve & Post buttons
    const approvePostButtons = document.querySelectorAll('.btn-approve-post');
    
    // Add click event listeners to each button
    approvePostButtons.forEach(button => {
        console.log('Found Approve & Post button for image ID:', button.dataset.imageId);
        
        button.addEventListener('click', async function() {
            const imageId = this.dataset.imageId;
            const batchItem = this.closest('.batch-item');
            const textarea = batchItem.querySelector('textarea');
            const caption = textarea.value.trim();
            
            if (!caption) {
                window.toastManager.showNotification('Please enter a caption before approving and posting.', 'warning');
                return;
            }
            
            // Disable button and show loading state
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Posting...';
            
            try {
                // Send the request to update and post the caption
                const response = await fetch(`/api/update_caption/${imageId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        caption: caption,
                        action: 'approve'
                    })
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    // Show success message
                    let message = 'Caption approved successfully!';
                    if (result.posted) {
                        message += ' Caption has been posted to Pixelfed.';
                    }
                    
                    // Update UI to show posted status
                    batchItem.classList.remove('rejected', 'skipped');
                    batchItem.classList.add('approved', 'posted');
                    batchItem.style.opacity = '0.5';
                    batchItem.querySelector('.batch-actions').innerHTML = '<span class="badge bg-success">Posted to Pixelfed</span>';
                    
                    // Show success notification
                    window.toastManager.showNotification(message, 'success');
                } else {
                    // Show error message
                    const errorMsg = 'Error: ' + (result.error || 'Failed to update caption');
                    window.toastManager.showNotification(errorMsg, 'error');
                    
                    // Reset button state
                    this.disabled = false;
                    this.innerHTML = '<i class="bi bi-cloud-upload"></i> Approve & Post';
                }
            } catch (error) {
                console.error('Error updating caption:', error);
                
                // Show error message
                window.toastManager.showNotification('Error: Failed to connect to server', 'error');
                
                // Reset button state
                this.disabled = false;
                this.innerHTML = '<i class="bi bi-cloud-upload"></i> Approve & Post';
            }
        });
    });
    
    // Find all Regenerate Caption buttons
    const regenerateButtons = document.querySelectorAll('.btn-regenerate');
    
    // Add click event listeners to each button
    regenerateButtons.forEach(button => {
        console.log('Found Regenerate button for image ID:', button.dataset.imageId);
        
        button.addEventListener('click', async function() {
            const imageId = this.dataset.imageId;
            const batchItem = this.closest('.batch-item');
            const textarea = batchItem.querySelector('textarea');
            const statusEl = batchItem.querySelector('.regenerate-status');
            
            // Save original button text
            const originalText = this.innerHTML;
            
            // Disable button and show loading state
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
            statusEl.textContent = 'Generating new caption...';
            statusEl.className = 'regenerate-status text-muted';
            
            try {
                // Send the request to regenerate the caption
                const response = await fetch(`/api/regenerate_caption/${imageId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    // Update caption field with new caption
                    textarea.value = result.caption;
                    statusEl.textContent = 'Caption regenerated successfully!';
                    statusEl.className = 'regenerate-status text-success';
                    
                    // Update category badge if available
                    if (result.category) {
                        const categoryBadge = batchItem.querySelector('.badge.bg-info');
                        if (categoryBadge) {
                            categoryBadge.textContent = result.category;
                        }
                        
                        // Reload the page to show updated quality metrics
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                } else {
                    statusEl.textContent = 'Error: ' + (result.error || 'Failed to regenerate caption');
                    statusEl.className = 'regenerate-status text-danger';
                }
            } catch (error) {
                console.error('Error regenerating caption:', error);
                statusEl.textContent = 'Error: Failed to connect to server';
                statusEl.className = 'regenerate-status text-danger';
            } finally {
                // Reset button state
                this.disabled = false;
                this.innerHTML = originalText;
                
                // Clear success message after 5 seconds
                if (statusEl.className.includes('text-success')) {
                    setTimeout(() => {
                        statusEl.textContent = '';
                    }, 5000);
                }
            }
        });
    });
});