// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * CSRF Handler - Centralized CSRF token management for AJAX requests
 * 
 * Provides secure CSRF token handling with automatic injection,
 * token refresh, and error handling for all AJAX requests.
 */

class CSRFHandler {
    constructor() {
        this.tokenCache = null;
        this.tokenExpiry = null;
        this.refreshPromise = null;
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second
        
        // Initialize token from meta tag
        this.loadTokenFromMeta();
        
        // Set up automatic token refresh
        this.setupTokenRefresh();
        
        // Bind methods to preserve context
        this.getCSRFToken = this.getCSRFToken.bind(this);
        this.injectCSRFToken = this.injectCSRFToken.bind(this);
        this.handleCSRFError = this.handleCSRFError.bind(this);
    }
    
    /**
     * Load CSRF token from meta tag
     */
    loadTokenFromMeta() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            this.tokenCache = metaTag.getAttribute('content');
            // Assume token is valid for 1 hour from page load
            this.tokenExpiry = Date.now() + (60 * 60 * 1000);
            console.debug('CSRF token loaded from meta tag');
        } else {
            console.warn('CSRF meta tag not found');
        }
    }
    
    /**
     * Get current CSRF token
     * @returns {Promise<string>} CSRF token
     */
    async getCSRFToken() {
        // Return cached token if valid
        if (this.tokenCache && this.tokenExpiry && Date.now() < this.tokenExpiry) {
            return this.tokenCache;
        }
        
        // Refresh token if expired or missing
        return await this.refreshCSRFToken();
    }
    
    /**
     * Refresh CSRF token from server
     * @returns {Promise<string>} New CSRF token
     */
    async refreshCSRFToken() {
        // Prevent multiple simultaneous refresh requests
        if (this.refreshPromise) {
            return await this.refreshPromise;
        }
        
        this.refreshPromise = this._performTokenRefresh();
        
        try {
            const token = await this.refreshPromise;
            this.refreshPromise = null;
            return token;
        } catch (error) {
            this.refreshPromise = null;
            throw error;
        }
    }
    
    /**
     * Perform actual token refresh
     * @private
     */
    async _performTokenRefresh() {
        try {
            console.debug('Refreshing CSRF token...');
            
            const response = await fetch('/api/csrf-token', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Token refresh failed: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.csrf_token) {
                this.tokenCache = data.csrf_token;
                this.tokenExpiry = Date.now() + (55 * 60 * 1000); // 55 minutes
                
                // Update meta tag
                const metaTag = document.querySelector('meta[name=\"csrf-token\"]');
                if (metaTag) {
                    metaTag.setAttribute('content', this.tokenCache);
                }
                
                console.debug('CSRF token refreshed successfully');
                return this.tokenCache;
            } else {
                throw new Error('Invalid token refresh response');
            }
            
        } catch (error) {
            console.error('CSRF token refresh failed:', error);
            
            // Fallback to meta tag if available
            this.loadTokenFromMeta();
            if (this.tokenCache) {
                console.warn('Using fallback CSRF token from meta tag');
                return this.tokenCache;
            }
            
            throw new Error('CSRF token unavailable');
        }
    }
    
    /**
     * Inject CSRF token into request
     * @param {XMLHttpRequest|Headers|Object} request - Request object to modify
     * @param {string} [token] - Optional token to use (will fetch if not provided)
     * @returns {Promise<void>}
     */
    async injectCSRFToken(request, token = null) {
        try {
            const csrfToken = token || await this.getCSRFToken();
            
            if (request instanceof XMLHttpRequest) {
                // XMLHttpRequest
                request.setRequestHeader('X-CSRFToken', csrfToken);
            } else if (request instanceof Headers) {
                // Fetch Headers object
                request.set('X-CSRFToken', csrfToken);
            } else if (typeof request === 'object' && request.headers) {
                // Fetch options object
                if (request.headers instanceof Headers) {
                    request.headers.set('X-CSRFToken', csrfToken);
                } else {
                    request.headers['X-CSRFToken'] = csrfToken;
                }
            } else {
                console.warn('Unknown request type for CSRF injection:', typeof request);
            }
            
        } catch (error) {
            console.error('Failed to inject CSRF token:', error);
            throw error;
        }
    }
    
    /**
     * Handle CSRF validation errors
     * @param {Response} response - Response object
     * @param {Object} originalRequest - Original request configuration
     * @returns {Promise<Response>} Retry response or original response
     */
    async handleCSRFError(response, originalRequest = null) {
        if (response.status === 403) {
            try {
                const errorData = await response.clone().json();
                
                if (errorData.error && errorData.error.toLowerCase().includes('csrf')) {
                    console.warn('CSRF validation failed, attempting token refresh...');
                    
                    // Refresh token
                    await this.refreshCSRFToken();
                    
                    // Retry original request if provided
                    if (originalRequest && originalRequest.retry !== false) {
                        return await this.retryRequest(originalRequest);
                    }
                }
            } catch (parseError) {
                console.debug('Could not parse error response as JSON');
            }
        }
        
        return response;
    }
    
    /**
     * Retry a failed request with new CSRF token
     * @param {Object} requestConfig - Original request configuration
     * @returns {Promise<Response>} Retry response
     */
    async retryRequest(requestConfig) {
        try {
            // Prevent infinite retry loops
            const retryCount = requestConfig.retryCount || 0;
            if (retryCount >= this.retryAttempts) {
                throw new Error('Maximum CSRF retry attempts exceeded');
            }
            
            // Wait before retry
            if (retryCount > 0) {
                await this.delay(this.retryDelay * retryCount);
            }
            
            // Update request with new token
            const newToken = await this.getCSRFToken();
            const retryConfig = { ...requestConfig };
            retryConfig.retryCount = retryCount + 1;
            
            // Inject new token
            if (!retryConfig.headers) {
                retryConfig.headers = {};
            }
            retryConfig.headers['X-CSRFToken'] = newToken;
            
            console.debug(`Retrying request (attempt ${retryCount + 1}/${this.retryAttempts})`);
            
            const response = await fetch(requestConfig.url, retryConfig);
            
            // Handle nested CSRF errors
            if (response.status === 403) {
                return await this.handleCSRFError(response, retryConfig);
            }
            
            return response;
            
        } catch (error) {
            console.error('Request retry failed:', error);
            throw error;
        }
    }
    
    /**
     * Setup automatic token refresh before expiry
     */
    setupTokenRefresh() {
        // Refresh token 5 minutes before expiry
        const refreshInterval = 50 * 60 * 1000; // 50 minutes
        
        setInterval(async () => {
            if (this.tokenExpiry && Date.now() > (this.tokenExpiry - 5 * 60 * 1000)) {
                try {
                    await this.refreshCSRFToken();
                } catch (error) {
                    console.warn('Automatic CSRF token refresh failed:', error);
                }
            }
        }, refreshInterval);
    }
    
    /**
     * Create a fetch wrapper with automatic CSRF handling
     * @param {string} url - Request URL
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>} Response with CSRF handling
     */
    async secureFetch(url, options = {}) {
        try {
            // Clone options to avoid mutation
            const requestOptions = { ...options };
            
            // Add CSRF token for state-changing requests
            const method = (requestOptions.method || 'GET').toUpperCase();
            if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
                await this.injectCSRFToken(requestOptions);
            }
            
            // Add credentials and AJAX header
            requestOptions.credentials = requestOptions.credentials || 'same-origin';
            if (!requestOptions.headers) {
                requestOptions.headers = {};
            }
            requestOptions.headers['X-Requested-With'] = 'XMLHttpRequest';
            
            // Store original request for retry
            const originalRequest = {
                url,
                ...requestOptions,
                retry: requestOptions.retry !== false
            };
            
            // Make request
            const response = await fetch(url, requestOptions);
            
            // Handle CSRF errors
            if (response.status === 403) {
                return await this.handleCSRFError(response, originalRequest);
            }
            
            return response;
            
        } catch (error) {
            console.error('Secure fetch failed:', error);
            throw error;
        }
    }
    
    /**
     * Utility function to delay execution
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise<void>}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Validate current token (for debugging)
     * @returns {Object} Token validation info
     */
    validateToken() {
        return {
            hasToken: !!this.tokenCache,
            tokenLength: this.tokenCache ? this.tokenCache.length : 0,
            isExpired: this.tokenExpiry ? Date.now() > this.tokenExpiry : true,
            expiresIn: this.tokenExpiry ? Math.max(0, this.tokenExpiry - Date.now()) : 0,
            expiresAt: this.tokenExpiry ? new Date(this.tokenExpiry).toISOString() : null
        };
    }
    
    /**
     * Clear cached token (for testing or logout)
     */
    clearToken() {
        this.tokenCache = null;
        this.tokenExpiry = null;
        console.debug('CSRF token cache cleared');
    }
}

// Create global instance
window.csrfHandler = new CSRFHandler();

// Convenience functions for backward compatibility
window.getCSRFToken = () => window.csrfHandler.getCSRFToken();
window.secureFetch = (url, options) => window.csrfHandler.secureFetch(url, options);

// jQuery integration if available
if (typeof $ !== 'undefined') {
    // Set up jQuery AJAX defaults
    $.ajaxSetup({
        beforeSend: async function(xhr, settings) {
            // Only add CSRF token for state-changing requests
            const method = (settings.type || 'GET').toUpperCase();
            if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
                try {
                    const token = await window.csrfHandler.getCSRFToken();
                    xhr.setRequestHeader('X-CSRFToken', token);
                } catch (error) {
                    console.error('Failed to add CSRF token to jQuery request:', error);
                }
            }
            
            // Add AJAX header
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        }
    });
    
    // Handle CSRF errors globally
    $(document).ajaxError(async function(event, xhr, settings) {
        if (xhr.status === 403) {
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.error && response.error.toLowerCase().includes('csrf')) {
                    console.warn('jQuery AJAX CSRF error detected');
                    
                    // Refresh token for future requests
                    await window.csrfHandler.refreshCSRFToken();
                    
                    // Show user-friendly message
                    if (window.errorHandler && window.errorHandler.showNotification) {
                        window.errorHandler.showNotification(
                            'Security token expired. Please try your action again.',
                            'warning'
                        );
                    }
                }
            } catch (parseError) {
                console.debug('Could not parse jQuery AJAX error response');
            }
        }
    });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSRFHandler;
}

console.debug('CSRF Handler initialized');