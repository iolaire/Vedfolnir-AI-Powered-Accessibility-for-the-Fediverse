# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Landing Page Performance Tests

This module contains unit tests for landing page performance optimizations
including template caching, asset optimization, and database query minimization.
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import time
from flask import Flask, g
from flask_login import AnonymousUserMixin

# Import the modules we're testing
from utils.template_cache import (
    TemplateCacheManager, 
    cached_render_template, 
    get_template_cache_manager,
    get_template_cache_stats
)
from utils.asset_optimizer import (
    AssetOptimizer,
    get_asset_optimizer,
    get_critical_css,
    get_resource_hints
)
from app.services.monitoring.performance.monitors.performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    get_performance_monitor,
    monitor_performance,
    record_database_query
)
from app.services.performance.components.performance_context import (
    performance_context_processor,
    _determine_page_type,
    _should_enable_template_caching
)

class TestTemplateCaching(unittest.TestCase):
    """Test template caching functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache_manager = TemplateCacheManager(max_size=10, ttl_seconds=60)
    
    def test_cache_manager_initialization(self):
        """Test cache manager initializes correctly."""
        self.assertEqual(self.cache_manager.max_size, 10)
        self.assertEqual(self.cache_manager.ttl_seconds, 60)
        self.assertEqual(len(self.cache_manager.cache), 0)
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        with patch('utils.template_cache.request') as mock_request:
            mock_request.headers.get.side_effect = lambda key, default='': {
                'User-Agent': 'test-agent',
                'Accept-Language': 'en-US'
            }.get(key, default)
            
            key1 = self.cache_manager._generate_cache_key('landing.html', test_var='value1')
            key2 = self.cache_manager._generate_cache_key('landing.html', test_var='value2')
            key3 = self.cache_manager._generate_cache_key('landing.html', test_var='value1')
            
            # Different context should generate different keys
            self.assertNotEqual(key1, key2)
            # Same context should generate same key
            self.assertEqual(key1, key3)
    
    def test_template_caching_workflow(self):
        """Test complete template caching workflow."""
        template_name = 'landing.html'
        rendered_html = '<html><body>Test Landing Page</body></html>'
        context = {'test_var': 'test_value'}
        
        with patch('utils.template_cache.request') as mock_request:
            mock_request.headers.get.return_value = 'test-agent'
            
            # Initially no cached template
            cached = self.cache_manager.get_cached_template(template_name, **context)
            self.assertIsNone(cached)
            
            # Cache the template
            self.cache_manager.cache_template(template_name, rendered_html, **context)
            
            # Now should retrieve from cache
            cached = self.cache_manager.get_cached_template(template_name, **context)
            self.assertEqual(cached, rendered_html)
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        template_name = 'landing.html'
        rendered_html = '<html><body>Test</body></html>'
        
        with patch('utils.template_cache.request') as mock_request:
            mock_request.headers.get.return_value = 'test-agent'
            
            # Initial stats
            stats = self.cache_manager.get_cache_stats()
            self.assertEqual(stats['hits'], 0)
            self.assertEqual(stats['misses'], 0)
            
            # Cache miss
            cached = self.cache_manager.get_cached_template(template_name)
            self.assertIsNone(cached)
            
            stats = self.cache_manager.get_cache_stats()
            self.assertEqual(stats['misses'], 1)
            
            # Cache template and hit
            self.cache_manager.cache_template(template_name, rendered_html)
            cached = self.cache_manager.get_cached_template(template_name)
            self.assertEqual(cached, rendered_html)
            
            stats = self.cache_manager.get_cache_stats()
            self.assertEqual(stats['hits'], 1)
            self.assertEqual(stats['misses'], 1)
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        template_name = 'landing.html'
        rendered_html = '<html><body>Test</body></html>'
        
        with patch('utils.template_cache.request') as mock_request:
            mock_request.headers.get.return_value = 'test-agent'
            
            # Cache template
            self.cache_manager.cache_template(template_name, rendered_html)
            
            # Verify cached
            cached = self.cache_manager.get_cached_template(template_name)
            self.assertEqual(cached, rendered_html)
            
            # Invalidate
            result = self.cache_manager.invalidate_template(template_name)
            self.assertTrue(result)
            
            # Should be cache miss now
            cached = self.cache_manager.get_cached_template(template_name)
            self.assertIsNone(cached)

class TestAssetOptimization(unittest.TestCase):
    """Test asset optimization functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.optimizer = AssetOptimizer()
    
    def test_critical_css_generation(self):
        """Test critical CSS generation."""
        critical_css = self.optimizer.get_critical_css('landing')
        
        # Should contain essential CSS for landing page
        self.assertIn(':root', critical_css)
        self.assertIn('--primary-color', critical_css)
        self.assertIn('.landing-hero', critical_css)
        self.assertIn('.cta-button', critical_css)
        self.assertIn('@media', critical_css)  # Responsive styles
    
    def test_resource_hints_generation(self):
        """Test resource hints generation."""
        hints = self.optimizer.get_resource_hints('landing')
        
        # Should have all hint types
        self.assertIn('preload', hints)
        self.assertIn('dns_prefetch', hints)
        self.assertIn('preconnect', hints)
        
        # Should include font preloads
        preload_assets = hints['preload']
        font_preload = any('fonts.googleapis.com' in asset.get('href', '') for asset in preload_assets)
        self.assertTrue(font_preload)
        
        # Should include DNS prefetch for fonts
        dns_prefetch = hints['dns_prefetch']
        self.assertIn('fonts.googleapis.com', dns_prefetch)
        self.assertIn('fonts.gstatic.com', dns_prefetch)
    
    def test_preconnect_domains(self):
        """Test preconnect domains."""
        domains = self.optimizer.get_preconnect_domains()
        
        self.assertIn('https://fonts.googleapis.com', domains)
        self.assertIn('https://fonts.gstatic.com', domains)
    
    @patch('utils.asset_optimizer.current_app')
    @patch('utils.asset_optimizer.Path')
    def test_asset_hash_generation(self, mock_path, mock_app):
        """Test asset hash generation."""
        # Mock file system
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.open.return_value.__enter__.return_value.read.return_value = b'test content'
        mock_path.return_value = mock_file
        
        # Mock Flask app
        mock_app.static_folder = '/static'
        
        asset_hash = self.optimizer.generate_asset_hash('css/style.css')
        
        # Should generate a hash
        self.assertIsNotNone(asset_hash)
        self.assertEqual(len(asset_hash), 8)  # MD5 hash truncated to 8 chars
    
    @patch('utils.asset_optimizer.url_for')
    def test_versioned_asset_url(self, mock_url_for):
        """Test versioned asset URL generation."""
        mock_url_for.return_value = '/static/css/style.css'
        
        with patch.object(self.optimizer, 'generate_asset_hash', return_value='abc12345'):
            versioned_url = self.optimizer.get_versioned_asset_url('css/style.css')
            self.assertEqual(versioned_url, '/static/css/style.css?v=abc12345')

class TestPerformanceMonitoring(unittest.TestCase):
    """Test performance monitoring functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor(max_metrics=10, ttl_seconds=60)
    
    def test_performance_metrics_initialization(self):
        """Test performance metrics initialization."""
        metrics = PerformanceMetrics()
        
        self.assertIsNotNone(metrics.start_time)
        self.assertIsNone(metrics.end_time)
        self.assertEqual(metrics.database_queries, 0)
        self.assertEqual(metrics.cache_hits, 0)
        self.assertEqual(metrics.cache_misses, 0)
        self.assertEqual(metrics.user_type, 'anonymous')
    
    def test_performance_metrics_timing(self):
        """Test performance metrics timing."""
        metrics = PerformanceMetrics()
        
        # Simulate some processing time
        time.sleep(0.01)  # 10ms
        
        metrics.finish(200, 1024)
        
        self.assertIsNotNone(metrics.end_time)
        self.assertGreater(metrics.total_time_ms, 5)  # Should be at least 5ms
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(metrics.response_size, 1024)
    
    def test_request_monitoring_workflow(self):
        """Test complete request monitoring workflow."""
        with patch('app.services.performance.components.performance_monitor.g') as mock_g, \
             patch('app.services.performance.components.performance_monitor.request') as mock_request, \
             patch('app.services.performance.components.performance_monitor.current_user') as mock_user:
            
            mock_request.endpoint = 'main.index'
            mock_user.is_authenticated = False
            
            # Start monitoring
            metrics = self.monitor.start_request_monitoring()
            
            # Verify metrics stored in g
            self.assertEqual(mock_g.performance_metrics, metrics)
            self.assertEqual(metrics.route_name, 'main.index')
            self.assertEqual(metrics.user_type, 'anonymous')
            
            # Record some operations
            self.monitor.record_database_query()
            self.monitor.record_cache_hit()
            self.monitor.record_cache_miss()
            
            # Finish monitoring
            self.monitor.finish_request_monitoring(200, 2048)
            
            # Check aggregated stats
            stats = self.monitor.get_performance_summary()
            self.assertEqual(stats['total_requests'], 1)
            self.assertEqual(stats['anonymous_requests'], 1)
    
    def test_database_query_tracking(self):
        """Test database query tracking for anonymous users."""
        with patch('app.services.performance.components.performance_monitor.g') as mock_g:
            metrics = PerformanceMetrics()
            metrics.user_type = 'anonymous'
            mock_g.performance_metrics = metrics
            
            # No database queries initially
            self.assertEqual(metrics.database_queries, 0)
            
            # Record database queries
            self.monitor.record_database_query()
            self.monitor.record_database_query()
            
            self.assertEqual(metrics.database_queries, 2)
    
    def test_zero_database_queries_for_anonymous_users(self):
        """Test that anonymous users can have zero database queries."""
        with patch('app.services.performance.components.performance_monitor.g') as mock_g:
            metrics = PerformanceMetrics()
            metrics.user_type = 'anonymous'
            metrics.route_name = 'main.index'
            mock_g.performance_metrics = metrics
            
            # Finish request with zero database queries
            metrics.finish(200, 1024)
            self.monitor._update_aggregated_stats(metrics)
            
            stats = self.monitor.get_performance_summary()
            self.assertEqual(stats['database_queries_saved'], 1)
    
    @patch('app.services.performance.components.performance_monitor.wraps')
    def test_performance_monitoring_decorator(self, mock_wraps):
        """Test performance monitoring decorator."""
        # Mock the decorator behavior
        def mock_route():
            return "Test response"
        
        # Apply decorator
        decorated_route = monitor_performance(mock_route)
        
        # The decorator should wrap the function
        self.assertIsNotNone(decorated_route)

class TestPerformanceContextProcessor(unittest.TestCase):
    """Test performance context processor."""
    
    @patch('app.services.performance.components.performance_context.current_user')
    @patch('app.services.performance.components.performance_context.request')
    def test_performance_context_processor(self, mock_request, mock_user):
        """Test performance context processor."""
        mock_request.endpoint = 'main.index'
        mock_user.is_authenticated = False
        
        context = performance_context_processor()
        
        self.assertIn('performance', context)
        performance_data = context['performance']
        
        self.assertIn('page_type', performance_data)
        self.assertIn('resource_hints', performance_data)
        self.assertIn('critical_css', performance_data)
        self.assertIn('flags', performance_data)
        
        # Should be landing page for anonymous user on main.index
        self.assertEqual(performance_data['page_type'], 'landing')
        
        # Should enable template caching for anonymous users
        self.assertTrue(performance_data['flags']['enable_template_caching'])
    
    @patch('app.services.performance.components.performance_context.current_user')
    @patch('app.services.performance.components.performance_context.request')
    def test_page_type_determination(self, mock_request, mock_user):
        """Test page type determination."""
        # Test landing page for anonymous user
        mock_request.endpoint = 'main.index'
        mock_user.is_authenticated = False
        
        page_type = _determine_page_type()
        self.assertEqual(page_type, 'landing')
        
        # Test dashboard for authenticated user
        mock_user.is_authenticated = True
        page_type = _determine_page_type()
        self.assertEqual(page_type, 'dashboard')
    
    @patch('app.services.performance.components.performance_context.current_user')
    def test_template_caching_flag(self, mock_user):
        """Test template caching flag determination."""
        # Should enable for anonymous users
        mock_user.is_authenticated = False
        self.assertTrue(_should_enable_template_caching())
        
        # Should disable for authenticated users
        mock_user.is_authenticated = True
        self.assertFalse(_should_enable_template_caching())

class TestLandingPagePerformanceIntegration(unittest.TestCase):
    """Integration tests for landing page performance."""
    
    def setUp(self):
        """Set up test Flask app."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['TEMPLATE_CACHE_MAX_SIZE'] = 10
        self.app.config['TEMPLATE_CACHE_TTL_SECONDS'] = 60
        
        # Register context processor
        from app.services.performance.components.performance_context import register_performance_context_processor
        register_performance_context_processor(self.app)
    
    def test_template_cache_integration(self):
        """Test template cache integration."""
        with self.app.app_context():
            # Get cache manager
            cache_manager = get_template_cache_manager()
            
            # Should be initialized with app config
            self.assertEqual(cache_manager.max_size, 10)
            self.assertEqual(cache_manager.ttl_seconds, 60)
    
    def test_asset_optimizer_integration(self):
        """Test asset optimizer integration."""
        with self.app.app_context():
            # Get asset optimizer
            optimizer = get_asset_optimizer()
            
            # Should generate critical CSS
            critical_css = get_critical_css('landing')
            self.assertIn('.landing-hero', critical_css)
            
            # Should generate resource hints
            hints = get_resource_hints('landing')
            self.assertIn('preload', hints)
    
    def test_performance_monitor_integration(self):
        """Test performance monitor integration."""
        with self.app.app_context():
            # Get performance monitor
            monitor = get_performance_monitor()
            
            # Should track metrics
            with patch('app.services.performance.components.performance_monitor.g') as mock_g, \
                 patch('app.services.performance.components.performance_monitor.request') as mock_request:
                
                mock_request.endpoint = 'main.index'
                
                metrics = monitor.start_request_monitoring()
                self.assertIsNotNone(metrics)
                
                # Should store in g
                self.assertEqual(mock_g.performance_metrics, metrics)

if __name__ == '__main__':
    unittest.main()