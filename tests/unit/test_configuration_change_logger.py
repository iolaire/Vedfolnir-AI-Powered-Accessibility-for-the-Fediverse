# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Configuration Change Impact Logger
"""

import unittest
import time
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from configuration_change_logger import (
    ConfigurationChangeLogger,
    ConfigurationChange,
    SystemBehaviorSnapshot,
    ChangeImpactAnalysis,
    RollbackPlan,
    ChangeImpactLevel,
    ChangeSource,
    SystemBehaviorMetric
)


class TestConfigurationChangeLogger(unittest.TestCase):
    """Test cases for ConfigurationChangeLogger"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = ConfigurationChangeLogger(
            retention_days=1,
            max_changes_in_memory=100,
            behavior_tracking_enabled=True
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.logger._monitoring_active:
            self.logger.stop_behavior_monitoring()
    
    def test_log_configuration_change(self):
        """Test logging configuration changes"""
        # Log a configuration change
        change_id = self.logger.log_configuration_change(
            key='max_concurrent_jobs',
            old_value=10,
            new_value=15,
            source=ChangeSource.ADMIN_UI,
            user_id=1,
            user_name='admin',
            requires_restart=True,
            impact_level=ChangeImpactLevel.MEDIUM,
            reason='Increase capacity for peak load',
            affected_services=['task_queue', 'worker_pool']
        )
        
        # Verify change was logged
        self.assertIsInstance(change_id, str)
        self.assertTrue(len(change_id) > 0)
        
        # Verify change is stored
        with self.logger._changes_lock:
            self.assertEqual(len(self.logger._changes), 1)
            self.assertIn(change_id, self.logger._changes_by_id)
            
            change = self.logger._changes_by_id[change_id]
            self.assertEqual(change.key, 'max_concurrent_jobs')
            self.assertEqual(change.old_value, 10)
            self.assertEqual(change.new_value, 15)
            self.assertEqual(change.source, ChangeSource.ADMIN_UI)
            self.assertEqual(change.user_id, 1)
            self.assertEqual(change.user_name, 'admin')
            self.assertTrue(change.requires_restart)
            self.assertEqual(change.impact_level, ChangeImpactLevel.MEDIUM)
            self.assertEqual(change.reason, 'Increase capacity for peak load')
            self.assertEqual(change.affected_services, ['task_queue', 'worker_pool'])
            self.assertIsNotNone(change.rollback_data)
    
    def test_metric_collector_registration(self):
        """Test registering metric collectors"""
        # Register a test metric collector
        def test_collector():
            return 42.5
        
        self.logger.register_metric_collector(
            SystemBehaviorMetric.RESPONSE_TIME,
            test_collector
        )
        
        # Verify collector was registered
        with self.logger._collector_lock:
            self.assertIn(SystemBehaviorMetric.RESPONSE_TIME, self.logger._metric_collectors)
            collector = self.logger._metric_collectors[SystemBehaviorMetric.RESPONSE_TIME]
            self.assertEqual(collector(), 42.5)
    
    def test_behavior_snapshot_creation(self):
        """Test creating system behavior snapshots"""
        # Register test collectors
        def cpu_collector():
            return 25.5
        
        def memory_collector():
            return 60.2
        
        self.logger.register_metric_collector(SystemBehaviorMetric.CPU_USAGE, cpu_collector)
        self.logger.register_metric_collector(SystemBehaviorMetric.MEMORY_USAGE, memory_collector)
        
        # Take a behavior snapshot
        snapshot = self.logger._take_behavior_snapshot()
        
        # Verify snapshot
        self.assertIsInstance(snapshot, SystemBehaviorSnapshot)
        self.assertIsInstance(snapshot.timestamp, datetime)
        self.assertEqual(snapshot.metrics[SystemBehaviorMetric.CPU_USAGE], 25.5)
        self.assertEqual(snapshot.metrics[SystemBehaviorMetric.MEMORY_USAGE], 60.2)
    
    def test_change_impact_analysis(self):
        """Test configuration change impact analysis"""
        # Register test collectors
        def response_time_collector():
            return 50.0  # Will change after configuration change
        
        self.logger.register_metric_collector(
            SystemBehaviorMetric.RESPONSE_TIME,
            response_time_collector
        )
        
        # Log a configuration change
        change_id = self.logger.log_configuration_change(
            key='cache_size',
            old_value=100,
            new_value=200,
            source=ChangeSource.ADMIN_UI,
            impact_level=ChangeImpactLevel.MEDIUM
        )
        
        # Simulate behavior snapshots
        pre_snapshot = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=1),
            metrics={SystemBehaviorMetric.RESPONSE_TIME: 50.0}
        )
        
        post_snapshot1 = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc),
            metrics={SystemBehaviorMetric.RESPONSE_TIME: 35.0}  # Improved response time
        )
        
        post_snapshot2 = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc) + timedelta(minutes=1),
            metrics={SystemBehaviorMetric.RESPONSE_TIME: 30.0}  # Further improvement
        )
        
        # Manually add snapshots to behavior history
        with self.logger._behavior_lock:
            self.logger._behavior_snapshots.extend([pre_snapshot, post_snapshot1, post_snapshot2])
        
        # Analyze impact
        analysis = self.logger.analyze_change_impact(change_id, analysis_duration_minutes=2)
        
        # Verify analysis
        self.assertIsInstance(analysis, ChangeImpactAnalysis)
        self.assertEqual(analysis.change_id, change_id)
        self.assertEqual(analysis.pre_change_snapshot, pre_snapshot)
        self.assertEqual(len(analysis.post_change_snapshots), 2)
        self.assertGreater(analysis.impact_score, 0.0)
        self.assertIn('response_time', analysis.performance_delta)
        # Average of post snapshots: (35 + 30) / 2 = 32.5, delta = 32.5 - 50 = -17.5
        self.assertEqual(analysis.performance_delta['response_time'], -17.5)
    
    def test_rollback_plan_creation(self):
        """Test creating rollback plans"""
        # Log multiple configuration changes
        change_id1 = self.logger.log_configuration_change(
            key='max_connections',
            old_value=100,
            new_value=200,
            source=ChangeSource.ADMIN_UI,
            requires_restart=True,
            impact_level=ChangeImpactLevel.HIGH
        )
        
        change_id2 = self.logger.log_configuration_change(
            key='timeout_seconds',
            old_value=30,
            new_value=60,
            source=ChangeSource.API,
            requires_restart=False,
            impact_level=ChangeImpactLevel.MEDIUM
        )
        
        # Create rollback plan
        plan = self.logger.create_rollback_plan(
            change_ids=[change_id1, change_id2],
            reason='Performance degradation detected'
        )
        
        # Verify rollback plan
        self.assertIsInstance(plan, RollbackPlan)
        self.assertEqual(len(plan.target_change_ids), 2)
        self.assertIn(change_id1, plan.target_change_ids)
        self.assertIn(change_id2, plan.target_change_ids)
        self.assertEqual(len(plan.rollback_steps), 2)
        self.assertTrue(plan.requires_restart)  # One of the changes requires restart
        self.assertEqual(plan.estimated_impact, ChangeImpactLevel.HIGH)  # Highest impact level
        
        # Verify rollback steps are in reverse chronological order
        self.assertEqual(plan.rollback_steps[0]['change_id'], change_id2)  # More recent change first
        self.assertEqual(plan.rollback_steps[1]['change_id'], change_id1)
        
        # Verify rollback values
        self.assertEqual(plan.rollback_steps[0]['rollback_value'], 30)  # timeout_seconds
        self.assertEqual(plan.rollback_steps[1]['rollback_value'], 100)  # max_connections
    
    def test_rollback_execution(self):
        """Test executing rollback plans"""
        # Log a configuration change
        change_id = self.logger.log_configuration_change(
            key='buffer_size',
            old_value=1024,
            new_value=2048,
            source=ChangeSource.ADMIN_UI
        )
        
        # Create rollback plan
        plan = self.logger.create_rollback_plan([change_id])
        
        # Mock configuration service
        mock_config_service = Mock()
        
        # Execute rollback
        success, errors = self.logger.execute_rollback(plan.rollback_id, mock_config_service)
        
        # Verify rollback execution
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        
        # Verify rollback was logged as a new change
        with self.logger._changes_lock:
            self.assertEqual(len(self.logger._changes), 2)  # Original change + rollback change
            rollback_change = self.logger._changes[-1]  # Most recent change
            self.assertEqual(rollback_change.source, ChangeSource.ROLLBACK)
            self.assertEqual(rollback_change.key, 'buffer_size')
            self.assertEqual(rollback_change.old_value, 2048)  # Current value
            self.assertEqual(rollback_change.new_value, 1024)  # Rollback value
    
    def test_change_history_filtering(self):
        """Test getting filtered change history"""
        # Log multiple changes
        change_id1 = self.logger.log_configuration_change(
            key='key1', old_value='old1', new_value='new1',
            source=ChangeSource.ADMIN_UI, user_id=1
        )
        
        change_id2 = self.logger.log_configuration_change(
            key='key2', old_value='old2', new_value='new2',
            source=ChangeSource.API, user_id=2
        )
        
        change_id3 = self.logger.log_configuration_change(
            key='key1', old_value='new1', new_value='newer1',
            source=ChangeSource.ADMIN_UI, user_id=1
        )
        
        # Test filtering by key
        key1_changes = self.logger.get_change_history(key='key1')
        self.assertEqual(len(key1_changes), 2)
        self.assertTrue(all(c.key == 'key1' for c in key1_changes))
        
        # Test filtering by user
        user1_changes = self.logger.get_change_history(user_id=1)
        self.assertEqual(len(user1_changes), 2)
        self.assertTrue(all(c.user_id == 1 for c in user1_changes))
        
        # Test combined filtering
        key1_user1_changes = self.logger.get_change_history(key='key1', user_id=1)
        self.assertEqual(len(key1_user1_changes), 2)
        self.assertTrue(all(c.key == 'key1' and c.user_id == 1 for c in key1_user1_changes))
        
        # Test limit
        limited_changes = self.logger.get_change_history(limit=2)
        self.assertEqual(len(limited_changes), 2)
        
        # Verify chronological order (newest first)
        all_changes = self.logger.get_change_history()
        self.assertEqual(len(all_changes), 3)
        self.assertEqual(all_changes[0].change_id, change_id3)  # Most recent
        self.assertEqual(all_changes[2].change_id, change_id1)  # Oldest
    
    def test_audit_trail_generation(self):
        """Test comprehensive audit trail generation"""
        # Log changes with different characteristics
        self.logger.log_configuration_change(
            key='setting1', old_value=1, new_value=2,
            source=ChangeSource.ADMIN_UI, user_id=1, user_name='admin',
            impact_level=ChangeImpactLevel.HIGH
        )
        
        self.logger.log_configuration_change(
            key='setting2', old_value='a', new_value='b',
            source=ChangeSource.API, user_id=2, user_name='api_user',
            impact_level=ChangeImpactLevel.LOW
        )
        
        self.logger.log_configuration_change(
            key='setting1', old_value=2, new_value=3,
            source=ChangeSource.ADMIN_UI, user_id=1, user_name='admin',
            impact_level=ChangeImpactLevel.CRITICAL
        )
        
        # Generate audit trail
        audit_trail = self.logger.get_audit_trail(hours=24)
        
        # Verify audit trail structure
        self.assertIn('total_changes', audit_trail)
        self.assertIn('changes_by_user', audit_trail)
        self.assertIn('changes_by_source', audit_trail)
        self.assertIn('changes_by_impact', audit_trail)
        self.assertIn('most_changed_keys', audit_trail)
        self.assertIn('recent_changes', audit_trail)
        self.assertIn('high_impact_changes', audit_trail)
        
        # Verify statistics
        self.assertEqual(audit_trail['total_changes'], 3)
        self.assertEqual(audit_trail['changes_by_user']['admin'], 2)
        self.assertEqual(audit_trail['changes_by_user']['api_user'], 1)
        self.assertEqual(audit_trail['changes_by_source']['admin_ui'], 2)
        self.assertEqual(audit_trail['changes_by_source']['api'], 1)
        self.assertEqual(audit_trail['changes_by_impact']['high'], 1)
        self.assertEqual(audit_trail['changes_by_impact']['critical'], 1)
        self.assertEqual(audit_trail['changes_by_impact']['low'], 1)
        
        # Verify most changed keys
        self.assertEqual(audit_trail['most_changed_keys'][0], ('setting1', 2))
        
        # Verify high impact changes
        high_impact_changes = audit_trail['high_impact_changes']
        self.assertEqual(len(high_impact_changes), 2)  # HIGH and CRITICAL
    
    def test_data_export(self):
        """Test audit data export functionality"""
        # Log a test change
        self.logger.log_configuration_change(
            key='export_test',
            old_value='before',
            new_value='after',
            source=ChangeSource.ADMIN_UI,
            user_name='test_user'
        )
        
        # Test JSON export
        json_export = self.logger.export_audit_data(hours=1, format='json')
        self.assertIsInstance(json_export, str)
        
        # Verify JSON structure
        data = json.loads(json_export)
        self.assertIn('export_timestamp', data)
        self.assertIn('audit_trail', data)
        self.assertEqual(data['audit_trail']['total_changes'], 1)
        
        # Test CSV export
        csv_export = self.logger.export_audit_data(hours=1, format='csv')
        self.assertIsInstance(csv_export, str)
        self.assertIn('timestamp,key,old_value,new_value,user,source,impact', csv_export)
        self.assertIn('export_test', csv_export)
    
    def test_behavior_monitoring(self):
        """Test continuous behavior monitoring"""
        # Register test collectors
        call_count = 0
        
        def test_collector():
            nonlocal call_count
            call_count += 1
            return call_count * 10.0
        
        self.logger.register_metric_collector(SystemBehaviorMetric.RESPONSE_TIME, test_collector)
        
        # Start monitoring with short interval
        self.logger.start_behavior_monitoring(interval_seconds=0.1)
        
        # Wait for a few monitoring cycles
        time.sleep(0.3)
        
        # Stop monitoring
        self.logger.stop_behavior_monitoring()
        
        # Verify snapshots were collected
        with self.logger._behavior_lock:
            self.assertGreater(len(self.logger._behavior_snapshots), 1)
            
            # Verify snapshots contain expected data
            for snapshot in self.logger._behavior_snapshots:
                self.assertIsInstance(snapshot, SystemBehaviorSnapshot)
                self.assertIn(SystemBehaviorMetric.RESPONSE_TIME, snapshot.metrics)
                self.assertGreater(snapshot.metrics[SystemBehaviorMetric.RESPONSE_TIME], 0)
    
    def test_anomaly_detection(self):
        """Test anomaly detection in behavior changes"""
        # Create snapshots with significant changes
        pre_snapshot = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc),
            metrics={
                SystemBehaviorMetric.RESPONSE_TIME: 10.0,
                SystemBehaviorMetric.CPU_USAGE: 20.0,
                SystemBehaviorMetric.MEMORY_USAGE: 50.0
            }
        )
        
        post_snapshot = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc),
            metrics={
                SystemBehaviorMetric.RESPONSE_TIME: 80.0,  # +70ms (above threshold)
                SystemBehaviorMetric.CPU_USAGE: 45.0,     # +25% (above threshold)
                SystemBehaviorMetric.MEMORY_USAGE: 55.0   # +5% (below threshold)
            }
        )
        
        # Detect anomalies
        anomalies = self.logger._detect_anomalies(pre_snapshot, [post_snapshot])
        
        # Verify anomaly detection
        self.assertGreater(len(anomalies), 0)
        
        # Should detect response_time and cpu_usage anomalies
        anomaly_text = ' '.join(anomalies)
        self.assertIn('response_time', anomaly_text)
        self.assertIn('cpu_usage', anomaly_text)
        self.assertNotIn('memory_usage', anomaly_text)  # Below threshold
    
    def test_recovery_time_detection(self):
        """Test recovery time detection"""
        # Create baseline snapshot
        pre_snapshot = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc),
            metrics={SystemBehaviorMetric.RESPONSE_TIME: 50.0}
        )
        
        # Create post-change snapshots showing recovery
        base_time = datetime.now(timezone.utc)
        post_snapshots = [
            SystemBehaviorSnapshot(
                timestamp=base_time + timedelta(seconds=30),
                metrics={SystemBehaviorMetric.RESPONSE_TIME: 80.0}  # Degraded
            ),
            SystemBehaviorSnapshot(
                timestamp=base_time + timedelta(seconds=60),
                metrics={SystemBehaviorMetric.RESPONSE_TIME: 65.0}  # Improving
            ),
            SystemBehaviorSnapshot(
                timestamp=base_time + timedelta(seconds=90),
                metrics={SystemBehaviorMetric.RESPONSE_TIME: 52.0}  # Recovered (within 10%)
            )
        ]
        
        # Detect recovery time
        recovery_time = self.logger._detect_recovery_time(pre_snapshot, post_snapshots)
        
        # Verify recovery detection
        self.assertIsNotNone(recovery_time)
        self.assertAlmostEqual(recovery_time, 90.0, delta=1.0)  # Should be ~90 seconds
    
    def test_correlation_confidence_calculation(self):
        """Test correlation confidence calculation"""
        # Create a high-impact change
        change = ConfigurationChange(
            change_id='test_change',
            timestamp=datetime.now(timezone.utc),
            key='critical_setting',
            old_value=100,
            new_value=200,
            source=ChangeSource.ADMIN_UI,
            impact_level=ChangeImpactLevel.HIGH
        )
        
        # Create snapshots showing significant behavior change
        pre_snapshot = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc),
            metrics={SystemBehaviorMetric.RESPONSE_TIME: 10.0}
        )
        
        post_snapshot = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc),
            metrics={SystemBehaviorMetric.RESPONSE_TIME: 60.0}  # Significant increase
        )
        
        # Calculate correlation confidence
        confidence = self.logger._calculate_correlation_confidence(
            change, pre_snapshot, [post_snapshot]
        )
        
        # Verify confidence calculation
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # High impact change with significant behavior change should have high confidence
        self.assertGreater(confidence, 0.5)
    
    def test_data_structures_serialization(self):
        """Test data structure serialization"""
        # Test ConfigurationChange serialization
        change = ConfigurationChange(
            change_id='test_id',
            timestamp=datetime.now(timezone.utc),
            key='test_key',
            old_value='old',
            new_value='new',
            source=ChangeSource.ADMIN_UI,
            impact_level=ChangeImpactLevel.MEDIUM
        )
        
        change_dict = change.to_dict()
        self.assertIsInstance(change_dict, dict)
        self.assertEqual(change_dict['change_id'], 'test_id')
        self.assertEqual(change_dict['source'], 'admin_ui')
        self.assertEqual(change_dict['impact_level'], 'medium')
        self.assertIsInstance(change_dict['timestamp'], str)
        
        # Test SystemBehaviorSnapshot serialization
        snapshot = SystemBehaviorSnapshot(
            timestamp=datetime.now(timezone.utc),
            metrics={SystemBehaviorMetric.RESPONSE_TIME: 25.5}
        )
        
        snapshot_dict = snapshot.to_dict()
        self.assertIsInstance(snapshot_dict, dict)
        self.assertIn('timestamp', snapshot_dict)
        self.assertIn('metrics', snapshot_dict)
        self.assertEqual(snapshot_dict['metrics']['response_time'], 25.5)
        
        # Test RollbackPlan serialization
        plan = RollbackPlan(
            rollback_id='test_rollback',
            target_change_ids=['change1', 'change2'],
            estimated_impact=ChangeImpactLevel.HIGH
        )
        
        plan_dict = plan.to_dict()
        self.assertIsInstance(plan_dict, dict)
        self.assertEqual(plan_dict['rollback_id'], 'test_rollback')
        self.assertEqual(plan_dict['estimated_impact'], 'high')
        self.assertIsInstance(plan_dict['created_at'], str)


if __name__ == '__main__':
    unittest.main()