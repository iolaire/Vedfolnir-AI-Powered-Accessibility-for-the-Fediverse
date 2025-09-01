#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Migration Safety Validation Script

Validates that legacy notification system removal is safe and provides
detailed safety analysis for each file and pattern.
"""

import argparse
import sys
import os
import ast
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from legacy_system_analyzer import LegacySystemAnalyzer, LegacyNotificationPattern


@dataclass
class SafetyCheck:
    """Represents a safety validation check"""
    check_name: str
    file_path: str
    pattern: Optional[LegacyNotificationPattern]
    status: str  # 'safe', 'warning', 'unsafe'
    reason: str
    recommendations: List[str]
    impact_level: str  # 'low', 'medium', 'high', 'critical'


class MigrationSafetyValidator:
    """
    Validates safety of legacy notification system removal
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.analyzer = LegacySystemAnalyzer(project_root)
        self.safety_checks: List[SafetyCheck] = []
        
        # Critical patterns that require special handling
        self.critical_patterns = [
            r'@app\.errorhandler',
            r'@.*\.errorhandler',
            r'except.*Exception',
            r'try:.*except',
            r'if.*error',
            r'raise.*Exception',
        ]
        
        # Safe patterns that can be removed with low risk
        self.safe_patterns = [
            r'flash\(["\'].*success.*["\']',
            r'flash\(["\'].*info.*["\']',
            r'flash\(["\'].*message.*["\']',
        ]
    
    def validate_all_patterns(self) -> Dict[str, List[SafetyCheck]]:
        """
        Validate safety of all detected legacy patterns
        
        Returns:
            Dictionary mapping safety levels to lists of checks
        """
        logging.info("Starting comprehensive safety validation")
        
        # First, scan for legacy patterns
        results = self.analyzer.scan_legacy_notifications()
        
        safety_results = {
            'safe': [],
            'warning': [],
            'unsafe': [],
            'critical': []
        }
        
        # Validate each pattern type
        for pattern_type, patterns in results.items():
            for pattern in patterns:
                checks = self._validate_pattern_safety(pattern)
                
                for check in checks:
                    if check.status in safety_results:
                        safety_results[check.status].append(check)
                    self.safety_checks.append(check)
        
        # Additional file-level safety checks
        self._perform_file_level_checks(safety_results)
        
        # System-level safety checks
        self._perform_system_level_checks(safety_results)
        
        logging.info(f"Safety validation complete. Found {len(self.safety_checks)} checks")
        return safety_results
    
    def _validate_pattern_safety(self, pattern: LegacyNotificationPattern) -> List[SafetyCheck]:
        """Validate safety of a specific pattern"""
        checks = []
        
        # Read file content for context analysis
        try:
            with open(pattern.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            checks.append(SafetyCheck(
                check_name='file_access',
                file_path=pattern.file_path,
                pattern=pattern,
                status='unsafe',
                reason=f'Cannot read file: {e}',
                recommendations=['Verify file exists and is readable'],
                impact_level='high'
            ))
            return checks
        
        # Context analysis around the pattern
        context_lines = self._get_context_lines(lines, pattern.line_number, 5)
        context_text = '\n'.join(context_lines)
        
        # Check if pattern is in critical code section
        if self._is_in_critical_section(context_text):
            checks.append(SafetyCheck(
                check_name='critical_section',
                file_path=pattern.file_path,
                pattern=pattern,
                status='unsafe',
                reason='Pattern found in critical error handling or authentication code',
                recommendations=[
                    'Review error handling logic carefully',
                    'Ensure replacement maintains error reporting',
                    'Test error scenarios thoroughly'
                ],
                impact_level='critical'
            ))
        
        # Check if pattern is in safe section
        elif self._is_safe_pattern(pattern.code_snippet):
            checks.append(SafetyCheck(
                check_name='safe_pattern',
                file_path=pattern.file_path,
                pattern=pattern,
                status='safe',
                reason='Pattern appears to be safe informational message',
                recommendations=[
                    'Replace with unified notification system',
                    'Test UI display after replacement'
                ],
                impact_level='low'
            ))
        
        # Check for dependencies
        dependency_check = self._check_pattern_dependencies(pattern, content)
        if dependency_check:
            checks.append(dependency_check)
        
        # Check for template usage
        template_check = self._check_template_usage(pattern)
        if template_check:
            checks.append(template_check)
        
        # Check for JavaScript integration
        js_check = self._check_javascript_integration(pattern)
        if js_check:
            checks.append(js_check)
        
        # Default safety assessment
        if not checks:
            checks.append(SafetyCheck(
                check_name='default_assessment',
                file_path=pattern.file_path,
                pattern=pattern,
                status='warning',
                reason='Pattern requires manual review for safety',
                recommendations=[
                    'Review pattern context manually',
                    'Test functionality after removal',
                    'Ensure replacement provides equivalent functionality'
                ],
                impact_level='medium'
            ))
        
        return checks
    
    def _perform_file_level_checks(self, safety_results: Dict[str, List[SafetyCheck]]) -> None:
        """Perform file-level safety checks"""
        
        # Get all files with patterns
        files_with_patterns = set()
        for checks in safety_results.values():
            for check in checks:
                if check.pattern:
                    files_with_patterns.add(check.file_path)
        
        for file_path in files_with_patterns:
            # Check if file is critical system file
            if self._is_critical_system_file(file_path):
                safety_results['critical'].append(SafetyCheck(
                    check_name='critical_system_file',
                    file_path=file_path,
                    pattern=None,
                    status='critical',
                    reason='File is critical to system operation',
                    recommendations=[
                        'Extra caution required for this file',
                        'Comprehensive testing after changes',
                        'Consider gradual migration approach',
                        'Maintain backup of original file'
                    ],
                    impact_level='critical'
                ))
            
            # Check file complexity
            complexity_check = self._assess_file_complexity(file_path)
            if complexity_check:
                safety_results[complexity_check.status].append(complexity_check)
    
    def _perform_system_level_checks(self, safety_results: Dict[str, List[SafetyCheck]]) -> None:
        """Perform system-level safety checks"""
        
        # Check if unified notification system exists
        unified_system_files = [
            'unified_notification_manager.py',
            'notification_message_router.py',
            'notification_ui_renderer.js'
        ]
        
        missing_files = []
        for file_name in unified_system_files:
            if not (self.project_root / file_name).exists():
                missing_files.append(file_name)
        
        if missing_files:
            safety_results['critical'].append(SafetyCheck(
                check_name='unified_system_missing',
                file_path='system',
                pattern=None,
                status='critical',
                reason=f'Unified notification system components missing: {", ".join(missing_files)}',
                recommendations=[
                    'Implement unified notification system before migration',
                    'Ensure all required components are in place',
                    'Test unified system thoroughly'
                ],
                impact_level='critical'
            ))
        
        # Check WebSocket framework availability
        websocket_files = [
            'websocket_factory.py',
            'websocket_cors_manager.py',
            'websocket_auth_handler.py'
        ]
        
        missing_ws_files = []
        for file_name in websocket_files:
            if not (self.project_root / file_name).exists():
                missing_ws_files.append(file_name)
        
        if missing_ws_files:
            safety_results['unsafe'].append(SafetyCheck(
                check_name='websocket_framework_missing',
                file_path='system',
                pattern=None,
                status='unsafe',
                reason=f'WebSocket framework components missing: {", ".join(missing_ws_files)}',
                recommendations=[
                    'Implement WebSocket framework before migration',
                    'Ensure CORS standardization is complete',
                    'Test WebSocket connections'
                ],
                impact_level='high'
            ))
    
    def _get_context_lines(self, lines: List[str], line_number: int, context_size: int) -> List[str]:
        """Get context lines around a specific line number"""
        start = max(0, line_number - context_size - 1)
        end = min(len(lines), line_number + context_size)
        return lines[start:end]
    
    def _is_in_critical_section(self, context: str) -> bool:
        """Check if pattern is in critical code section"""
        for pattern in self.critical_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        return False
    
    def _is_safe_pattern(self, code_snippet: str) -> bool:
        """Check if pattern is safe to remove"""
        for pattern in self.safe_patterns:
            if re.search(pattern, code_snippet, re.IGNORECASE):
                return True
        return False
    
    def _check_pattern_dependencies(self, pattern: LegacyNotificationPattern, file_content: str) -> Optional[SafetyCheck]:
        """Check for dependencies that might be affected by pattern removal"""
        
        # Check for imports that might be affected
        if pattern.pattern_type == 'flask_flash':
            if 'from flask import' in file_content and 'flash' in file_content:
                # Count flash usage
                flash_count = len(re.findall(r'flash\s*\(', file_content))
                
                if flash_count == 1:
                    return SafetyCheck(
                        check_name='import_cleanup',
                        file_path=pattern.file_path,
                        pattern=pattern,
                        status='warning',
                        reason='Last flash usage in file - import can be removed',
                        recommendations=[
                            'Remove flash import after removing this pattern',
                            'Update other imports if necessary'
                        ],
                        impact_level='low'
                    )
        
        return None
    
    def _check_template_usage(self, pattern: LegacyNotificationPattern) -> Optional[SafetyCheck]:
        """Check if pattern affects template rendering"""
        
        if pattern.pattern_type == 'flask_flash':
            # Look for corresponding template files
            template_dirs = ['templates', 'admin/templates']
            
            for template_dir in template_dirs:
                template_path = self.project_root / template_dir
                if template_path.exists():
                    for template_file in template_path.rglob('*.html'):
                        try:
                            with open(template_file, 'r', encoding='utf-8') as f:
                                template_content = f.read()
                            
                            if 'get_flashed_messages' in template_content:
                                return SafetyCheck(
                                    check_name='template_dependency',
                                    file_path=pattern.file_path,
                                    pattern=pattern,
                                    status='warning',
                                    reason=f'Template {template_file} uses get_flashed_messages',
                                    recommendations=[
                                        'Update template to use unified notification system',
                                        'Test template rendering after changes'
                                    ],
                                    impact_level='medium'
                                )
                        except Exception:
                            continue
        
        return None
    
    def _check_javascript_integration(self, pattern: LegacyNotificationPattern) -> Optional[SafetyCheck]:
        """Check if pattern has JavaScript integration"""
        
        if pattern.pattern_type in ['js_notification', 'ajax_polling']:
            # Check if this is part of a larger JavaScript system
            try:
                with open(pattern.file_path, 'r', encoding='utf-8') as f:
                    js_content = f.read()
                
                # Look for complex integrations
                complex_patterns = [
                    r'class\s+\w*[Nn]otification',
                    r'function\s+\w*[Nn]otification',
                    r'\.prototype\.',
                    r'addEventListener',
                    r'jQuery|$\(',
                ]
                
                for complex_pattern in complex_patterns:
                    if re.search(complex_pattern, js_content):
                        return SafetyCheck(
                            check_name='complex_js_integration',
                            file_path=pattern.file_path,
                            pattern=pattern,
                            status='warning',
                            reason='Pattern is part of complex JavaScript system',
                            recommendations=[
                                'Review entire JavaScript file for dependencies',
                                'Test all JavaScript functionality after changes',
                                'Consider gradual replacement approach'
                            ],
                            impact_level='medium'
                        )
            
            except Exception:
                pass
        
        return None
    
    def _is_critical_system_file(self, file_path: str) -> bool:
        """Check if file is critical to system operation"""
        critical_files = [
            'main.py',
            'web_app.py',
            'config.py',
            'database.py',
            'models.py',
            '__init__.py'
        ]
        
        file_name = Path(file_path).name
        return file_name in critical_files
    
    def _assess_file_complexity(self, file_path: str) -> Optional[SafetyCheck]:
        """Assess file complexity and migration risk"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            # Simple complexity metrics
            line_count = len(non_empty_lines)
            function_count = len(re.findall(r'def\s+\w+\s*\(', content))
            class_count = len(re.findall(r'class\s+\w+', content))
            
            complexity_score = line_count + (function_count * 10) + (class_count * 20)
            
            if complexity_score > 1000:
                return SafetyCheck(
                    check_name='high_complexity_file',
                    file_path=file_path,
                    pattern=None,
                    status='warning',
                    reason=f'High complexity file (score: {complexity_score})',
                    recommendations=[
                        'Extra testing required for this file',
                        'Consider breaking changes into smaller steps',
                        'Review all functionality after changes'
                    ],
                    impact_level='medium'
                )
        
        except Exception:
            pass
        
        return None
    
    def generate_safety_report(self, output_path: str) -> None:
        """Generate comprehensive safety report"""
        
        safety_results = self.validate_all_patterns()
        
        report = {
            'validation_metadata': {
                'project_root': str(self.project_root),
                'validation_timestamp': self._get_timestamp(),
                'total_checks': len(self.safety_checks),
                'safety_distribution': {
                    level: len(checks) for level, checks in safety_results.items()
                }
            },
            'safety_checks': [asdict(check) for check in self.safety_checks],
            'safety_summary': self._generate_safety_summary(safety_results),
            'migration_readiness': self._assess_migration_readiness(safety_results),
            'recommendations': self._generate_safety_recommendations(safety_results)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logging.info(f"Safety report exported to {output_path}")
    
    def _generate_safety_summary(self, safety_results: Dict[str, List[SafetyCheck]]) -> Dict[str, Any]:
        """Generate safety summary"""
        return {
            'total_patterns_analyzed': sum(
                1 for check in self.safety_checks if check.pattern is not None
            ),
            'safe_patterns': len(safety_results['safe']),
            'warning_patterns': len(safety_results['warning']),
            'unsafe_patterns': len(safety_results['unsafe']),
            'critical_issues': len(safety_results['critical']),
            'files_affected': len(set(check.file_path for check in self.safety_checks)),
            'high_impact_checks': len([
                check for check in self.safety_checks 
                if check.impact_level in ['high', 'critical']
            ])
        }
    
    def _assess_migration_readiness(self, safety_results: Dict[str, List[SafetyCheck]]) -> Dict[str, Any]:
        """Assess overall migration readiness"""
        critical_count = len(safety_results['critical'])
        unsafe_count = len(safety_results['unsafe'])
        warning_count = len(safety_results['warning'])
        
        if critical_count > 0:
            readiness = 'not_ready'
            reason = f'{critical_count} critical issues must be resolved first'
        elif unsafe_count > 5:
            readiness = 'caution_required'
            reason = f'{unsafe_count} unsafe patterns require careful review'
        elif warning_count > 20:
            readiness = 'proceed_with_caution'
            reason = f'{warning_count} warnings require attention'
        else:
            readiness = 'ready'
            reason = 'No major safety concerns detected'
        
        return {
            'status': readiness,
            'reason': reason,
            'critical_blockers': critical_count,
            'unsafe_patterns': unsafe_count,
            'warnings': warning_count
        }
    
    def _generate_safety_recommendations(self, safety_results: Dict[str, List[SafetyCheck]]) -> List[str]:
        """Generate safety recommendations"""
        recommendations = []
        
        if safety_results['critical']:
            recommendations.append("🚨 CRITICAL: Resolve all critical issues before proceeding with migration")
            recommendations.append("Implement missing unified notification system components")
        
        if safety_results['unsafe']:
            recommendations.append("⚠️  Review all unsafe patterns manually before removal")
            recommendations.append("Create comprehensive test cases for unsafe pattern areas")
        
        if len(safety_results['warning']) > 10:
            recommendations.append("📋 High number of warnings - consider phased migration approach")
        
        recommendations.extend([
            "✅ Test each file thoroughly after pattern removal",
            "💾 Maintain backups throughout migration process",
            "🔄 Use rollback procedures if issues are discovered",
            "📊 Monitor system behavior after each migration phase"
        ])
        
        return recommendations
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Validate safety of legacy notification system migration"
    )
    
    parser.add_argument(
        '--project-root',
        default='.',
        help='Root directory of the project to validate'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='migration_safety_report.json',
        help='Output file for safety report'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    try:
        validator = MigrationSafetyValidator(args.project_root)
        
        print("🔍 Validating migration safety...")
        safety_results = validator.validate_all_patterns()
        
        # Print summary
        print(f"\n📊 SAFETY VALIDATION RESULTS:")
        print(f"   ✅ Safe patterns: {len(safety_results['safe'])}")
        print(f"   ⚠️  Warning patterns: {len(safety_results['warning'])}")
        print(f"   ❌ Unsafe patterns: {len(safety_results['unsafe'])}")
        print(f"   🚨 Critical issues: {len(safety_results['critical'])}")
        
        # Generate report
        validator.generate_safety_report(args.output)
        print(f"\n📄 Detailed safety report saved to: {args.output}")
        
        # Exit with appropriate code
        if safety_results['critical']:
            print("\n🚨 CRITICAL ISSUES FOUND - Migration not recommended")
            sys.exit(2)
        elif safety_results['unsafe']:
            print("\n⚠️  UNSAFE PATTERNS FOUND - Proceed with extreme caution")
            sys.exit(1)
        else:
            print("\n✅ Migration appears safe to proceed")
            sys.exit(0)
    
    except Exception as e:
        logging.error(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()