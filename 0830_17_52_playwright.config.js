// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Playwright Configuration for System Administration Testing
 * 
 * Comprehensive browser testing configuration for end-to-end system administration
 * validation across multiple browsers and environments.
 */

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  // Test directory
  testDir: './tests/playwright',
  
  // Test file patterns
  testMatch: '**/0910_16_30_test_security_management.js',
  
  // Global test timeout
  timeout: 120000,
  
  // Expect timeout for assertions
  expect: {
    timeout: 30000
  },
  
  // Test execution configuration
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : 1,
  
  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'tests/playwright/reports/html-report' }],
    ['json', { outputFile: 'tests/playwright/reports/test-results.json' }],
    ['junit', { outputFile: 'tests/playwright/reports/test-results.xml' }],
    ['list']
  ],
  
  // Global test configuration
  use: {
    // REQUIRED: Run with visible browser for debugging
    headless: false,
    
    // Base URL for tests
    baseURL: 'http://127.0.0.1:5000',
    
    // Browser context options
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    
    // Screenshots and videos
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Trace collection
    trace: 'retain-on-failure',
    
    // Action timeout
    actionTimeout: 15000,
    
    // Navigation timeout
    navigationTimeout: 30000,
    
    // Console log capture
    ignoreConsoleErrors: true
  },

  // Browser projects for cross-browser testing
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        headless: false,
        // Chrome-specific options
        launchOptions: {
          args: [
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--enable-logging',
            '--log-level=0'
          ]
        }
      },
    }
  ],

  // Web server configuration for local testing
  webServer: {
    command: 'python web_app.py',
    port: 5000,
    timeout: 120000,
    reuseExistingServer: !process.env.CI,
    env: {
      FLASK_ENV: 'testing',
      FLASK_HOST: '127.0.0.1',
      FLASK_PORT: '5000'
    }
  },

  // Test output directories
  outputDir: 'tests/playwright/test-results',
  
  // Metadata
  metadata: {
    testSuite: 'System Administration',
    version: '1.0.0',
    environment: 'testing',
    timestamp: new Date().toISOString()
  }
});