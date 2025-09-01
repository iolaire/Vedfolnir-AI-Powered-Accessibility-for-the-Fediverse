# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Migration Utilities

This module provides utilities for converting legacy notifications to standardized format,
including Flask flash message conversion, legacy notification system migration,
and validation tools for ensuring migration success.
"""

import logging
import re
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from unified_notification_manager import NotificationMessage, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)


class LegacyNotificationType(Enum):
    """Types of legacy notification systems"""
    FLASK_FLASH = "flask_flash"
    CUSTOM_NOTIFICATION = "custom_notification"
    AJAX_POLLING = "ajax_polling"
    JAVASCRIPT_ALERT = "javascript_alert"
    TEMPLATE_MESSAGE = "template_message"


@dataclass
class LegacyNotificationPattern:
    """Pattern for identifying legacy notifications"""
    pattern_type: LegacyNotificationType
    regex_pattern: str
    file_extensions: List[str]
    description: str
    replacement_template: Optional[str] = None
    migration_notes: Optional[str] = None


@dataclass
class MigrationItem:
    """Item to be migrated from legacy to standardized format"""
    file_path: str
    line_number: int
    legacy_type: LegacyNotificationType
    original_code: str
    suggested_replacement: str
    migration_priority: str  # 'high', 'medium', 'low'
    requires_manual_review: bool
    dependencies: List[str]
    notes: str


@dataclass
class ConversionResult:
    """Result of converting legacy notification to standardized format"""
    success: bool
    original_notification: Dict[str, Any]
    converted_notification: Optional[NotificationMessage]
    conversion_notes: List[str]
    warnings: List[str]
    errors: List[str]


class NotificationMigrationUtilities:
    """
    Utilities for converting legacy notifications to standardized format
    
    Provides pattern recognition, code conversion, validation tools,
    and migration planning for legacy notification systems.
    """
    
    def __init__(self, project_root: str):
        """
        Initialize migration utilities
        
        Args:
            project_root: Root directory of the project to migrate
        """
        self.project_root = Path(project_root)
        self.logger = logging.getLogger(__name__)
        
        # Legacy notification patterns
        self._legacy_patterns = self._initialize_legacy_patterns()
        
        # Migration statistics
        self._migration_stats = {
            'files_scanned': 0,
            'patterns_found': 0,
            'items_migrated': 0,
            'errors_encountered': 0,
            'warnings_generated': 0
        }
        
        # Conversion mappings
        self._flash_category_mapping = {
            'success': NotificationType.SUCCESS,
            'info': NotificationType.INFO,
            'warning': NotificationType.WARNING,
            'error': NotificationType.ERROR,
            'danger': NotificationType.ERROR,
            'message': NotificationType.INFO
        }
        
        self._priority_mapping = {
            'success': NotificationPriority.NORMAL,
            'info': NotificationPriority.LOW,
            'warning': NotificationPriority.HIGH,
            'error': NotificationPriority.CRITICAL,
            'danger': NotificationPriority.CRITICAL
        }
    
    def scan_for_legacy_notifications(self, exclude_dirs: Optional[List[str]] = None) -> List[MigrationItem]:
        """
        Scan project for legacy notification patterns
        
        Args:
            exclude_dirs: Directories to exclude from scanning
            
        Returns:
            List of migration items found
        """
        try:
            if exclude_dirs is None:
                exclude_dirs = ['.git', '__pycache__', 'node_modules', '.pytest_cache', 'venv', '.env']
            
            migration_items = []
            
            self.logger.info(f"Starting legacy notification scan in {self.project_root}")
            
            for pattern_info in self._legacy_patterns:
                items = self._scan_pattern(pattern_info, exclude_dirs)
                migration_items.extend(items)
                self.logger.debug(f"Found {len(items)} items for pattern {pattern_info.pattern_type.value}")
            
            # Sort by priority and file path
            migration_items.sort(key=lambda x: (x.migration_priority, x.file_path, x.line_number))
            
            self._migration_stats['files_scanned'] = len(set(item.file_path for item in migration_items))
            self._migration_stats['patterns_found'] = len(migration_items)
            
            self.logger.info(f"Legacy notification scan complete: {len(migration_items)} items found")
            
            return migration_items
            
        except Exception as e:
            self.logger.error(f"Error scanning for legacy notifications: {e}")
            self._migration_stats['errors_encountered'] += 1
            raise RuntimeError(f"Legacy notification scan failed: {e}")
    
    def convert_flask_flash_to_notification(self, flash_call: str, context: Dict[str, Any] = None) -> ConversionResult:
        """
        Convert Flask flash message to standardized notification
        
        Args:
            flash_call: Flask flash() call code
            context: Additional context for conversion
            
        Returns:
            ConversionResult with conversion details
        """
        try:
            conversion_notes = []
            warnings = []
            errors = []
            
            # Parse flash call
            flash_match = re.search(r'flash\s*\(\s*["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']*)["\'])?\s*\)', flash_call)
            
            if not flash_match:
                errors.append("Could not parse flash() call")
                return ConversionResult(
                    success=False,
                    original_notification={'code': flash_call},
                    converted_notification=None,
                    conversion_notes=conversion_notes,
                    warnings=warnings,
                    errors=errors
                )
            
            message = flash_match.group(1)
            category = flash_match.group(2) or 'message'
            
            # Convert to standardized notification
            notification_type = self._flash_category_mapping.get(category.lower(), NotificationType.INFO)
            priority = self._priority_mapping.get(category.lower(), NotificationPriority.NORMAL)
            
            # Generate notification ID
            notification_id = f"migrated_{hash(flash_call)}_{int(datetime.now().timestamp())}"
            
            # Create standardized notification
            notification = NotificationMessage(
                id=notification_id,
                type=notification_type,
                title=self._generate_title_from_message(message),
                message=message,
                user_id=None,  # Will be set at runtime
                priority=priority,
                category='system',  # Default category for migrated notifications
                data={'migrated_from': 'flask_flash', 'original_category': category},
                timestamp=datetime.now(timezone.utc),
                expires_at=None,
                requires_action=False,
                action_url=None,
                action_text=None,
                delivered=False,
                read=False
            )
            
            conversion_notes.append(f"Converted Flask flash message with category '{category}' to {notification_type.value}")
            
            if category.lower() not in self._flash_category_mapping:
                warnings.append(f"Unknown flash category '{category}', defaulted to INFO")
            
            return ConversionResult(
                success=True,
                original_notification={'message': message, 'category': category, 'code': flash_call},
                converted_notification=notification,
                conversion_notes=conversion_notes,
                warnings=warnings,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"Error converting Flask flash to notification: {e}")
            return ConversionResult(
                success=False,
                original_notification={'code': flash_call},
                converted_notification=None,
                conversion_notes=[],
                warnings=[],
                errors=[f"Conversion error: {str(e)}"]
            )
    
    def convert_custom_notification_to_standard(self, notification_data: Dict[str, Any]) -> ConversionResult:
        """
        Convert custom notification format to standardized notification
        
        Args:
            notification_data: Custom notification data
            
        Returns:
            ConversionResult with conversion details
        """
        try:
            conversion_notes = []
            warnings = []
            errors = []
            
            # Extract common fields
            message = notification_data.get('message', notification_data.get('text', ''))
            if not message:
                errors.append("No message content found in notification data")
                return ConversionResult(
                    success=False,
                    original_notification=notification_data,
                    converted_notification=None,
                    conversion_notes=conversion_notes,
                    warnings=warnings,
                    errors=errors
                )
            
            # Map notification type
            original_type = notification_data.get('type', notification_data.get('level', 'info')).lower()
            notification_type = self._map_custom_type_to_standard(original_type)
            
            # Map priority
            priority = self._map_custom_priority_to_standard(
                notification_data.get('priority', notification_data.get('importance', 'normal'))
            )
            
            # Generate notification ID
            notification_id = f"migrated_custom_{hash(str(notification_data))}_{int(datetime.now().timestamp())}"
            
            # Create standardized notification
            notification = NotificationMessage(
                id=notification_id,
                type=notification_type,
                title=notification_data.get('title', self._generate_title_from_message(message)),
                message=message,
                user_id=notification_data.get('user_id'),
                priority=priority,
                category=notification_data.get('category', 'system'),
                data={
                    'migrated_from': 'custom_notification',
                    'original_data': notification_data
                },
                timestamp=datetime.now(timezone.utc),
                expires_at=self._parse_expiration(notification_data.get('expires_at')),
                requires_action=notification_data.get('requires_action', False),
                action_url=notification_data.get('action_url'),
                action_text=notification_data.get('action_text'),
                delivered=False,
                read=False
            )
            
            conversion_notes.append(f"Converted custom notification type '{original_type}' to {notification_type.value}")
            
            return ConversionResult(
                success=True,
                original_notification=notification_data,
                converted_notification=notification,
                conversion_notes=conversion_notes,
                warnings=warnings,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"Error converting custom notification: {e}")
            return ConversionResult(
                success=False,
                original_notification=notification_data,
                converted_notification=None,
                conversion_notes=[],
                warnings=[],
                errors=[f"Conversion error: {str(e)}"]
            )
    
    def generate_migration_plan(self, migration_items: List[MigrationItem]) -> Dict[str, Any]:
        """
        Generate comprehensive migration plan
        
        Args:
            migration_items: List of items to migrate
            
        Returns:
            Migration plan with phases, dependencies, and rollback procedures
        """
        try:
            # Group items by file and type
            files_by_type = {}
            dependencies = set()
            
            for item in migration_items:
                if item.legacy_type not in files_by_type:
                    files_by_type[item.legacy_type] = []
                files_by_type[item.legacy_type].append(item)
                dependencies.update(item.dependencies)
            
            # Create migration phases
            phases = []
            
            # Phase 1: Flask flash messages (lowest risk)
            if LegacyNotificationType.FLASK_FLASH in files_by_type:
                phases.append({
                    'phase': 1,
                    'name': 'Flask Flash Message Migration',
                    'description': 'Convert Flask flash() calls to unified notification system',
                    'items': files_by_type[LegacyNotificationType.FLASK_FLASH],
                    'risk_level': 'low',
                    'estimated_duration': '2-4 hours',
                    'rollback_complexity': 'simple'
                })
            
            # Phase 2: Template messages
            if LegacyNotificationType.TEMPLATE_MESSAGE in files_by_type:
                phases.append({
                    'phase': 2,
                    'name': 'Template Message Migration',
                    'description': 'Update template notification displays',
                    'items': files_by_type[LegacyNotificationType.TEMPLATE_MESSAGE],
                    'risk_level': 'medium',
                    'estimated_duration': '4-6 hours',
                    'rollback_complexity': 'moderate'
                })
            
            # Phase 3: JavaScript notifications
            if LegacyNotificationType.JAVASCRIPT_ALERT in files_by_type:
                phases.append({
                    'phase': 3,
                    'name': 'JavaScript Notification Migration',
                    'description': 'Replace JavaScript alerts with unified system',
                    'items': files_by_type[LegacyNotificationType.JAVASCRIPT_ALERT],
                    'risk_level': 'medium',
                    'estimated_duration': '3-5 hours',
                    'rollback_complexity': 'moderate'
                })
            
            # Phase 4: Custom notification systems
            if LegacyNotificationType.CUSTOM_NOTIFICATION in files_by_type:
                phases.append({
                    'phase': 4,
                    'name': 'Custom Notification System Migration',
                    'description': 'Migrate custom notification implementations',
                    'items': files_by_type[LegacyNotificationType.CUSTOM_NOTIFICATION],
                    'risk_level': 'high',
                    'estimated_duration': '6-8 hours',
                    'rollback_complexity': 'complex'
                })
            
            # Phase 5: AJAX polling systems
            if LegacyNotificationType.AJAX_POLLING in files_by_type:
                phases.append({
                    'phase': 5,
                    'name': 'AJAX Polling System Migration',
                    'description': 'Replace AJAX polling with WebSocket notifications',
                    'items': files_by_type[LegacyNotificationType.AJAX_POLLING],
                    'risk_level': 'high',
                    'estimated_duration': '8-12 hours',
                    'rollback_complexity': 'complex'
                })
            
            # Calculate totals
            total_items = len(migration_items)
            high_priority_items = len([item for item in migration_items if item.migration_priority == 'high'])
            manual_review_items = len([item for item in migration_items if item.requires_manual_review])
            
            migration_plan = {
                'plan_generated_at': datetime.now(timezone.utc).isoformat(),
                'project_root': str(self.project_root),
                'total_items': total_items,
                'high_priority_items': high_priority_items,
                'manual_review_items': manual_review_items,
                'phases': phases,
                'dependencies': list(dependencies),
                'estimated_total_duration': self._calculate_total_duration(phases),
                'rollback_procedures': self._generate_rollback_procedures(phases),
                'validation_checklist': self._generate_validation_checklist(),
                'risk_assessment': self._assess_migration_risks(migration_items)
            }
            
            self.logger.info(f"Generated migration plan with {len(phases)} phases for {total_items} items")
            
            return migration_plan
            
        except Exception as e:
            self.logger.error(f"Error generating migration plan: {e}")
            raise RuntimeError(f"Migration plan generation failed: {e}")
    
    def validate_migration_success(self, migration_plan: Dict[str, Any], 
                                 completed_phases: List[int]) -> Dict[str, Any]:
        """
        Validate migration success and completeness
        
        Args:
            migration_plan: Original migration plan
            completed_phases: List of completed phase numbers
            
        Returns:
            Validation results with success status and recommendations
        """
        try:
            validation_results = {
                'validation_timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_success': True,
                'completed_phases': completed_phases,
                'validation_checks': [],
                'remaining_items': [],
                'recommendations': [],
                'next_steps': []
            }
            
            # Check phase completion
            total_phases = len(migration_plan['phases'])
            completed_count = len(completed_phases)
            
            validation_results['validation_checks'].append({
                'check': 'Phase Completion',
                'status': 'pass' if completed_count == total_phases else 'partial',
                'details': f"{completed_count}/{total_phases} phases completed"
            })
            
            # Scan for remaining legacy patterns
            remaining_items = self.scan_for_legacy_notifications()
            validation_results['remaining_items'] = [asdict(item) for item in remaining_items]
            
            if remaining_items:
                validation_results['overall_success'] = False
                validation_results['validation_checks'].append({
                    'check': 'Legacy Pattern Removal',
                    'status': 'fail',
                    'details': f"{len(remaining_items)} legacy patterns still found"
                })
                validation_results['recommendations'].append(
                    "Complete migration of remaining legacy notification patterns"
                )
            else:
                validation_results['validation_checks'].append({
                    'check': 'Legacy Pattern Removal',
                    'status': 'pass',
                    'details': "No legacy notification patterns found"
                })
            
            # Check for orphaned imports
            orphaned_imports = self._check_orphaned_imports()
            if orphaned_imports:
                validation_results['validation_checks'].append({
                    'check': 'Orphaned Imports',
                    'status': 'warning',
                    'details': f"{len(orphaned_imports)} orphaned imports found"
                })
                validation_results['recommendations'].append(
                    "Remove orphaned imports from legacy notification systems"
                )
            else:
                validation_results['validation_checks'].append({
                    'check': 'Orphaned Imports',
                    'status': 'pass',
                    'details': "No orphaned imports found"
                })
            
            # Generate next steps
            if not validation_results['overall_success']:
                validation_results['next_steps'].extend([
                    "Review and complete remaining migration items",
                    "Test notification functionality on all migrated pages",
                    "Update documentation to reflect changes"
                ])
            else:
                validation_results['next_steps'].extend([
                    "Perform comprehensive testing of notification system",
                    "Update user documentation",
                    "Monitor system for any issues",
                    "Clean up migration artifacts"
                ])
            
            self.logger.info(f"Migration validation complete: {'SUCCESS' if validation_results['overall_success'] else 'INCOMPLETE'}")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating migration success: {e}")
            return {
                'validation_timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_success': False,
                'error': str(e),
                'validation_checks': [],
                'remaining_items': [],
                'recommendations': ['Fix validation errors and retry'],
                'next_steps': ['Investigate validation failure']
            }
    
    def _initialize_legacy_patterns(self) -> List[LegacyNotificationPattern]:
        """
        Initialize patterns for detecting legacy notifications
        
        Returns:
            List of legacy notification patterns
        """
        return [
            LegacyNotificationPattern(
                pattern_type=LegacyNotificationType.FLASK_FLASH,
                regex_pattern=r'flash\s*\(\s*["\'][^"\']+["\'](?:\s*,\s*["\'][^"\']*["\'])?\s*\)',
                file_extensions=['.py'],
                description='Flask flash() message calls',
                replacement_template='unified_notification_manager.send_user_notification(...)',
                migration_notes='Convert to unified notification system with appropriate type mapping'
            ),
            LegacyNotificationPattern(
                pattern_type=LegacyNotificationType.TEMPLATE_MESSAGE,
                regex_pattern=r'\{\{\s*get_flashed_messages\(\)|with\s+messages\s*=\s*get_flashed_messages\(\)',
                file_extensions=['.html', '.jinja2'],
                description='Template flash message rendering',
                replacement_template='Unified notification UI components',
                migration_notes='Replace with NotificationUIRenderer components'
            ),
            LegacyNotificationPattern(
                pattern_type=LegacyNotificationType.JAVASCRIPT_ALERT,
                regex_pattern=r'alert\s*\(\s*["\'][^"\']+["\']\s*\)|window\.alert\s*\(',
                file_extensions=['.js', '.html'],
                description='JavaScript alert() calls',
                replacement_template='NotificationUIRenderer.renderNotification(...)',
                migration_notes='Replace with unified notification UI system'
            ),
            LegacyNotificationPattern(
                pattern_type=LegacyNotificationType.CUSTOM_NOTIFICATION,
                regex_pattern=r'showNotification\s*\(|displayMessage\s*\(|notify\s*\(',
                file_extensions=['.js', '.py'],
                description='Custom notification function calls',
                replacement_template='Unified notification system calls',
                migration_notes='Analyze custom implementation and map to standardized system'
            ),
            LegacyNotificationPattern(
                pattern_type=LegacyNotificationType.AJAX_POLLING,
                regex_pattern=r'setInterval\s*\([^}]*ajax|setTimeout\s*\([^}]*ajax.*notification',
                file_extensions=['.js'],
                description='AJAX polling for notifications',
                replacement_template='WebSocket notification subscription',
                migration_notes='Replace with real-time WebSocket notifications'
            )
        ]
    
    def _scan_pattern(self, pattern_info: LegacyNotificationPattern, 
                     exclude_dirs: List[str]) -> List[MigrationItem]:
        """
        Scan for a specific legacy notification pattern
        
        Args:
            pattern_info: Pattern information to scan for
            exclude_dirs: Directories to exclude
            
        Returns:
            List of migration items found for this pattern
        """
        migration_items = []
        
        try:
            for file_path in self.project_root.rglob('*'):
                # Skip directories and excluded paths
                if file_path.is_dir() or any(excluded in str(file_path) for excluded in exclude_dirs):
                    continue
                
                # Check file extension
                if file_path.suffix not in pattern_info.file_extensions:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Find pattern matches
                    matches = re.finditer(pattern_info.regex_pattern, content, re.MULTILINE | re.IGNORECASE)
                    
                    for match in matches:
                        # Calculate line number
                        line_number = content[:match.start()].count('\n') + 1
                        
                        # Extract surrounding context
                        lines = content.split('\n')
                        start_line = max(0, line_number - 2)
                        end_line = min(len(lines), line_number + 2)
                        context_lines = lines[start_line:end_line]
                        
                        # Create migration item
                        migration_item = MigrationItem(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_number,
                            legacy_type=pattern_info.pattern_type,
                            original_code=match.group(0),
                            suggested_replacement=pattern_info.replacement_template or '',
                            migration_priority=self._assess_item_priority(pattern_info, file_path),
                            requires_manual_review=self._requires_manual_review(pattern_info, match.group(0)),
                            dependencies=self._extract_dependencies(file_path, content),
                            notes=f"{pattern_info.description} - {pattern_info.migration_notes or ''}"
                        )
                        
                        migration_items.append(migration_item)
                
                except Exception as e:
                    self.logger.warning(f"Error scanning file {file_path}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error scanning pattern {pattern_info.pattern_type.value}: {e}")
        
        return migration_items
    
    def _assess_item_priority(self, pattern_info: LegacyNotificationPattern, file_path: Path) -> str:
        """
        Assess migration priority for an item
        
        Args:
            pattern_info: Pattern information
            file_path: File containing the pattern
            
        Returns:
            Priority level: 'high', 'medium', or 'low'
        """
        # High priority for admin and critical functionality
        if any(keyword in str(file_path).lower() for keyword in ['admin', 'security', 'auth', 'login']):
            return 'high'
        
        # High priority for Flask flash messages (easy to migrate)
        if pattern_info.pattern_type == LegacyNotificationType.FLASK_FLASH:
            return 'high'
        
        # Medium priority for templates and JavaScript
        if pattern_info.pattern_type in [LegacyNotificationType.TEMPLATE_MESSAGE, 
                                       LegacyNotificationType.JAVASCRIPT_ALERT]:
            return 'medium'
        
        # Lower priority for complex custom systems
        return 'low'
    
    def _requires_manual_review(self, pattern_info: LegacyNotificationPattern, code: str) -> bool:
        """
        Determine if migration item requires manual review
        
        Args:
            pattern_info: Pattern information
            code: Code snippet containing the pattern
            
        Returns:
            True if manual review is required
        """
        # Complex patterns require manual review
        if pattern_info.pattern_type in [LegacyNotificationType.CUSTOM_NOTIFICATION, 
                                       LegacyNotificationType.AJAX_POLLING]:
            return True
        
        # Complex JavaScript requires review
        if 'function' in code.lower() or 'callback' in code.lower():
            return True
        
        # Multi-line patterns require review
        if '\n' in code:
            return True
        
        return False
    
    def _extract_dependencies(self, file_path: Path, content: str) -> List[str]:
        """
        Extract dependencies from file content
        
        Args:
            file_path: File path
            content: File content
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        # Python imports
        if file_path.suffix == '.py':
            import_matches = re.findall(r'from\s+([^\s]+)\s+import|import\s+([^\s,]+)', content)
            for match in import_matches:
                module = match[0] or match[1]
                if module and 'flask' in module.lower():
                    dependencies.append(module)
        
        # JavaScript dependencies
        elif file_path.suffix == '.js':
            # Look for jQuery, AJAX, etc.
            if 'jquery' in content.lower() or '$' in content:
                dependencies.append('jquery')
            if 'ajax' in content.lower():
                dependencies.append('ajax')
        
        return dependencies
    
    def _map_custom_type_to_standard(self, custom_type: str) -> NotificationType:
        """
        Map custom notification type to standard type
        
        Args:
            custom_type: Custom type string
            
        Returns:
            Standard NotificationType
        """
        type_mapping = {
            'success': NotificationType.SUCCESS,
            'error': NotificationType.ERROR,
            'warning': NotificationType.WARNING,
            'info': NotificationType.INFO,
            'information': NotificationType.INFO,
            'alert': NotificationType.WARNING,
            'danger': NotificationType.ERROR,
            'notice': NotificationType.INFO,
            'message': NotificationType.INFO
        }
        
        return type_mapping.get(custom_type.lower(), NotificationType.INFO)
    
    def _map_custom_priority_to_standard(self, custom_priority: str) -> NotificationPriority:
        """
        Map custom priority to standard priority
        
        Args:
            custom_priority: Custom priority string
            
        Returns:
            Standard NotificationPriority
        """
        priority_mapping = {
            'low': NotificationPriority.LOW,
            'normal': NotificationPriority.NORMAL,
            'medium': NotificationPriority.NORMAL,
            'high': NotificationPriority.HIGH,
            'critical': NotificationPriority.CRITICAL,
            'urgent': NotificationPriority.CRITICAL
        }
        
        return priority_mapping.get(str(custom_priority).lower(), NotificationPriority.NORMAL)
    
    def _generate_title_from_message(self, message: str) -> str:
        """
        Generate notification title from message content
        
        Args:
            message: Notification message
            
        Returns:
            Generated title
        """
        # Take first sentence or first 50 characters
        sentences = message.split('.')
        if len(sentences) > 1 and len(sentences[0]) < 50:
            return sentences[0].strip()
        
        if len(message) <= 50:
            return message
        
        return message[:47] + '...'
    
    def _parse_expiration(self, expiration_str: Any) -> Optional[datetime]:
        """
        Parse expiration string to datetime
        
        Args:
            expiration_str: Expiration string or datetime
            
        Returns:
            Parsed datetime or None
        """
        if not expiration_str:
            return None
        
        if isinstance(expiration_str, datetime):
            return expiration_str
        
        try:
            return datetime.fromisoformat(str(expiration_str))
        except:
            return None
    
    def _calculate_total_duration(self, phases: List[Dict[str, Any]]) -> str:
        """
        Calculate total estimated duration for all phases
        
        Args:
            phases: List of migration phases
            
        Returns:
            Total duration estimate
        """
        total_hours = 0
        
        for phase in phases:
            duration_str = phase.get('estimated_duration', '0-0 hours')
            # Extract max hours from range like "2-4 hours"
            hours_match = re.search(r'(\d+)-(\d+)\s*hours?', duration_str)
            if hours_match:
                max_hours = int(hours_match.group(2))
                total_hours += max_hours
        
        if total_hours < 8:
            return f"{total_hours} hours"
        elif total_hours < 40:
            days = total_hours / 8
            return f"{days:.1f} days"
        else:
            weeks = total_hours / 40
            return f"{weeks:.1f} weeks"
    
    def _generate_rollback_procedures(self, phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate rollback procedures for migration phases
        
        Args:
            phases: List of migration phases
            
        Returns:
            Rollback procedures
        """
        return {
            'backup_required': True,
            'backup_locations': [
                'Git commit before migration',
                'File system backup of modified files',
                'Database backup if applicable'
            ],
            'rollback_steps': [
                'Stop application services',
                'Restore backed up files',
                'Revert database changes if applicable',
                'Restart application services',
                'Verify functionality'
            ],
            'validation_after_rollback': [
                'Check application starts successfully',
                'Verify legacy notification functionality',
                'Test critical user workflows',
                'Monitor error logs'
            ]
        }
    
    def _generate_validation_checklist(self) -> List[Dict[str, str]]:
        """
        Generate validation checklist for migration
        
        Returns:
            List of validation items
        """
        return [
            {
                'item': 'No legacy notification patterns remain',
                'description': 'Scan codebase to ensure all legacy patterns are removed',
                'validation_method': 'Automated pattern scanning'
            },
            {
                'item': 'Unified notification system functional',
                'description': 'Test notification delivery and display',
                'validation_method': 'Manual testing and automated tests'
            },
            {
                'item': 'WebSocket connections established',
                'description': 'Verify WebSocket connections work on all pages',
                'validation_method': 'Browser testing and monitoring'
            },
            {
                'item': 'No JavaScript console errors',
                'description': 'Check for JavaScript errors related to notifications',
                'validation_method': 'Browser console monitoring'
            },
            {
                'item': 'Notification styling consistent',
                'description': 'Verify consistent notification appearance',
                'validation_method': 'Visual testing across pages'
            },
            {
                'item': 'Admin notifications secure',
                'description': 'Ensure admin notifications only reach authorized users',
                'validation_method': 'Security testing with different user roles'
            }
        ]
    
    def _assess_migration_risks(self, migration_items: List[MigrationItem]) -> Dict[str, Any]:
        """
        Assess risks associated with migration
        
        Args:
            migration_items: List of items to migrate
            
        Returns:
            Risk assessment
        """
        high_risk_count = len([item for item in migration_items if item.migration_priority == 'high'])
        manual_review_count = len([item for item in migration_items if item.requires_manual_review])
        
        # Count files affected
        affected_files = set(item.file_path for item in migration_items)
        admin_files = len([f for f in affected_files if 'admin' in f.lower()])
        
        risk_level = 'low'
        if manual_review_count > 10 or admin_files > 5:
            risk_level = 'high'
        elif manual_review_count > 5 or admin_files > 2:
            risk_level = 'medium'
        
        return {
            'overall_risk_level': risk_level,
            'total_items': len(migration_items),
            'high_priority_items': high_risk_count,
            'manual_review_items': manual_review_count,
            'affected_files': len(affected_files),
            'admin_files_affected': admin_files,
            'risk_factors': [
                f"{manual_review_count} items require manual review",
                f"{admin_files} admin files affected",
                f"{high_risk_count} high priority items"
            ],
            'mitigation_strategies': [
                'Thorough testing in development environment',
                'Gradual rollout with rollback plan',
                'Monitor error logs during migration',
                'Have backup restoration procedure ready'
            ]
        }
    
    def _check_orphaned_imports(self) -> List[str]:
        """
        Check for orphaned imports from legacy notification systems
        
        Returns:
            List of orphaned import statements
        """
        orphaned_imports = []
        
        try:
            # Common legacy notification imports to check for
            legacy_imports = [
                'from flask import flash',
                'import flash',
                'from notifications import',
                'import notifications'
            ]
            
            for file_path in self.project_root.rglob('*.py'):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for legacy_import in legacy_imports:
                        if legacy_import in content:
                            # Check if the import is actually used
                            import_name = legacy_import.split()[-1]
                            if import_name not in content.replace(legacy_import, ''):
                                orphaned_imports.append(f"{file_path}: {legacy_import}")
                
                except Exception as e:
                    self.logger.warning(f"Error checking imports in {file_path}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error checking orphaned imports: {e}")
        
        return orphaned_imports
    
    def get_migration_statistics(self) -> Dict[str, Any]:
        """
        Get migration statistics
        
        Returns:
            Dictionary containing migration statistics
        """
        return {
            'statistics_timestamp': datetime.now(timezone.utc).isoformat(),
            'project_root': str(self.project_root),
            **self._migration_stats
        }