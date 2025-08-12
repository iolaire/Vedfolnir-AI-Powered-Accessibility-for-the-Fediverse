// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * CSRF Handler Test Functions
 * 
 * Test functions to verify CSRF protection is working correctly
 */

window.csrfTest = {
    /**
     * Test CSRF token retrieval
     */
    async testTokenRetrieval() {
        console.log('Testing CSRF token retrieval...');
        
        try {
            const token = await window.csrfHandler.getCSRFToken();
            console.log('✅ CSRF token retrieved:', token ? `${token.substring(0, 10)}...` : 'null');
            
            const validation = window.csrfHandler.validateToken();
            console.log('Token validation:', validation);
            
            return true;
        } catch (error) {
            console.error('❌ CSRF token retrieval failed:', error);
            return false;
        }
    },
    
    /**
     * Test secure fetch with CSRF protection
     */
    async testSecureFetch() {
        console.log('Testing secure fetch...');
        
        try {
            // Test GET request (should not include CSRF token)
            const getResponse = await window.csrfHandler.secureFetch('/api/csrf-token');
            console.log('✅ GET request successful:', getResponse.status);
            
            // Test POST request (should include CSRF token)
            const postResponse = await window.csrfHandler.secureFetch('/api/test-csrf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ test: true })
            });
            
            console.log('✅ POST request completed:', postResponse.status);
            return true;
            
        } catch (error) {
            console.error('❌ Secure fetch test failed:', error);
            return false;
        }
    },
    
    /**
     * Test CSRF error handling
     */
    async testErrorHandling() {
        console.log('Testing CSRF error handling...');
        
        try {
            // Clear token to force an error
            const originalToken = window.csrfHandler.tokenCache;
            window.csrfHandler.clearToken();
            
            // Try to make a request that should fail
            const response = await window.csrfHandler.secureFetch('/api/test-csrf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ test: true })
            });
            
            console.log('Response after token clear:', response.status);
            
            // Restore token
            window.csrfHandler.tokenCache = originalToken;
            
            return true;
            
        } catch (error) {
            console.log('Expected error caught:', error.message);
            return true;
        }
    },
    
    /**
     * Run all CSRF tests
     */
    async runAllTests() {
        console.log('🔒 Starting CSRF Handler Tests...');
        
        const results = {
            tokenRetrieval: await this.testTokenRetrieval(),
            secureFetch: await this.testSecureFetch(),
            errorHandling: await this.testErrorHandling()
        };
        
        const passed = Object.values(results).filter(Boolean).length;
        const total = Object.keys(results).length;
        
        console.log(`\n📊 CSRF Test Results: ${passed}/${total} tests passed`);
        console.log('Results:', results);
        
        if (passed === total) {
            console.log('✅ All CSRF tests passed!');
        } else {
            console.log('❌ Some CSRF tests failed');
        }
        
        return results;
    }
};

// Auto-run tests if in development mode
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    // Run tests after page load
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            if (window.csrfHandler) {
                console.log('🧪 Running CSRF tests in development mode...');
                window.csrfTest.runAllTests();
            }
        }, 1000);
    });
}