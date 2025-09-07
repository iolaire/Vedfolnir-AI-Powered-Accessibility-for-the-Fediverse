// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Progress Bar Initialization Utility
 * 
 * This utility initializes all progress bars that use the progress-bar-dynamic class
 * by setting their CSS custom property --progress-width from data-progress-width attributes.
 * This replaces inline style="width: X%" attributes for CSP compliance.
 */

class ProgressBarInitializer {
    constructor() {
        this.init();
    }
    
    init() {
        // Initialize all progress bars on page load
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeAllProgressBars();
        });
        
        // Also initialize immediately if DOM is already loaded
        if (document.readyState === 'loading') {
            // DOM is still loading, event listener will handle it
        } else {
            // DOM is already loaded
            this.initializeAllProgressBars();
        }
    }
    
    initializeAllProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar-dynamic');
        
        progressBars.forEach(progressBar => {
            this.initializeProgressBar(progressBar);
        });
        
        console.log(`Initialized ${progressBars.length} progress bars`);
    }
    
    initializeProgressBar(progressBar) {
        if (progressBar.dataset.progressWidth) {
            progressBar.style.setProperty('--progress-width', progressBar.dataset.progressWidth);
        }
    }
    
    // Utility method to update a progress bar dynamically
    updateProgressBar(progressBarElement, percentage) {
        if (progressBarElement) {
            const percentageStr = percentage + '%';
            progressBarElement.style.setProperty('--progress-width', percentageStr);
            progressBarElement.setAttribute('aria-valuenow', percentage);
            
            // Update text content if it exists
            const textContent = progressBarElement.textContent.trim();
            if (textContent.includes('%')) {
                progressBarElement.textContent = percentageStr;
            }
        }
    }
    
    // Utility method to update progress bar by ID
    updateProgressBarById(id, percentage) {
        const progressBar = document.getElementById(id);
        this.updateProgressBar(progressBar, percentage);
    }
    
    // Utility method to update progress bar by selector
    updateProgressBarBySelector(selector, percentage) {
        const progressBar = document.querySelector(selector);
        this.updateProgressBar(progressBar, percentage);
    }
}

// Initialize the progress bar system
const progressBarInitializer = new ProgressBarInitializer();

// Make it globally available for other scripts
window.progressBarInitializer = progressBarInitializer;