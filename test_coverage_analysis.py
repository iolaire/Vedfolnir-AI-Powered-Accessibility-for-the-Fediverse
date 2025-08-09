#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive Test Coverage Analysis

Analyzes the current test coverage and identifies gaps.
"""

import os
import ast
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Tuple
import unittest

class TestCoverageAnalyzer:
    """Analyzes test coverage across the project"""
    
    def __init__(self):
        self.project_root = Path('.')
        self.source_files = []
        self.test_files = []
        self.coverage_report = {
            'modules_with_tests': set(),
            'modules_without_tests': set(),
            'test_methods_count': 0,
            'source_methods_count': 0,
            'coverage_gaps': [],
            'recommendations': []
        }
    
    def analyze_coverage(self) -> Dict:
        """Run comprehensive coverage analysis"""
        print("🔍 Analyzing test coverage...")
        
        # 1. Discover source and test files
        self._discover_files()
        
        # 2. Analyze source code
        self._analyze_source_files()
        
        # 3. Analyze test files
        self._analyze_test_files()
        
        # 4. Identify coverage gaps
        self._identify_coverage_gaps()
        
        # 5. Generate recommendations
        self._generate_recommendations()
        
        return self.coverage_report
    
    def _discover_files(self):
        """Discover all Python source and test files"""
        print("📁 Discovering files...")
        
        # Source files (exclude tests, migrations, scripts)
        exclude_dirs = {'tests', '__pycache__', '.pytest_cache', 'migrations', 'scripts', '.kiro', '.vscode', '.devcontainer'}
        exclude_files = {'setup.py', 'conftest.py'}
        
        for file_path in self.project_root.rglob('*.py'):
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.name in exclude_files:
                continue
            if file_path.name.startswith('test_'):
                continue
            
            self.source_files.append(file_path)
        
        # Test files
        test_dir = self.project_root / 'tests'
        if test_dir.exists():
            for file_path in test_dir.rglob('test_*.py'):
                self.test_files.append(file_path)
        
        # Also check for test files in scripts/testing
        scripts_test_dir = self.project_root / 'scripts' / 'testing'
        if scripts_test_dir.exists():
            for file_path in scripts_test_dir.rglob('test_*.py'):
                self.test_files.append(file_path)
        
        print(f"   Found {len(self.source_files)} source files")
        print(f"   Found {len(self.test_files)} test files")
    
    def _analyze_source_files(self):
        """Analyze source files to identify functions and classes"""
        print("🔍 Analyzing source files...")
        
        for file_path in self.source_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Count functions and classes
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith('_'):  # Skip private methods
                            self.coverage_report['source_methods_count'] += 1
                    elif isinstance(node, ast.ClassDef):
                        # Count public methods in classes
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if not item.name.startswith('_'):
                                    self.coverage_report['source_methods_count'] += 1
                
            except Exception as e:
                print(f"   ⚠️  Error analyzing {file_path}: {e}")
    
    def _analyze_test_files(self):
        """Analyze test files to identify test methods"""
        print("🧪 Analyzing test files...")
        
        for file_path in self.test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Find test classes and methods
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if node.name.startswith('Test'):
                            # This is a test class
                            module_name = file_path.stem.replace('test_', '')
                            self.coverage_report['modules_with_tests'].add(module_name)
                            
                            # Count test methods
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    if item.name.startswith('test_'):
                                        self.coverage_report['test_methods_count'] += 1
                    
                    elif isinstance(node, ast.FunctionDef):
                        if node.name.startswith('test_'):
                            # Standalone test function
                            module_name = file_path.stem.replace('test_', '')
                            self.coverage_report['modules_with_tests'].add(module_name)
                            self.coverage_report['test_methods_count'] += 1
                
            except Exception as e:
                print(f"   ⚠️  Error analyzing {file_path}: {e}")
    
    def _identify_coverage_gaps(self):
        """Identify modules without test coverage"""
        print("🔍 Identifying coverage gaps...")
        
        # Get all source module names
        source_modules = set()
        for file_path in self.source_files:
            module_name = file_path.stem
            if module_name not in ['__init__', 'conftest']:
                source_modules.add(module_name)
        
        # Find modules without tests
        self.coverage_report['modules_without_tests'] = source_modules - self.coverage_report['modules_with_tests']
        
        # Identify critical modules that need tests
        critical_modules = {
            'web_app', 'models', 'database', 'config', 'security_middleware',
            'session_manager', 'caption_security', 'web_caption_generation_service',
            'task_queue_manager', 'progress_tracker', 'websocket_progress_handler',
            'platform_aware_caption_adapter', 'error_recovery_manager',
            'admin_monitoring', 'secure_error_handlers', 'secure_logging'
        }
        
        missing_critical_tests = critical_modules & self.coverage_report['modules_without_tests']
        
        for module in missing_critical_tests:
            self.coverage_report['coverage_gaps'].append({
                'type': 'missing_critical_test',
                'module': module,
                'priority': 'high',
                'description': f'Critical module {module} has no test coverage'
            })
        
        # Check for insufficient test coverage (less than 3 tests per module)
        for file_path in self.test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                test_count = content.count('def test_')
                if test_count < 3:
                    module_name = file_path.stem.replace('test_', '')
                    self.coverage_report['coverage_gaps'].append({
                        'type': 'insufficient_coverage',
                        'module': module_name,
                        'priority': 'medium',
                        'description': f'Module {module_name} has only {test_count} tests'
                    })
            except Exception:
                pass
    
    def _generate_recommendations(self):
        """Generate recommendations for improving test coverage"""
        print("💡 Generating recommendations...")
        
        recommendations = []
        
        # High priority recommendations
        critical_missing = [gap for gap in self.coverage_report['coverage_gaps'] 
                          if gap['type'] == 'missing_critical_test']
        
        if critical_missing:
            recommendations.append({
                'priority': 'high',
                'category': 'Critical Test Coverage',
                'description': 'Create comprehensive test suites for critical modules',
                'modules': [gap['module'] for gap in critical_missing],
                'action': 'Create test files with unit tests, integration tests, and edge case coverage'
            })
        
        # Security testing recommendations
        security_modules = ['security_middleware', 'caption_security', 'secure_error_handlers', 'secure_logging']
        missing_security_tests = [m for m in security_modules if m in self.coverage_report['modules_without_tests']]
        
        if missing_security_tests:
            recommendations.append({
                'priority': 'high',
                'category': 'Security Test Coverage',
                'description': 'Implement comprehensive security testing',
                'modules': missing_security_tests,
                'action': 'Create security-focused tests including penetration testing scenarios'
            })
        
        # Integration testing recommendations
        recommendations.append({
            'priority': 'medium',
            'category': 'Integration Testing',
            'description': 'Implement end-to-end integration tests',
            'modules': ['web_app', 'session_manager', 'database'],
            'action': 'Create tests that verify complete user workflows'
        })
        
        # Performance testing recommendations
        recommendations.append({
            'priority': 'medium',
            'category': 'Performance Testing',
            'description': 'Add performance and load testing',
            'modules': ['web_app', 'database', 'task_queue_manager'],
            'action': 'Create tests for concurrent users, database performance, and memory usage'
        })
        
        # API testing recommendations
        recommendations.append({
            'priority': 'medium',
            'category': 'API Testing',
            'description': 'Comprehensive API endpoint testing',
            'modules': ['web_app'],
            'action': 'Test all API endpoints with various input scenarios and error conditions'
        })
        
        self.coverage_report['recommendations'] = recommendations
    
    def generate_report(self) -> str:
        """Generate a comprehensive coverage report"""
        report = []
        report.append("# Test Coverage Analysis Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        total_modules = len(self.source_files)
        tested_modules = len(self.coverage_report['modules_with_tests'])
        coverage_percentage = (tested_modules / total_modules * 100) if total_modules > 0 else 0
        
        report.append("## Summary")
        report.append(f"- **Total Source Modules**: {total_modules}")
        report.append(f"- **Modules with Tests**: {tested_modules}")
        report.append(f"- **Coverage Percentage**: {coverage_percentage:.1f}%")
        report.append(f"- **Total Test Methods**: {self.coverage_report['test_methods_count']}")
        report.append(f"- **Total Source Methods**: {self.coverage_report['source_methods_count']}")
        report.append("")
        
        # Coverage Status
        if coverage_percentage >= 80:
            status = "🟢 EXCELLENT"
        elif coverage_percentage >= 60:
            status = "🟡 GOOD"
        elif coverage_percentage >= 40:
            status = "🟠 FAIR"
        else:
            status = "🔴 POOR"
        
        report.append(f"## Coverage Status: {status}")
        report.append("")
        
        # Modules with Tests
        if self.coverage_report['modules_with_tests']:
            report.append("## ✅ Modules with Test Coverage")
            for module in sorted(self.coverage_report['modules_with_tests']):
                report.append(f"- {module}")
            report.append("")
        
        # Modules without Tests
        if self.coverage_report['modules_without_tests']:
            report.append("## ❌ Modules without Test Coverage")
            for module in sorted(self.coverage_report['modules_without_tests']):
                report.append(f"- {module}")
            report.append("")
        
        # Coverage Gaps
        if self.coverage_report['coverage_gaps']:
            report.append("## 🔍 Coverage Gaps")
            for gap in self.coverage_report['coverage_gaps']:
                priority_emoji = "🔴" if gap['priority'] == 'high' else "🟡"
                report.append(f"- {priority_emoji} **{gap['module']}**: {gap['description']}")
            report.append("")
        
        # Recommendations
        if self.coverage_report['recommendations']:
            report.append("## 💡 Recommendations")
            for rec in self.coverage_report['recommendations']:
                priority_emoji = "🔴" if rec['priority'] == 'high' else "🟡"
                report.append(f"### {priority_emoji} {rec['category']}")
                report.append(f"**Description**: {rec['description']}")
                report.append(f"**Modules**: {', '.join(rec['modules'])}")
                report.append(f"**Action**: {rec['action']}")
                report.append("")
        
        return "\n".join(report)

def main():
    """Run test coverage analysis"""
    analyzer = TestCoverageAnalyzer()
    
    print("🚀 Starting Test Coverage Analysis")
    print("=" * 50)
    
    # Run analysis
    coverage_data = analyzer.analyze_coverage()
    
    # Generate and save report
    report = analyzer.generate_report()
    
    # Save to file
    os.makedirs('docs/summary', exist_ok=True)
    with open('docs/summary/TEST_COVERAGE_REPORT.md', 'w') as f:
        f.write(report)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 ANALYSIS COMPLETE")
    print("=" * 50)
    
    total_modules = len(analyzer.source_files)
    tested_modules = len(coverage_data['modules_with_tests'])
    coverage_percentage = (tested_modules / total_modules * 100) if total_modules > 0 else 0
    
    print(f"Coverage: {coverage_percentage:.1f}% ({tested_modules}/{total_modules} modules)")
    print(f"Test Methods: {coverage_data['test_methods_count']}")
    print(f"Coverage Gaps: {len(coverage_data['coverage_gaps'])}")
    print(f"Recommendations: {len(coverage_data['recommendations'])}")
    
    print(f"\n📄 Detailed report saved to: docs/summary/TEST_COVERAGE_REPORT.md")
    
    return coverage_percentage >= 70  # Return success if coverage is good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)