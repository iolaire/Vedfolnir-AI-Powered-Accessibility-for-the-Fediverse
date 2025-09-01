# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for LegacySystemAnalyzer

Tests the legacy notification system analysis and migration planning functionality.
"""

import unittest
import tempfile
import os
import json
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from legacy_system_analyzer import (
    LegacySystemAnalyzer,
    LegacyNotificationPattern,
    DependencyMapping,
    MigrationPlan,
    create_migration_backup,
    validate_migration_prerequisites
)


class TestLegacySystemAnalyzer(unittest.TestCase):
    """Test cases for LegacySystemAnalyzer"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = LegacySystemAnalyzer(self.test_dir)
        
        # Create test files
        self._create_test_files()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_files(self):
        """Create test files with legacy notification patterns"""
        
        # Python file with Flask flash messages
        python_content = '''from flask import flash, render_template

def test_route():
    flash('Success message', 'success')
    flash('Error occurred', 'error')
    return render_template('test.html')

def another_function():
    messages = get_flashed_messages(with_categories=True)
    return messages
'''
        
        # JavaScript file with notifications and polling
        js_content = '''
function showNotification(message) {
    alert(message);
    confirm('Are you sure?');
}

function startPolling() {
    setInterval(function() {
        fetch('/api/status').then(response => {
            // Handle response
        });
    }, 5000);
}

function customNotify(msg) {
    $('.notification').notify(msg);
}
'''
        
        # HTML template with notification displays
        html_content = '''
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <div class="notification-area"></div>
</body>
</html>
'''
        
        # Create directories
        os.makedirs(os.path.join(self.test_dir, 'templates'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'static', 'js'), exist_ok=True)
        
        # Write test files
        with open(os.path.join(self.test_dir, 'test_routes.py'), 'w') as f:
            f.write(python_content)
        
        with open(os.path.join(self.test_dir, 'static', 'js', 'notifications.js'), 'w') as f:
            f.write(js_content)
        
        with open(os.path.join(self.test_dir, 'templates', 'base.html'), 'w') as f:
            f.write(html_content)
    
    def test_initialization(self):
        """Test LegacySystemAnalyzer initialization"""
        self.assertEqual(str(self.analyzer.project_root), self.test_dir)
        self.assertEqual(len(self.analyzer.patterns), 0)
        self.assertEqual(len(self.analyzer.dependencies), 0)
        self.assertEqual(len(self.analyzer.migration_plans), 0)
    
    def test_scan_legacy_notifications(self):
        """Test scanning for legacy notification patterns"""
        results = self.analyzer.scan_legacy_notifications()
        
        # Should find patterns in all categories
        self.assertIn('flask_flash', results)
        self.assertIn('js_notifications', results)
        self.assertIn('ajax_polling', results)
        self.assertIn('template_notifications', results)
        
        # Should find Flask flash patterns
        self.assertGreater(len(results['flask_flash']), 0)
        
        # Should find JavaScript notification patterns
        self.assertGreater(len(results['js_notifications']), 0)
        
        # Should find AJAX polling patterns
        self.assertGreater(len(results['ajax_polling']), 0)
        
        # Should find template notification patterns
        self.assertGreater(len(results['template_notifications']), 0)
        
        # Verify pattern details
        flash_pattern = results['flask_flash'][0]
        self.assertEqual(flash_pattern.pattern_type, 'flask_flash')
        self.assertIn('flash(', flash_pattern.code_snippet)
        self.assertIsNotNone(flash_pattern.file_path)
        self.assertGreater(flash_pattern.line_number, 0)
    
    def test_identify_dependencies(self):
        """Test dependency identification"""
        # First scan for patterns
        self.analyzer.scan_legacy_notifications()
        
        # Then identify dependencies
        dependencies = self.analyzer.identify_dependencies()
        
        self.assertIn('imports', dependencies)
        self.assertIn('template_includes', dependencies)
        self.assertIn('js_references', dependencies)
        self.assertIn('route_dependencies', dependencies)
        
        # Should have found some dependencies
        total_deps = sum(len(deps) for deps in dependencies.values())
        self.assertGreater(total_deps, 0)
    
    def test_generate_removal_plan(self):
        """Test migration plan generation"""
        # First scan and analyze
        self.analyzer.scan_legacy_notifications()
        self.analyzer.identify_dependencies()
        
        # Generate migration plan
        plans = self.analyzer.generate_removal_plan()
        
        # Should have multiple phases
        self.assertGreater(len(plans), 0)
        
        # Verify plan structure
        for plan in plans:
            self.assertIsInstance(plan, MigrationPlan)
            self.assertGreater(plan.phase, 0)
            self.assertIsNotNone(plan.description)
            self.assertIsInstance(plan.rollback_procedures, list)
            self.assertIsInstance(plan.validation_steps, list)
            self.assertIn(plan.estimated_effort, ['low', 'medium', 'high'])
    
    def test_validate_safe_removal(self):
        """Test safe removal validation"""
        # Test with existing file
        test_file = os.path.join(self.test_dir, 'test_routes.py')
        result = self.analyzer.validate_safe_removal(test_file)
        self.assertIsInstance(result, bool)
        
        # Test with non-existent file
        result = self.analyzer.validate_safe_removal('nonexistent.py')
        self.assertFalse(result)
        
        # Test with critical system file
        critical_file = os.path.join(self.test_dir, 'config.py')
        with open(critical_file, 'w') as f:
            f.write('# Critical config file')
        
        result = self.analyzer.validate_safe_removal(critical_file)
        self.assertFalse(result)
    
    def test_export_analysis_report(self):
        """Test analysis report export"""
        # Perform analysis
        self.analyzer.scan_legacy_notifications()
        self.analyzer.identify_dependencies()
        self.analyzer.generate_removal_plan()
        
        # Export report
        report_path = os.path.join(self.test_dir, 'test_report.json')
        self.analyzer.export_analysis_report(report_path)
        
        # Verify report was created
        self.assertTrue(os.path.exists(report_path))
        
        # Verify report content
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        self.assertIn('analysis_metadata', report)
        self.assertIn('legacy_patterns', report)
        self.assertIn('dependencies', report)
        self.assertIn('migration_plans', report)
        self.assertIn('risk_assessment', report)
        self.assertIn('recommendations', report)
        
        # Verify metadata
        metadata = report['analysis_metadata']
        self.assertEqual(metadata['project_root'], self.test_dir)
        self.assertGreater(metadata['total_patterns_found'], 0)
    
    def test_pattern_risk_assessment(self):
        """Test risk level assessment for different patterns"""
        # Test Flask flash risk assessment
        high_risk_line = "flash('Critical error occurred', 'error')"
        risk = self.analyzer._assess_flash_risk(high_risk_line)
        self.assertEqual(risk, 'high')
        
        low_risk_line = "flash('Welcome message', 'info')"
        risk = self.analyzer._assess_flash_risk(low_risk_line)
        self.assertEqual(risk, 'low')
        
        # Test JavaScript risk assessment
        high_risk_js = "alert('Critical error');"
        risk = self.analyzer._assess_js_risk(high_risk_js)
        self.assertEqual(risk, 'high')
        
        medium_risk_js = "$('.notification').show();"
        risk = self.analyzer._assess_js_risk(medium_risk_js)
        self.assertEqual(risk, 'medium')
    
    def test_function_name_extraction(self):
        """Test function name extraction from code"""
        lines = [
            "def test_function():",
            "    flash('message')",
            "    return True"
        ]
        
        # Test with line 2 (1-indexed) which contains flash, should find function at line 1 (0-indexed)
        function_name = self.analyzer._extract_function_name(lines, 2)  
        self.assertEqual(function_name, 'test_function')
        
        # Test JavaScript function extraction
        js_lines = [
            "function showAlert() {",
            "    alert('message');",
            "}"
        ]
        
        js_function_name = self.analyzer._extract_js_function_name(js_lines, 2)
        self.assertEqual(js_function_name, 'showAlert')
    
    def test_file_exclusion(self):
        """Test file exclusion logic"""
        # Test excluded patterns
        test_cases = [
            ('__pycache__/test.py', True),
            ('.git/config', True),
            ('node_modules/package.json', True),
            ('normal_file.py', False),
            ('src/main.py', False),
            ('migrations/versions/abc123.py', True)
        ]
        
        for file_path, should_exclude in test_cases:
            result = self.analyzer._should_exclude_file(Path(file_path))
            self.assertEqual(result, should_exclude, f"File {file_path} exclusion failed")


class TestLegacyNotificationPattern(unittest.TestCase):
    """Test cases for LegacyNotificationPattern dataclass"""
    
    def test_pattern_creation(self):
        """Test creating notification pattern"""
        pattern = LegacyNotificationPattern(
            file_path='test.py',
            line_number=10,
            pattern_type='flask_flash',
            code_snippet="flash('test message')",
            function_name='test_func',
            risk_level='medium'
        )
        
        self.assertEqual(pattern.file_path, 'test.py')
        self.assertEqual(pattern.line_number, 10)
        self.assertEqual(pattern.pattern_type, 'flask_flash')
        self.assertEqual(pattern.risk_level, 'medium')
        self.assertEqual(pattern.dependencies, [])  # Default empty list
    
    def test_pattern_with_dependencies(self):
        """Test pattern with dependencies"""
        pattern = LegacyNotificationPattern(
            file_path='test.py',
            line_number=5,
            pattern_type='js_notification',
            code_snippet="alert('message')",
            dependencies=['jquery', 'bootstrap']
        )
        
        self.assertEqual(pattern.dependencies, ['jquery', 'bootstrap'])


class TestDependencyMapping(unittest.TestCase):
    """Test cases for DependencyMapping dataclass"""
    
    def test_dependency_creation(self):
        """Test creating dependency mapping"""
        dependency = DependencyMapping(
            source_file='main.py',
            target_files=['utils.py', 'helpers.py'],
            dependency_type='import',
            impact_level='high'
        )
        
        self.assertEqual(dependency.source_file, 'main.py')
        self.assertEqual(dependency.target_files, ['utils.py', 'helpers.py'])
        self.assertEqual(dependency.dependency_type, 'import')
        self.assertEqual(dependency.impact_level, 'high')


class TestMigrationPlan(unittest.TestCase):
    """Test cases for MigrationPlan dataclass"""
    
    def test_migration_plan_creation(self):
        """Test creating migration plan"""
        plan = MigrationPlan(
            phase=1,
            description='Test phase',
            files_to_modify=['file1.py', 'file2.py'],
            patterns_to_remove=[],
            dependencies_to_update=[],
            rollback_procedures=['backup files', 'restore from backup'],
            validation_steps=['run tests', 'check functionality'],
            estimated_effort='medium'
        )
        
        self.assertEqual(plan.phase, 1)
        self.assertEqual(plan.description, 'Test phase')
        self.assertEqual(plan.files_to_modify, ['file1.py', 'file2.py'])
        self.assertEqual(plan.estimated_effort, 'medium')


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.backup_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(self.backup_dir, ignore_errors=True)
    
    def test_create_migration_backup(self):
        """Test migration backup creation"""
        # Create test files
        test_file = os.path.join(self.test_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write('# Test file')
        
        # Create backup
        backup_path = os.path.join(self.backup_dir, 'backup')
        result = create_migration_backup(self.test_dir, backup_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(os.path.exists(os.path.join(backup_path, 'test.py')))
    
    @patch('os.path.exists')
    def test_validate_migration_prerequisites(self, mock_exists):
        """Test migration prerequisites validation"""
        # Mock file existence
        def mock_exists_side_effect(path):
            if 'websocket_factory.py' in path:
                return True
            elif 'unified_notification_manager.py' in path:
                return True
            elif path == 'tests':
                return True
            return False
        
        mock_exists.side_effect = mock_exists_side_effect
        
        with patch('os.listdir', return_value=['test1.py', 'test2.py']):
            checks = validate_migration_prerequisites()
        
        self.assertIn('websocket_framework_exists', checks)
        self.assertIn('unified_notification_manager_exists', checks)
        self.assertIn('test_suite_available', checks)
        self.assertIn('backup_created', checks)


if __name__ == '__main__':
    unittest.main()