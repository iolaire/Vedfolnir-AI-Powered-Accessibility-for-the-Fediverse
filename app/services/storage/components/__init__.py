# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Framework Components

Consolidated storage management components for the Vedfolnir application.
All storage-related functionality is centralized in this module.
"""

# Core storage services
from .storage_configuration_service import StorageConfigurationService
from .storage_monitor_service import StorageMonitorService, StorageMetrics
from .storage_limit_enforcer import StorageLimitEnforcer, StorageCheckResult, StorageBlockingState

# Health and monitoring
from .storage_health_checker import StorageHealthChecker, StorageHealthStatus
from .storage_health_endpoints import register_storage_health_endpoints

# Alert and notification systems
from .storage_alert_system import StorageAlertSystem
from .storage_warning_monitor import StorageWarningMonitor, StorageEventType
from .storage_user_notification_system import StorageUserNotificationSystem
from .storage_email_notification_service import StorageEmailNotificationService

# Integration and management
from .storage_override_system import StorageOverrideSystem
from .storage_cleanup_integration import StorageCleanupIntegration
from .storage_monitoring_dashboard_integration import StorageMonitoringDashboardIntegration
from .storage_warning_dashboard_integration import StorageWarningDashboardIntegration
from .storage_event_logger import StorageEventLogger