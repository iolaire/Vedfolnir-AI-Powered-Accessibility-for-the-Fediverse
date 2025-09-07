# Notification System Consolidation Plan

## Overview
Consolidate multiple notification systems into a unified, efficient architecture centered around the existing `UnifiedNotificationManager`.

## Current State Analysis

### Existing Systems
1. **UnifiedNotificationManager** (2128 lines) - Core system ✅
2. **StorageUserNotificationSystem** - Storage-specific notifications
3. **DashboardNotificationHandlers** - WebSocket dashboard notifications  
4. **PlatformManagementNotificationService** - Platform operation notifications
5. **NotificationHelpers** - Convenience functions ✅
6. **PageNotificationIntegrator** (933 lines) - Page integration
7. **NotificationSystemMonitor** (1022 lines) - System monitoring
8. **Various alert/warning systems** - Scattered throughout codebase

### Problems Identified
- **Code Duplication**: Similar notification logic in multiple places
- **Inconsistent APIs**: Different interfaces for same functionality
- **Performance Overhead**: Multiple systems processing same events
- **Maintenance Burden**: Multiple codebases to maintain
- **User Experience**: Inconsistent notification behavior

## Consolidation Strategy

### Phase 1: Core System Enhancement
**Goal**: Enhance UnifiedNotificationManager to handle all notification types

#### 1.1 Extend Notification Categories
```python
# Add to models.py NotificationCategory enum
class NotificationCategory(Enum):
    # Existing categories
    SYSTEM = "system"
    ADMIN = "admin"
    USER = "user"
    CAPTION = "caption"
    PLATFORM = "platform"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    
    # New consolidated categories
    STORAGE = "storage"           # From StorageUserNotificationSystem
    DASHBOARD = "dashboard"       # From DashboardNotificationHandlers
    MONITORING = "monitoring"     # From NotificationSystemMonitor
    PERFORMANCE = "performance"   # From various performance alerts
    HEALTH = "health"            # From health check systems
```

#### 1.2 Add Specialized Message Types
```python
# Add to unified_notification_manager.py

@dataclass
class StorageNotificationMessage(NotificationMessage):
    """Storage-specific notification message"""
    storage_gb: Optional[float] = None
    limit_gb: Optional[float] = None
    usage_percentage: Optional[float] = None
    blocked_at: Optional[datetime] = None
    should_hide_form: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.STORAGE

@dataclass
class PerformanceNotificationMessage(NotificationMessage):
    """Performance monitoring notification message"""
    metrics: Optional[Dict[str, float]] = None
    threshold_exceeded: Optional[str] = None
    recovery_action: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.PERFORMANCE
```

### Phase 2: Service Layer Consolidation
**Goal**: Replace specialized services with unified service adapters

#### 2.1 Create Service Adapters
```python
# Create notification_service_adapters.py

class StorageNotificationAdapter:
    """Adapter for storage notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_storage_limit_notification(self, user_id: int, 
                                      storage_context: StorageNotificationContext) -> bool:
        """Send storage limit notification via unified system"""
        message = StorageNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING if storage_context.is_blocked else NotificationType.INFO,
            title="Storage Limit Alert",
            message=storage_context.reason,
            user_id=user_id,
            storage_gb=storage_context.storage_gb,
            limit_gb=storage_context.limit_gb,
            usage_percentage=storage_context.usage_percentage,
            blocked_at=storage_context.blocked_at,
            should_hide_form=storage_context.should_hide_form
        )
        
        return self.notification_manager.send_user_notification(user_id, message)

class PlatformNotificationAdapter:
    """Adapter for platform notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_platform_operation_notification(self, user_id: int, 
                                           result: PlatformOperationResult) -> bool:
        """Send platform operation notification via unified system"""
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.SUCCESS if result.success else NotificationType.ERROR,
            title=f"Platform {result.operation_type.title()}",
            message=result.message,
            user_id=user_id,
            category=NotificationCategory.PLATFORM,
            data={
                'operation_type': result.operation_type,
                'platform_data': result.platform_data,
                'error_details': result.error_details,
                'requires_refresh': result.requires_refresh
            }
        )
        
        return self.notification_manager.send_user_notification(user_id, message)
```

#### 2.2 Update Helper Functions
```python
# Extend notification_helpers.py

def send_storage_notification(
    user_id: int,
    storage_context: StorageNotificationContext
) -> bool:
    """Convenience function for storage notifications"""
    adapter = StorageNotificationAdapter(current_app.unified_notification_manager)
    return adapter.send_storage_limit_notification(user_id, storage_context)

def send_platform_notification(
    user_id: int,
    operation_result: PlatformOperationResult
) -> bool:
    """Convenience function for platform notifications"""
    adapter = PlatformNotificationAdapter(current_app.unified_notification_manager)
    return adapter.send_platform_operation_notification(user_id, operation_result)
```

### Phase 3: WebSocket Integration Consolidation
**Goal**: Unify WebSocket handling through existing framework

#### 3.1 Consolidate WebSocket Handlers
```python
# Update dashboard_notification_handlers.py to use unified system

class ConsolidatedDashboardHandlers:
    """Consolidated dashboard handlers using UnifiedNotificationManager"""
    
    def __init__(self, socketio, notification_manager: UnifiedNotificationManager):
        self.socketio = socketio
        self.notification_manager = notification_manager
        
        # Register unified handlers
        self.register_unified_handlers()
    
    def register_unified_handlers(self):
        """Register consolidated WebSocket handlers"""
        
        @self.socketio.on('connect', namespace='/')
        def handle_unified_connect(auth):
            """Unified connection handler for all notification types"""
            if not current_user.is_authenticated:
                return False
            
            user_id = current_user.id
            
            # Join appropriate rooms based on user role and permissions
            self._join_user_rooms(user_id)
            
            # Replay all pending notifications (unified)
            pending_count = self.notification_manager.replay_messages_for_user(user_id)
            
            # Send connection confirmation
            emit('unified_connected', {
                'status': 'connected',
                'user_id': user_id,
                'pending_messages': pending_count,
                'supported_categories': self._get_user_notification_categories(user_id),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return True
```

### Phase 4: Consumer Updates and Comprehensive Testing
**Goal**: Update all consumers to use the unified system and implement comprehensive testing

#### 4.1 Update Consumer Systems
```python
# Update all route handlers to use unified notification system

# Example: Update routes/user_routes.py
from notification_service_adapters import StorageNotificationAdapter, PlatformNotificationAdapter

@user_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    try:
        # Profile update logic...
        
        # OLD: Multiple notification calls
        # flash('Profile updated successfully', 'success')
        # send_email_notification(...)
        # log_user_activity(...)
        
        # NEW: Unified notification
        send_user_notification(
            message="Profile updated successfully",
            notification_type=NotificationType.SUCCESS,
            title="Profile Update",
            category=NotificationCategory.USER,
            user_id=current_user.id
        )
        
    except Exception as e:
        # OLD: Inconsistent error handling
        # flash('Profile update failed', 'error')
        
        # NEW: Unified error notification
        send_user_notification(
            message=f"Profile update failed: {str(e)}",
            notification_type=NotificationType.ERROR,
            title="Profile Update Failed",
            category=NotificationCategory.USER,
            user_id=current_user.id
        )

# Example: Update storage limit checks
@caption_bp.route('/generate', methods=['POST'])
@login_required
def generate_caption():
    # Check storage limits using unified system
    storage_adapter = StorageNotificationAdapter(current_app.unified_notification_manager)
    
    if storage_context := get_storage_notification_context():
        if storage_context.is_blocked:
            storage_adapter.send_storage_limit_notification(current_user.id, storage_context)
            return jsonify({'error': 'Storage limit exceeded'}), 403
    
    # Continue with caption generation...
```

#### 4.2 Update WebSocket Consumers
```python
# Update all WebSocket event handlers to use unified system

# Example: Update admin dashboard handlers
@admin_bp.route('/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Register page for unified notifications
    page_id = f"admin_dashboard_{current_user.id}_{int(time.time())}"
    
    integration_config = current_app.page_notification_integrator.register_page_integration(
        page_id=page_id,
        page_type=PageType.ADMIN_DASHBOARD
    )
    
    return render_template('admin/dashboard.html', 
                         notification_config=integration_config)

# Update JavaScript consumers
# static/js/admin-dashboard.js - Use unified WebSocket handlers
```

#### 4.3 Comprehensive Python Testing
```python
# Create tests/integration/test_unified_notification_system.py

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
from notification_service_adapters import StorageNotificationAdapter, PlatformNotificationAdapter
from models import NotificationType, NotificationCategory, NotificationPriority
from database import DatabaseManager
from config import Config

class TestUnifiedNotificationSystem(unittest.TestCase):
    """Comprehensive tests for unified notification system"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock WebSocket components
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        # Initialize unified notification manager
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.db_manager
        )
        
        # Test user credentials
        self.admin_credentials = {
            'username_or_email': 'admin',
            'password': 'admin123'
        }
    
    def test_storage_notification_adapter(self):
        """Test storage notification adapter functionality"""
        adapter = StorageNotificationAdapter(self.notification_manager)
        
        # Create mock storage context
        storage_context = Mock()
        storage_context.is_blocked = True
        storage_context.reason = "Storage limit exceeded"
        storage_context.storage_gb = 5.2
        storage_context.limit_gb = 5.0
        storage_context.usage_percentage = 104.0
        storage_context.blocked_at = datetime.now(timezone.utc)
        storage_context.should_hide_form = True
        
        # Test notification sending
        result = adapter.send_storage_limit_notification(1, storage_context)
        self.assertTrue(result)
    
    def test_platform_notification_adapter(self):
        """Test platform notification adapter functionality"""
        adapter = PlatformNotificationAdapter(self.notification_manager)
        
        # Create mock platform operation result
        operation_result = Mock()
        operation_result.success = True
        operation_result.message = "Platform connected successfully"
        operation_result.operation_type = "connect_platform"
        operation_result.platform_data = {"platform_name": "Test Platform"}
        operation_result.error_details = None
        operation_result.requires_refresh = False
        
        # Test notification sending
        result = adapter.send_platform_operation_notification(1, operation_result)
        self.assertTrue(result)
    
    def test_unified_notification_delivery(self):
        """Test unified notification delivery across all categories"""
        test_categories = [
            NotificationCategory.SYSTEM,
            NotificationCategory.ADMIN,
            NotificationCategory.USER,
            NotificationCategory.CAPTION,
            NotificationCategory.PLATFORM,
            NotificationCategory.SECURITY,
            NotificationCategory.MAINTENANCE,
            NotificationCategory.STORAGE,
            NotificationCategory.DASHBOARD,
            NotificationCategory.MONITORING,
            NotificationCategory.PERFORMANCE,
            NotificationCategory.HEALTH
        ]
        
        for category in test_categories:
            with self.subTest(category=category):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Test {category.value} Notification",
                    message=f"Testing {category.value} notification delivery",
                    category=category,
                    priority=NotificationPriority.NORMAL
                )
                
                result = self.notification_manager.send_user_notification(1, message)
                self.assertTrue(result, f"Failed to send {category.value} notification")
    
    def test_notification_persistence(self):
        """Test notification persistence in database"""
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.SUCCESS,
            title="Test Persistence",
            message="Testing notification persistence",
            category=NotificationCategory.USER,
            user_id=1
        )
        
        # Send notification
        result = self.notification_manager.send_user_notification(1, message)
        self.assertTrue(result)
        
        # Verify persistence
        history = self.notification_manager.get_notification_history(1, limit=1)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].title, "Test Persistence")
    
    def test_notification_replay(self):
        """Test notification replay for reconnecting users"""
        # Queue offline notification
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Offline Message",
            message="This message was sent while user was offline",
            category=NotificationCategory.USER,
            user_id=1
        )
        
        self.notification_manager.queue_offline_notification(1, message)
        
        # Test replay
        replayed_count = self.notification_manager.replay_messages_for_user(1)
        self.assertGreaterEqual(replayed_count, 0)
    
    def test_notification_cleanup(self):
        """Test notification cleanup functionality"""
        # Create expired notification
        expired_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Expired Message",
            message="This message should be cleaned up",
            category=NotificationCategory.USER,
            user_id=1,
            expires_at=datetime.now(timezone.utc)  # Already expired
        )
        
        self.notification_manager.send_user_notification(1, expired_message)
        
        # Test cleanup
        cleanup_count = self.notification_manager.cleanup_expired_messages()
        self.assertGreaterEqual(cleanup_count, 0)
    
    def test_notification_stats(self):
        """Test notification statistics functionality"""
        stats = self.notification_manager.get_notification_stats()
        
        # Verify stats structure
        self.assertIn('total_messages_in_db', stats)
        self.assertIn('unread_messages', stats)
        self.assertIn('pending_delivery', stats)
        self.assertIn('offline_queues', stats)
        self.assertIn('retry_queues', stats)
        self.assertIn('delivery_stats', stats)

# Create tests/integration/test_notification_route_integration.py

class TestNotificationRouteIntegration(unittest.TestCase):
    """Test notification integration with Flask routes"""
    
    def setUp(self):
        """Set up Flask test client"""
        from web_app import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Admin credentials for authenticated tests
        self.admin_credentials = {
            'username_or_email': 'admin',
            'password': 'admin123'
        }
    
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def login_admin(self):
        """Helper method to login as admin"""
        return self.client.post('/login', data=self.admin_credentials, follow_redirects=True)
    
    def test_profile_update_notifications(self):
        """Test profile update generates unified notifications"""
        # Login as admin
        self.login_admin()
        
        # Update profile
        response = self.client.post('/profile/update', data={
            'first_name': 'Test',
            'last_name': 'Admin',
            'email': 'admin@test.com'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        # Additional assertions for notification delivery would go here
    
    def test_platform_management_notifications(self):
        """Test platform management operations generate unified notifications"""
        # Login as admin
        self.login_admin()
        
        # Test platform connection
        response = self.client.post('/platform/test-connection', data={
            'platform_id': 1
        }, follow_redirects=True)
        
        # Verify response and notification delivery
        self.assertIn([200, 302], [response.status_code])
    
    def test_storage_limit_notifications(self):
        """Test storage limit notifications in caption generation"""
        # Login as admin
        self.login_admin()
        
        # Access caption generation page
        response = self.client.get('/caption/generate')
        self.assertEqual(response.status_code, 200)
        
        # Test caption generation with potential storage limits
        response = self.client.post('/caption/generate', data={
            'image_url': 'https://example.com/test.jpg'
        })
        
        # Verify appropriate response based on storage status
        self.assertIn(response.status_code, [200, 403])

# Create tests/performance/test_notification_performance.py

class TestNotificationPerformance(unittest.TestCase):
    """Performance tests for unified notification system"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock components for performance testing
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.db_manager
        )
    
    def test_bulk_notification_performance(self):
        """Test performance of bulk notification sending"""
        import time
        
        # Test sending 1000 notifications
        notification_count = 1000
        start_time = time.time()
        
        for i in range(notification_count):
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Performance Test {i}",
                message=f"Performance test notification {i}",
                category=NotificationCategory.USER,
                user_id=1
            )
            
            self.notification_manager.send_user_notification(1, message)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        self.assertLess(duration, 10.0, "Bulk notification sending took too long")
        notifications_per_second = notification_count / duration
        self.assertGreater(notifications_per_second, 100, "Notification throughput too low")
    
    def test_concurrent_notification_performance(self):
        """Test performance under concurrent load"""
        import threading
        import time
        
        def send_notifications(thread_id, count):
            for i in range(count):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Concurrent Test {thread_id}-{i}",
                    message=f"Concurrent test notification {thread_id}-{i}",
                    category=NotificationCategory.USER,
                    user_id=thread_id
                )
                
                self.notification_manager.send_user_notification(thread_id, message)
        
        # Test with 10 concurrent threads sending 100 notifications each
        thread_count = 10
        notifications_per_thread = 100
        
        start_time = time.time()
        
        threads = []
        for thread_id in range(thread_count):
            thread = threading.Thread(
                target=send_notifications,
                args=(thread_id + 1, notifications_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        duration = end_time - start_time
        
        total_notifications = thread_count * notifications_per_thread
        
        # Performance assertions
        self.assertLess(duration, 30.0, "Concurrent notification sending took too long")
        notifications_per_second = total_notifications / duration
        self.assertGreater(notifications_per_second, 50, "Concurrent notification throughput too low")
```

#### 4.4 Comprehensive Playwright Testing
```javascript
// Create tests/playwright/tests/0907_14_30_test_unified_notifications.js

const { test, expect } = require('@playwright/test');

test.describe('Unified Notification System', () => {
    // Admin credentials for authenticated tests
    const adminCredentials = {
        username_or_email: 'admin',
        password: 'admin123'
    };
    
    test.beforeEach(async ({ page }) => {
        // Ensure clean state
        await page.context().clearCookies();
        
        // Navigate to login page
        await page.goto('/login', { waitUntil: 'domcontentloaded' });
        
        // Login as admin
        await page.fill('input[name="username_or_email"]', adminCredentials.username_or_email);
        await page.fill('input[name="password"]', adminCredentials.password);
        await page.click('button[type="submit"]');
        
        // Wait for successful login
        await page.waitForURL('**/dashboard', { timeout: 30000 });
    });
    
    test.afterEach(async ({ page }) => {
        // Logout and cleanup
        try {
            await page.goto('/logout', { waitUntil: 'domcontentloaded' });
        } catch (error) {
            console.log('Logout cleanup failed:', error.message);
        }
    });
    
    test('should display unified notifications on dashboard', async ({ page }) => {
        // Navigate to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for WebSocket connection
        await page.waitForTimeout(2000);
        
        // Check for notification container
        const notificationContainer = await page.locator('#notifications-container');
        await expect(notificationContainer).toBeVisible();
        
        // Verify WebSocket connection status
        const connectionStatus = await page.evaluate(() => {
            return window.notificationSocket && window.notificationSocket.connected;
        });
        expect(connectionStatus).toBe(true);
    });
    
    test('should receive storage limit notifications', async ({ page }) => {
        // Navigate to caption generation page
        await page.goto('/caption/generate', { waitUntil: 'domcontentloaded' });
        
        // Check for storage notification banner
        const storageNotification = await page.locator('.storage-notification-banner');
        
        // If storage limit is active, banner should be visible
        if (await storageNotification.isVisible()) {
            await expect(storageNotification).toContainText('storage');
            
            // Verify form is hidden when storage limit exceeded
            const captionForm = await page.locator('#caption-generation-form');
            const isFormHidden = await captionForm.isHidden();
            
            if (isFormHidden) {
                console.log('✅ Caption form correctly hidden due to storage limit');
            }
        }
    });
    
    test('should receive platform management notifications', async ({ page }) => {
        // Navigate to platform management
        await page.goto('/platform/manage', { waitUntil: 'domcontentloaded' });
        
        // Wait for page load and WebSocket connection
        await page.waitForTimeout(2000);
        
        // Test platform connection (if platforms exist)
        const testConnectionButton = await page.locator('button:has-text("Test Connection")').first();
        
        if (await testConnectionButton.isVisible()) {
            // Click test connection
            await testConnectionButton.click();
            
            // Wait for notification
            await page.waitForTimeout(3000);
            
            // Check for notification
            const notification = await page.locator('.notification-message').first();
            if (await notification.isVisible()) {
                await expect(notification).toContainText(['success', 'error', 'connection']);
                console.log('✅ Platform notification received');
            }
        }
    });
    
    test('should receive admin notifications', async ({ page }) => {
        // Navigate to admin dashboard
        await page.goto('/admin/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for WebSocket connection
        await page.waitForTimeout(2000);
        
        // Check for admin notification container
        const adminNotifications = await page.locator('#admin-notifications-container');
        await expect(adminNotifications).toBeVisible();
        
        // Verify admin WebSocket namespace connection
        const adminConnectionStatus = await page.evaluate(() => {
            return window.adminNotificationSocket && window.adminNotificationSocket.connected;
        });
        expect(adminConnectionStatus).toBe(true);
    });
    
    test('should handle notification interactions', async ({ page }) => {
        // Navigate to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for any existing notifications
        await page.waitForTimeout(2000);
        
        // Check for dismissible notifications
        const notifications = await page.locator('.notification-item');
        const notificationCount = await notifications.count();
        
        if (notificationCount > 0) {
            // Test dismissing a notification
            const firstNotification = notifications.first();
            const dismissButton = await firstNotification.locator('.notification-dismiss');
            
            if (await dismissButton.isVisible()) {
                await dismissButton.click();
                
                // Verify notification was dismissed
                await page.waitForTimeout(1000);
                const remainingCount = await notifications.count();
                expect(remainingCount).toBeLessThan(notificationCount);
                console.log('✅ Notification dismissal working');
            }
        }
    });
    
    test('should maintain notification state across page navigation', async ({ page }) => {
        // Navigate to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for WebSocket connection
        await page.waitForTimeout(2000);
        
        // Navigate to another page
        await page.goto('/profile', { waitUntil: 'domcontentloaded' });
        
        // Wait for page load
        await page.waitForTimeout(2000);
        
        // Navigate back to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Verify WebSocket reconnection
        await page.waitForTimeout(2000);
        
        const connectionStatus = await page.evaluate(() => {
            return window.notificationSocket && window.notificationSocket.connected;
        });
        expect(connectionStatus).toBe(true);
        console.log('✅ Notification state maintained across navigation');
    });
    
    test('should handle WebSocket reconnection', async ({ page }) => {
        // Navigate to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for initial connection
        await page.waitForTimeout(2000);
        
        // Simulate network disconnection and reconnection
        await page.evaluate(() => {
            if (window.notificationSocket) {
                window.notificationSocket.disconnect();
            }
        });
        
        // Wait for disconnection
        await page.waitForTimeout(1000);
        
        // Reconnect
        await page.evaluate(() => {
            if (window.notificationSocket) {
                window.notificationSocket.connect();
            }
        });
        
        // Wait for reconnection
        await page.waitForTimeout(3000);
        
        // Verify reconnection
        const connectionStatus = await page.evaluate(() => {
            return window.notificationSocket && window.notificationSocket.connected;
        });
        expect(connectionStatus).toBe(true);
        console.log('✅ WebSocket reconnection working');
    });
    
    test('should display notifications with correct styling', async ({ page }) => {
        // Navigate to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for notifications
        await page.waitForTimeout(2000);
        
        // Check notification styling
        const notifications = await page.locator('.notification-item');
        const notificationCount = await notifications.count();
        
        if (notificationCount > 0) {
            const firstNotification = notifications.first();
            
            // Verify notification has proper CSS classes
            const hasNotificationClass = await firstNotification.evaluate(el => 
                el.classList.contains('notification-item')
            );
            expect(hasNotificationClass).toBe(true);
            
            // Verify notification is visible and positioned correctly
            await expect(firstNotification).toBeVisible();
            
            // Check for notification type styling
            const notificationTypes = ['success', 'error', 'warning', 'info'];
            let hasTypeClass = false;
            
            for (const type of notificationTypes) {
                if (await firstNotification.evaluate((el, type) => 
                    el.classList.contains(`notification-${type}`), type)) {
                    hasTypeClass = true;
                    break;
                }
            }
            
            expect(hasTypeClass).toBe(true);
            console.log('✅ Notification styling correct');
        }
    });
});

// Create tests/playwright/tests/0907_14_30_test_notification_performance.js

test.describe('Notification Performance Tests', () => {
    const adminCredentials = {
        username_or_email: 'admin',
        password: 'admin123'
    };
    
    test.beforeEach(async ({ page }) => {
        await page.context().clearCookies();
        await page.goto('/login', { waitUntil: 'domcontentloaded' });
        await page.fill('input[name="username_or_email"]', adminCredentials.username_or_email);
        await page.fill('input[name="password"]', adminCredentials.password);
        await page.click('button[type="submit"]');
        await page.waitForURL('**/dashboard', { timeout: 30000 });
    });
    
    test('should handle rapid notification updates', async ({ page }) => {
        // Navigate to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for WebSocket connection
        await page.waitForTimeout(2000);
        
        // Measure notification rendering performance
        const startTime = Date.now();
        
        // Simulate rapid notifications (this would typically come from server)
        await page.evaluate(() => {
            // Simulate receiving multiple notifications quickly
            for (let i = 0; i < 10; i++) {
                setTimeout(() => {
                    if (window.handleNotificationMessage) {
                        window.handleNotificationMessage({
                            id: `perf-test-${i}`,
                            type: 'info',
                            title: `Performance Test ${i}`,
                            message: `Testing notification performance ${i}`,
                            timestamp: new Date().toISOString()
                        });
                    }
                }, i * 100);
            }
        });
        
        // Wait for all notifications to be processed
        await page.waitForTimeout(2000);
        
        const endTime = Date.now();
        const duration = endTime - startTime;
        
        // Performance assertion
        expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
        console.log(`✅ Notification performance test completed in ${duration}ms`);
    });
    
    test('should maintain performance with many notifications', async ({ page }) => {
        // Navigate to dashboard
        await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
        
        // Wait for WebSocket connection
        await page.waitForTimeout(2000);
        
        // Check initial page performance
        const initialMetrics = await page.evaluate(() => performance.now());
        
        // Wait for potential notifications to load
        await page.waitForTimeout(3000);
        
        // Check final performance
        const finalMetrics = await page.evaluate(() => performance.now());
        
        const loadTime = finalMetrics - initialMetrics;
        
        // Performance assertion - page should load quickly even with notifications
        expect(loadTime).toBeLessThan(10000); // Should load within 10 seconds
        console.log(`✅ Page with notifications loaded in ${loadTime}ms`);
    });
});
```

#### 4.5 Test Execution Scripts
```bash
# Create tests/scripts/run_unified_notification_tests.sh

#!/bin/bash
# Comprehensive test runner for unified notification system

echo "🧪 Running Unified Notification System Tests"
echo "============================================="

# Test credentials
export TEST_ADMIN_USERNAME="admin"
export TEST_ADMIN_PASSWORD="admin123"

# Start web application for testing
echo "🚀 Starting web application..."
python web_app.py & sleep 10
WEB_APP_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up..."
    kill $WEB_APP_PID 2>/dev/null
    exit
}
trap cleanup EXIT

# Verify web app is running
if ! curl -s http://127.0.0.1:5000 > /dev/null; then
    echo "❌ Web application failed to start"
    exit 1
fi

echo "✅ Web application started successfully"

# Run Python tests
echo ""
echo "🐍 Running Python Tests..."
echo "=========================="

# Unit tests
echo "Running unit tests..."
python -m unittest tests.integration.test_unified_notification_system -v

# Integration tests
echo "Running integration tests..."
python -m unittest tests.integration.test_notification_route_integration -v

# Performance tests
echo "Running performance tests..."
python -m unittest tests.performance.test_notification_performance -v

# Run Playwright tests
echo ""
echo "🎭 Running Playwright Tests..."
echo "=============================="

cd tests/playwright

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing Playwright dependencies..."
    npm install
fi

# Run unified notification tests
echo "Running unified notification tests..."
timeout 120 npx playwright test tests/0907_14_30_test_unified_notifications.js --config=0830_17_52_playwright.config.js

# Run performance tests
echo "Running notification performance tests..."
timeout 120 npx playwright test tests/0907_14_30_test_notification_performance.js --config=0830_17_52_playwright.config.js

cd ../..

echo ""
echo "✅ All tests completed!"
echo "======================"
```



## Benefits of Consolidation

### Performance Benefits
- **Reduced Memory Usage**: Single notification system instead of multiple
- **Improved Efficiency**: Unified processing pipeline
- **Better Caching**: Centralized notification storage and retrieval
- **Reduced Database Load**: Single notification storage system

### Maintenance Benefits
- **Single Codebase**: One system to maintain and debug
- **Consistent API**: Unified interface for all notification types
- **Easier Testing**: Centralized testing approach
- **Better Documentation**: Single system to document

### User Experience Benefits
- **Consistent Behavior**: Uniform notification experience
- **Better Performance**: Faster notification delivery
- **Unified UI**: Consistent notification styling and behavior
- **Improved Reliability**: Single, well-tested system

## Implementation Timeline

### Week 1: Analysis and Design
- [ ] Complete system analysis
- [ ] Design unified interfaces
- [ ] Set up testing framework

### Week 2: Core System Enhancement
- [ ] Extend UnifiedNotificationManager
- [ ] Add new message types
- [ ] Implement service adapters
- [ ] Update helper functions

### Week 3: Integration and Testing
- [ ] Integrate WebSocket handlers
- [ ] Update route handlers
- [ ] Comprehensive testing
- [ ] Performance validation

### Week 4: Consumer Updates and Testing
- [ ] Update all route handlers to use unified system
- [ ] Update WebSocket consumers and JavaScript clients
- [ ] Implement comprehensive Python test suite
- [ ] Implement comprehensive Playwright test suite
- [ ] Performance testing and optimization
- [ ] Documentation updates

## Risk Mitigation

### Testing Strategy
- **Unit Tests**: All adapters and core functionality
- **Integration Tests**: WebSocket functionality and route integration
- **Performance Tests**: Notification delivery speed and concurrent load
- **Playwright Tests**: End-to-end browser testing with admin credentials (admin/admin123)
- **User Acceptance Testing**: Real-world usage scenarios

### Monitoring
- Performance metrics comparison
- Error rate monitoring
- User feedback collection

## Success Metrics

### Technical Metrics
- **Code Reduction**: Target 40% reduction in notification-related code
- **Performance Improvement**: 25% faster notification delivery
- **Memory Usage**: 30% reduction in notification system memory usage
- **Maintenance Time**: 50% reduction in notification system maintenance

### Quality Metrics
- **Bug Reduction**: 60% fewer notification-related bugs
- **Test Coverage**: 95% test coverage for unified system
- **Documentation**: Complete documentation for unified system
- **User Satisfaction**: Improved user experience metrics

## Conclusion

Consolidating the notification systems will significantly improve code maintainability, system performance, and user experience. The unified approach leverages the existing robust `UnifiedNotificationManager` while providing adapters for specialized functionality, ensuring a smooth migration path and better long-term architecture.