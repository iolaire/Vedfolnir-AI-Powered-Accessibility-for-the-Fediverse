# Unified Notification System Documentation

## Overview

The Unified Notification System provides consistent notification display across all pages in Vedfolnir. It replaces all legacy notification systems including Flask flash messages, custom alert components, and page-specific notification implementations.

## Features

- **Consistent Styling**: Uniform appearance across all pages
- **Multiple Types**: Support for success, warning, error, info, and progress notifications
- **Auto-hide and Manual Dismiss**: Configurable auto-hide with manual dismiss options
- **Notification Stacking**: Queue management for multiple notifications
- **Progress Updates**: Real-time progress tracking for long-running operations
- **WebSocket Integration**: Real-time notifications via WebSocket events
- **Accessibility**: Full screen reader support and keyboard navigation
- **Responsive Design**: Mobile-friendly notification display
- **Theme Support**: Modern, classic, and minimal themes

## Architecture

### Core Components

1. **NotificationUIRenderer** (`static/js/notification-ui-renderer.js`)
   - Main notification rendering engine
   - Handles display, animations, and lifecycle management

2. **PageNotificationIntegrator** (`static/js/page_notification_integrator.js`)
   - Page-specific notification integration
   - WebSocket event handling

3. **Unified CSS** (`static/css/unified-notifications.css`, `static/css/notification-ui.css`)
   - Consistent styling across all notification types
   - Responsive design and accessibility features

4. **Legacy Migration** (`static/js/legacy-notification-migration.js`)
   - Compatibility layer for legacy notification calls
   - Automatic migration of existing notifications

### Template Integration

#### Base Templates

Both `templates/base.html` and `admin/templates/base_admin.html` include:
- Unified notification CSS
- NotificationUIRenderer JavaScript
- Legacy migration utilities
- Global notification functions

#### Page-Specific Integration

Pages can include specific notification configurations using:
```html
{% set page_id = 'unique-page-id' %}
{% set page_type = 'page_type' %}
{% set notification_config = {
    'enabled_types': ['success', 'error', 'warning', 'info'],
    'auto_hide': true,
    'max_notifications': 5,
    'position': 'top-right'
} %}
{% set websocket_events = ['event1', 'event2'] %}
{% include 'components/page_notification_integration.html' %}
```

## Usage

### Basic Notifications

```javascript
// Show a simple notification
window.showNotification('Operation completed successfully!', 'success');

// Show with custom title
window.showNotification('File uploaded', 'success', 'Upload Complete');

// Show with options
window.showNotification('Processing...', 'info', 'Status', {
    persistent: true,
    priority: 'high'
});
```

### Admin Notifications

```javascript
// Admin-specific notifications
window.showAdminNotification('User created successfully', 'success');

// System alerts
window.showAdminAlert('System maintenance required', 'warning', true);
```

### Progress Notifications

```javascript
// Show progress
const progressId = window.showProgress('upload-task', 'Uploading file...', 25);

// Update progress
window.showProgress('upload-task', 'Processing file...', 75);

// Progress completes automatically at 100%
```

### Legacy Compatibility

The system provides automatic compatibility for legacy notification calls:

```javascript
// These legacy calls are automatically redirected to the unified system
alert('This is an alert');
showAlert('Custom alert', 'warning');
showSuccess('Success message');
showError('Error message');
flash('Flash message', 'info');
```

## Configuration Options

### Notification Types
- `success`: Green, checkmark icon
- `warning`: Yellow, warning triangle icon
- `error`: Red, X circle icon
- `info`: Blue, info circle icon
- `progress`: Purple, spinning arrow icon

### Positions
- `top-right` (default)
- `top-left`
- `top-center`
- `bottom-right`
- `bottom-left`
- `bottom-center`

### Themes
- `modern` (default): Rounded corners, shadows, gradients
- `classic`: Traditional alert styling
- `minimal`: Clean, simple design

### Priority Levels
- `low`: Standard display
- `normal`: Default priority
- `high`: Enhanced visibility
- `critical`: Maximum prominence, persistent

## WebSocket Integration

The system automatically handles WebSocket events for real-time notifications:

```javascript
// WebSocket events are automatically converted to notifications
document.addEventListener('caption_progress', function(event) {
    // Automatically shows progress notification
});

document.addEventListener('system_notification', function(event) {
    // Automatically shows system notification
});
```

## Accessibility Features

- **Screen Reader Support**: All notifications are announced to screen readers
- **Keyboard Navigation**: Full keyboard accessibility
- **High Contrast Mode**: Automatic adaptation for high contrast displays
- **Reduced Motion**: Respects user motion preferences
- **Focus Management**: Proper focus handling for interactive notifications

## Migration from Legacy Systems

### Removed Components

The following legacy components have been removed:
- `admin/templates/components/admin_notification_system.html`
- `static/css/user_profile_notifications.css`
- Legacy alert components in templates
- Custom notification JavaScript implementations

### Template Updates

All templates have been updated to:
- Remove legacy flash message displays
- Include unified notification containers
- Use consistent notification integration
- Provide fallback compatibility

### CSS Updates

Legacy notification CSS has been replaced with:
- `static/css/unified-notifications.css`: Main notification styles
- `static/css/notification-ui.css`: UI component styles
- `static/css/legacy-notification-fallback.css`: Compatibility styles

## Best Practices

### For Developers

1. **Use Appropriate Types**: Choose the correct notification type for the message
2. **Provide Clear Messages**: Write concise, actionable notification text
3. **Set Appropriate Priorities**: Use priority levels to guide user attention
4. **Handle Errors Gracefully**: Always provide error notifications for failed operations
5. **Test Accessibility**: Verify notifications work with screen readers

### For Administrators

1. **Monitor Notification Volume**: Avoid overwhelming users with too many notifications
2. **Use System Alerts Sparingly**: Reserve critical alerts for genuine emergencies
3. **Provide Clear Actions**: Include actionable buttons when appropriate
4. **Test Across Devices**: Verify notifications display correctly on all devices

## Troubleshooting

### Common Issues

1. **Notifications Not Appearing**
   - Check browser console for JavaScript errors
   - Verify NotificationUIRenderer is initialized
   - Ensure CSS files are loaded correctly

2. **Legacy Notifications Still Showing**
   - Check for custom CSS overriding the fallback styles
   - Verify legacy migration script is loaded
   - Look for hardcoded notification HTML in templates

3. **WebSocket Notifications Not Working**
   - Verify WebSocket connection is established
   - Check event listener registration
   - Confirm event data format matches expected structure

### Debug Mode

Enable debug logging:
```javascript
// Enable debug mode for notification system
window.notificationDebug = true;
```

### Browser Compatibility

The unified notification system supports:
- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Performance Considerations

- **Memory Management**: Notifications are automatically cleaned up after dismissal
- **Animation Performance**: CSS transforms used for smooth animations
- **Queue Management**: Automatic queuing prevents notification overflow
- **Lazy Loading**: Notification components loaded only when needed

## Security Considerations

- **XSS Prevention**: All notification content is properly escaped
- **CSRF Protection**: Notification actions include CSRF tokens
- **Input Validation**: Notification data is validated before display
- **Rate Limiting**: Built-in protection against notification spam

## Future Enhancements

Planned improvements include:
- Push notification support for offline users
- Advanced notification scheduling
- User preference management
- Enhanced analytics and tracking
- Additional theme options
- Mobile app integration

## Support

For issues or questions about the unified notification system:
1. Check this documentation
2. Review browser console for errors
3. Test with legacy compatibility mode
4. Verify WebSocket connectivity
5. Check notification system initialization

The unified notification system ensures consistent, accessible, and user-friendly notifications across all of Vedfolnir while maintaining compatibility with existing code during the migration process.