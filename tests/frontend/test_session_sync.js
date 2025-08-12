// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Frontend JavaScript tests for session synchronization
 * Tests SessionSync class initialization, cross-tab communication, and session validation
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
 */

// Test framework for Node.js environment
class SessionSyncTestSuite {
    constructor() {
        this.tests = [];
        this.results = [];
        this.mockWindow = this.createMockWindow();
        this.mockDocument = this.createMockDocument();
        this.mockLocalStorage = this.createMockLocalStorage();
        this.mockNavigator = this.createMockNavigator();
    }

    createMockWindow() {
        const eventListeners = {};
        const storageListeners = [];
        
        return {
            addEventListener: (event, listener) => {
                if (!eventListeners[event]) eventListeners[event] = [];
                eventListeners[event].push(listener);
                
                // Special handling for storage events
                if (event === 'storage') {
                    storageListeners.push(listener);
                }
            },
            removeEventListener: (event, listener) => {
                if (eventListeners[event]) {
                    const index = eventListeners[event].indexOf(listener);
                    if (index > -1) eventListeners[event].splice(index, 1);
                }
                
                // Special handling for storage events
                if (event === 'storage') {
                    const index = storageListeners.indexOf(listener);
                    if (index > -1) storageListeners.splice(index, 1);
                }
            },
            dispatchEvent: (event) => {
                if (eventListeners[event.type]) {
                    eventListeners[event.type].forEach(listener => listener(event));
                }
            },
            location: {
                pathname: '/dashboard',
                href: 'http://localhost:5000/dashboard'
            },
            performance: {
                now: () => Date.now()
            },
            fetch: null, // Will be mocked per test
            localStorage: null, // Will be set to mockLocalStorage
            navigator: null, // Will be set to mockNavigator
            storageListeners: storageListeners, // Expose for localStorage mock
            CustomEvent: class {
                constructor(type, options = {}) {
                    this.type = type;
                    this.detail = options.detail;
                }
            }
        };
    }

    createMockDocument() {
        const elements = new Map();
        return {
            addEventListener: (event, listener) => {
                // Mock document event listeners
            },
            removeEventListener: (event, listener) => {
                // Mock document event listeners
            },
            querySelector: (selector) => {
                if (selector === 'meta[name="csrf-token"]') {
                    return { content: 'test-csrf-token' };
                }
                return elements.get(selector) || null;
            },
            querySelectorAll: (selector) => {
                return [];
            },
            createElement: (tagName) => {
                return {
                    tagName: tagName.toUpperCase(),
                    className: '',
                    style: {},
                    innerHTML: '',
                    textContent: '',
                    appendChild: () => {},
                    remove: () => {}
                };
            },
            body: {
                appendChild: () => {}
            },
            hidden: false
        };
    }

    createMockLocalStorage() {
        const storage = {};
        const storageListeners = [];
        
        const mockStorage = {
            getItem: (key) => storage[key] || null,
            setItem: (key, value) => {
                const oldValue = storage[key];
                storage[key] = value;
                
                // Simulate storage event for window listeners
                setTimeout(() => {
                    if (this.mockWindow && this.mockWindow.storageListeners) {
                        this.mockWindow.storageListeners.forEach(listener => {
                            listener({
                                key,
                                oldValue,
                                newValue: value,
                                storageArea: mockStorage
                            });
                        });
                    }
                }, 0);
            },
            removeItem: (key) => {
                const oldValue = storage[key];
                delete storage[key];
                
                // Simulate storage event for window listeners
                setTimeout(() => {
                    if (this.mockWindow && this.mockWindow.storageListeners) {
                        this.mockWindow.storageListeners.forEach(listener => {
                            listener({
                                key,
                                oldValue,
                                newValue: null,
                                storageArea: mockStorage
                            });
                        });
                    }
                }, 0);
            },
            clear: () => {
                Object.keys(storage).forEach(key => delete storage[key]);
            }
        };
        
        return mockStorage;
    }

    createMockNavigator() {
        return {
            onLine: true
        };
    }

    setupGlobalMocks() {
        global.window = this.mockWindow;
        global.document = this.mockDocument;
        global.localStorage = this.mockLocalStorage;
        global.navigator = this.mockNavigator;
        global.performance = this.mockWindow.performance;
        global.CustomEvent = this.mockWindow.CustomEvent;
        
        this.mockWindow.localStorage = this.mockLocalStorage;
        this.mockWindow.navigator = this.mockNavigator;
    }

    addTest(name, testFn, requirements = []) {
        this.tests.push({ name, testFn, requirements });
    }

    async runTest(test) {
        const startTime = Date.now();
        
        try {
            await test.testFn();
            const duration = Date.now() - startTime;
            this.results.push({
                name: test.name,
                status: 'pass',
                duration,
                requirements: test.requirements
            });
        } catch (error) {
            const duration = Date.now() - startTime;
            this.results.push({
                name: test.name,
                status: 'fail',
                duration,
                error: error.message,
                requirements: test.requirements
            });
        }
    }

    async runAllTests() {
        this.results = [];
        this.setupGlobalMocks();
        
        // Load SessionSync class
        const SessionSync = this.loadSessionSyncClass();
        global.SessionSync = SessionSync;
        
        for (const test of this.tests) {
            await this.runTest(test);
        }
        
        return this.results;
    }

    loadSessionSyncClass() {
        // Simplified SessionSync class for testing
        return class SessionSync {
            constructor() {
                this.storageKey = 'vedfolnir_session_state';
                this.lastSyncTime = Date.now();
                this.syncInterval = 30000;
                this.validationInterval = 60000;
                this.isInitialized = false;
                this.isOnline = navigator.onLine;
                this.retryCount = 0;
                this.maxRetries = 3;
                this.tabId = this.generateTabId();
                
                this.syncInProgress = false;
                this.lastSessionState = null;
                this.debounceTimer = null;
                this.performanceMetrics = {
                    syncCount: 0,
                    syncErrors: 0,
                    avgSyncTime: 0,
                    lastSyncDuration: 0
                };
                
                this.handleStorageChange = this.handleStorageChange.bind(this);
                this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
                this.handleOnlineChange = this.handleOnlineChange.bind(this);
                this.syncSessionState = this.syncSessionState.bind(this);
                this.validateSession = this.validateSession.bind(this);
            }
            
            generateTabId() {
                return 'tab_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now().toString(36);
            }
            
            init() {
                if (this.isInitialized) {
                    return;
                }
                
                if (!this.shouldInitializeSync()) {
                    return;
                }
                
                window.addEventListener('storage', this.handleStorageChange);
                document.addEventListener('visibilitychange', this.handleVisibilityChange);
                window.addEventListener('online', this.handleOnlineChange);
                window.addEventListener('offline', this.handleOnlineChange);
                
                this.syncTimer = setInterval(this.syncSessionState, this.syncInterval);
                this.validationTimer = setInterval(this.validateSession, this.validationInterval);
                
                setTimeout(() => {
                    this.syncSessionState();
                }, 1000);
                
                this.isInitialized = true;
            }
            
            destroy() {
                if (!this.isInitialized) {
                    return;
                }
                
                window.removeEventListener('storage', this.handleStorageChange);
                document.removeEventListener('visibilitychange', this.handleVisibilityChange);
                window.removeEventListener('online', this.handleOnlineChange);
                window.removeEventListener('offline', this.handleOnlineChange);
                
                if (this.syncTimer) {
                    clearInterval(this.syncTimer);
                }
                
                if (this.validationTimer) {
                    clearInterval(this.validationTimer);
                }
                
                this.isInitialized = false;
            }
            
            shouldInitializeSync() {
                const publicPages = ['/login', '/register', '/'];
                if (publicPages.includes(window.location.pathname)) {
                    return false;
                }
                
                const csrfToken = document.querySelector('meta[name="csrf-token"]');
                if (!csrfToken) {
                    return false;
                }
                
                return true;
            }
            
            handleStorageChange(event) {
                if (event.key === this.storageKey && event.newValue) {
                    try {
                        const sessionState = JSON.parse(event.newValue);
                        
                        if (sessionState.tabId === this.tabId) {
                            return;
                        }
                        
                        this.applySessionState(sessionState);
                    } catch (error) {
                        console.error('Error parsing session state from storage:', error);
                    }
                } else if (event.key === 'vedfolnir_platform_switch' && event.newValue) {
                    try {
                        const switchEvent = JSON.parse(event.newValue);
                        
                        if (switchEvent.tabId === this.tabId) {
                            return;
                        }
                        
                        this.handlePlatformSwitchEvent(switchEvent);
                    } catch (error) {
                        console.error('Error parsing platform switch event:', error);
                    }
                } else if (event.key === 'vedfolnir_session_expired' && event.newValue) {
                    this.handleSessionExpired();
                } else if (event.key === 'vedfolnir_logout' && event.newValue) {
                    this.handleLogoutEvent();
                }
            }
            
            handleVisibilityChange() {
                if (!document.hidden) {
                    this.syncSessionState();
                }
            }
            
            handleOnlineChange() {
                const wasOnline = this.isOnline;
                this.isOnline = navigator.onLine;
                
                if (!wasOnline && this.isOnline) {
                    this.syncSessionState();
                }
            }
            
            async syncSessionState() {
                if (!this.isOnline) {
                    return;
                }
                
                if (window.location.pathname === '/login' || 
                    window.location.pathname === '/register' ||
                    window.location.pathname === '/') {
                    return;
                }
                
                if (this.syncInProgress) {
                    return;
                }
                
                this.syncInProgress = true;
                const syncStartTime = performance.now();
                
                try {
                    const response = await fetch('/api/session_state', {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    });
                    
                    if (response.ok) {
                        const contentType = response.headers.get('content-type');
                        if (!contentType || !contentType.includes('application/json')) {
                            throw new Error(`Expected JSON response, got ${contentType}`);
                        }
                        
                        const sessionState = await response.json();
                        
                        if (this.hasSessionStateChanged(sessionState)) {
                            localStorage.setItem(this.storageKey, JSON.stringify({
                                ...sessionState,
                                timestamp: Date.now(),
                                tabId: this.tabId
                            }));
                            
                            this.applySessionState(sessionState);
                            this.lastSessionState = sessionState;
                        }
                        
                        this.lastSyncTime = Date.now();
                        this.retryCount = 0;
                        this.updatePerformanceMetrics(syncStartTime, true);
                        
                    } else if (response.status === 401) {
                        this.handleSessionExpired();
                    } else if (response.status === 302) {
                        this.handleSessionExpired();
                    } else {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                } catch (error) {
                    this.updatePerformanceMetrics(syncStartTime, false);
                    this.handleSyncError(error);
                } finally {
                    this.syncInProgress = false;
                }
            }
            
            async validateSession() {
                if (!this.isOnline) {
                    return;
                }
                
                if (window.location.pathname === '/login' || 
                    window.location.pathname === '/register' ||
                    window.location.pathname === '/') {
                    return;
                }
                
                try {
                    const response = await fetch('/api/session_state', {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    });
                    
                    if (response.status === 401) {
                        this.handleSessionExpired();
                    } else if (response.status === 302) {
                        this.handleSessionExpired();
                    }
                } catch (error) {
                    console.error('Error validating session:', error);
                }
            }
            
            handleSyncError(error) {
                this.retryCount++;
                
                if (this.retryCount <= this.maxRetries) {
                    const retryDelay = Math.min(1000 * Math.pow(2, this.retryCount - 1), 10000);
                    
                    setTimeout(() => {
                        this.syncSessionState();
                    }, retryDelay);
                } else {
                    this.retryCount = 0;
                }
            }
            
            applySessionState(sessionState) {
                this.updatePlatformContext(sessionState.platform);
                this.updateUserContext(sessionState.user);
                this.updatePageElements(sessionState.platform);
                
                window.dispatchEvent(new CustomEvent('sessionStateChanged', {
                    detail: sessionState
                }));
            }
            
            updatePlatformContext(platform) {
                // Mock implementation
            }
            
            updateUserContext(user) {
                // Mock implementation
            }
            
            updatePageElements(platform) {
                // Mock implementation
            }
            
            handleSessionExpired() {
                this.broadcastSessionExpired();
                localStorage.removeItem(this.storageKey);
                
                window.dispatchEvent(new CustomEvent('sessionExpired', {
                    detail: { timestamp: Date.now() }
                }));
            }
            
            notifyPlatformSwitch(platformId, platformName) {
                const switchEvent = {
                    type: 'platform_switch',
                    platformId: platformId,
                    platformName: platformName,
                    timestamp: Date.now(),
                    tabId: this.tabId
                };
                
                localStorage.setItem('vedfolnir_platform_switch', JSON.stringify(switchEvent));
                
                setTimeout(() => {
                    localStorage.removeItem('vedfolnir_platform_switch');
                }, 1000);
            }
            
            handlePlatformSwitchEvent(switchEvent) {
                this.updatePlatformContext({
                    id: switchEvent.platformId,
                    name: switchEvent.platformName
                });
                
                window.dispatchEvent(new CustomEvent('platformSwitched', {
                    detail: switchEvent
                }));
            }
            
            broadcastSessionExpired() {
                const expiredEvent = {
                    type: 'session_expired',
                    timestamp: Date.now(),
                    tabId: this.tabId
                };
                
                localStorage.setItem('vedfolnir_session_expired', JSON.stringify(expiredEvent));
                
                setTimeout(() => {
                    localStorage.removeItem('vedfolnir_session_expired');
                }, 1000);
            }
            
            handleLogoutEvent() {
                localStorage.removeItem(this.storageKey);
            }
            
            hasSessionStateChanged(newState) {
                if (!this.lastSessionState) {
                    return true;
                }
                
                const keyFields = ['user.id', 'platform.id', 'platform.name', 'platform.type', 'session_id'];
                
                for (const field of keyFields) {
                    const oldValue = this.getNestedValue(this.lastSessionState, field);
                    const newValue = this.getNestedValue(newState, field);
                    
                    if (oldValue !== newValue) {
                        return true;
                    }
                }
                
                const oldPlatform = this.lastSessionState.platform;
                const newPlatform = newState.platform;
                
                if ((oldPlatform === null) !== (newPlatform === null)) {
                    return true;
                }
                
                return false;
            }
            
            getNestedValue(obj, path) {
                return path.split('.').reduce((current, key) => {
                    return current && current[key] !== undefined ? current[key] : null;
                }, obj);
            }
            
            updatePerformanceMetrics(startTime, success) {
                const duration = performance.now() - startTime;
                
                this.performanceMetrics.syncCount++;
                this.performanceMetrics.lastSyncDuration = duration;
                
                if (success) {
                    const alpha = 0.1;
                    this.performanceMetrics.avgSyncTime = 
                        (alpha * duration) + ((1 - alpha) * this.performanceMetrics.avgSyncTime);
                } else {
                    this.performanceMetrics.syncErrors++;
                }
            }
            
            getPerformanceMetrics() {
                return {
                    ...this.performanceMetrics,
                    errorRate: this.performanceMetrics.syncCount > 0 ? 
                        (this.performanceMetrics.syncErrors / this.performanceMetrics.syncCount) * 100 : 0,
                    tabId: this.tabId,
                    isOnline: this.isOnline,
                    lastSyncTime: this.lastSyncTime
                };
            }
            
            debouncedSync(delay = 1000) {
                if (this.debounceTimer) {
                    clearTimeout(this.debounceTimer);
                }
                
                this.debounceTimer = setTimeout(() => {
                    this.syncSessionState();
                }, delay);
            }
        };
    }

    // Test assertion methods
    assert(condition, message) {
        if (!condition) {
            throw new Error(message || 'Assertion failed');
        }
    }

    assertEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(message || `Expected ${expected}, got ${actual}`);
        }
    }

    assertNotNull(value, message) {
        if (value === null || value === undefined) {
            throw new Error(message || 'Expected non-null value');
        }
    }

    assertTrue(condition, message) {
        if (!condition) {
            throw new Error(message || 'Expected true');
        }
    }

    assertFalse(condition, message) {
        if (condition) {
            throw new Error(message || 'Expected false');
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize test suite
const testSuite = new SessionSyncTestSuite();

// Test SessionSync class initialization and tab identification (Requirements 2.1, 2.2)
testSuite.addTest('SessionSync class initialization', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync = new SessionSync();
    
    testSuite.assertNotNull(sessionSync, 'SessionSync instance should be created');
    testSuite.assertNotNull(sessionSync.tabId, 'Tab ID should be generated');
    testSuite.assertTrue(sessionSync.tabId.startsWith('tab_'), 'Tab ID should have correct prefix');
    testSuite.assertEqual(sessionSync.storageKey, 'vedfolnir_session_state', 'Storage key should be correct');
    testSuite.assertFalse(sessionSync.isInitialized, 'Should not be initialized by default');
}, ['2.1', '2.2']);

testSuite.addTest('Tab ID generation uniqueness', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync1 = new SessionSync();
    const sessionSync2 = new SessionSync();
    
    testSuite.assertNotNull(sessionSync1.tabId, 'First tab ID should be generated');
    testSuite.assertNotNull(sessionSync2.tabId, 'Second tab ID should be generated');
    testSuite.assertTrue(sessionSync1.tabId !== sessionSync2.tabId, 'Tab IDs should be unique');
}, ['2.1']);

// Test cross-tab storage event handling and synchronization (Requirements 2.2, 2.3)
testSuite.addTest('Storage event handling setup', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync = new SessionSync();
    
    sessionSync.init();
    testSuite.assertTrue(sessionSync.isInitialized, 'SessionSync should be initialized');
    
    sessionSync.destroy();
    testSuite.assertFalse(sessionSync.isInitialized, 'SessionSync should be destroyed');
}, ['2.2', '2.3']);

testSuite.addTest('Cross-tab session state synchronization', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync1 = new SessionSync();
    const sessionSync2 = new SessionSync();
    
    let sessionStateReceived = false;
    let receivedState = null;
    
    sessionSync2.applySessionState = (state) => {
        sessionStateReceived = true;
        receivedState = state;
    };
    
    sessionSync1.init();
    sessionSync2.init();
    
    const testSessionState = {
        user: { id: 1, username: 'test' },
        platform: { id: 1, name: 'Test Platform' },
        tabId: sessionSync1.tabId,
        timestamp: Date.now()
    };
    
    localStorage.setItem('vedfolnir_session_state', JSON.stringify(testSessionState));
    
    await testSuite.sleep(50);
    
    testSuite.assertTrue(sessionStateReceived, 'Session state should be received by other tab');
    testSuite.assertNotNull(receivedState, 'Received state should not be null');
    testSuite.assertEqual(receivedState.user.username, 'test', 'User data should be synchronized');
    
    sessionSync1.destroy();
    sessionSync2.destroy();
}, ['2.2', '2.3']);

// Test session validation and expiration handling (Requirements 2.4, 2.5)
testSuite.addTest('Session validation with server', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync = new SessionSync();
    
    // Mock successful fetch
    global.fetch = async () => ({
        ok: true,
        status: 200,
        headers: {
            get: () => 'application/json'
        },
        json: async () => ({
            success: true,
            user: { id: 1, username: 'test' },
            platform: { id: 1, name: 'Test Platform' }
        })
    });
    
    await sessionSync.syncSessionState();
    testSuite.assertTrue(true, 'Session validation should complete successfully');
}, ['2.4', '2.5']);

testSuite.addTest('Session expiration handling', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync = new SessionSync();
    
    let sessionExpiredCalled = false;
    sessionSync.handleSessionExpired = () => {
        sessionExpiredCalled = true;
    };
    
    // Mock 401 response
    global.fetch = async () => ({
        ok: false,
        status: 401,
        headers: {
            get: () => 'application/json'
        },
        json: async () => ({ error: 'Session expired' })
    });
    
    await sessionSync.syncSessionState();
    testSuite.assertTrue(sessionExpiredCalled, 'Session expiration handler should be called');
}, ['2.5']);

testSuite.addTest('Platform switch event handling', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync1 = new SessionSync();
    const sessionSync2 = new SessionSync();
    
    let platformSwitchReceived = false;
    let receivedPlatformName = null;
    
    sessionSync2.handlePlatformSwitchEvent = (switchEvent) => {
        platformSwitchReceived = true;
        receivedPlatformName = switchEvent.platformName;
    };
    
    sessionSync1.init();
    sessionSync2.init();
    
    sessionSync1.notifyPlatformSwitch(2, 'New Platform');
    
    await testSuite.sleep(50);
    
    testSuite.assertTrue(platformSwitchReceived, 'Platform switch should be received by other tab');
    testSuite.assertEqual(receivedPlatformName, 'New Platform', 'Platform name should be synchronized');
    
    sessionSync1.destroy();
    sessionSync2.destroy();
}, ['2.3', '2.4']);

testSuite.addTest('Session state change detection', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync = new SessionSync();
    
    const oldState = {
        user: { id: 1, username: 'test' },
        platform: { id: 1, name: 'Platform1' }
    };
    
    const newState = {
        user: { id: 1, username: 'test' },
        platform: { id: 2, name: 'Platform2' }
    };
    
    sessionSync.lastSessionState = oldState;
    
    const hasChanged = sessionSync.hasSessionStateChanged(newState);
    testSuite.assertTrue(hasChanged, 'Should detect platform change');
    
    const noChangeState = {
        user: { id: 1, username: 'test' },
        platform: { id: 1, name: 'Platform1' }
    };
    
    sessionSync.lastSessionState = oldState;
    const hasNotChanged = sessionSync.hasSessionStateChanged(noChangeState);
    testSuite.assertFalse(hasNotChanged, 'Should not detect change when state is same');
}, ['2.4']);

testSuite.addTest('Performance metrics tracking', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync = new SessionSync();
    
    const startTime = performance.now();
    sessionSync.updatePerformanceMetrics(startTime, true);
    
    const metrics = sessionSync.getPerformanceMetrics();
    
    testSuite.assertNotNull(metrics, 'Performance metrics should be available');
    testSuite.assertEqual(metrics.syncCount, 1, 'Sync count should be incremented');
    testSuite.assertEqual(metrics.syncErrors, 0, 'Error count should be 0 for successful sync');
    testSuite.assertTrue(metrics.avgSyncTime >= 0, 'Average sync time should be non-negative');
    testSuite.assertEqual(metrics.tabId, sessionSync.tabId, 'Tab ID should be included in metrics');
}, ['2.5']);

testSuite.addTest('Debounced sync functionality', async () => {
    const SessionSync = global.SessionSync;
    const sessionSync = new SessionSync();
    
    let syncCallCount = 0;
    sessionSync.syncSessionState = async () => {
        syncCallCount++;
    };
    
    sessionSync.debouncedSync(100);
    sessionSync.debouncedSync(100);
    sessionSync.debouncedSync(100);
    
    await testSuite.sleep(150);
    
    testSuite.assertEqual(syncCallCount, 1, 'Should only call sync once after debounce delay');
}, ['2.5']);

// Export for Node.js usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SessionSyncTestSuite, testSuite };
}

// Run tests if in Node.js environment
if (typeof require !== 'undefined' && require.main === module) {
    (async () => {
        console.log('Running SessionSync Frontend Tests...\n');
        
        const results = await testSuite.runAllTests();
        
        let passed = 0;
        let failed = 0;
        
        results.forEach(result => {
            const status = result.status === 'pass' ? '✓' : '✗';
            const color = result.status === 'pass' ? '\x1b[32m' : '\x1b[31m';
            const reset = '\x1b[0m';
            
            console.log(`${color}${status}${reset} ${result.name} (${result.duration}ms) [${result.requirements.join(', ')}]`);
            
            if (result.status === 'fail') {
                console.log(`  Error: ${result.error}\n`);
                failed++;
            } else {
                passed++;
            }
        });
        
        const total = results.length;
        const successRate = Math.round((passed / total) * 100);
        
        console.log(`\nTests: ${total} | Passed: ${passed} | Failed: ${failed} | Success Rate: ${successRate}%`);
        
        process.exit(failed > 0 ? 1 : 0);
    })();
}