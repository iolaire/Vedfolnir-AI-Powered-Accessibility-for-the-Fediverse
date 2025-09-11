# Framework Consolidation File Mapping

## Overview
This document provides the detailed file-by-file mapping for consolidating all root directory framework files into the proper `app/` directory structure.

## Security Framework Consolidation
**Target**: `app/core/security/`

### Core Security Components → `app/core/security/core/`
- `security_decorators.py` → `app/core/security/core/decorators.py`
- `input_validation.py` → `app/core/security/validation/input_validation.py`
- `enhanced_input_validation.py` → `app/core/security/validation/enhanced_input_validation.py`
- `rate_limiter.py` → `app/core/security/core/rate_limiter.py`
- `audit_logger.py` → `app/core/security/audit/audit_logger.py`

### Security Error Handling → `app/core/security/error_handling/`
- `enhanced_error_recovery_manager.py` → `app/core/security/error_handling/enhanced_error_recovery_manager.py`
- `error_recovery_manager.py` → `app/core/security/error_handling/error_recovery_manager.py`
- `graceful_shutdown_handler.py` → `app/core/security/error_handling/graceful_shutdown_handler.py`
- `system_recovery_manager.py` → `app/core/security/error_handling/system_recovery_manager.py`
- `system_recovery_integration.py` → `app/core/security/error_handling/system_recovery_integration.py`
- `detached_instance_handler.py` → `app/core/security/error_handling/detached_instance_handler.py`

### Security Integration → `app/core/security/integration/`
- `security_notification_integration_service.py` → `app/core/security/integration/notification_integration_service.py`

## Session Management Framework Consolidation
**Target**: `app/core/session/`

### Core Session Components → `app/core/session/core/`
- `session_manager.py` → `app/core/session/core/session_manager.py`
- `unified_session_manager.py` → `app/core/session/core/unified_session_manager.py`
- `session_cookie_manager.py` → `app/core/session/core/session_cookie_manager.py`
- `session_aware_user.py` → `app/core/session/core/session_aware_user.py`
- `session_state_manager.py` → `app/core/session/core/session_state_manager.py`

### Session Middleware → `app/core/session/middleware/`
- `session_middleware_v2.py` → `app/core/session/middleware/session_middleware_v2.py`

### Redis Session Components → `app/core/session/redis/`
- `redis_session_backend.py` → `app/core/session/redis/redis_session_backend.py`
- `redis_session_health_checker.py` → `app/core/session/redis/redis_session_health_checker.py`

### Session Health and Monitoring → `app/core/session/health/`
- `session_health_checker.py` → `app/core/session/health/session_health_checker.py`
- `session_monitoring.py` → `app/core/session/health/session_monitoring.py`
- `session_performance_monitor.py` → `app/core/session/health/session_performance_monitor.py`
- `session_performance_optimizer.py` → `app/core/session/health/session_performance_optimizer.py`

### Session API and Routes → `app/core/session/api/`
- `session_monitoring_api.py` → `app/core/session/api/session_monitoring_api.py`
- `session_monitoring_routes.py` → `app/core/session/api/session_monitoring_routes.py`
- `session_alert_routes.py` → `app/core/session/api/session_alert_routes.py`
- `session_health_routes.py` → `app/core/session/api/session_health_routes.py`
- `session_state_api.py` → `app/core/session/api/session_state_api.py`

### Session Utilities → `app/core/session/utils/`
- `session_monitoring_cli.py` → `app/core/session/utils/session_monitoring_cli.py`
- `session_alerting_system.py` → `app/core/session/utils/session_alerting_system.py`
- `session_aware_decorators.py` → `app/core/session/utils/session_aware_decorators.py`
- `session_platform_fix.py` → `app/core/session/utils/session_platform_fix.py`

### Session Error Handling → `app/core/session/error_handling/`
- `session_error_handlers.py` → `app/core/session/error_handling/session_error_handlers.py`
- `session_error_handling.py` → `app/core/session/error_handling/session_error_handling.py`
- `session_error_logger.py` → `app/core/session/error_handling/session_error_logger.py`

### Session Security → `app/core/session/security/`
- `session_security.py` → `app/core/session/security/session_security.py`

## Database Framework Consolidation
**Target**: `app/core/database/`

### Core Database Components → `app/core/database/core/`
- `database.py` → `app/core/database/core/database_manager.py`

### Database Connection Management → `app/core/database/connections/`
- `database_connection_recovery.py` → `app/core/database/connections/database_connection_recovery.py`
- `database_context_middleware.py` → `app/core/database/connections/database_context_middleware.py`
- `database_responsiveness_recovery.py` → `app/core/database/connections/database_responsiveness_recovery.py`

### Database Optimization → `app/core/database/optimization/`
- `database_query_optimizer.py` → `app/core/database/optimization/database_query_optimizer.py`

### MySQL Components → `app/core/database/mysql/`
- `mysql_connection_validator.py` → `app/core/database/mysql/mysql_connection_validator.py`
- `mysql_health_endpoints.py` → `app/core/database/mysql/mysql_health_endpoints.py`
- `mysql_performance_optimizer.py` → `app/core/database/mysql/mysql_performance_optimizer.py`

## Configuration Framework Consolidation
**Target**: `app/core/configuration/`

### Core Configuration Components → `app/core/configuration/core/`
- `configuration_service.py` → `app/core/configuration/core/configuration_service.py`
- `system_configuration_manager.py` → `app/core/configuration/core/system_configuration_manager.py`

### Configuration Cache → `app/core/configuration/cache/`
- `configuration_cache.py` → `app/core/configuration/cache/configuration_cache.py`

### Configuration Monitoring → `app/core/configuration/monitoring/`
- `configuration_change_logger.py` → `app/core/configuration/monitoring/configuration_change_logger.py`
- `configuration_health_monitor.py` → `app/core/configuration/monitoring/configuration_health_monitor.py`
- `configuration_metrics.py` → `app/core/configuration/monitoring/configuration_metrics.py`
- `configuration_health_endpoints.py` → `app/core/configuration/monitoring/configuration_health_endpoints.py`

### Configuration Validation → `app/core/configuration/validation/`
- `configuration_validation.py` → `app/core/configuration/validation/configuration_validation.py`

### Configuration Error Handling → `app/core/configuration/error_handling/`
- `configuration_error_handling.py` → `app/core/configuration/error_handling/configuration_error_handling.py`

### Configuration Events → `app/core/configuration/events/`
- `configuration_event_bus.py` → `app/core/configuration/events/configuration_event_bus.py`

### Configuration Adapters → `app/core/configuration/adapters/`
- `alert_configuration_adapter.py` → `app/core/configuration/adapters/alert_configuration_adapter.py`
- `performance_configuration_adapter.py` → `app/core/configuration/adapters/performance_configuration_adapter.py`

## Maintenance Framework Consolidation
**Target**: `app/services/maintenance/`

### Core Maintenance Components → `app/services/maintenance/core/`
- `maintenance_mode_service.py` → `app/services/maintenance/core/maintenance_mode_service.py`
- `enhanced_maintenance_mode_service.py` → `app/services/maintenance/core/enhanced_maintenance_mode_service.py`
- `maintenance_mode_transition_manager.py` → `app/services/maintenance/core/maintenance_mode_transition_manager.py`

### Maintenance Middleware → `app/services/maintenance/middleware/`
- `maintenance_mode_middleware.py` → `app/services/maintenance/middleware/maintenance_mode_middleware.py`
- `maintenance_mode_decorators.py` → `app/services/maintenance/middleware/maintenance_mode_decorators.py`

### Maintenance Validation → `app/services/maintenance/validation/`
- `maintenance_configuration_validator.py` → `app/services/maintenance/validation/maintenance_configuration_validator.py`
- `maintenance_procedure_validator.py` → `app/services/maintenance/validation/maintenance_procedure_validator.py`

### Maintenance Operations → `app/services/maintenance/operations/`
- `maintenance_operation_classifier.py` → `app/services/maintenance/operations/maintenance_operation_classifier.py`
- `maintenance_operation_completion_tracker.py` → `app/services/maintenance/operations/maintenance_operation_completion_tracker.py`
- `maintenance_data_integrity_protection.py` → `app/services/maintenance/operations/maintenance_data_integrity_protection.py`

### Maintenance API → `app/services/maintenance/api/`
- `maintenance_status_api.py` → `app/services/maintenance/api/maintenance_status_api.py`
- `maintenance_response_helper.py` → `app/services/maintenance/api/maintenance_response_helper.py`

### Maintenance Integration → `app/services/maintenance/integration/`
- `maintenance_notification_integration_service.py` → `app/services/maintenance/integration/maintenance_notification_integration_service.py`
- `maintenance_progress_websocket_handler.py` → `app/services/maintenance/integration/maintenance_progress_websocket_handler.py`

### Emergency Maintenance → `app/services/maintenance/emergency/`
- `emergency_maintenance_handler.py` → `app/services/maintenance/emergency/emergency_maintenance_handler.py`

## Performance Framework Consolidation
**Target**: `app/services/performance/`

### Core Performance Components → `app/services/performance/core/`
- `performance_cache_manager.py` → `app/services/performance/core/performance_cache_manager.py`
- `performance_monitoring_dashboard.py` → `app/services/performance/core/performance_monitoring_dashboard.py`

### Performance Configuration → `app/services/performance/configuration/`
- `performance_configuration_adapter.py` → `app/services/performance/configuration/performance_configuration_adapter.py`
- `performance_configuration_validator.py` → `app/services/performance/configuration/performance_configuration_validator.py`

### Performance Middleware → `app/services/performance/middleware/`
- `request_performance_middleware.py` → `app/services/performance/middleware/request_performance_middleware.py`

### Performance Monitoring → `app/services/performance/monitoring/`
- `memory_monitor.py` → `app/services/performance/monitoring/memory_monitor.py`
- `queue_size_monitor.py` → `app/services/performance/monitoring/queue_size_monitor.py`
- `ai_service_monitor.py` → `app/services/performance/monitoring/ai_service_monitor.py`

### Performance Error Recovery → `app/services/performance/error_recovery/`
- `responsiveness_error_recovery.py` → `app/services/performance/error_recovery/responsiveness_error_recovery.py`

### Performance Examples → `app/services/performance/examples/`
- `performance_optimization_integration_example.py` → `app/services/performance/examples/performance_optimization_integration_example.py`

## Platform Framework Consolidation
**Target**: `app/services/platform/`

### Core Platform Components → `app/services/platform/core/`
- `platform_context.py` → `app/services/platform/core/platform_context.py`
- `detect_platform.py` → `app/services/platform/core/detect_platform.py`

### Platform Utilities → `app/services/platform/utils/`
- `platform_context_utils.py` → `app/services/platform/utils/platform_context_utils.py`

### Platform Error Handling → `app/services/platform/error_handling/`
- `platform_management_error_handling.py` → `app/services/platform/error_handling/platform_management_error_handling.py`

### Platform Integration → `app/services/platform/integration/`
- `platform_management_notification_integration.py` → `app/services/platform/integration/platform_management_notification_integration.py`
- `platform_management_route_integration.py` → `app/services/platform/integration/platform_management_route_integration.py`

### Platform Adapters → `app/services/platform/adapters/`
- `platform_aware_caption_adapter.py` → `app/services/platform/adapters/platform_aware_caption_adapter.py`

### Platform Examples → `app/services/platform/examples/`
- `platform_management_route_examples.py` → `app/services/platform/examples/platform_management_route_examples.py`

## Storage Framework Consolidation
**Target**: `app/services/storage/`

### Core Storage Components → `app/services/storage/core/`
- `storage_monitor_service.py` → `app/services/storage/core/storage_monitor_service.py`
- `storage_configuration_service.py` → `app/services/storage/core/storage_configuration_service.py`
- `storage_limit_enforcer.py` → `app/services/storage/core/storage_limit_enforcer.py`
- `storage_override_system.py` → `app/services/storage/core/storage_override_system.py`

### Storage Health → `app/services/storage/health/`
- `storage_health_checker.py` → `app/services/storage/health/storage_health_checker.py`
- `storage_health_endpoints.py` → `app/services/storage/health/storage_health_endpoints.py`

### Storage Alerts → `app/services/storage/alerts/`
- `storage_alert_system.py` → `app/services/storage/alerts/storage_alert_system.py`
- `storage_warning_monitor.py` → `app/services/storage/alerts/storage_warning_monitor.py`

### Storage Integration → `app/services/storage/integration/`
- `storage_cleanup_integration.py` → `app/services/storage/integration/storage_cleanup_integration.py`
- `storage_monitoring_dashboard_integration.py` → `app/services/storage/integration/storage_monitoring_dashboard_integration.py`
- `storage_warning_dashboard_integration.py` → `app/services/storage/integration/storage_warning_dashboard_integration.py`

### Storage Notifications → `app/services/storage/notifications/`
- `storage_email_notification_service.py` → `app/services/storage/notifications/storage_email_notification_service.py`
- `storage_user_notification_system.py` → `app/services/storage/notifications/storage_user_notification_system.py`

### Storage Events → `app/services/storage/events/`
- `storage_event_logger.py` → `app/services/storage/events/storage_event_logger.py`

## Task Framework Consolidation
**Target**: `app/services/task/`

### Core Task Components → `app/services/task/core/`
- `task_queue_manager.py` → `app/services/task/core/task_queue_manager.py`
- `background_cleanup_manager.py` → `app/services/task/core/background_cleanup_manager.py`
- `concurrent_operation_manager.py` → `app/services/task/core/concurrent_operation_manager.py`

### Task Configuration → `app/services/task/configuration/`
- `task_queue_configuration_adapter.py` → `app/services/task/configuration/task_queue_configuration_adapter.py`

### Task Scheduling → `app/services/task/scheduling/`
- `job_priority_scheduler.py` → `app/services/task/scheduling/job_priority_scheduler.py`

### Task Emergency → `app/services/task/emergency/`
- `emergency_job_termination_manager.py` → `app/services/task/emergency/emergency_job_termination_manager.py`

## Alert Framework Consolidation
**Target**: `app/services/alerts/`

### Core Alert Components → `app/services/alerts/core/`
- `alert_manager.py` → `app/services/alerts/core/alert_manager.py`

### Alert Configuration → `app/services/alerts/configuration/`
- `alert_configuration_adapter.py` → `app/services/alerts/configuration/alert_configuration_adapter.py`
- `rate_limiting_configuration_adapter.py` → `app/services/alerts/configuration/rate_limiting_configuration_adapter.py`

### Alert Validation → `app/services/alerts/validation/`
- `alert_threshold_validator.py` → `app/services/alerts/validation/alert_threshold_validator.py`

## ActivityPub Framework Consolidation
**Target**: `app/services/activitypub/`

### Core ActivityPub Components → `app/services/activitypub/core/`
- `activitypub_client.py` → `app/services/activitypub/core/activitypub_client.py`

### ActivityPub Platforms → `app/services/activitypub/platforms/`
- `activitypub_platforms.py` → `app/services/activitypub/platforms/activitypub_platforms.py`
- `activitypub_platforms_pagination.py` → `app/services/activitypub/platforms/activitypub_platforms_pagination.py`

### ActivityPub Posts → `app/services/activitypub/posts/`
- `post_service.py` → `app/services/activitypub/posts/post_service.py`

## Admin Framework Consolidation
**Target**: `app/services/admin/`

### Core Admin Components → `app/services/admin/core/`
- `admin_management_service.py` → `app/services/admin/core/admin_management_service.py`
- `enhanced_admin_management_service.py` → `app/services/admin/core/enhanced_admin_management_service.py`

### Admin Integration → `app/services/admin/integration/`
- `admin_dashboard_health_integration.py` → `app/services/admin/integration/admin_dashboard_health_integration.py`
- `admin_user_management_integration.py` → `app/services/admin/integration/admin_user_management_integration.py`

### Admin WebSocket → `app/services/admin/websocket/`
- `admin_health_websocket_handlers.py` → `app/services/admin/websocket/admin_health_websocket_handlers.py`

### Admin Notifications → `app/services/admin/notifications/`
- `admin_security_audit_notification_handler.py` → `app/services/admin/notifications/admin_security_audit_notification_handler.py`
- `admin_system_health_notification_handler.py` → `app/services/admin/notifications/admin_system_health_notification_handler.py`

### Admin Storage → `app/services/admin/storage/`
- `admin_storage_dashboard.py` → `app/services/admin/storage/admin_storage_dashboard.py`

## Batch Processing Framework Consolidation
**Target**: `app/services/batch/`

### Core Batch Components → `app/services/batch/core/`
- `batch_update_service.py` → `app/services/batch/core/batch_update_service.py`
- `multi_tenant_control_service.py` → `app/services/batch/core/multi_tenant_control_service.py`

### Batch CLI → `app/services/batch/cli/`
- `batch_update_cli.py` → `app/services/batch/cli/batch_update_cli.py`

### Batch Operations → `app/services/batch/operations/`
- `concurrent_operation_manager.py` → `app/services/batch/operations/concurrent_operation_manager.py`

## Notification Framework Consolidation
**Target**: `app/services/notification/`

### Core Notification Components → `app/services/notification/core/`
- `unified_notification_manager.py` → `app/services/notification/core/unified_notification_manager.py`
- `notification_helpers.py` → `app/services/notification/core/notification_helpers.py`

### Notification Adapters → `app/services/notification/adapters/`
- `notification_service_adapters.py` → `app/services/notification/adapters/notification_service_adapters.py`

### Notification Monitoring → `app/services/notification/monitoring/`
- `notification_system_monitor.py` → `app/services/notification/monitoring/notification_system_monitor.py`
- `notification_monitoring_dashboard.py` → `app/services/notification/monitoring/notification_monitoring_dashboard.py`

### Notification Optimization → `app/services/notification/optimization/`
- `notification_database_optimizer.py` → `app/services/notification/optimization/notification_database_optimizer.py`
- `notification_performance_optimizer.py` → `app/services/notification/optimization/notification_performance_optimizer.py`

### Notification Delivery → `app/services/notification/delivery/`
- `notification_delivery_fallback.py` → `app/services/notification/delivery/notification_delivery_fallback.py`
- `notification_persistence_manager.py` → `app/services/notification/delivery/notification_persistence_manager.py`

### Notification Emergency → `app/services/notification/emergency/`
- `notification_emergency_recovery.py` → `app/services/notification/emergency/notification_emergency_recovery.py`

### Notification WebSocket → `app/services/notification/websocket/`
- `notification_websocket_recovery.py` → `app/services/notification/websocket/notification_websocket_recovery.py`

### Notification Integration → `app/services/notification/integration/`
- `dashboard_notification_handlers.py` → `app/services/notification/integration/dashboard_notification_handlers.py`
- `page_notification_integrator.py` → `app/services/notification/integration/page_notification_integrator.py`
- `user_profile_notification_helper.py` → `app/services/notification/integration/user_profile_notification_helper.py`

### Notification Migration → `app/services/notification/migration/`
- `migrate_user_profile_notifications.py` → `app/services/notification/migration/migrate_user_profile_notifications.py`

## Monitoring Framework Consolidation
**Target**: `app/services/monitoring/`

### Core Monitoring Components → `app/services/monitoring/core/`
- `system_monitor.py` → `app/services/monitoring/core/system_monitor.py`
- `advanced_monitoring_service.py` → `app/services/monitoring/core/advanced_monitoring_service.py`
- `monitoring_dashboard_service.py` → `app/services/monitoring/core/monitoring_dashboard_service.py`

### Monitoring Health → `app/services/monitoring/health/`
- `health_check.py` → `app/services/monitoring/health/health_check.py`

### Monitoring Progress → `app/services/monitoring/progress/`
- `progress_tracker.py` → `app/services/monitoring/progress/progress_tracker.py`

### Monitoring Platform → `app/services/monitoring/platform/`
- `redis_platform_manager.py` → `app/services/monitoring/platform/redis_platform_manager.py`

### Monitoring Storage → `app/services/monitoring/storage/`
- `register_storage_health_endpoints.py` → `app/services/monitoring/storage/register_storage_health_endpoints.py`
- `storage_warning_monitor.py` → `app/services/monitoring/storage/storage_warning_monitor.py`

## Utility Framework Consolidation
**Target**: `app/utils/`

### Utility Helpers → `app/utils/helpers/`
- `utils.py` → `app/utils/helpers/utils.py`

### Utility Templates → `app/utils/templates/`
- `safe_template_context.py` → `app/utils/templates/safe_template_context.py`

### Utility Migration → `app/utils/migration/`
- `migration_error_handler.py` → `app/utils/migration/migration_error_handler.py`
- `migration_validation_tools.py` → `app/utils/migration/migration_validation_tools.py`

### Utility Logging → `app/utils/logging/`
- `logger.py` → `app/utils/logging/logger.py`

### Utility Processing → `app/utils/processing/`
- `image_processor.py` → `app/utils/processing/image_processor.py`
- `ollama_caption_generator.py` → `app/utils/processing/ollama_caption_generator.py`
- `caption_quality_assessment.py` → `app/utils/processing/caption_quality_assessment.py`
- `caption_fallback.py` → `app/utils/processing/caption_fallback.py`
- `caption_formatter.py` → `app/utils/processing/caption_formatter.py`
- `caption_review_integration.py` → `app/utils/processing/caption_review_integration.py`
- `web_caption_generation_service.py` → `app/utils/processing/web_caption_generation_service.py`

### Utility Initialization → `app/utils/initialization/`
- `app_initialization.py` → `app/utils/initialization/app_initialization.py`
- `pre_auth_session.py` → `app/utils/initialization/pre_auth_session.py`
- `null_session_interface.py` → `app/utils/initialization/null_session_interface.py`

### Utility Version → `app/utils/version/`
- `version.py` → `app/utils/version/version.py`

## Files to Keep in Root Directory

### Essential Application Files (Keep in Root)
- `main.py` - Bot entry point
- `web_app.py` - Flask web application
- `config.py` - Core configuration
- `models.py` - Core data models

### Files to Remove from Root (after migration)
All 150+ framework files listed above will be moved to appropriate `app/` locations.

## Import Statement Updates Required

### High-Priority Import Updates (affects many files)
1. `from unified_notification_manager import` → `from app.services.notification.core.unified_notification_manager import`
2. `from database import` → `from app.core.database.core.database_manager import`
3. `from utils import` → `from app.utils.helpers.utils import`
4. `from session_manager import` → `from app.core.session.core.session_manager import`
5. `from security_decorators import` → `from app.core.security.core.decorators import`

### Template Reference Updates
- Update all template references to use new import paths
- Update all configuration file references
- Update all documentation references

### Configuration Reference Updates
- Update all environment variable references
- Update all deployment script references
- Update all Docker configuration references

## Verification Steps

### Post-Migration Verification
1. **Import Verification** - ensure all imports resolve correctly
2. **Functionality Testing** - verify all features work
3. **Performance Testing** - ensure no performance degradation
4. **Security Testing** - verify security features still work
5. **Integration Testing** - test all framework interactions

### Success Criteria
- All 150+ framework files moved to proper `app/` locations
- Root directory contains only 4 essential files
- All import statements updated and working
- All functionality preserved
- All tests passing
- Clean, organized codebase structure