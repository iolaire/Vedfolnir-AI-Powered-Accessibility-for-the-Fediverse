# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Configuration Validator

Provides comprehensive validation for maintenance mode configuration parameters.
Includes client-side and server-side validation with consistency checking.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation message severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    """Validation message with severity and details"""
    severity: ValidationSeverity
    field: str
    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Comprehensive validation result"""
    is_valid: bool
    messages: List[ValidationMessage]
    warnings_count: int
    errors_count: int
    info_count: int
    validated_config: Optional[Dict[str, Any]] = None


class MaintenanceConfigurationValidator:
    """
    Comprehensive maintenance configuration validator
    
    Features:
    - Client-side and server-side validation
    - Configuration consistency checking
    - Business rule validation
    - Security validation
    - Performance impact assessment
    """
    
    # Configuration constraints
    MIN_REASON_LENGTH = 10
    MAX_REASON_LENGTH = 500
    MIN_DURATION_MINUTES = 1
    MAX_DURATION_MINUTES = 1440  # 24 hours
    WARNING_DURATION_THRESHOLD = 480  # 8 hours
    SHORT_DURATION_THRESHOLD = 5  # 5 minutes
    
    # Valid maintenance modes
    VALID_MODES = ['normal', 'emergency', 'test']
    
    # Reason validation patterns
    REASON_PATTERNS = {
        'maintenance_keywords': [
            'maintenance', 'update', 'upgrade', 'patch', 'fix', 'repair',
            'optimization', 'migration', 'backup', 'security', 'database',
            'system', 'server', 'network', 'infrastructure'
        ],
        'emergency_keywords': [
            'emergency', 'critical', 'urgent', 'security breach', 'data loss',
            'system failure', 'outage', 'vulnerability', 'attack', 'corruption'
        ],
        'test_keywords': [
            'test', 'testing', 'validation', 'verification', 'simulation',
            'drill', 'practice', 'rehearsal', 'trial'
        ]
    }
    
    def __init__(self, maintenance_service=None):
        """
        Initialize configuration validator
        
        Args:
            maintenance_service: Optional maintenance service for context validation
        """
        self.maintenance_service = maintenance_service
        
        # Validation statistics
        self._validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'warnings_generated': 0,
            'errors_generated': 0
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete maintenance configuration
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            ValidationResult with comprehensive validation details
        """
        try:
            self._validation_stats['total_validations'] += 1
            
            # Validate input type
            if not isinstance(config, dict):
                return ValidationResult(
                    is_valid=False,
                    messages=[ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        field='general',
                        message='Configuration must be a dictionary',
                        code='INVALID_INPUT_TYPE'
                    )],
                    warnings_count=0,
                    errors_count=1,
                    info_count=0
                )
            
            messages = []
            validated_config = {}
            
            # Validate individual fields
            messages.extend(self._validate_reason(config.get('reason')))
            messages.extend(self._validate_duration(config.get('duration')))
            messages.extend(self._validate_mode(config.get('mode', 'normal')))
            
            # Cross-field validation
            messages.extend(self._validate_consistency(config))
            
            # Context validation (if maintenance service available)
            if self.maintenance_service:
                messages.extend(self._validate_context(config))
            
            # Business rule validation
            messages.extend(self._validate_business_rules(config))
            
            # Security validation
            messages.extend(self._validate_security(config))
            
            # Performance impact assessment
            messages.extend(self._assess_performance_impact(config))
            
            # Count message types
            errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
            warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
            info = [m for m in messages if m.severity == ValidationSeverity.INFO]
            
            # Update statistics
            self._validation_stats['warnings_generated'] += len(warnings)
            self._validation_stats['errors_generated'] += len(errors)
            
            is_valid = len(errors) == 0
            
            if is_valid:
                self._validation_stats['successful_validations'] += 1
                validated_config = self._create_validated_config(config)
            else:
                self._validation_stats['failed_validations'] += 1
            
            return ValidationResult(
                is_valid=is_valid,
                messages=messages,
                warnings_count=len(warnings),
                errors_count=len(errors),
                info_count=len(info),
                validated_config=validated_config if is_valid else None
            )
        
        except Exception as e:
            logger.error(f"Error during configuration validation: {e}")
            return ValidationResult(
                is_valid=False,
                messages=[ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    field='general',
                    message=f'Validation error: {str(e)}',
                    code='VALIDATION_ERROR'
                )],
                warnings_count=0,
                errors_count=1,
                info_count=0
            )
    
    def _validate_reason(self, reason: Any) -> List[ValidationMessage]:
        """Validate maintenance reason"""
        messages = []
        
        # Type validation
        if reason is None:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='reason',
                message='Maintenance reason is required',
                code='REASON_REQUIRED'
            ))
            return messages
        
        if not isinstance(reason, str):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='reason',
                message='Maintenance reason must be a string',
                code='REASON_INVALID_TYPE'
            ))
            return messages
        
        reason = reason.strip()
        
        # Length validation
        if len(reason) == 0:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='reason',
                message='Maintenance reason cannot be empty',
                code='REASON_EMPTY'
            ))
            return messages
        
        if len(reason) < self.MIN_REASON_LENGTH:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='reason',
                message=f'Maintenance reason should be more descriptive (at least {self.MIN_REASON_LENGTH} characters)',
                code='REASON_TOO_SHORT',
                details={'min_length': self.MIN_REASON_LENGTH, 'current_length': len(reason)}
            ))
        
        if len(reason) > self.MAX_REASON_LENGTH:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='reason',
                message=f'Maintenance reason is too long (max {self.MAX_REASON_LENGTH} characters)',
                code='REASON_TOO_LONG',
                details={'max_length': self.MAX_REASON_LENGTH, 'current_length': len(reason)}
            ))
        
        # Content validation
        reason_lower = reason.lower()
        
        # Check for maintenance-related keywords
        has_maintenance_keywords = any(keyword in reason_lower for keyword in self.REASON_PATTERNS['maintenance_keywords'])
        if not has_maintenance_keywords:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field='reason',
                message='Consider including maintenance-related keywords for clarity',
                code='REASON_KEYWORDS_SUGGESTION',
                details={'suggested_keywords': self.REASON_PATTERNS['maintenance_keywords'][:5]}
            ))
        
        # Check for inappropriate content
        if self._contains_inappropriate_content(reason):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='reason',
                message='Maintenance reason should be professional and appropriate',
                code='REASON_INAPPROPRIATE_CONTENT'
            ))
        
        return messages
    
    def _validate_duration(self, duration: Any) -> List[ValidationMessage]:
        """Validate maintenance duration"""
        messages = []
        
        # Duration is optional
        if duration is None:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field='duration',
                message='No duration specified - consider providing an estimate for user planning',
                code='DURATION_NOT_SPECIFIED'
            ))
            return messages
        
        # Type validation and conversion
        try:
            duration = int(duration)
        except (ValueError, TypeError):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='duration',
                message='Duration must be a valid number (minutes)',
                code='DURATION_INVALID_TYPE'
            ))
            return messages
        
        # Range validation
        if duration <= 0:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='duration',
                message='Duration must be positive',
                code='DURATION_NOT_POSITIVE'
            ))
            return messages  # Return early to avoid further validation
        elif duration > self.MAX_DURATION_MINUTES:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='duration',
                message=f'Duration cannot exceed {self.MAX_DURATION_MINUTES} minutes (24 hours)',
                code='DURATION_TOO_LONG',
                details={'max_duration': self.MAX_DURATION_MINUTES, 'requested_duration': duration}
            ))
        elif duration < self.SHORT_DURATION_THRESHOLD:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='duration',
                message=f'Very short maintenance duration ({duration} minutes) - ensure this is sufficient',
                code='DURATION_VERY_SHORT',
                details={'threshold': self.SHORT_DURATION_THRESHOLD, 'duration': duration}
            ))
        elif duration > self.WARNING_DURATION_THRESHOLD:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='duration',
                message=f'Long maintenance duration ({duration} minutes) - consider user impact',
                code='DURATION_LONG',
                details={'threshold': self.WARNING_DURATION_THRESHOLD, 'duration': duration}
            ))
        
        return messages
    
    def _validate_mode(self, mode: Any) -> List[ValidationMessage]:
        """Validate maintenance mode"""
        messages = []
        
        # Type validation
        if not isinstance(mode, str):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='mode',
                message='Maintenance mode must be a string',
                code='MODE_INVALID_TYPE'
            ))
            return messages
        
        mode = mode.lower().strip()
        
        # Valid mode validation
        if mode not in self.VALID_MODES:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field='mode',
                message=f'Invalid maintenance mode. Must be one of: {", ".join(self.VALID_MODES)}',
                code='MODE_INVALID',
                details={'valid_modes': self.VALID_MODES, 'provided_mode': mode}
            ))
            return messages
        
        # Mode-specific warnings
        if mode == 'emergency':
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='mode',
                message='Emergency mode will immediately terminate all non-admin operations and invalidate user sessions',
                code='MODE_EMERGENCY_WARNING'
            ))
        elif mode == 'test':
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field='mode',
                message='Test mode will simulate maintenance without actually blocking operations',
                code='MODE_TEST_INFO'
            ))
        
        return messages
    
    def _validate_consistency(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate configuration consistency across fields"""
        messages = []
        
        reason = config.get('reason', '').lower() if config.get('reason') else ''
        duration = config.get('duration')
        mode = config.get('mode', 'normal').lower()
        
        # Convert duration to int if it's a string
        if duration is not None:
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                duration = None  # Skip duration-based consistency checks if invalid
        
        # Emergency mode consistency
        if mode == 'emergency':
            has_emergency_keywords = any(keyword in reason for keyword in self.REASON_PATTERNS['emergency_keywords'])
            if not has_emergency_keywords:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    field='consistency',
                    message='Emergency mode selected but reason does not indicate emergency - verify this is correct',
                    code='EMERGENCY_MODE_REASON_MISMATCH'
                ))
            
            if duration and duration > 120:  # 2 hours
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    field='consistency',
                    message='Emergency mode with long duration - consider if normal mode is more appropriate',
                    code='EMERGENCY_MODE_LONG_DURATION'
                ))
        
        # Test mode consistency
        if mode == 'test':
            has_test_keywords = any(keyword in reason for keyword in self.REASON_PATTERNS['test_keywords'])
            if not has_test_keywords:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.INFO,
                    field='consistency',
                    message='Test mode selected - consider including test-related keywords in reason',
                    code='TEST_MODE_REASON_SUGGESTION'
                ))
            
            if duration and duration > 60:  # 1 hour
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.INFO,
                    field='consistency',
                    message='Test mode with long duration - consider shorter duration for testing',
                    code='TEST_MODE_LONG_DURATION'
                ))
        
        return messages
    
    def _validate_context(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate configuration against current system context"""
        messages = []
        
        try:
            current_status = self.maintenance_service.get_maintenance_status()
            
            # Check if maintenance is already active
            if current_status.is_active:
                mode = config.get('mode', 'normal').lower()
                if mode != 'test':
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        field='context',
                        message='Maintenance mode is already active - this will update the current maintenance',
                        code='MAINTENANCE_ALREADY_ACTIVE',
                        details={
                            'current_mode': current_status.mode.value,
                            'current_reason': current_status.reason
                        }
                    ))
                
                # Check for mode escalation
                if current_status.mode.value == 'normal' and mode == 'emergency':
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        field='context',
                        message='Escalating from normal to emergency maintenance mode',
                        code='MAINTENANCE_MODE_ESCALATION'
                    ))
            
            # Check system load
            service_stats = self.maintenance_service.get_service_stats()
            if service_stats and 'current_status' in service_stats:
                # Add context-aware warnings based on system state
                pass
        
        except Exception as e:
            logger.warning(f"Could not validate context: {e}")
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field='context',
                message='Could not validate against current system context',
                code='CONTEXT_VALIDATION_UNAVAILABLE'
            ))
        
        return messages
    
    def _validate_business_rules(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate against business rules"""
        messages = []
        
        mode = config.get('mode', 'normal').lower()
        duration = config.get('duration')
        
        # Convert duration to int if it's a string
        if duration is not None:
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                duration = None  # Skip business rules validation if duration is invalid
        
        # Business hours consideration
        current_time = datetime.now(timezone.utc)
        is_business_hours = 9 <= current_time.hour <= 17  # Simple business hours check
        
        if mode == 'normal' and is_business_hours and duration and duration > 60:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='business_rules',
                message='Long maintenance during business hours may significantly impact users',
                code='BUSINESS_HOURS_IMPACT'
            ))
        
        # Weekend/holiday consideration (simplified)
        is_weekend = current_time.weekday() >= 5  # Saturday = 5, Sunday = 6
        if mode == 'normal' and not is_weekend:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field='business_rules',
                message='Consider scheduling maintenance during weekends for reduced user impact',
                code='WEEKEND_SCHEDULING_SUGGESTION'
            ))
        
        return messages
    
    def _validate_security(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate security aspects of configuration"""
        messages = []
        
        reason = config.get('reason', '').lower() if config.get('reason') else ''
        
        # Check for security-related maintenance
        security_keywords = ['security', 'vulnerability', 'patch', 'breach', 'attack', 'exploit']
        has_security_keywords = any(keyword in reason for keyword in security_keywords)
        
        if has_security_keywords:
            mode = config.get('mode', 'normal').lower()
            if mode != 'emergency':
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    field='security',
                    message='Security-related maintenance may require emergency mode for immediate protection',
                    code='SECURITY_MODE_SUGGESTION'
                ))
        
        # Check for sensitive information in reason
        if self._contains_sensitive_info(reason):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='security',
                message='Avoid including sensitive information in maintenance reason',
                code='SENSITIVE_INFO_WARNING'
            ))
        
        return messages
    
    def _assess_performance_impact(self, config: Dict[str, Any]) -> List[ValidationMessage]:
        """Assess performance impact of maintenance configuration"""
        messages = []
        
        mode = config.get('mode', 'normal').lower()
        duration = config.get('duration')
        
        # Convert duration to int if it's a string
        if duration is not None:
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                duration = None  # Skip duration-based impact assessment if invalid
        
        # Calculate estimated impact
        impact_score = 0
        
        if mode == 'emergency':
            impact_score += 80
        elif mode == 'normal':
            impact_score += 40
        elif mode == 'test':
            impact_score += 5
        
        if duration:
            if duration > 240:  # 4 hours
                impact_score += 30
            elif duration > 60:  # 1 hour
                impact_score += 15
            elif duration > 15:  # 15 minutes
                impact_score += 5
        
        # Provide impact assessment
        if impact_score >= 80:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field='performance_impact',
                message='High impact maintenance - significant user disruption expected',
                code='HIGH_IMPACT_WARNING',
                details={'impact_score': impact_score}
            ))
        elif impact_score >= 50:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field='performance_impact',
                message='Medium impact maintenance - moderate user disruption expected',
                code='MEDIUM_IMPACT_INFO',
                details={'impact_score': impact_score}
            ))
        else:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field='performance_impact',
                message='Low impact maintenance - minimal user disruption expected',
                code='LOW_IMPACT_INFO',
                details={'impact_score': impact_score}
            ))
        
        return messages
    
    def _contains_inappropriate_content(self, text: str) -> bool:
        """Check for inappropriate content in text"""
        # Simple inappropriate content detection
        inappropriate_patterns = [
            r'\b(damn|hell|crap)\b',  # Mild profanity
            r'[!]{3,}',  # Excessive exclamation
            r'[A-Z]{10,}',  # Excessive caps
        ]
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_sensitive_info(self, text: str) -> bool:
        """Check for sensitive information in text"""
        # Simple sensitive information detection
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card pattern
            r'\bpassword\s*[:=]\s*\S+\b',  # Password
            r'\bapi[_-]?key\s*[:=]\s*\S+\b',  # API key
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _create_validated_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create validated and normalized configuration"""
        validated = {}
        
        # Normalize reason
        if config.get('reason'):
            validated['reason'] = config['reason'].strip()
        
        # Normalize duration
        if config.get('duration') is not None:
            try:
                validated['duration'] = int(config['duration'])
            except (ValueError, TypeError):
                # Don't include invalid duration in validated config
                pass
        
        # Normalize mode
        if config.get('mode'):
            validated['mode'] = config['mode'].lower().strip()
        else:
            validated['mode'] = 'normal'
        
        # Add validation metadata
        validated['_validated_at'] = datetime.now(timezone.utc).isoformat()
        validated['_validator_version'] = '1.0.0'
        
        return validated
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return self._validation_stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset validation statistics"""
        self._validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'warnings_generated': 0,
            'errors_generated': 0
        }
    
    def get_validation_rules_summary(self) -> Dict[str, Any]:
        """Get summary of validation rules"""
        return {
            'reason_constraints': {
                'min_length': self.MIN_REASON_LENGTH,
                'max_length': self.MAX_REASON_LENGTH,
                'required': True
            },
            'duration_constraints': {
                'min_minutes': self.MIN_DURATION_MINUTES,
                'max_minutes': self.MAX_DURATION_MINUTES,
                'warning_threshold': self.WARNING_DURATION_THRESHOLD,
                'short_threshold': self.SHORT_DURATION_THRESHOLD,
                'required': False
            },
            'mode_constraints': {
                'valid_modes': self.VALID_MODES,
                'default': 'normal',
                'required': True
            },
            'validation_features': [
                'Type validation',
                'Range validation',
                'Content validation',
                'Consistency checking',
                'Context validation',
                'Business rules validation',
                'Security validation',
                'Performance impact assessment'
            ]
        }