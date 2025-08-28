# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Scalability Tester

Provides comprehensive scalability testing for WebSocket systems,
including load testing, stress testing, and horizontal scaling validation.
"""

import time
import json
import asyncio
import threading
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import socketio
import requests
from websocket_debug_logger import get_debug_logger, DebugLevel


class TestPhase(Enum):
    """Test phase indicators"""
    RAMP_UP = "ramp_up"
    STEADY_STATE = "steady_state"
    RAMP_DOWN = "ramp_down"
    COMPLETED = "completed"


class TestResult(Enum):
    """Test result indicators"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LoadTestConfig:
    """Load test configuration"""
    target_url: str
    max_connections: int
    ramp_up_duration: int  # seconds
    steady_state_duration: int  # seconds
    ramp_down_duration: int  # seconds
    messages_per_connection: int
    message_interval: float  # seconds
    connection_timeout: int
    namespaces: List[str]
    test_data_size: int  # bytes


@dataclass
class ConnectionMetrics:
    """Metrics for a single connection"""
    connection_id: str
    connected_at: Optional[datetime]
    disconnected_at: Optional[datetime]
    connection_time: float
    messages_sent: int
    messages_received: int
    errors: List[str]
    latency_samples: List[float]
    status: str


@dataclass
class ScalabilityTestResult:
    """Result of a scalability test"""
    test_name: str
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    total_duration: float
    phase_durations: Dict[str, float]
    connection_metrics: List[ConnectionMetrics]
    aggregate_metrics: Dict[str, Any]
    performance_summary: Dict[str, Any]
    result: TestResult
    issues: List[str]
    recommendations: List[str]


class WebSocketLoadTester:
    """Individual WebSocket connection load tester"""
    
    def __init__(self, connection_id: str, target_url: str, config: LoadTestConfig):
        self.connection_id = connection_id
        self.target_url = target_url
        self.config = config
        self.logger = get_debug_logger(f'load_tester_{connection_id}', DebugLevel.WARNING)
        
        # Connection state
        self.sio = None
        self.connected = False
        self.connection_time = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.errors = []
        self.latency_samples = []
        
        # Test control
        self.should_stop = False
        self.test_start_time = None
        
    async def run_test(self) -> ConnectionMetrics:
        """Run the load test for this connection"""
        metrics = ConnectionMetrics(
            connection_id=self.connection_id,
            connected_at=None,
            disconnected_at=None,
            connection_time=0,
            messages_sent=0,
            messages_received=0,
            errors=[],
            latency_samples=[],
            status='not_started'
        )
        
        try:
            # Create SocketIO client
            self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
            self._setup_event_handlers()
            
            # Attempt connection
            connect_start = time.time()
            await self.sio.connect(self.target_url, wait_timeout=self.config.connection_timeout)
            
            if self.connected:
                metrics.connected_at = datetime.utcnow()
                metrics.connection_time = time.time() - connect_start
                metrics.status = 'connected'
                
                # Run message sending loop
                await self._message_loop()
                
                # Disconnect
                await self.sio.disconnect()
                metrics.disconnected_at = datetime.utcnow()
                metrics.status = 'completed'
                
            else:
                metrics.status = 'connection_failed'
                self.errors.append('Failed to establish connection')
                
        except Exception as e:
            self.errors.append(f'Test error: {str(e)}')
            metrics.status = 'error'
            self.logger.error(f"Load test error for {self.connection_id}: {e}")
            
        # Copy final metrics
        metrics.messages_sent = self.messages_sent
        metrics.messages_received = self.messages_received
        metrics.errors = self.errors.copy()
        metrics.latency_samples = self.latency_samples.copy()
        
        return metrics
        
    def _setup_event_handlers(self):
        """Set up SocketIO event handlers"""
        
        @self.sio.event
        async def connect():
            self.connected = True
            self.logger.debug(f"Connection {self.connection_id} established")
            
        @self.sio.event
        async def disconnect():
            self.connected = False
            self.logger.debug(f"Connection {self.connection_id} disconnected")
            
        @self.sio.event
        async def connect_error(data):
            self.errors.append(f'Connection error: {data}')
            self.logger.warning(f"Connection {self.connection_id} error: {data}")
            
        @self.sio.event
        async def test_response(data):
            """Handle test message responses"""
            self.messages_received += 1
            
            # Calculate latency if timestamp is included
            if isinstance(data, dict) and 'timestamp' in data:
                try:
                    sent_time = datetime.fromisoformat(data['timestamp'])
                    latency = (datetime.utcnow() - sent_time).total_seconds() * 1000
                    self.latency_samples.append(latency)
                except Exception:
                    pass
                    
    async def _message_loop(self):
        """Send messages at configured intervals"""
        self.test_start_time = time.time()
        
        for i in range(self.config.messages_per_connection):
            if self.should_stop or not self.connected:
                break
                
            try:
                # Create test message
                message = {
                    'connection_id': self.connection_id,
                    'message_number': i + 1,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': 'x' * self.config.test_data_size  # Padding to reach desired size
                }
                
                # Send message
                await self.sio.emit('test_message', message)
                self.messages_sent += 1
                
                # Wait for next message
                if self.config.message_interval > 0:
                    await asyncio.sleep(self.config.message_interval)
                    
            except Exception as e:
                self.errors.append(f'Message send error: {str(e)}')
                
    def stop_test(self):
        """Stop the test"""
        self.should_stop = True


class WebSocketScalabilityTester:
    """Comprehensive WebSocket scalability testing system"""
    
    def __init__(self):
        self.logger = get_debug_logger('scalability_tester', DebugLevel.INFO)
        self.test_results = []
        self.active_tests = {}
        
    async def run_load_test(self, config: LoadTestConfig) -> ScalabilityTestResult:
        """Run a comprehensive load test"""
        self.logger.info(f"Starting load test: {config.max_connections} connections to {config.target_url}")
        
        test_start = datetime.now(timezone.utc)
        phase_durations = {}
        
        # Initialize result
        result = ScalabilityTestResult(
            test_name=f"load_test_{int(time.time())}",
            config=config,
            start_time=test_start,
            end_time=test_start,  # Will be updated
            total_duration=0,
            phase_durations={},
            connection_metrics=[],
            aggregate_metrics={},
            performance_summary={},
            result=TestResult.PASS,
            issues=[],
            recommendations=[]
        )
        
        try:
            # Phase 1: Ramp up
            self.logger.info("Phase 1: Ramp up connections")
            ramp_up_start = time.time()
            connection_tasks = await self._ramp_up_connections(config)
            phase_durations['ramp_up'] = time.time() - ramp_up_start
            
            # Phase 2: Steady state
            self.logger.info("Phase 2: Steady state testing")
            steady_start = time.time()
            await asyncio.sleep(config.steady_state_duration)
            phase_durations['steady_state'] = time.time() - steady_start
            
            # Phase 3: Ramp down
            self.logger.info("Phase 3: Ramp down connections")
            ramp_down_start = time.time()
            connection_metrics = await self._ramp_down_connections(connection_tasks)
            phase_durations['ramp_down'] = time.time() - ramp_down_start
            
            # Analyze results
            result.end_time = datetime.now(timezone.utc)
            result.total_duration = (result.end_time - result.start_time).total_seconds()
            result.phase_durations = phase_durations
            result.connection_metrics = connection_metrics
            result.aggregate_metrics = self._calculate_aggregate_metrics(connection_metrics)
            result.performance_summary = self._generate_performance_summary(result.aggregate_metrics)
            result.result, result.issues, result.recommendations = self._analyze_test_results(result)
            
        except Exception as e:
            self.logger.error(f"Load test failed: {e}")
            result.result = TestResult.ERROR
            result.issues.append(f"Test execution error: {str(e)}")
            
        self.test_results.append(result)
        return result
        
    async def run_stress_test(self, base_config: LoadTestConfig, 
                            max_connections_list: List[int]) -> List[ScalabilityTestResult]:
        """Run stress test with increasing connection counts"""
        self.logger.info(f"Starting stress test with connection counts: {max_connections_list}")
        
        stress_results = []
        
        for max_connections in max_connections_list:
            self.logger.info(f"Stress test phase: {max_connections} connections")
            
            # Create config for this phase
            stress_config = LoadTestConfig(
                target_url=base_config.target_url,
                max_connections=max_connections,
                ramp_up_duration=base_config.ramp_up_duration,
                steady_state_duration=base_config.steady_state_duration,
                ramp_down_duration=base_config.ramp_down_duration,
                messages_per_connection=base_config.messages_per_connection,
                message_interval=base_config.message_interval,
                connection_timeout=base_config.connection_timeout,
                namespaces=base_config.namespaces,
                test_data_size=base_config.test_data_size
            )
            
            # Run test
            result = await self.run_load_test(stress_config)
            stress_results.append(result)
            
            # Check if we should stop (system is failing)
            if result.result == TestResult.FAIL:
                self.logger.warning(f"Stress test failed at {max_connections} connections, stopping")
                break
                
            # Brief pause between stress phases
            await asyncio.sleep(10)
            
        return stress_results
        
    async def run_horizontal_scaling_test(self, config: LoadTestConfig, 
                                        server_urls: List[str]) -> Dict[str, ScalabilityTestResult]:
        """Test horizontal scaling across multiple server instances"""
        self.logger.info(f"Starting horizontal scaling test across {len(server_urls)} servers")
        
        scaling_results = {}
        
        # Test each server individually first
        for i, server_url in enumerate(server_urls):
            self.logger.info(f"Testing server {i+1}: {server_url}")
            
            server_config = LoadTestConfig(
                target_url=server_url,
                max_connections=config.max_connections // len(server_urls),
                ramp_up_duration=config.ramp_up_duration,
                steady_state_duration=config.steady_state_duration,
                ramp_down_duration=config.ramp_down_duration,
                messages_per_connection=config.messages_per_connection,
                message_interval=config.message_interval,
                connection_timeout=config.connection_timeout,
                namespaces=config.namespaces,
                test_data_size=config.test_data_size
            )
            
            result = await self.run_load_test(server_config)
            scaling_results[f"server_{i+1}_{server_url}"] = result
            
        # Test all servers simultaneously
        self.logger.info("Testing all servers simultaneously")
        
        # Create tasks for all servers
        simultaneous_tasks = []
        for i, server_url in enumerate(server_urls):
            server_config = LoadTestConfig(
                target_url=server_url,
                max_connections=config.max_connections // len(server_urls),
                ramp_up_duration=config.ramp_up_duration,
                steady_state_duration=config.steady_state_duration,
                ramp_down_duration=config.ramp_down_duration,
                messages_per_connection=config.messages_per_connection,
                message_interval=config.message_interval,
                connection_timeout=config.connection_timeout,
                namespaces=config.namespaces,
                test_data_size=config.test_data_size
            )
            
            task = asyncio.create_task(self.run_load_test(server_config))
            simultaneous_tasks.append((f"simultaneous_server_{i+1}", task))
            
        # Wait for all simultaneous tests to complete
        for server_name, task in simultaneous_tasks:
            result = await task
            scaling_results[server_name] = result
            
        return scaling_results
        
    async def _ramp_up_connections(self, config: LoadTestConfig) -> List[asyncio.Task]:
        """Ramp up connections gradually"""
        connection_tasks = []
        connections_per_second = config.max_connections / config.ramp_up_duration
        
        for i in range(config.max_connections):
            # Create connection tester
            connection_id = f"conn_{i+1}"
            tester = WebSocketLoadTester(connection_id, config.target_url, config)
            
            # Create task
            task = asyncio.create_task(tester.run_test())
            connection_tasks.append(task)
            
            # Wait before creating next connection (ramp up)
            if i < config.max_connections - 1:
                delay = 1.0 / connections_per_second
                await asyncio.sleep(delay)
                
        self.logger.info(f"Created {len(connection_tasks)} connection tasks")
        return connection_tasks
        
    async def _ramp_down_connections(self, connection_tasks: List[asyncio.Task]) -> List[ConnectionMetrics]:
        """Wait for all connections to complete and collect metrics"""
        self.logger.info("Waiting for all connections to complete")
        
        connection_metrics = []
        
        # Wait for all tasks to complete
        for task in asyncio.as_completed(connection_tasks):
            try:
                metrics = await task
                connection_metrics.append(metrics)
            except Exception as e:
                self.logger.error(f"Connection task failed: {e}")
                
        self.logger.info(f"Collected metrics from {len(connection_metrics)} connections")
        return connection_metrics
        
    def _calculate_aggregate_metrics(self, connection_metrics: List[ConnectionMetrics]) -> Dict[str, Any]:
        """Calculate aggregate metrics from individual connection metrics"""
        if not connection_metrics:
            return {}
            
        # Connection success metrics
        successful_connections = [m for m in connection_metrics if m.connected_at is not None]
        failed_connections = [m for m in connection_metrics if m.connected_at is None]
        
        # Connection time metrics
        connection_times = [m.connection_time for m in successful_connections if m.connection_time > 0]
        
        # Message metrics
        total_messages_sent = sum(m.messages_sent for m in connection_metrics)
        total_messages_received = sum(m.messages_received for m in connection_metrics)
        
        # Latency metrics
        all_latency_samples = []
        for m in connection_metrics:
            all_latency_samples.extend(m.latency_samples)
            
        # Error metrics
        total_errors = sum(len(m.errors) for m in connection_metrics)
        connections_with_errors = len([m for m in connection_metrics if m.errors])
        
        return {
            'total_connections': len(connection_metrics),
            'successful_connections': len(successful_connections),
            'failed_connections': len(failed_connections),
            'connection_success_rate': len(successful_connections) / len(connection_metrics) if connection_metrics else 0,
            
            'connection_time_avg': statistics.mean(connection_times) if connection_times else 0,
            'connection_time_min': min(connection_times) if connection_times else 0,
            'connection_time_max': max(connection_times) if connection_times else 0,
            'connection_time_p95': statistics.quantiles(connection_times, n=20)[18] if len(connection_times) > 20 else 0,
            
            'total_messages_sent': total_messages_sent,
            'total_messages_received': total_messages_received,
            'message_success_rate': total_messages_received / total_messages_sent if total_messages_sent > 0 else 0,
            
            'latency_avg': statistics.mean(all_latency_samples) if all_latency_samples else 0,
            'latency_min': min(all_latency_samples) if all_latency_samples else 0,
            'latency_max': max(all_latency_samples) if all_latency_samples else 0,
            'latency_p95': statistics.quantiles(all_latency_samples, n=20)[18] if len(all_latency_samples) > 20 else 0,
            
            'total_errors': total_errors,
            'connections_with_errors': connections_with_errors,
            'error_rate': total_errors / len(connection_metrics) if connection_metrics else 0
        }
        
    def _generate_performance_summary(self, aggregate_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary from aggregate metrics"""
        if not aggregate_metrics:
            return {'status': 'no_data'}
            
        # Determine performance level
        success_rate = aggregate_metrics.get('connection_success_rate', 0)
        message_success_rate = aggregate_metrics.get('message_success_rate', 0)
        avg_latency = aggregate_metrics.get('latency_avg', 0)
        error_rate = aggregate_metrics.get('error_rate', 0)
        
        # Performance scoring
        performance_score = 0
        
        if success_rate >= 0.95:
            performance_score += 25
        elif success_rate >= 0.9:
            performance_score += 20
        elif success_rate >= 0.8:
            performance_score += 15
        elif success_rate >= 0.7:
            performance_score += 10
            
        if message_success_rate >= 0.95:
            performance_score += 25
        elif message_success_rate >= 0.9:
            performance_score += 20
        elif message_success_rate >= 0.8:
            performance_score += 15
        elif message_success_rate >= 0.7:
            performance_score += 10
            
        if avg_latency <= 50:
            performance_score += 25
        elif avg_latency <= 100:
            performance_score += 20
        elif avg_latency <= 200:
            performance_score += 15
        elif avg_latency <= 500:
            performance_score += 10
            
        if error_rate <= 0.01:
            performance_score += 25
        elif error_rate <= 0.05:
            performance_score += 20
        elif error_rate <= 0.1:
            performance_score += 15
        elif error_rate <= 0.2:
            performance_score += 10
            
        # Determine performance level
        if performance_score >= 90:
            performance_level = 'excellent'
        elif performance_score >= 75:
            performance_level = 'good'
        elif performance_score >= 60:
            performance_level = 'fair'
        elif performance_score >= 40:
            performance_level = 'poor'
        else:
            performance_level = 'critical'
            
        return {
            'performance_level': performance_level,
            'performance_score': performance_score,
            'connection_success_rate': success_rate,
            'message_success_rate': message_success_rate,
            'avg_latency_ms': avg_latency,
            'error_rate': error_rate,
            'throughput_messages_per_second': self._calculate_throughput(aggregate_metrics)
        }
        
    def _calculate_throughput(self, aggregate_metrics: Dict[str, Any]) -> float:
        """Calculate message throughput"""
        # This is a simplified calculation
        # In a real implementation, you'd need the actual test duration
        total_messages = aggregate_metrics.get('total_messages_sent', 0)
        # Assuming average test duration for now
        estimated_duration = 60  # seconds
        return total_messages / estimated_duration if estimated_duration > 0 else 0
        
    def _analyze_test_results(self, result: ScalabilityTestResult) -> Tuple[TestResult, List[str], List[str]]:
        """Analyze test results and generate issues and recommendations"""
        issues = []
        recommendations = []
        test_result = TestResult.PASS
        
        performance = result.performance_summary
        metrics = result.aggregate_metrics
        
        # Check connection success rate
        if metrics.get('connection_success_rate', 0) < 0.9:
            issues.append(f"Low connection success rate: {metrics['connection_success_rate']:.2%}")
            test_result = TestResult.FAIL
            recommendations.append("Investigate connection failures and increase connection timeout")
            
        # Check message success rate
        if metrics.get('message_success_rate', 0) < 0.95:
            issues.append(f"Low message success rate: {metrics['message_success_rate']:.2%}")
            if test_result != TestResult.FAIL:
                test_result = TestResult.WARNING
            recommendations.append("Investigate message delivery issues")
            
        # Check latency
        avg_latency = metrics.get('latency_avg', 0)
        if avg_latency > 500:
            issues.append(f"High average latency: {avg_latency:.1f}ms")
            test_result = TestResult.FAIL
            recommendations.append("Optimize server performance and network configuration")
        elif avg_latency > 200:
            issues.append(f"Elevated latency: {avg_latency:.1f}ms")
            if test_result == TestResult.PASS:
                test_result = TestResult.WARNING
            recommendations.append("Monitor latency and consider performance optimizations")
            
        # Check error rate
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 0.1:
            issues.append(f"High error rate: {error_rate:.2%}")
            test_result = TestResult.FAIL
            recommendations.append("Investigate and fix error sources")
        elif error_rate > 0.05:
            issues.append(f"Elevated error rate: {error_rate:.2%}")
            if test_result == TestResult.PASS:
                test_result = TestResult.WARNING
            recommendations.append("Monitor errors and improve error handling")
            
        # Performance-based recommendations
        if performance.get('performance_level') == 'excellent':
            recommendations.append("System performing excellently - consider increasing load capacity")
        elif performance.get('performance_level') == 'good':
            recommendations.append("Good performance - monitor for any degradation")
        elif performance.get('performance_level') in ['fair', 'poor']:
            recommendations.append("Performance needs improvement - optimize server and network")
        elif performance.get('performance_level') == 'critical':
            recommendations.append("Critical performance issues - immediate optimization required")
            
        return test_result, issues, recommendations
        
    def export_test_results(self, filename: str = None) -> str:
        """Export test results to JSON file"""
        if not filename:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"websocket_scalability_test_results_{timestamp}.json"
            
        # Convert results to serializable format
        serializable_results = []
        for result in self.test_results:
            result_dict = asdict(result)
            # Convert datetime objects to strings
            result_dict['start_time'] = result.start_time.isoformat()
            result_dict['end_time'] = result.end_time.isoformat()
            
            # Convert connection metrics
            for i, metrics in enumerate(result_dict['connection_metrics']):
                if metrics['connected_at']:
                    metrics['connected_at'] = result.connection_metrics[i].connected_at.isoformat()
                if metrics['disconnected_at']:
                    metrics['disconnected_at'] = result.connection_metrics[i].disconnected_at.isoformat()
                    
            serializable_results.append(result_dict)
            
        with open(filename, 'w') as f:
            json.dump({
                'export_timestamp': datetime.utcnow().isoformat(),
                'test_results': serializable_results
            }, f, indent=2)
            
        self.logger.info(f"Test results exported to {filename}")
        return filename


def create_load_test_config(target_url: str, max_connections: int = 100, 
                          steady_state_duration: int = 60) -> LoadTestConfig:
    """Create a standard load test configuration"""
    return LoadTestConfig(
        target_url=target_url,
        max_connections=max_connections,
        ramp_up_duration=30,
        steady_state_duration=steady_state_duration,
        ramp_down_duration=30,
        messages_per_connection=10,
        message_interval=1.0,
        connection_timeout=10,
        namespaces=['/'],
        test_data_size=1024
    )


async def run_quick_scalability_test(target_url: str) -> ScalabilityTestResult:
    """Run a quick scalability test with default settings"""
    tester = WebSocketScalabilityTester()
    config = create_load_test_config(target_url, max_connections=50, steady_state_duration=30)
    return await tester.run_load_test(config)


async def run_comprehensive_scalability_test(target_url: str) -> List[ScalabilityTestResult]:
    """Run a comprehensive scalability test with multiple phases"""
    tester = WebSocketScalabilityTester()
    base_config = create_load_test_config(target_url, max_connections=100, steady_state_duration=60)
    
    # Test with increasing connection counts
    connection_counts = [50, 100, 200, 500, 1000]
    return await tester.run_stress_test(base_config, connection_counts)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python websocket_scalability_tester.py <target_url> [max_connections]")
        sys.exit(1)
        
    target_url = sys.argv[1]
    max_connections = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    async def main():
        config = create_load_test_config(target_url, max_connections)
        tester = WebSocketScalabilityTester()
        result = await tester.run_load_test(config)
        
        print(f"\nScalability Test Results:")
        print(f"Test Result: {result.result.value}")
        print(f"Performance Level: {result.performance_summary.get('performance_level', 'unknown')}")
        print(f"Connection Success Rate: {result.aggregate_metrics.get('connection_success_rate', 0):.2%}")
        print(f"Average Latency: {result.aggregate_metrics.get('latency_avg', 0):.1f}ms")
        print(f"Error Rate: {result.aggregate_metrics.get('error_rate', 0):.2%}")
        
        if result.issues:
            print(f"\nIssues Found:")
            for issue in result.issues:
                print(f"  - {issue}")
                
        if result.recommendations:
            print(f"\nRecommendations:")
            for rec in result.recommendations:
                print(f"  - {rec}")
                
        # Export results
        filename = tester.export_test_results()
        print(f"\nDetailed results exported to: {filename}")
        
    asyncio.run(main())