#!/usr/bin/env python3
"""
MySQL Performance Testing Module

Provides MySQL-specific performance testing utilities for integration tests.
Measures MySQL connection pooling, query performance, and optimization features.
"""

import time
import logging
import statistics
from typing import Dict, List, Any, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy import text

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Represents a performance metric measurement"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class PerformanceTestResult:
    """Results from a performance test"""
    test_name: str
    metrics: List[PerformanceMetric]
    duration: float
    success: bool
    error_message: Optional[str] = None
    
    def get_metric(self, name: str) -> Optional[PerformanceMetric]:
        """Get a specific metric by name"""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None
    
    def get_average_metric(self, name: str) -> Optional[float]:
        """Get average value for metrics with the same name"""
        values = [m.value for m in self.metrics if m.name == name]
        return statistics.mean(values) if values else None

class MySQLPerformanceTester:
    """MySQL-specific performance testing utilities"""
    
    def __init__(self, db_manager, session_factory):
        """
        Initialize performance tester
        
        Args:
            db_manager: DatabaseManager instance
            session_factory: SQLAlchemy session factory
        """
        self.db_manager = db_manager
        self.session_factory = session_factory
        self.results = []
    
    @contextmanager
    def measure_time(self, operation_name: str):
        """Context manager to measure operation time"""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            logger.info(f"{operation_name} took {duration:.4f} seconds")
    
    def test_connection_pool_performance(self, concurrent_connections: int = 10, operations_per_connection: int = 5) -> PerformanceTestResult:
        """Test MySQL connection pool performance"""
        logger.info(f"Testing connection pool with {concurrent_connections} connections, {operations_per_connection} ops each")
        
        metrics = []
        start_time = time.perf_counter()
        
        try:
            import threading
            import queue
            
            results_queue = queue.Queue()
            
            def connection_worker(worker_id: int):
                """Worker function for testing connections"""
                worker_metrics = []
                
                for op_num in range(operations_per_connection):
                    op_start = time.perf_counter()
                    
                    try:
                        session = self.session_factory()
                        
                        # Perform a simple query to test connection
                        result = session.execute(text("SELECT 1 as test_value")).fetchone()
                        
                        session.close()
                        
                        op_end = time.perf_counter()
                        op_duration = op_end - op_start
                        
                        worker_metrics.append(PerformanceMetric(
                            name="connection_operation_time",
                            value=op_duration,
                            unit="seconds",
                            timestamp=datetime.now(),
                            metadata={
                                "worker_id": worker_id,
                                "operation_number": op_num,
                                "query_result": result[0] if result else None
                            }
                        ))
                        
                    except Exception as e:
                        logger.error(f"Connection worker {worker_id} operation {op_num} failed: {e}")
                        worker_metrics.append(PerformanceMetric(
                            name="connection_error",
                            value=1,
                            unit="count",
                            timestamp=datetime.now(),
                            metadata={
                                "worker_id": worker_id,
                                "operation_number": op_num,
                                "error": str(e)
                            }
                        ))
                
                results_queue.put(worker_metrics)
            
            # Start worker threads
            threads = []
            for i in range(concurrent_connections):
                thread = threading.Thread(target=connection_worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Collect results
            while not results_queue.empty():
                worker_metrics = results_queue.get()
                metrics.extend(worker_metrics)
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            # Calculate summary metrics
            operation_times = [m.value for m in metrics if m.name == "connection_operation_time"]
            error_count = len([m for m in metrics if m.name == "connection_error"])
            
            if operation_times:
                metrics.append(PerformanceMetric(
                    name="average_connection_time",
                    value=statistics.mean(operation_times),
                    unit="seconds",
                    timestamp=datetime.now()
                ))
                
                metrics.append(PerformanceMetric(
                    name="max_connection_time",
                    value=max(operation_times),
                    unit="seconds",
                    timestamp=datetime.now()
                ))
                
                metrics.append(PerformanceMetric(
                    name="min_connection_time",
                    value=min(operation_times),
                    unit="seconds",
                    timestamp=datetime.now()
                ))
            
            metrics.append(PerformanceMetric(
                name="connection_error_count",
                value=error_count,
                unit="count",
                timestamp=datetime.now()
            ))
            
            metrics.append(PerformanceMetric(
                name="total_operations",
                value=len(operation_times) + error_count,
                unit="count",
                timestamp=datetime.now()
            ))
            
            return PerformanceTestResult(
                test_name="connection_pool_performance",
                metrics=metrics,
                duration=total_duration,
                success=error_count == 0
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            return PerformanceTestResult(
                test_name="connection_pool_performance",
                metrics=metrics,
                duration=total_duration,
                success=False,
                error_message=str(e)
            )
    
    def test_query_performance(self, query: str, iterations: int = 100) -> PerformanceTestResult:
        """Test MySQL query performance"""
        logger.info(f"Testing query performance: {query[:50]}... ({iterations} iterations)")
        
        metrics = []
        start_time = time.perf_counter()
        
        try:
            session = self.session_factory()
            
            # Warm up
            session.execute(text(query))
            
            # Measure query performance
            query_times = []
            for i in range(iterations):
                query_start = time.perf_counter()
                
                try:
                    result = session.execute(text(query))
                    row_count = len(result.fetchall()) if hasattr(result, 'fetchall') else 0
                    
                    query_end = time.perf_counter()
                    query_duration = query_end - query_start
                    
                    query_times.append(query_duration)
                    
                    metrics.append(PerformanceMetric(
                        name="query_execution_time",
                        value=query_duration,
                        unit="seconds",
                        timestamp=datetime.now(),
                        metadata={
                            "iteration": i,
                            "row_count": row_count
                        }
                    ))
                    
                except Exception as e:
                    logger.error(f"Query iteration {i} failed: {e}")
                    metrics.append(PerformanceMetric(
                        name="query_error",
                        value=1,
                        unit="count",
                        timestamp=datetime.now(),
                        metadata={
                            "iteration": i,
                            "error": str(e)
                        }
                    ))
            
            session.close()
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            # Calculate summary metrics
            if query_times:
                metrics.append(PerformanceMetric(
                    name="average_query_time",
                    value=statistics.mean(query_times),
                    unit="seconds",
                    timestamp=datetime.now()
                ))
                
                metrics.append(PerformanceMetric(
                    name="median_query_time",
                    value=statistics.median(query_times),
                    unit="seconds",
                    timestamp=datetime.now()
                ))
                
                metrics.append(PerformanceMetric(
                    name="query_throughput",
                    value=len(query_times) / total_duration,
                    unit="queries_per_second",
                    timestamp=datetime.now()
                ))
            
            error_count = len([m for m in metrics if m.name == "query_error"])
            
            return PerformanceTestResult(
                test_name="query_performance",
                metrics=metrics,
                duration=total_duration,
                success=error_count == 0
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            return PerformanceTestResult(
                test_name="query_performance",
                metrics=metrics,
                duration=total_duration,
                success=False,
                error_message=str(e)
            )
    
    def test_transaction_performance(self, operations_per_transaction: int = 10, transaction_count: int = 50) -> PerformanceTestResult:
        """Test MySQL transaction performance"""
        logger.info(f"Testing transaction performance: {transaction_count} transactions, {operations_per_transaction} ops each")
        
        metrics = []
        start_time = time.perf_counter()
        
        try:
            from models import User, UserRole
            
            for tx_num in range(transaction_count):
                tx_start = time.perf_counter()
                
                try:
                    session = self.session_factory()
                    
                    # Perform multiple operations in a transaction
                    for op_num in range(operations_per_transaction):
                        # Create a test user
                        user = User(
                            username=f"perf_test_user_{tx_num}_{op_num}",
                            email=f"perf_test_{tx_num}_{op_num}@example.com",
                            role=UserRole.VIEWER,
                            is_active=True
                        )
                        user.set_password("testpassword")
                        session.add(user)
                    
                    session.commit()
                    
                    # Clean up test data
                    session.query(User).filter(
                        User.username.like(f"perf_test_user_{tx_num}_%")
                    ).delete(synchronize_session=False)
                    session.commit()
                    
                    session.close()
                    
                    tx_end = time.perf_counter()
                    tx_duration = tx_end - tx_start
                    
                    metrics.append(PerformanceMetric(
                        name="transaction_time",
                        value=tx_duration,
                        unit="seconds",
                        timestamp=datetime.now(),
                        metadata={
                            "transaction_number": tx_num,
                            "operations_count": operations_per_transaction
                        }
                    ))
                    
                except Exception as e:
                    logger.error(f"Transaction {tx_num} failed: {e}")
                    metrics.append(PerformanceMetric(
                        name="transaction_error",
                        value=1,
                        unit="count",
                        timestamp=datetime.now(),
                        metadata={
                            "transaction_number": tx_num,
                            "error": str(e)
                        }
                    ))
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            # Calculate summary metrics
            transaction_times = [m.value for m in metrics if m.name == "transaction_time"]
            error_count = len([m for m in metrics if m.name == "transaction_error"])
            
            if transaction_times:
                metrics.append(PerformanceMetric(
                    name="average_transaction_time",
                    value=statistics.mean(transaction_times),
                    unit="seconds",
                    timestamp=datetime.now()
                ))
                
                metrics.append(PerformanceMetric(
                    name="transaction_throughput",
                    value=len(transaction_times) / total_duration,
                    unit="transactions_per_second",
                    timestamp=datetime.now()
                ))
            
            return PerformanceTestResult(
                test_name="transaction_performance",
                metrics=metrics,
                duration=total_duration,
                success=error_count == 0
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            return PerformanceTestResult(
                test_name="transaction_performance",
                metrics=metrics,
                duration=total_duration,
                success=False,
                error_message=str(e)
            )
    
    def test_mysql_optimization_features(self) -> PerformanceTestResult:
        """Test MySQL-specific optimization features"""
        logger.info("Testing MySQL optimization features")
        
        metrics = []
        start_time = time.perf_counter()
        
        try:
            session = self.session_factory()
            
            # Test 1: Index usage
            index_start = time.perf_counter()
            result = session.execute(text("SHOW INDEX FROM users")).fetchall()
            index_end = time.perf_counter()
            
            metrics.append(PerformanceMetric(
                name="index_query_time",
                value=index_end - index_start,
                unit="seconds",
                timestamp=datetime.now(),
                metadata={"index_count": len(result)}
            ))
            
            # Test 2: Query plan analysis
            explain_start = time.perf_counter()
            explain_result = session.execute(text("EXPLAIN SELECT * FROM users LIMIT 1")).fetchall()
            explain_end = time.perf_counter()
            
            metrics.append(PerformanceMetric(
                name="explain_query_time",
                value=explain_end - explain_start,
                unit="seconds",
                timestamp=datetime.now(),
                metadata={"explain_rows": len(explain_result)}
            ))
            
            # Test 3: Connection status
            status_start = time.perf_counter()
            status_result = session.execute(text("SHOW STATUS LIKE 'Connections'")).fetchall()
            status_end = time.perf_counter()
            
            metrics.append(PerformanceMetric(
                name="status_query_time",
                value=status_end - status_start,
                unit="seconds",
                timestamp=datetime.now(),
                metadata={"status_info": dict(status_result) if status_result else {}}
            ))
            
            # Test 4: MySQL version and capabilities
            version_start = time.perf_counter()
            version_result = session.execute(text("SELECT VERSION()")).fetchone()
            version_end = time.perf_counter()
            
            metrics.append(PerformanceMetric(
                name="version_query_time",
                value=version_end - version_start,
                unit="seconds",
                timestamp=datetime.now(),
                metadata={"mysql_version": version_result[0] if version_result else "unknown"}
            ))
            
            session.close()
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            return PerformanceTestResult(
                test_name="mysql_optimization_features",
                metrics=metrics,
                duration=total_duration,
                success=True
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            return PerformanceTestResult(
                test_name="mysql_optimization_features",
                metrics=metrics,
                duration=total_duration,
                success=False,
                error_message=str(e)
            )
    
    def run_comprehensive_performance_test(self) -> List[PerformanceTestResult]:
        """Run all performance tests and return results"""
        logger.info("Running comprehensive MySQL performance test suite")
        
        test_results = []
        
        # Test connection pool performance
        logger.info("1. Testing connection pool performance...")
        pool_result = self.test_connection_pool_performance()
        test_results.append(pool_result)
        
        # Test query performance
        logger.info("2. Testing query performance...")
        query_result = self.test_query_performance("SELECT COUNT(*) FROM users")
        test_results.append(query_result)
        
        # Test transaction performance
        logger.info("3. Testing transaction performance...")
        tx_result = self.test_transaction_performance()
        test_results.append(tx_result)
        
        # Test MySQL optimization features
        logger.info("4. Testing MySQL optimization features...")
        opt_result = self.test_mysql_optimization_features()
        test_results.append(opt_result)
        
        self.results.extend(test_results)
        
        # Log summary
        successful_tests = len([r for r in test_results if r.success])
        logger.info(f"Performance test suite completed: {successful_tests}/{len(test_results)} tests passed")
        
        return test_results
    
    def generate_performance_report(self, results: List[PerformanceTestResult] = None) -> str:
        """Generate a comprehensive performance report"""
        if results is None:
            results = self.results
        
        report = [
            "=== MySQL Performance Test Report ===",
            "",
            f"Test Execution Time: {datetime.now().isoformat()}",
            f"Total Tests: {len(results)}",
            f"Successful Tests: {len([r for r in results if r.success])}",
            f"Failed Tests: {len([r for r in results if not r.success])}",
            ""
        ]
        
        for result in results:
            report.extend([
                f"## {result.test_name.upper()}",
                f"Duration: {result.duration:.4f} seconds",
                f"Status: {'✅ PASSED' if result.success else '❌ FAILED'}",
                ""
            ])
            
            if not result.success and result.error_message:
                report.extend([
                    f"Error: {result.error_message}",
                    ""
                ])
            
            # Group metrics by name
            metric_groups = {}
            for metric in result.metrics:
                if metric.name not in metric_groups:
                    metric_groups[metric.name] = []
                metric_groups[metric.name].append(metric)
            
            for metric_name, metrics in metric_groups.items():
                if len(metrics) == 1:
                    metric = metrics[0]
                    report.append(f"  {metric_name}: {metric.value:.4f} {metric.unit}")
                else:
                    values = [m.value for m in metrics]
                    report.extend([
                        f"  {metric_name}:",
                        f"    Count: {len(values)}",
                        f"    Average: {statistics.mean(values):.4f} {metrics[0].unit}",
                        f"    Min: {min(values):.4f} {metrics[0].unit}",
                        f"    Max: {max(values):.4f} {metrics[0].unit}",
                    ])
            
            report.append("")
        
        return "\n".join(report)


# Convenience functions for integration tests
def create_performance_tester(db_manager, session_factory) -> MySQLPerformanceTester:
    """Create a MySQL performance tester instance"""
    return MySQLPerformanceTester(db_manager, session_factory)

def measure_mysql_performance(test_func: Callable, *args, **kwargs) -> PerformanceTestResult:
    """Decorator/function to measure performance of a test function"""
    start_time = time.perf_counter()
    
    try:
        result = test_func(*args, **kwargs)
        end_time = time.perf_counter()
        
        return PerformanceTestResult(
            test_name=test_func.__name__,
            metrics=[
                PerformanceMetric(
                    name="execution_time",
                    value=end_time - start_time,
                    unit="seconds",
                    timestamp=datetime.now()
                )
            ],
            duration=end_time - start_time,
            success=True
        )
        
    except Exception as e:
        end_time = time.perf_counter()
        
        return PerformanceTestResult(
            test_name=test_func.__name__,
            metrics=[],
            duration=end_time - start_time,
            success=False,
            error_message=str(e)
        )


if __name__ == "__main__":
    # Example usage
    print("MySQL Performance Testing Module")
    print("This module provides utilities for testing MySQL performance in integration tests.")
    print("Import and use MySQLPerformanceTester in your integration tests.")
