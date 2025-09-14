// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Playwright Configuration for Admin Interface Testing
 */

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/admin/playwright',
  
  // Run tests in files in parallel
  fullyParallel: false,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 1,
  
  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : 1,
  
  // Reporter to use
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit-results.xml' }]
  ],
  
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: 'http://127.0.0.1:5000',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Take screenshot on failure
    screenshot: 'only-on-failure',
    
    // Record video on failure
    video: 'retain-on-failure',
    
    // Browser to use (WebKit as specified in requirements)
    browserName: 'webkit',
    
    // Headless mode (false for debugging)
    headless: false,
    
    // Viewport size
    viewport: { width: 1280, height: 720 },
    
    // Timeout for actions
    actionTimeout: 30000,
    
    // Timeout for navigation
    navigationTimeout: 30000,
    
    // Ignore HTTPS errors (for local development)
    ignoreHTTPSErrors: true,
    
    // Extra HTTP headers
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9',
    },
  },

  // Configure projects for different browsers (focus on WebKit as required)
  projects: [
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  // Global setup and teardown
  globalSetup: './tests/admin/playwright/helpers/global-setup.js',
  globalTeardown: './tests/admin/playwright/helpers/global-teardown.js',

  // Web server configuration (app should already be running)
  webServer: {
    url: 'http://127.0.0.1:5000',
    reuseExistingServer: true,
    timeout: 10000,
  },

  // Expect options
  expect: {
    timeout: 10000,
  },

  // Test output directory
  outputDir: 'test-results/',

  // Metadata
  metadata: {
    project: 'Vedfolnir Admin Interface Testing',
    version: '1.0.0',
    testType: 'admin-interface',
  },
});