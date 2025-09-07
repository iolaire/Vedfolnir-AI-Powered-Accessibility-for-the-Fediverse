// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Progress Bar Utility Functions
 * 
 * This module provides utility functions for updating progress bars using CSS custom properties
 * instead of inline styles. This ensures CSP compliance and maintains security best practices.
 * 
 * All progress bar updates should use these utility functions to maintain consistency
 * and avoid inline style violations.
 */

class ProgressBarUtils {
    constructor() {
        this.defaultTransition = 'width 0.3s ease';
        this.init();
    }
    
    init() {
        // Initialize all progress bars on page load
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeAllProgressBars();
        });
        
        // Also initialize immediately if DOM is already loaded
        if (document.readyState !== 'loading') {
            this.initializeAllProgressBars();
        }
    }
    
    /**
     * Initialize all progress bars with data-progress-width attributes
     */
    initializeAllProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar-dynamic');
        
        progressBars.forEach(progressBar => {
            this.initializeProgressBar(progressBar);
        });
        
        console.log(`Initialized ${progressBars.length} progress bars with CSS custom properties`);
    }
    
    /**
     * Initialize a single progress bar from its data attribute
     * @param {HTMLElement} progressBar - The progress bar element
     */
    initializeProgressBar(progressBar) {
        if (progressBar && progressBar.dataset.progressWidth) {
            const width = progressBar.dataset.progressWidth;
            this.setProgressBarWidth(progressBar, width);
        }
    }
    
    /**
     * Update a progress bar's width using CSS custom properties
     * @param {HTMLElement} progressBarElement - The progress bar element
     * @param {number|string} percentage - The percentage value (0-100)
     * @param {Object} options - Additional options
     */
    updateProgressBar(progressBarElement, percentage, options = {}) {
        if (!progressBarElement) {
            console.warn('Progress bar element not found');
            return;
        }
        
        const {
            updateText = true,
            updateAriaValue = true,
            animate = true,
            customClass = null
        } = options;
        
        // Ensure percentage is a number
        const numericPercentage = typeof percentage === 'string' 
            ? parseFloat(percentage.replace('%', '')) 
            : percentage;
        
        // Clamp percentage between 0 and 100
        const clampedPercentage = Math.max(0, Math.min(100, numericPercentage));
        const percentageStr = clampedPercentage + '%';
        
        // Set CSS custom property for width
        progressBarElement.style.setProperty('--progress-width', percentageStr);
        
        // Update aria-valuenow for accessibility
        if (updateAriaValue) {
            progressBarElement.setAttribute('aria-valuenow', clampedPercentage);
        }
        
        // Update text content if it contains a percentage
        if (updateText) {
            this.updateProgressBarText(progressBarElement, percentageStr);
        }
        
        // Add custom class if provided
        if (customClass) {
            progressBarElement.classList.add(customClass);
        }
        
        // Add transition if animate is true
        if (animate && !progressBarElement.style.transition) {
            progressBarElement.style.transition = this.defaultTransition;
        }
        
        console.log(`Updated progress bar to ${percentageStr}`);
    }
    
    /**
     * Update progress bar by ID
     * @param {string} id - The element ID
     * @param {number|string} percentage - The percentage value
     * @param {Object} options - Additional options
     */
    updateProgressBarById(id, percentage, options = {}) {
        const progressBar = document.getElementById(id);
        if (progressBar) {
            this.updateProgressBar(progressBar, percentage, options);
        } else {
            console.warn(`Progress bar with ID '${id}' not found`);
        }
    }
    
    /**
     * Update progress bar by CSS selector
     * @param {string} selector - The CSS selector
     * @param {number|string} percentage - The percentage value
     * @param {Object} options - Additional options
     */
    updateProgressBarBySelector(selector, percentage, options = {}) {
        const progressBar = document.querySelector(selector);
        if (progressBar) {
            this.updateProgressBar(progressBar, percentage, options);
        } else {
            console.warn(`Progress bar with selector '${selector}' not found`);
        }
    }
    
    /**
     * Update multiple progress bars by CSS selector
     * @param {string} selector - The CSS selector
     * @param {number|string} percentage - The percentage value
     * @param {Object} options - Additional options
     */
    updateProgressBarsBySelector(selector, percentage, options = {}) {
        const progressBars = document.querySelectorAll(selector);
        progressBars.forEach(progressBar => {
            this.updateProgressBar(progressBar, percentage, options);
        });
        
        if (progressBars.length === 0) {
            console.warn(`No progress bars found with selector '${selector}'`);
        }
    }
    
    /**
     * Set progress bar width directly (internal method)
     * @param {HTMLElement} progressBar - The progress bar element
     * @param {string} width - The width value (should include %)
     */
    setProgressBarWidth(progressBar, width) {
        progressBar.style.setProperty('--progress-width', width);
    }
    
    /**
     * Update progress bar text content
     * @param {HTMLElement} progressBar - The progress bar element
     * @param {string} text - The text to display
     */
    updateProgressBarText(progressBar, text) {
        // Look for text content that contains a percentage
        const textElement = progressBar.querySelector('.progress-text') || progressBar;
        const currentText = textElement.textContent.trim();
        
        if (currentText.includes('%') || currentText === '' || currentText === '0') {
            textElement.textContent = text;
        }
    }
    
    /**
     * Animate progress bar to a target percentage
     * @param {HTMLElement} progressBarElement - The progress bar element
     * @param {number} targetPercentage - The target percentage
     * @param {Object} options - Animation options
     */
    animateProgressBar(progressBarElement, targetPercentage, options = {}) {
        if (!progressBarElement) return;
        
        const {
            duration = 1000,
            easing = 'ease',
            onComplete = null,
            updateText = true
        } = options;
        
        // Get current percentage
        const currentWidth = progressBarElement.style.getPropertyValue('--progress-width') || '0%';
        const currentPercentage = parseFloat(currentWidth.replace('%', ''));
        
        // Set up animation
        const startTime = performance.now();
        const percentageDiff = targetPercentage - currentPercentage;
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Apply easing (simple ease-out)
            const easedProgress = easing === 'ease-out' 
                ? 1 - Math.pow(1 - progress, 3)
                : progress;
            
            const currentValue = currentPercentage + (percentageDiff * easedProgress);
            
            this.updateProgressBar(progressBarElement, currentValue, {
                updateText,
                animate: false // Disable CSS transition during JS animation
            });
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else if (onComplete) {
                onComplete();
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    /**
     * Reset progress bar to 0%
     * @param {HTMLElement} progressBarElement - The progress bar element
     * @param {Object} options - Reset options
     */
    resetProgressBar(progressBarElement, options = {}) {
        this.updateProgressBar(progressBarElement, 0, options);
    }
    
    /**
     * Complete progress bar (set to 100%)
     * @param {HTMLElement} progressBarElement - The progress bar element
     * @param {Object} options - Completion options
     */
    completeProgressBar(progressBarElement, options = {}) {
        const defaultOptions = {
            customClass: 'bg-success',
            ...options
        };
        this.updateProgressBar(progressBarElement, 100, defaultOptions);
    }
    
    /**
     * Set progress bar to error state
     * @param {HTMLElement} progressBarElement - The progress bar element
     * @param {number} percentage - Current percentage when error occurred
     * @param {Object} options - Error options
     */
    setProgressBarError(progressBarElement, percentage, options = {}) {
        const defaultOptions = {
            customClass: 'bg-danger',
            updateText: false,
            ...options
        };
        this.updateProgressBar(progressBarElement, percentage, defaultOptions);
        
        // Update text to show error
        if (options.errorText) {
            this.updateProgressBarText(progressBarElement, options.errorText);
        }
    }
    
    /**
     * Create a new progress bar element with proper structure
     * @param {Object} config - Progress bar configuration
     * @returns {HTMLElement} The created progress bar container
     */
    createProgressBar(config = {}) {
        const {
            id = null,
            percentage = 0,
            height = 'md',
            showText = true,
            animated = false,
            striped = false,
            className = ''
        } = config;
        
        const container = document.createElement('div');
        container.className = `progress progress-${height} ${className}`;
        
        const progressBar = document.createElement('div');
        progressBar.className = `progress-bar progress-bar-dynamic ${animated ? 'progress-bar-animated' : ''} ${striped ? 'progress-bar-striped' : ''}`;
        progressBar.setAttribute('role', 'progressbar');
        progressBar.setAttribute('aria-valuenow', percentage);
        progressBar.setAttribute('aria-valuemin', '0');
        progressBar.setAttribute('aria-valuemax', '100');
        progressBar.style.setProperty('--progress-width', percentage + '%');
        
        if (id) {
            progressBar.id = id;
        }
        
        if (showText) {
            const textSpan = document.createElement('span');
            textSpan.className = 'progress-text';
            textSpan.textContent = percentage + '%';
            progressBar.appendChild(textSpan);
        }
        
        container.appendChild(progressBar);
        return container;
    }
}

// Create global instance
const progressBarUtils = new ProgressBarUtils();

// Make it globally available
window.progressBarUtils = progressBarUtils;

// Also provide backward compatibility with the old initializer
window.progressBarInitializer = {
    updateProgressBar: (element, percentage) => progressBarUtils.updateProgressBar(element, percentage),
    updateProgressBarById: (id, percentage) => progressBarUtils.updateProgressBarById(id, percentage),
    updateProgressBarBySelector: (selector, percentage) => progressBarUtils.updateProgressBarBySelector(selector, percentage)
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgressBarUtils;
}