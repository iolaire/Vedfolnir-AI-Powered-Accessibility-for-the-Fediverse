# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Error Handling Module

Comprehensive error handling system for RQ operations including:
- Automatic retry logic with exponential backoff
- Error categorization and appropriate handling
- Dead letter queue for permanently failed tasks
- Proper database session management to prevent connection leaks
- Detailed error logging and reporting
- Error notification system for administrators
- Error recovery procedures and documentation
"""

from .rq_error_handler import RQErrorHandler, ErrorCategory, RetryStrategy
from .rq_session_manager import RQSessionManager
from .dead_letter_queue import DeadLetterQueue
from .rq_error_logger import RQErrorLogger, LogLevel
from .rq_error_notifier import RQErrorNotifier, NotificationSeverity, NotificationChannel
from .error_recovery_procedures import ErrorRecoveryProcedures, RecoveryAction, RecoveryStatus
from .rq_task_validator import RQTaskValidator, ValidationResult, ValidationSeverity
from .rq_data_recovery import RQDataRecovery, RecoveryMethod, RecoveryResult

__all__ = [
    'RQErrorHandler',
    'ErrorCategory', 
    'RetryStrategy',
    'RQSessionManager',
    'DeadLetterQueue',
    'RQErrorLogger',
    'LogLevel',
    'RQErrorNotifier',
    'NotificationSeverity',
    'NotificationChannel',
    'ErrorRecoveryProcedures',
    'RecoveryAction',
    'RecoveryStatus',
    'RQTaskValidator',
    'ValidationResult',
    'ValidationSeverity',
    'RQDataRecovery',
    'RecoveryMethod',
    'RecoveryResult'
]