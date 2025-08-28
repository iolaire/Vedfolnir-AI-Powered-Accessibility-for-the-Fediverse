# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Performance Optimizer

Provides intelligent performance optimization for WebSocket systems,
including adaptive configuration, resource management, and graceful degradation.
"""

import time
import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from collections import deque
import statistics
from websocket_debug_logger import get_debug_logger, DebugLevel
from websocket_performance_monitor import WebSocketPerformanceMonitor, LoadLevel, PerformanceLevel


class OptimizationStrategy(Enum):
    """Optimization strategy types"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    EMERGENCY = "emergency"


class OptimizationAction(Enum):
    """Types of optimization actions"""
    INCREASE_LIMITS = "increase_limits"
    DECREASE_LIMITS = "decrease_limits"
    ADJUST_TIMEOUTS = "adjust_timeouts"
    MODIFY_BATCHING = "modify_batching"
    ENABLE_COMPRESSION = "enable_compression"
    DISABLE_FEATURES = "disable_features"
    RESTART_SERVICES = "restart_services"
    SCALE_RESOURCES = "scale_resources"


@dataclass
class OptimizationRule:
    """Rule for performance optimization"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    action: OptimizationAction
    parameters: Dict[str, Any]
    priority: int
    cooldown_seconds: int
    description: str


@dataclass
class OptimizationResult:
    """Result of an optimization action"""
    timestamp: datetime
    rule_name: str
    action: OptimizationAction
    parameters_before: Dict[str, Any]
    parameters_after: Dict[str, Any]
    expected_impact: str
    success: bool
    error_message: Optional[str] = None


class WebSocketPerformanceOptimizer:
    """Intelligent WebSocket performance optimization system"""
    
    def __init__(self, performance_monitor: WebSocketPerformanceMonitor, 
                 strategy: OptimizationStrategy = OptimizationStrategy.BALANCED):
        self.performance_monitor = performance_monitor
        self.strategy = strategy
        self.logger = get_debug_logger('performance_optimizer', DebugLevel.INFO)
        
        # Optimization state
        self.current_settings = {
            'max_connections': 1000,
            'connection_timeout': 30,
            'message_batch_size': 10,
            'retry_attempts': 3,
            'backoff_multiplier': 2.0,
            'compression_enabled': False,
            'keep_alive_interval': 25,
            'ping_timeout': 60,
            'max_message_size': 1024 * 1024,  # 1MB
            'rate_limit_per_second': 100,
            'buffer_size': 4096,
            'worker_threads': 4
        }
        
        # Optimization history
        self.optimization_history = deque(maxlen=1000)
        self.rule_last_applied = {}
        
        # Optimization rules
        self.optimization_rules = self._create_optimization_rules()
        
        # Auto-optimization settings
        self.auto_optimization_enabled = True
        self.optimization_interval = 60  # seconds
        self.optimization_thread = None
        self.optimization_active = False
        
        # Performance baselines
        self.performance_baselines = {
            'connection_success_rate': 0.95,
            'message_success_rate': 0.98,
            'avg_latency_ms': 100,
            'error_rate': 0.02,
            'cpu_usage': 70,
            'memory_usage': 80
        }
        
        # Callbacks
        self.optimization_callbacks = []
        
    def start_auto_optimization(self):
        """Start automatic performance optimization"""
        if self.optimization_active:
            self.logger.warning("Auto-optimization is already active")
            return
            
        self.optimization_active = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        self.logger.info(f"Started auto-optimization with {self.strategy.value} strategy")
        
    def stop_auto_optimization(self):
        """Stop automatic performance optimization"""
        self.optimization_active = False
        if self.optimization_thread:
            self.optimization_thread.join(timeout=5)
            
        self.logger.info("Stopped auto-optimization")
        
    def optimize_now(self) -> List[OptimizationResult]:
        """Perform immediate optimization based on current performance"""
        current_performance = self.performance_monitor.get_current_performance_summary()
        return self._apply_optimization_rules(current_performance)
        
    def add_optimization_rule(self, rule: OptimizationRule):
        """Add a custom optimization rule"""
        self.optimization_rules.append(rule)
        self.logger.info(f"Added optimization rule: {rule.name}")
        
    def remove_optimization_rule(self, rule_name: str):
        """Remove an optimization rule"""
        self.optimization_rules = [r for r in self.optimization_rules if r.name != rule_name]
        self.logger.info(f"Removed optimization rule: {rule_name}")
        
    def set_performance_baselines(self, baselines: Dict[str, float]):
        """Set performance baselines for optimization decisions"""
        self.performance_baselines.update(baselines)
        self.logger.info("Updated performance baselines")
        
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations without applying them"""
        current_performance = self.performance_monitor.get_current_performance_summary()
        recommendations = []
        
        for rule in self.optimization_rules:
            if self._can_apply_rule(rule) and rule.condition(current_performance):
                recommendations.append({
                    'rule_name': rule.name,
                    'action': rule.action.value,
                    'description': rule.description,
                    'priority': rule.priority,
                    'parameters': rule.parameters
                })
                
        # Sort by priority
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        return recommendations
        
    def simulate_optimization(self, rule_name: str) -> Dict[str, Any]:
        """Simulate the effect of applying an optimization rule"""
        rule = next((r for r in self.optimization_rules if r.name == rule_name), None)
        if not rule:
            return {'error': f'Rule {rule_name} not found'}
            
        current_performance = self.performance_monitor.get_current_performance_summary()
        
        # Create a copy of current settings
        simulated_settings = self.current_settings.copy()
        
        # Apply the rule's parameters
        simulated_settings.update(rule.parameters)
        
        # Estimate impact (simplified model)
        impact_estimate = self._estimate_optimization_impact(rule, current_performance, simulated_settings)
        
        return {
            'rule_name': rule_name,
            'current_settings': self.current_settings.copy(),
            'simulated_settings': simulated_settings,
            'estimated_impact': impact_estimate,
            'recommendation': 'apply' if impact_estimate['overall_improvement'] > 0 else 'skip'
        }
        
    def rollback_last_optimization(self) -> bool:
        """Rollback the last optimization if possible"""
        if not self.optimization_history:
            self.logger.warning("No optimization history to rollback")
            return False
            
        last_optimization = self.optimization_history[-1]
        
        try:
            # Restore previous settings
            self.current_settings.update(last_optimization.parameters_before)
            
            # Log rollback
            rollback_result = OptimizationResult(
                timestamp=datetime.utcnow(),
                rule_name=f"rollback_{last_optimization.rule_name}",
                action=OptimizationAction.RESTART_SERVICES,  # Generic rollback action
                parameters_before=last_optimization.parameters_after,
                parameters_after=last_optimization.parameters_before,
                expected_impact="Rollback to previous configuration",
                success=True
            )
            
            self.optimization_history.append(rollback_result)
            
            # Notify callbacks
            for callback in self.optimization_callbacks:
                try:
                    callback(rollback_result)
                except Exception as e:
                    self.logger.error(f"Optimization callback failed: {e}")
                    
            self.logger.info(f"Rolled back optimization: {last_optimization.rule_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
            
    def add_optimization_callback(self, callback: Callable[[OptimizationResult], None]):
        """Add callback for optimization events"""
        self.optimization_callbacks.append(callback)
        
    def get_optimization_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get optimization history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        history = [
            asdict(result) for result in self.optimization_history
            if result.timestamp > cutoff_time
        ]
        
        # Convert datetime objects to strings
        for item in history:
            item['timestamp'] = item['timestamp'].isoformat()
            
        return history
        
    def _optimization_loop(self):
        """Main optimization loop"""
        while self.optimization_active:
            try:
                # Get current performance
                current_performance = self.performance_monitor.get_current_performance_summary()
                
                # Apply optimization rules
                optimizations = self._apply_optimization_rules(current_performance)
                
                if optimizations:
                    self.logger.info(f"Applied {len(optimizations)} optimizations")
                    
                # Sleep until next optimization cycle
                time.sleep(self.optimization_interval)
                
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                time.sleep(30)  # Wait before retrying
                
    def _apply_optimization_rules(self, current_performance: Dict[str, Any]) -> List[OptimizationResult]:
        """Apply applicable optimization rules"""
        applied_optimizations = []
        
        # Sort rules by priority
        sorted_rules = sorted(self.optimization_rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if self._can_apply_rule(rule) and rule.condition(current_performance):
                try:
                    result = self._apply_optimization_rule(rule, current_performance)
                    applied_optimizations.append(result)
                    
                    # Update last applied time
                    self.rule_last_applied[rule.name] = datetime.utcnow()
                    
                    # For emergency strategy, apply multiple rules
                    if self.strategy != OptimizationStrategy.EMERGENCY:
                        break  # Apply only one rule at a time for non-emergency strategies
                        
                except Exception as e:
                    self.logger.error(f"Failed to apply optimization rule {rule.name}: {e}")
                    
        return applied_optimizations
        
    def _can_apply_rule(self, rule: OptimizationRule) -> bool:
        """Check if a rule can be applied (considering cooldown)"""
        if rule.name not in self.rule_last_applied:
            return True
            
        last_applied = self.rule_last_applied[rule.name]
        cooldown_elapsed = (datetime.utcnow() - last_applied).total_seconds()
        
        return cooldown_elapsed >= rule.cooldown_seconds
        
    def _apply_optimization_rule(self, rule: OptimizationRule, 
                               current_performance: Dict[str, Any]) -> OptimizationResult:
        """Apply a specific optimization rule"""
        parameters_before = self.current_settings.copy()
        
        try:
            # Apply the optimization
            if rule.action == OptimizationAction.INCREASE_LIMITS:
                self._increase_limits(rule.parameters)
            elif rule.action == OptimizationAction.DECREASE_LIMITS:
                self._decrease_limits(rule.parameters)
            elif rule.action == OptimizationAction.ADJUST_TIMEOUTS:
                self._adjust_timeouts(rule.parameters)
            elif rule.action == OptimizationAction.MODIFY_BATCHING:
                self._modify_batching(rule.parameters)
            elif rule.action == OptimizationAction.ENABLE_COMPRESSION:
                self._enable_compression(rule.parameters)
            elif rule.action == OptimizationAction.DISABLE_FEATURES:
                self._disable_features(rule.parameters)
            else:
                raise ValueError(f"Unknown optimization action: {rule.action}")
                
            parameters_after = self.current_settings.copy()
            
            result = OptimizationResult(
                timestamp=datetime.utcnow(),
                rule_name=rule.name,
                action=rule.action,
                parameters_before=parameters_before,
                parameters_after=parameters_after,
                expected_impact=rule.description,
                success=True
            )
            
            self.optimization_history.append(result)
            
            # Notify callbacks
            for callback in self.optimization_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    self.logger.error(f"Optimization callback failed: {e}")
                    
            self.logger.info(f"Applied optimization rule: {rule.name}")
            return result
            
        except Exception as e:
            result = OptimizationResult(
                timestamp=datetime.utcnow(),
                rule_name=rule.name,
                action=rule.action,
                parameters_before=parameters_before,
                parameters_after=parameters_before,  # No change due to error
                expected_impact=rule.description,
                success=False,
                error_message=str(e)
            )
            
            self.optimization_history.append(result)
            self.logger.error(f"Failed to apply optimization rule {rule.name}: {e}")
            return result
            
    def _create_optimization_rules(self) -> List[OptimizationRule]:
        """Create default optimization rules"""
        rules = []
        
        # High CPU usage rules
        rules.append(OptimizationRule(
            name="reduce_connections_high_cpu",
            condition=lambda perf: perf.get('resource_usage', {}).get('cpu_usage', 0) > 85,
            action=OptimizationAction.DECREASE_LIMITS,
            parameters={'max_connections': lambda current: int(current * 0.8)},
            priority=90,
            cooldown_seconds=300,
            description="Reduce connection limits due to high CPU usage"
        ))
        
        # High memory usage rules
        rules.append(OptimizationRule(
            name="reduce_connections_high_memory",
            condition=lambda perf: perf.get('resource_usage', {}).get('memory_usage', 0) > 90,
            action=OptimizationAction.DECREASE_LIMITS,
            parameters={'max_connections': lambda current: int(current * 0.7)},
            priority=95,
            cooldown_seconds=300,
            description="Reduce connection limits due to high memory usage"
        ))
        
        # High latency rules
        rules.append(OptimizationRule(
            name="optimize_for_high_latency",
            condition=lambda perf: perf.get('connection_quality', {}).get('avg_latency', 0) > 200,
            action=OptimizationAction.ADJUST_TIMEOUTS,
            parameters={
                'connection_timeout': lambda current: min(current * 1.5, 120),
                'ping_timeout': lambda current: min(current * 1.2, 120)
            },
            priority=70,
            cooldown_seconds=180,
            description="Increase timeouts due to high latency"
        ))
        
        # High error rate rules
        rules.append(OptimizationRule(
            name="reduce_load_high_errors",
            condition=lambda perf: perf.get('connection_quality', {}).get('error_rate', 0) > 0.1,
            action=OptimizationAction.DECREASE_LIMITS,
            parameters={
                'max_connections': lambda current: int(current * 0.9),
                'rate_limit_per_second': lambda current: int(current * 0.8)
            },
            priority=80,
            cooldown_seconds=240,
            description="Reduce load due to high error rate"
        ))
        
        # Low resource usage rules (scale up)
        rules.append(OptimizationRule(
            name="increase_capacity_low_usage",
            condition=lambda perf: (
                perf.get('resource_usage', {}).get('cpu_usage', 100) < 50 and
                perf.get('resource_usage', {}).get('memory_usage', 100) < 60 and
                perf.get('connection_quality', {}).get('error_rate', 1) < 0.02
            ),
            action=OptimizationAction.INCREASE_LIMITS,
            parameters={'max_connections': lambda current: min(int(current * 1.2), 2000)},
            priority=30,
            cooldown_seconds=600,
            description="Increase capacity due to low resource usage"
        ))
        
        # Message delivery optimization
        rules.append(OptimizationRule(
            name="optimize_message_batching",
            condition=lambda perf: perf.get('message_delivery', {}).get('avg_delivery_time', 0) > 100,
            action=OptimizationAction.MODIFY_BATCHING,
            parameters={'message_batch_size': lambda current: max(int(current * 0.8), 1)},
            priority=50,
            cooldown_seconds=120,
            description="Reduce batch size to improve message delivery time"
        ))
        
        # Compression optimization
        rules.append(OptimizationRule(
            name="enable_compression_high_throughput",
            condition=lambda perf: (
                perf.get('message_delivery', {}).get('throughput_messages_per_second', 0) > 50 and
                not self.current_settings.get('compression_enabled', False)
            ),
            action=OptimizationAction.ENABLE_COMPRESSION,
            parameters={'compression_enabled': True},
            priority=40,
            cooldown_seconds=300,
            description="Enable compression for high throughput scenarios"
        ))
        
        # Emergency rules for critical performance
        rules.append(OptimizationRule(
            name="emergency_reduce_all_limits",
            condition=lambda perf: (
                perf.get('resource_usage', {}).get('cpu_usage', 0) > 95 or
                perf.get('resource_usage', {}).get('memory_usage', 0) > 95 or
                perf.get('connection_quality', {}).get('error_rate', 0) > 0.2
            ),
            action=OptimizationAction.DECREASE_LIMITS,
            parameters={
                'max_connections': lambda current: int(current * 0.5),
                'rate_limit_per_second': lambda current: int(current * 0.5),
                'message_batch_size': lambda current: max(int(current * 0.5), 1)
            },
            priority=100,
            cooldown_seconds=60,
            description="Emergency: Drastically reduce limits due to critical performance"
        ))
        
        return rules
        
    def _increase_limits(self, parameters: Dict[str, Any]):
        """Increase system limits"""
        for key, value in parameters.items():
            if key in self.current_settings:
                if callable(value):
                    self.current_settings[key] = value(self.current_settings[key])
                else:
                    self.current_settings[key] = value
                    
    def _decrease_limits(self, parameters: Dict[str, Any]):
        """Decrease system limits"""
        for key, value in parameters.items():
            if key in self.current_settings:
                if callable(value):
                    self.current_settings[key] = value(self.current_settings[key])
                else:
                    self.current_settings[key] = value
                    
    def _adjust_timeouts(self, parameters: Dict[str, Any]):
        """Adjust timeout settings"""
        for key, value in parameters.items():
            if key in self.current_settings:
                if callable(value):
                    self.current_settings[key] = value(self.current_settings[key])
                else:
                    self.current_settings[key] = value
                    
    def _modify_batching(self, parameters: Dict[str, Any]):
        """Modify message batching settings"""
        for key, value in parameters.items():
            if key in self.current_settings:
                if callable(value):
                    self.current_settings[key] = value(self.current_settings[key])
                else:
                    self.current_settings[key] = value
                    
    def _enable_compression(self, parameters: Dict[str, Any]):
        """Enable compression features"""
        for key, value in parameters.items():
            if key in self.current_settings:
                self.current_settings[key] = value
                
    def _disable_features(self, parameters: Dict[str, Any]):
        """Disable non-essential features"""
        for key, value in parameters.items():
            if key in self.current_settings:
                self.current_settings[key] = value
                
    def _estimate_optimization_impact(self, rule: OptimizationRule, 
                                    current_performance: Dict[str, Any],
                                    simulated_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate the impact of an optimization (simplified model)"""
        impact = {
            'cpu_usage_change': 0,
            'memory_usage_change': 0,
            'latency_change': 0,
            'throughput_change': 0,
            'error_rate_change': 0,
            'overall_improvement': 0
        }
        
        # Simple impact estimation based on action type
        if rule.action == OptimizationAction.DECREASE_LIMITS:
            impact['cpu_usage_change'] = -10  # Reduce CPU usage
            impact['memory_usage_change'] = -15  # Reduce memory usage
            impact['throughput_change'] = -20  # Reduce throughput
            impact['error_rate_change'] = -30  # Reduce errors
            
        elif rule.action == OptimizationAction.INCREASE_LIMITS:
            impact['cpu_usage_change'] = 15  # Increase CPU usage
            impact['memory_usage_change'] = 20  # Increase memory usage
            impact['throughput_change'] = 30  # Increase throughput
            impact['error_rate_change'] = 10  # Might increase errors
            
        elif rule.action == OptimizationAction.ADJUST_TIMEOUTS:
            impact['latency_change'] = -10  # Improve latency handling
            impact['error_rate_change'] = -15  # Reduce timeout errors
            
        elif rule.action == OptimizationAction.ENABLE_COMPRESSION:
            impact['cpu_usage_change'] = 5  # Slight CPU increase
            impact['throughput_change'] = 20  # Improve throughput
            impact['latency_change'] = -5  # Slight latency improvement
            
        # Calculate overall improvement score
        current_cpu = current_performance.get('resource_usage', {}).get('cpu_usage', 50)
        current_memory = current_performance.get('resource_usage', {}).get('memory_usage', 50)
        current_errors = current_performance.get('connection_quality', {}).get('error_rate', 0.05)
        
        # Weight the improvements based on current state
        cpu_weight = 1.0 if current_cpu > 80 else 0.5
        memory_weight = 1.0 if current_memory > 80 else 0.5
        error_weight = 2.0 if current_errors > 0.1 else 1.0
        
        impact['overall_improvement'] = (
            impact['cpu_usage_change'] * cpu_weight +
            impact['memory_usage_change'] * memory_weight +
            impact['error_rate_change'] * error_weight +
            impact['throughput_change'] * 0.5
        ) / 4
        
        return impact


def create_performance_optimizer(performance_monitor: WebSocketPerformanceMonitor,
                               strategy: OptimizationStrategy = OptimizationStrategy.BALANCED) -> WebSocketPerformanceOptimizer:
    """Create a WebSocket performance optimizer"""
    return WebSocketPerformanceOptimizer(performance_monitor, strategy)


def setup_auto_optimization(performance_monitor: WebSocketPerformanceMonitor,
                          strategy: OptimizationStrategy = OptimizationStrategy.BALANCED) -> WebSocketPerformanceOptimizer:
    """Set up automatic performance optimization"""
    optimizer = create_performance_optimizer(performance_monitor, strategy)
    optimizer.start_auto_optimization()
    return optimizer