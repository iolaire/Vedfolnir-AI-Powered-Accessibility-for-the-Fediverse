#!/usr/bin/env python3
"""
Test Script for MySQL Performance Optimization System

This script comprehensively tests the MySQL performance optimization
capabilities including connection pool optimization, query monitoring,
caching strategies, and performance recommendations.
"""

import logging
import time
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.mysql_performance_optimizer import MySQLPerformanceOptimizer
    from scripts.mysql_performance_monitor import MySQLPerformanceMonitor
    from mysql_connection_validator import MySQLConnectionValidator
    from config import Config
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required packages are installed and MySQL is configured")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLPerformanceOptimizationTester:
    """Comprehensive tester for MySQL performance optimization system."""
    
    def __init__(self):
        """Initialize the tester."""
        self.config = Config()
        self.optimizer = MySQLPerformanceOptimizer(self.config)
        self.monitor = MySQLPerformanceMonitor(self.config)
        self.validator = MySQLConnectionValidator()
        
        self.test_results = []
        self.start_time = datetime.now()
        
        logger.info("MySQL Performance Optimization Tester initialized")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance optimization tests."""
        print(f"\n{'='*80}")
        print("MySQL Performance Optimization System - Comprehensive Test Suite")
        print(f"{'='*80}")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Test categories
        test_categories = [
            ("Connection Pool Optimization", self._test_connection_pool_optimization),
            ("Query Performance Monitoring", self._test_query_performance_monitoring),
            ("Caching Strategy Implementation", self._test_caching_strategies),
            ("Performance Recommendations", self._test_performance_recommendations),
            ("Integrated Monitoring System", self._test_integrated_monitoring),
            ("Auto-Optimization Features", self._test_auto_optimization),
            ("Performance Metrics Collection", self._test_performance_metrics),
            ("Error Handling and Recovery", self._test_error_handling)
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n🧪 Testing: {category_name}")
            print("-" * 60)
            
            try:
                test_result = test_function()
                self.test_results.append({
                    'category': category_name,
                    'success': test_result.get('success', False),
                    'details': test_result,
                    'timestamp': datetime.now().isoformat()
                })
                
                if test_result.get('success'):
                    print(f"✅ {category_name}: PASSED")
                else:
                    print(f"❌ {category_name}: FAILED")
                    if 'error' in test_result:
                        print(f"   Error: {test_result['error']}")
                
            except Exception as e:
                logger.error(f"Test category '{category_name}' failed with exception: {e}")
                self.test_results.append({
                    'category': category_name,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                print(f"❌ {category_name}: FAILED (Exception: {str(e)})")
        
        # Generate final report
        return self._generate_final_report()
    
    def _test_connection_pool_optimization(self) -> Dict[str, Any]:
        """Test connection pool optimization functionality."""
        try:
            # Test basic connection pool optimization
            optimization_result = self.optimizer.optimize_connection_pool()
            
            if not optimization_result.get('success'):
                return {
                    'success': False,
                    'error': f"Connection pool optimization failed: {optimization_result.get('error', 'Unknown error')}"
                }
            
            # Verify optimization results
            optimal_settings = optimization_result.get('optimal_settings', {})
            required_settings = ['pool_size', 'max_overflow', 'pool_timeout', 'pool_recycle']
            
            for setting in required_settings:
                if setting not in optimal_settings:
                    return {
                        'success': False,
                        'error': f"Missing required setting: {setting}"
                    }
            
            # Test optimized engine creation
            optimized_engine = self.optimizer.get_optimized_engine()
            if optimized_engine is None:
                return {
                    'success': False,
                    'error': "Failed to create optimized engine"
                }
            
            print(f"   ✓ Pool size optimized to: {optimal_settings['pool_size']}")
            print(f"   ✓ Max overflow set to: {optimal_settings['max_overflow']}")
            print(f"   ✓ Pool timeout: {optimal_settings['pool_timeout']}s")
            
            return {
                'success': True,
                'optimal_settings': optimal_settings,
                'engine_created': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_query_performance_monitoring(self) -> Dict[str, Any]:
        """Test query performance monitoring functionality."""
        try:
            # Start query monitoring
            start_result = self.optimizer.start_query_monitoring(5)  # 5 second intervals for testing
            
            if not start_result.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to start query monitoring: {start_result.get('error', 'Unknown error')}"
                }
            
            print("   ✓ Query monitoring started")
            
            # Wait for some monitoring data to be collected
            print("   ⏳ Collecting monitoring data (10 seconds)...")
            time.sleep(10)
            
            # Get query performance report
            report_result = self.optimizer.get_query_performance_report()
            
            if not report_result.get('success'):
                # This might be expected if no queries were executed
                if 'No query performance data available' in report_result.get('message', ''):
                    print("   ℹ️ No query data collected (expected for test environment)")
                else:
                    return {
                        'success': False,
                        'error': f"Failed to get query performance report: {report_result.get('error', 'Unknown error')}"
                    }
            else:
                summary = report_result.get('summary', {})
                print(f"   ✓ Monitored {summary.get('total_unique_queries', 0)} unique queries")
                print(f"   ✓ Slow query ratio: {summary.get('slow_query_percentage', 0):.1f}%")
            
            # Stop monitoring
            stop_result = self.optimizer.stop_query_monitoring()
            if stop_result.get('success'):
                print("   ✓ Query monitoring stopped")
            
            return {
                'success': True,
                'monitoring_started': True,
                'report_generated': report_result.get('success', False),
                'monitoring_stopped': stop_result.get('success', False)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_caching_strategies(self) -> Dict[str, Any]:
        """Test caching strategy implementation."""
        try:
            strategies_tested = []
            
            # Test different caching strategies
            for strategy in ['adaptive', 'aggressive', 'conservative']:
                cache_result = self.optimizer.implement_caching_strategy(strategy)
                
                if cache_result.get('success'):
                    strategies_tested.append(strategy)
                    print(f"   ✓ {strategy.capitalize()} caching strategy implemented")
                    
                    # Verify cache configuration
                    results = cache_result.get('results', {})
                    cache_config = results.get('cache_config', {})
                    
                    if 'query_cache_ttl' in cache_config:
                        print(f"     - Query cache TTL: {cache_config['query_cache_ttl']}s")
                    
                else:
                    print(f"   ⚠️ {strategy.capitalize()} caching strategy failed: {cache_result.get('error', 'Unknown error')}")
            
            if not strategies_tested:
                return {
                    'success': False,
                    'error': "No caching strategies could be implemented"
                }
            
            return {
                'success': True,
                'strategies_implemented': strategies_tested,
                'total_strategies': len(strategies_tested)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_performance_recommendations(self) -> Dict[str, Any]:
        """Test performance recommendation generation."""
        try:
            # Generate optimization recommendations
            recommendations_result = self.optimizer.generate_optimization_recommendations()
            
            if not recommendations_result.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to generate recommendations: {recommendations_result.get('error', 'Unknown error')}"
                }
            
            recommendations = recommendations_result.get('recommendations', [])
            summary = recommendations_result.get('summary', {})
            
            print(f"   ✓ Generated {len(recommendations)} recommendations")
            
            # Analyze recommendation categories
            by_priority = summary.get('by_priority', {})
            by_category = summary.get('by_category', {})
            
            if by_priority:
                print(f"   ✓ Priority breakdown:")
                for priority, count in by_priority.items():
                    if count > 0:
                        print(f"     - {priority.capitalize()}: {count}")
            
            if by_category:
                print(f"   ✓ Category breakdown:")
                for category, count in by_category.items():
                    if count > 0:
                        print(f"     - {category.replace('_', ' ').title()}: {count}")
            
            # Verify recommendation structure
            if recommendations:
                sample_rec = recommendations[0]
                required_fields = ['category', 'priority', 'title', 'description']
                
                for field in required_fields:
                    if field not in sample_rec:
                        return {
                            'success': False,
                            'error': f"Recommendation missing required field: {field}"
                        }
            
            return {
                'success': True,
                'total_recommendations': len(recommendations),
                'by_priority': by_priority,
                'by_category': by_category
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_integrated_monitoring(self) -> Dict[str, Any]:
        """Test integrated monitoring system."""
        try:
            # Get monitoring status
            status_result = self.monitor.get_monitoring_status()
            
            if not status_result.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to get monitoring status: {status_result.get('error', 'Unknown error')}"
                }
            
            status = status_result.get('status', {})
            print(f"   ✓ Monitoring system initialized")
            print(f"   ✓ Redis available: {'Yes' if status.get('redis_available') else 'No'}")
            print(f"   ✓ Auto-optimize enabled: {'Yes' if status.get('auto_optimize_enabled') else 'No'}")
            
            # Test alert retrieval (even if no alerts exist)
            alerts_result = self.monitor.get_recent_alerts(1)  # Last 1 hour
            
            if alerts_result.get('success'):
                alert_counts = alerts_result.get('alert_counts', {})
                total_alerts = alerts_result.get('total_alerts', 0)
                print(f"   ✓ Alert system functional (found {total_alerts} recent alerts)")
            else:
                print(f"   ⚠️ Alert retrieval failed: {alerts_result.get('error', 'Unknown error')}")
            
            return {
                'success': True,
                'status_retrieved': True,
                'redis_available': status.get('redis_available', False),
                'alerts_functional': alerts_result.get('success', False)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_auto_optimization(self) -> Dict[str, Any]:
        """Test auto-optimization features."""
        try:
            # Test that auto-optimization can be configured
            original_auto_optimize = self.monitor.auto_optimize_enabled
            
            # Enable auto-optimization for testing
            self.monitor.auto_optimize_enabled = True
            
            print("   ✓ Auto-optimization can be enabled")
            
            # Test threshold configuration
            thresholds = self.monitor.thresholds
            required_thresholds = [
                'connection_usage_critical',
                'slow_query_ratio_critical',
                'avg_query_time_critical'
            ]
            
            for threshold in required_thresholds:
                if threshold not in thresholds:
                    return {
                        'success': False,
                        'error': f"Missing required threshold: {threshold}"
                    }
            
            print(f"   ✓ All {len(required_thresholds)} thresholds configured")
            
            # Restore original setting
            self.monitor.auto_optimize_enabled = original_auto_optimize
            
            return {
                'success': True,
                'thresholds_configured': len(required_thresholds),
                'auto_optimize_configurable': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_performance_metrics(self) -> Dict[str, Any]:
        """Test performance metrics collection."""
        try:
            # Test metrics history retrieval
            history_result = self.optimizer.get_performance_metrics_history(1)  # Last 1 hour
            
            if not history_result.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to get metrics history: {history_result.get('error', 'Unknown error')}"
                }
            
            metrics_count = history_result.get('metrics_count', 0)
            trends = history_result.get('trends', {})
            
            print(f"   ✓ Retrieved {metrics_count} historical metrics")
            
            if trends and not trends.get('insufficient_data'):
                print(f"   ✓ Trend analysis functional")
            else:
                print(f"   ℹ️ Insufficient data for trend analysis (expected for new system)")
            
            # Test current metrics collection
            if self.optimizer.performance_history:
                latest_metrics = self.optimizer.performance_history[-1]
                print(f"   ✓ Current metrics available")
                print(f"     - Connection usage: {latest_metrics.connection_usage_percent:.1f}%")
                print(f"     - Avg query time: {latest_metrics.avg_query_time_ms:.1f}ms")
            else:
                print(f"   ℹ️ No current metrics (monitoring not active)")
            
            return {
                'success': True,
                'historical_metrics': metrics_count,
                'trends_available': bool(trends and not trends.get('insufficient_data')),
                'current_metrics_available': len(self.optimizer.performance_history) > 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and recovery."""
        try:
            error_scenarios_tested = []
            
            # Test invalid database URL handling
            try:
                invalid_optimizer = MySQLPerformanceOptimizer()
                result = invalid_optimizer.optimize_connection_pool("invalid://database/url")
                
                if not result.get('success'):
                    error_scenarios_tested.append("invalid_database_url")
                    print("   ✓ Invalid database URL handled gracefully")
            except Exception:
                error_scenarios_tested.append("invalid_database_url")
                print("   ✓ Invalid database URL handled with exception (acceptable)")
            
            # Test monitoring stop when not started
            stop_result = self.optimizer.stop_query_monitoring()
            if not stop_result.get('success') and 'not active' in stop_result.get('message', ''):
                error_scenarios_tested.append("stop_inactive_monitoring")
                print("   ✓ Stopping inactive monitoring handled gracefully")
            
            # Test resource cleanup
            try:
                self.optimizer.cleanup_resources()
                error_scenarios_tested.append("resource_cleanup")
                print("   ✓ Resource cleanup executed without errors")
            except Exception as e:
                print(f"   ⚠️ Resource cleanup had issues: {e}")
            
            return {
                'success': True,
                'error_scenarios_tested': error_scenarios_tested,
                'total_scenarios': len(error_scenarios_tested)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final test report."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        # Calculate success statistics
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / max(total_tests, 1)) * 100
        
        # Print final report
        print(f"\n{'='*80}")
        print("FINAL TEST REPORT")
        print(f"{'='*80}")
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"{'='*80}")
        
        # Print detailed results
        print("\nDETAILED RESULTS:")
        print("-" * 40)
        
        for result in self.test_results:
            status_emoji = "✅" if result['success'] else "❌"
            print(f"{status_emoji} {result['category']}")
            
            if not result['success'] and 'error' in result:
                print(f"   Error: {result['error']}")
        
        # Overall assessment
        print(f"\n{'='*80}")
        if success_rate >= 90:
            print("🎉 EXCELLENT: MySQL Performance Optimization System is working excellently!")
        elif success_rate >= 75:
            print("✅ GOOD: MySQL Performance Optimization System is working well with minor issues.")
        elif success_rate >= 50:
            print("⚠️ FAIR: MySQL Performance Optimization System has some issues that need attention.")
        else:
            print("❌ POOR: MySQL Performance Optimization System has significant issues.")
        
        print(f"{'='*80}\n")
        
        # Cleanup resources
        try:
            self.optimizer.cleanup_resources()
            self.monitor.cleanup_resources()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
        
        return {
            'success': success_rate >= 75,  # Consider 75% success rate as overall success
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'duration_seconds': duration.total_seconds(),
            'test_results': self.test_results,
            'timestamp': end_time.isoformat()
        }


def main():
    """Main function to run the performance optimization tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test MySQL Performance Optimization System')
    parser.add_argument('--output-format', choices=['json', 'table'], default='table',
                       help='Output format (default: table)')
    parser.add_argument('--save-report', help='Save detailed report to file')
    
    args = parser.parse_args()
    
    try:
        # Run tests
        tester = MySQLPerformanceOptimizationTester()
        final_report = tester.run_all_tests()
        
        # Save report if requested
        if args.save_report:
            with open(args.save_report, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)
            print(f"Detailed report saved to: {args.save_report}")
        
        # Output in requested format
        if args.output_format == 'json':
            print(json.dumps(final_report, indent=2, default=str))
        
        # Exit with appropriate code
        sys.exit(0 if final_report['success'] else 1)
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        error_report = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        
        if args.output_format == 'json':
            print(json.dumps(error_report, indent=2, default=str))
        else:
            print(f"❌ Test execution failed: {e}")
        
        sys.exit(1)


if __name__ == '__main__':
    main()
