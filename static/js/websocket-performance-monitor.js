// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Performance Monitor
 * 
 * Tracks WebSocket initialization performance and provides metrics
 * for comparing bundle vs individual script loading performance.
 */

class WebSocketPerformanceMonitor {
    constructor() {
        this.metrics = {
            startTime: performance.now(),
            scriptLoadTime: null,
            configFetchTime: null,
            connectionTime: null,
            statusUpdateTime: null,
            totalInitTime: null,
            errors: []
        };
        
        this.milestones = [];
        this.isMonitoring = true;
        
        console.log('🔍 WebSocket Performance Monitor initialized');
        this.recordMilestone('monitor_initialized');
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Listen for WebSocket status changes
        window.addEventListener('websocketStatusChange', (event) => {
            this.recordMilestone('status_changed', event.detail);
        });
        
        // Listen for DOM content loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.recordMilestone('dom_ready');
            });
        } else {
            this.recordMilestone('dom_already_ready');
        }
        
        // Listen for window load
        if (document.readyState !== 'complete') {
            window.addEventListener('load', () => {
                this.recordMilestone('window_loaded');
            });
        } else {
            this.recordMilestone('window_already_loaded');
        }
    }
    
    recordMilestone(name, data = null) {
        if (!this.isMonitoring) return;
        
        const timestamp = performance.now();
        const milestone = {
            name,
            timestamp,
            relativeTime: timestamp - this.metrics.startTime,
            data
        };
        
        this.milestones.push(milestone);
        
        // Update specific metrics
        switch (name) {
            case 'scripts_loaded':
                this.metrics.scriptLoadTime = milestone.relativeTime;
                break;
            case 'config_fetched':
                this.metrics.configFetchTime = milestone.relativeTime;
                break;
            case 'websocket_connected':
                this.metrics.connectionTime = milestone.relativeTime;
                break;
            case 'status_updated':
                this.metrics.statusUpdateTime = milestone.relativeTime;
                break;
            case 'initialization_complete':
                this.metrics.totalInitTime = milestone.relativeTime;
                this.isMonitoring = false;
                this.generateReport();
                break;
        }
        
        console.log(`📊 Milestone: ${name} at ${milestone.relativeTime.toFixed(2)}ms`);
    }
    
    recordError(error, context = '') {
        this.metrics.errors.push({
            error: error.message || error,
            context,
            timestamp: performance.now(),
            relativeTime: performance.now() - this.metrics.startTime
        });
        
        console.error(`❌ Performance Monitor Error [${context}]:`, error);
    }
    
    generateReport() {
        const report = {
            summary: {
                totalInitializationTime: this.metrics.totalInitTime,
                scriptLoadTime: this.metrics.scriptLoadTime,
                configFetchTime: this.metrics.configFetchTime,
                connectionTime: this.metrics.connectionTime,
                statusUpdateTime: this.metrics.statusUpdateTime,
                errorCount: this.metrics.errors.length
            },
            milestones: this.milestones,
            errors: this.metrics.errors,
            performance: {
                scriptsToConnection: this.metrics.connectionTime - (this.metrics.scriptLoadTime || 0),
                configToConnection: this.metrics.connectionTime - (this.metrics.configFetchTime || 0),
                connectionToStatus: (this.metrics.statusUpdateTime || 0) - (this.metrics.connectionTime || 0)
            },
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        console.log('📊 WebSocket Performance Report:', report);
        
        // Store report for analysis
        if (typeof localStorage !== 'undefined') {
            try {
                const reports = JSON.parse(localStorage.getItem('websocket_performance_reports') || '[]');
                reports.push(report);
                
                // Keep only last 10 reports
                if (reports.length > 10) {
                    reports.splice(0, reports.length - 10);
                }
                
                localStorage.setItem('websocket_performance_reports', JSON.stringify(reports));
                console.log('📊 Performance report saved to localStorage');
            } catch (error) {
                console.warn('Failed to save performance report:', error);
            }
        }
        
        return report;
    }
    
    getStoredReports() {
        if (typeof localStorage === 'undefined') return [];
        
        try {
            return JSON.parse(localStorage.getItem('websocket_performance_reports') || '[]');
        } catch (error) {
            console.warn('Failed to load stored performance reports:', error);
            return [];
        }
    }
    
    compareReports() {
        const reports = this.getStoredReports();
        if (reports.length < 2) {
            console.log('📊 Need at least 2 reports for comparison');
            return null;
        }
        
        const latest = reports[reports.length - 1];
        const previous = reports[reports.length - 2];
        
        const comparison = {
            totalInitTime: {
                latest: latest.summary.totalInitializationTime,
                previous: previous.summary.totalInitializationTime,
                improvement: previous.summary.totalInitializationTime - latest.summary.totalInitializationTime,
                percentImprovement: ((previous.summary.totalInitializationTime - latest.summary.totalInitializationTime) / previous.summary.totalInitializationTime * 100)
            },
            configFetchTime: {
                latest: latest.summary.configFetchTime,
                previous: previous.summary.configFetchTime,
                improvement: (previous.summary.configFetchTime || 0) - (latest.summary.configFetchTime || 0)
            },
            connectionTime: {
                latest: latest.summary.connectionTime,
                previous: previous.summary.connectionTime,
                improvement: (previous.summary.connectionTime || 0) - (latest.summary.connectionTime || 0)
            }
        };
        
        console.log('📊 Performance Comparison:', comparison);
        return comparison;
    }
    
    clearStoredReports() {
        if (typeof localStorage !== 'undefined') {
            localStorage.removeItem('websocket_performance_reports');
            console.log('📊 Cleared stored performance reports');
        }
    }
}

// Initialize performance monitor if enabled
if (window.location.search.includes('monitor=true') || window.location.search.includes('debug=true')) {
    window.WebSocketPerformanceMonitor = new WebSocketPerformanceMonitor();
    
    // Hook into WebSocket initialization
    const originalLog = console.log;
    console.log = function(...args) {
        originalLog.apply(console, args);
        
        if (window.WebSocketPerformanceMonitor) {
            const message = args.join(' ');
            
            if (message.includes('WebSocket bundle loaded successfully')) {
                window.WebSocketPerformanceMonitor.recordMilestone('scripts_loaded');
            } else if (message.includes('Server configuration pre-loaded successfully')) {
                window.WebSocketPerformanceMonitor.recordMilestone('config_fetched');
            } else if (message.includes('WebSocket connected successfully')) {
                window.WebSocketPerformanceMonitor.recordMilestone('websocket_connected');
            } else if (message.includes('WebSocket bundle initialization completed')) {
                window.WebSocketPerformanceMonitor.recordMilestone('initialization_complete');
            }
        }
    };
    
    console.log('🔍 WebSocket Performance Monitoring enabled');
}