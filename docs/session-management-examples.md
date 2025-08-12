# Session Management Code Examples

This document provides practical code examples for implementing session-aware components and integrating with the Vedfolnir session management system.

## Table of Contents

1. [Basic Session Integration](#basic-session-integration)
2. [Platform-Aware Components](#platform-aware-components)
3. [Cross-Tab Synchronization](#cross-tab-synchronization)
4. [Custom Session Decorators](#custom-session-decorators)
5. [Error Handling Patterns](#error-handling-patterns)
6. [Performance Optimization](#performance-optimization)
7. [Testing Examples](#testing-examples)

## Basic Session Integration

### Simple Flask Route with Session Context

```python
from flask import Flask, jsonify, request
from flask_login import login_required, current_user
from session_manager import get_current_platform_context
from session_aware_decorators import with_db_session

@app.route('/api/user_data')
@login_required
@with_db_session
def get_user_data():
    """Get user data with current platform context"""
    
    # Get current platform context
    context = get_current_platform_context()
    if not context:
        return jsonify({'error': 'No platform context available'}), 400
    
    # Extract platform information
    platform_id = context['platform_connection_id']
    platform_name = context['platform_name']
    user_id = context['user_id']
    
    # Return user data with platform context
    return jsonify({
        'user_id': user_id,
        'platform': {
            'id': platform_id,
            'name': platform_name,
            'type': context.get('platform_type')
        },
        'session_info': {
            'created_at': context.get('created_at'),
            'last_activity': context.get('last_activity')
        }
    })
```

### Creating a New Session

```python
from session_manager import SessionManager
from database import DatabaseManager
from config import Config

def create_user_session_example():
    """Example of creating a new user session"""
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    session_manager = SessionManager(db_manager)
    
    try:
        # Create session for user with specific platform
        session_id = session_manager.create_user_session(
            user_id=123,
            platform_connection_id=456
        )
        
        print(f"Created session: {session_id}")
        
        # Get session context to verify
        context = session_manager.get_session_context(session_id)
        if context:
            print(f"Session created for user {context['user_username']}")
            print(f"Active platform: {context['platform_name']}")
        
        return session_id
        
    except Exception as e:
        print(f"Error creating session: {e}")
        return None
```

## Platform-Aware Components

### Platform-Specific Data Service

```python
from session_manager import get_current_platform_context, get_current_platform
from request_scoped_session_manager import RequestScopedSessionManager
from models import Post, Image, PlatformConnection

class PlatformDataService:
    """Service for handling platform-specific data operations"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.request_session_manager = RequestScopedSessionManager(db_manager)
    
    def get_platform_posts(self, limit=50):
        """Get posts for the current platform"""
        
        # Get current platform context
        context = get_current_platform_context()
        if not context:
            raise ValueError("No platform context available")
        
        platform_id = context['platform_connection_id']
        
        # Use request-scoped session for database operations
        with self.request_session_manager.session_scope() as db_session:
            posts = db_session.query(Post).filter_by(
                platform_connection_id=platform_id
            ).order_by(Post.created_at.desc()).limit(limit).all()
            
            # Convert to dictionaries to avoid DetachedInstanceError
            return [self._post_to_dict(post) for post in posts]
    
    def get_platform_statistics(self):
        """Get statistics for the current platform"""
        
        context = get_current_platform_context()
        if not context:
            raise ValueError("No platform context available")
        
        platform_id = context['platform_connection_id']
        
        with self.request_session_manager.session_scope() as db_session:
            stats = {
                'total_posts': db_session.query(Post).filter_by(
                    platform_connection_id=platform_id
                ).count(),
                'total_images': db_session.query(Image).filter_by(
                    platform_connection_id=platform_id
                ).count(),
                'pending_images': db_session.query(Image).filter_by(
                    platform_connection_id=platform_id,
                    status='pending'
                ).count()
            }
            
            return stats
    
    def switch_platform_context(self, new_platform_id):
        """Switch to a different platform context"""
        
        # Validate platform belongs to current user
        context = get_current_platform_context()
        if not context:
            raise ValueError("No current session context")
        
        user_id = context['user_id']
        
        with self.request_session_manager.session_scope() as db_session:
            platform = db_session.query(PlatformConnection).filter_by(
                id=new_platform_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not platform:
                raise ValueError("Platform not found or not accessible")
        
        # Update session context
        from flask import session
        from session_manager import SessionManager
        
        session_manager = SessionManager(self.db_manager)
        flask_session_id = session.get('_id')
        
        if flask_session_id:
            success = session_manager.update_platform_context(
                flask_session_id, new_platform_id
            )
            if success:
                return True
        
        return False
    
    def _post_to_dict(self, post):
        """Convert post object to dictionary"""
        return {
            'id': post.id,
            'post_url': post.post_url,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'image_count': len(post.images) if post.images else 0
        }

# Usage example
def use_platform_service():
    """Example of using the platform data service"""
    
    service = PlatformDataService(db_manager)
    
    try:
        # Get platform-specific data
        posts = service.get_platform_posts(limit=10)
        stats = service.get_platform_statistics()
        
        print(f"Found {len(posts)} posts")
        print(f"Platform statistics: {stats}")
        
        # Switch platform if needed
        # success = service.switch_platform_context(new_platform_id=789)
        
    except ValueError as e:
        print(f"Platform context error: {e}")
    except Exception as e:
        print(f"Service error: {e}")
```

### Session-Aware Form Handler

```python
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from session_manager import get_current_platform_context

class PlatformAwareForm(FlaskForm):
    """Form that adapts based on current platform context"""
    
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Submit')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Customize form based on platform context
        context = get_current_platform_context()
        if context:
            platform_type = context.get('platform_type')
            
            if platform_type == 'mastodon':
                # Mastodon has character limits
                self.content.validators = [DataRequired(), Length(max=500)]
                self.content.render_kw = {
                    'placeholder': 'What\'s happening? (500 characters max)',
                    'rows': 4
                }
            elif platform_type == 'pixelfed':
                # Pixelfed focuses on images
                self.content.render_kw = {
                    'placeholder': 'Describe your photo...',
                    'rows': 3
                }
    
    def validate_content(self, field):
        """Custom validation based on platform context"""
        context = get_current_platform_context()
        if context:
            platform_type = context.get('platform_type')
            
            if platform_type == 'mastodon' and len(field.data) > 500:
                raise ValidationError('Content too long for Mastodon (500 characters max)')

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
@require_platform_context
def create_post():
    """Create a post with platform-aware form"""
    
    form = PlatformAwareForm()
    
    if form.validate_on_submit():
        context = get_current_platform_context()
        platform_id = context['platform_connection_id']
        
        # Create post with platform context
        post_data = {
            'title': form.title.data,
            'content': form.content.data,
            'platform_connection_id': platform_id,
            'user_id': current_user.id
        }
        
        # Save post logic here
        flash('Post created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('create_post.html', form=form)
```

## Cross-Tab Synchronization

### JavaScript Session Sync Integration

```javascript
class CustomSessionHandler {
    constructor() {
        this.sessionSync = null;
        this.currentPlatform = null;
        this.init();
    }
    
    init() {
        // Wait for SessionSync to be available
        if (window.sessionSync) {
            this.sessionSync = window.sessionSync;
            this.setupEventListeners();
        } else {
            // Retry after DOM is loaded
            document.addEventListener('DOMContentLoaded', () => {
                this.sessionSync = window.sessionSync;
                this.setupEventListeners();
            });
        }
    }
    
    setupEventListeners() {
        // Listen for session state changes
        window.addEventListener('sessionStateChanged', (event) => {
            this.handleSessionStateChange(event.detail);
        });
        
        // Listen for platform switches
        window.addEventListener('platformSwitched', (event) => {
            this.handlePlatformSwitch(event.detail);
        });
        
        // Listen for session expiration
        window.addEventListener('sessionExpired', (event) => {
            this.handleSessionExpired(event.detail);
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.sessionSync) {
                this.sessionSync.syncSessionState();
            }
        });
    }
    
    handleSessionStateChange(sessionState) {
        console.log('Session state changed:', sessionState);
        
        // Update current platform
        this.currentPlatform = sessionState.platform;
        
        // Update UI elements
        this.updatePlatformUI(sessionState.platform);
        this.updateUserUI(sessionState.user);
        
        // Trigger custom events for other components
        this.notifyComponents('sessionUpdated', sessionState);
    }
    
    handlePlatformSwitch(switchEvent) {
        console.log('Platform switched:', switchEvent);
        
        // Show notification
        this.showNotification(
            `Switched to ${switchEvent.platformName}`,
            'info'
        );
        
        // Update platform-specific UI
        this.updatePlatformSpecificElements(switchEvent);
        
        // Refresh platform-dependent data
        this.refreshPlatformData();
    }
    
    handleSessionExpired(expiredEvent) {
        console.log('Session expired:', expiredEvent);
        
        // Clear local data
        this.clearLocalData();
        
        // Show expiration message
        this.showNotification(
            'Your session has expired. Please log in again.',
            'warning',
            5000
        );
        
        // Redirect to login after delay
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }
    
    updatePlatformUI(platform) {
        if (!platform) return;
        
        // Update platform dropdown
        const platformDropdown = document.getElementById('platformsDropdown');
        if (platformDropdown) {
            platformDropdown.textContent = `Platform: ${platform.name}`;
        }
        
        // Update platform-specific navigation
        const platformNavItems = document.querySelectorAll('[data-platform-required]');
        platformNavItems.forEach(item => {
            item.style.display = platform ? 'block' : 'none';
        });
        
        // Update platform type indicators
        const platformTypeElements = document.querySelectorAll('[data-platform-type]');
        platformTypeElements.forEach(element => {
            element.setAttribute('data-platform-type', platform.type);
            element.classList.toggle('mastodon-platform', platform.type === 'mastodon');
            element.classList.toggle('pixelfed-platform', platform.type === 'pixelfed');
        });
    }
    
    updateUserUI(user) {
        if (!user) return;
        
        // Update user display elements
        const userElements = document.querySelectorAll('[data-user-info]');
        userElements.forEach(element => {
            const infoType = element.getAttribute('data-user-info');
            if (infoType === 'username' && user.username) {
                element.textContent = user.username;
            } else if (infoType === 'email' && user.email) {
                element.textContent = user.email;
            }
        });
    }
    
    updatePlatformSpecificElements(switchEvent) {
        // Update forms based on platform
        const forms = document.querySelectorAll('form[data-platform-aware]');
        forms.forEach(form => {
            this.updateFormForPlatform(form, switchEvent.platformId);
        });
        
        // Update character counters
        const textareas = document.querySelectorAll('textarea[data-char-limit]');
        textareas.forEach(textarea => {
            this.updateCharacterLimit(textarea, switchEvent.platformType);
        });
    }
    
    updateFormForPlatform(form, platformId) {
        // Update hidden platform ID fields
        const platformIdInputs = form.querySelectorAll('input[name="platform_id"]');
        platformIdInputs.forEach(input => {
            input.value = platformId;
        });
        
        // Update form action URLs if needed
        const currentAction = form.getAttribute('action');
        if (currentAction && currentAction.includes('/platform/')) {
            const newAction = currentAction.replace(/\/platform\/\d+/, `/platform/${platformId}`);
            form.setAttribute('action', newAction);
        }
    }
    
    updateCharacterLimit(textarea, platformType) {
        const limits = {
            'mastodon': 500,
            'pixelfed': 2200
        };
        
        const limit = limits[platformType] || 1000;
        textarea.setAttribute('maxlength', limit);
        
        // Update character counter if present
        const counter = textarea.parentElement.querySelector('.char-counter');
        if (counter) {
            counter.setAttribute('data-max', limit);
            this.updateCharacterCounter(textarea, counter);
        }
    }
    
    updateCharacterCounter(textarea, counter) {
        const maxLength = parseInt(counter.getAttribute('data-max')) || 1000;
        const currentLength = textarea.value.length;
        const remaining = maxLength - currentLength;
        
        counter.textContent = `${remaining} characters remaining`;
        counter.classList.toggle('text-warning', remaining < 50);
        counter.classList.toggle('text-danger', remaining < 10);
    }
    
    refreshPlatformData() {
        // Refresh platform-specific data
        const dataElements = document.querySelectorAll('[data-auto-refresh]');
        dataElements.forEach(element => {
            const refreshUrl = element.getAttribute('data-refresh-url');
            if (refreshUrl) {
                this.loadElementData(element, refreshUrl);
            }
        });
    }
    
    async loadElementData(element, url) {
        try {
            const response = await fetch(url, {
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.html) {
                    element.innerHTML = data.html;
                }
            }
        } catch (error) {
            console.error('Error refreshing element data:', error);
        }
    }
    
    notifyComponents(eventType, data) {
        // Dispatch custom events for other components
        const customEvent = new CustomEvent(eventType, {
            detail: data,
            bubbles: true
        });
        document.dispatchEvent(customEvent);
    }
    
    showNotification(message, type = 'info', duration = 3000) {
        // Use global notification system if available
        if (window.notificationSystem) {
            window.notificationSystem.show(message, type, duration);
            return;
        }
        
        // Fallback notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 1060;
            min-width: 300px;
        `;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }
    }
    
    clearLocalData() {
        // Clear session-related local storage
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('vedfolnir_')) {
                keysToRemove.push(key);
            }
        }
        
        keysToRemove.forEach(key => {
            localStorage.removeItem(key);
        });
    }
    
    // Public methods for manual control
    async switchPlatform(platformId) {
        try {
            const response = await fetch(`/api/switch_platform/${platformId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Notify other tabs
                if (this.sessionSync) {
                    this.sessionSync.notifyPlatformSwitch(
                        platformId,
                        result.platform.name
                    );
                }
                return true;
            } else {
                this.showNotification(result.error || 'Failed to switch platform', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error switching platform:', error);
            this.showNotification('Network error switching platform', 'error');
            return false;
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// Initialize custom session handler
const customSessionHandler = new CustomSessionHandler();

// Make it globally available
window.customSessionHandler = customSessionHandler;
```

### Platform Switch Component

```javascript
class PlatformSwitcher {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentPlatform = null;
        this.platforms = [];
        this.init();
    }
    
    init() {
        this.loadPlatforms();
        this.setupEventListeners();
    }
    
    async loadPlatforms() {
        try {
            const response = await fetch('/api/user_platforms', {
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.platforms = data.platforms;
                this.currentPlatform = data.current_platform;
                this.render();
            }
        } catch (error) {
            console.error('Error loading platforms:', error);
        }
    }
    
    setupEventListeners() {
        // Listen for platform switches from other tabs
        window.addEventListener('platformSwitched', (event) => {
            this.currentPlatform = {
                id: event.detail.platformId,
                name: event.detail.platformName
            };
            this.render();
        });
    }
    
    render() {
        if (!this.container) return;
        
        const html = `
            <div class="dropdown">
                <button class="btn btn-outline-primary dropdown-toggle" type="button" 
                        id="platformDropdown" data-bs-toggle="dropdown">
                    ${this.currentPlatform ? this.currentPlatform.name : 'Select Platform'}
                </button>
                <ul class="dropdown-menu">
                    ${this.platforms.map(platform => `
                        <li>
                            <a class="dropdown-item ${platform.id === this.currentPlatform?.id ? 'active' : ''}" 
                               href="#" data-platform-id="${platform.id}">
                                <i class="fas fa-${this.getPlatformIcon(platform.platform_type)}"></i>
                                ${platform.name}
                                ${platform.is_default ? '<span class="badge bg-primary ms-2">Default</span>' : ''}
                            </a>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
        
        this.container.innerHTML = html;
        
        // Add click handlers
        this.container.querySelectorAll('[data-platform-id]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const platformId = parseInt(link.getAttribute('data-platform-id'));
                this.switchToPlatform(platformId);
            });
        });
    }
    
    async switchToPlatform(platformId) {
        if (platformId === this.currentPlatform?.id) return;
        
        // Show loading state
        const button = this.container.querySelector('#platformDropdown');
        const originalText = button.textContent;
        button.textContent = 'Switching...';
        button.disabled = true;
        
        try {
            const success = await window.customSessionHandler.switchPlatform(platformId);
            
            if (success) {
                // Update current platform
                const platform = this.platforms.find(p => p.id === platformId);
                if (platform) {
                    this.currentPlatform = platform;
                    this.render();
                }
            }
        } catch (error) {
            console.error('Error switching platform:', error);
        } finally {
            // Restore button state
            button.textContent = originalText;
            button.disabled = false;
        }
    }
    
    getPlatformIcon(platformType) {
        const icons = {
            'mastodon': 'mastodon',
            'pixelfed': 'camera',
            'default': 'globe'
        };
        return icons[platformType] || icons.default;
    }
}

// Initialize platform switcher
document.addEventListener('DOMContentLoaded', () => {
    new PlatformSwitcher('platform-switcher-container');
});
```

## Custom Session Decorators

### Advanced Session Decorator

```python
from functools import wraps
from flask import request, jsonify, g
from flask_login import current_user
from session_manager import get_current_platform_context, SessionManager
from database import DatabaseManager

def require_session_context(require_platform=True, allow_expired=False):
    """
    Advanced decorator that ensures proper session context
    
    Args:
        require_platform: Whether platform context is required
        allow_expired: Whether to allow expired sessions (for cleanup operations)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check authentication
            if not current_user or not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login'))
            
            # Get session context
            context = get_current_platform_context()
            
            if not context:
                if request.is_json:
                    return jsonify({'error': 'No session context available'}), 400
                flash('Session context not available. Please log in again.', 'error')
                return redirect(url_for('login'))
            
            # Check if platform is required
            if require_platform and not context.get('platform_connection_id'):
                if request.is_json:
                    return jsonify({'error': 'Platform context required'}), 400
                flash('Please select a platform to continue.', 'warning')
                return redirect(url_for('platform_management'))
            
            # Validate session if not allowing expired
            if not allow_expired:
                session_manager = SessionManager(DatabaseManager())
                session_id = context.get('session_id')
                user_id = context.get('user_id')
                
                if session_id and user_id:
                    is_valid = session_manager.validate_session(session_id, user_id)
                    if not is_valid:
                        if request.is_json:
                            return jsonify({'error': 'Session expired'}), 401
                        flash('Your session has expired. Please log in again.', 'warning')
                        return redirect(url_for('login'))
            
            # Store context in g for use in the route
            g.session_context = context
            g.platform_id = context.get('platform_connection_id')
            g.platform_name = context.get('platform_name')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage examples
@app.route('/api/platform_data')
@require_session_context(require_platform=True)
def get_platform_data():
    """Route that requires platform context"""
    platform_id = g.platform_id
    platform_name = g.platform_name
    
    return jsonify({
        'platform_id': platform_id,
        'platform_name': platform_name,
        'data': 'platform-specific data here'
    })

@app.route('/api/cleanup_sessions')
@require_session_context(require_platform=False, allow_expired=True)
def cleanup_sessions():
    """Route that allows expired sessions for cleanup"""
    # Cleanup logic here
    return jsonify({'message': 'Sessions cleaned up'})
```

### Performance Monitoring Decorator

```python
import time
from functools import wraps
from flask import g, request
from session_performance_monitor import get_performance_monitor

def monitor_session_performance(operation_name=None):
    """Decorator to monitor session-related operation performance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get operation name
            op_name = operation_name or f.__name__
            
            # Start timing
            start_time = time.time()
            
            try:
                # Execute function
                result = f(*args, **kwargs)
                
                # Record successful operation
                duration = time.time() - start_time
                monitor = get_performance_monitor()
                if monitor:
                    monitor.record_operation_success(op_name, duration)
                
                return result
                
            except Exception as e:
                # Record failed operation
                duration = time.time() - start_time
                monitor = get_performance_monitor()
                if monitor:
                    monitor.record_operation_error(op_name, duration, str(e))
                
                raise
                
        return decorated_function
    return decorator

# Usage example
@app.route('/api/switch_platform/<int:platform_id>', methods=['POST'])
@login_required
@monitor_session_performance('platform_switch')
@require_session_context()
def switch_platform_monitored(platform_id):
    """Platform switch with performance monitoring"""
    # Platform switch logic here
    return jsonify({'success': True})
```

## Error Handling Patterns

### Comprehensive Error Handler

```python
from flask import jsonify, request, current_app
from session_manager import SessionError, SessionDatabaseError
from sqlalchemy.exc import SQLAlchemyError

class SessionErrorHandler:
    """Centralized session error handling"""
    
    @staticmethod
    def handle_session_error(error, context=None):
        """Handle session-related errors with appropriate responses"""
        
        error_info = {
            'error_type': type(error).__name__,
            'message': str(error),
            'context': context or {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Log error
        current_app.logger.error(f"Session error: {error_info}")
        
        # Determine response based on error type
        if isinstance(error, SessionDatabaseError):
            return SessionErrorHandler._handle_database_error(error, error_info)
        elif isinstance(error, SessionError):
            return SessionErrorHandler._handle_session_error(error, error_info)
        elif isinstance(error, SQLAlchemyError):
            return SessionErrorHandler._handle_sqlalchemy_error(error, error_info)
        else:
            return SessionErrorHandler._handle_generic_error(error, error_info)
    
    @staticmethod
    def _handle_database_error(error, error_info):
        """Handle database-specific session errors"""
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Database error occurred',
                'error_code': 'DATABASE_ERROR',
                'retry_after': 30
            }), 503
        else:
            flash('Database error occurred. Please try again later.', 'error')
            return redirect(url_for('index'))
    
    @staticmethod
    def _handle_session_error(error, error_info):
        """Handle general session errors"""
        if 'expired' in str(error).lower():
            return SessionErrorHandler._handle_expired_session()
        elif 'invalid' in str(error).lower():
            return SessionErrorHandler._handle_invalid_session()
        else:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Session error occurred',
                    'error_code': 'SESSION_ERROR'
                }), 400
            else:
                flash('Session error occurred. Please try again.', 'error')
                return redirect(url_for('index'))
    
    @staticmethod
    def _handle_expired_session():
        """Handle expired session specifically"""
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Session expired',
                'error_code': 'SESSION_EXPIRED',
                'redirect_url': '/login'
            }), 401
        else:
            flash('Your session has expired. Please log in again.', 'warning')
            return redirect(url_for('login'))
    
    @staticmethod
    def _handle_invalid_session():
        """Handle invalid session specifically"""
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Invalid session',
                'error_code': 'SESSION_INVALID',
                'redirect_url': '/login'
            }), 401
        else:
            flash('Invalid session. Please log in again.', 'error')
            return redirect(url_for('login'))
    
    @staticmethod
    def _handle_sqlalchemy_error(error, error_info):
        """Handle SQLAlchemy errors"""
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Database operation failed',
                'error_code': 'DATABASE_OPERATION_ERROR'
            }), 500
        else:
            flash('Database operation failed. Please try again.', 'error')
            return redirect(url_for('index'))
    
    @staticmethod
    def _handle_generic_error(error, error_info):
        """Handle generic errors"""
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'An unexpected error occurred',
                'error_code': 'GENERIC_ERROR'
            }), 500
        else:
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('index'))

# Error handler decorator
def handle_session_errors(f):
    """Decorator to automatically handle session errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (SessionError, SessionDatabaseError, SQLAlchemyError) as e:
            return SessionErrorHandler.handle_session_error(e, {
                'function': f.__name__,
                'args': args,
                'kwargs': kwargs
            })
    return decorated_function

# Usage example
@app.route('/api/session_operation')
@login_required
@handle_session_errors
def session_operation():
    """Route with automatic error handling"""
    # Session operation that might fail
    context = get_current_platform_context()
    if not context:
        raise SessionError("No session context available")
    
    return jsonify({'success': True, 'context': context})
```

## Performance Optimization

### Session Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta
import threading

class SessionCache:
    """Thread-safe session context cache"""
    
    def __init__(self, cache_ttl_seconds=300):  # 5 minutes default
        self.cache = {}
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.lock = threading.RLock()
    
    def get(self, session_id):
        """Get cached session context"""
        with self.lock:
            if session_id in self.cache:
                context, timestamp = self.cache[session_id]
                
                # Check if cache is still valid
                if datetime.now() - timestamp < self.cache_ttl:
                    return context
                else:
                    # Remove expired entry
                    del self.cache[session_id]
            
            return None
    
    def set(self, session_id, context):
        """Cache session context"""
        with self.lock:
            self.cache[session_id] = (context, datetime.now())
    
    def invalidate(self, session_id):
        """Invalidate cached session"""
        with self.lock:
            if session_id in self.cache:
                del self.cache[session_id]
    
    def clear(self):
        """Clear all cached sessions"""
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self):
        """Remove expired cache entries"""
        with self.lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if now - timestamp >= self.cache_ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)

# Global cache instance
session_cache = SessionCache()

# Enhanced session manager with caching
class CachedSessionManager(SessionManager):
    """Session manager with caching support"""
    
    def get_session_context(self, session_id):
        """Get session context with caching"""
        
        # Try cache first
        cached_context = session_cache.get(session_id)
        if cached_context:
            return cached_context
        
        # Get from database
        context = super().get_session_context(session_id)
        
        # Cache the result
        if context:
            session_cache.set(session_id, context)
        
        return context
    
    def update_platform_context(self, session_id, platform_connection_id):
        """Update platform context and invalidate cache"""
        
        # Update in database
        success = super().update_platform_context(session_id, platform_connection_id)
        
        # Invalidate cache
        if success:
            session_cache.invalidate(session_id)
        
        return success
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions and cache"""
        
        # Clean up database sessions
        count = super().cleanup_expired_sessions()
        
        # Clean up cache
        cache_cleaned = session_cache.cleanup_expired()
        
        if cache_cleaned > 0:
            self.logger.debug(f"Cleaned up {cache_cleaned} expired cache entries")
        
        return count

# Usage example
def use_cached_session_manager():
    """Example using cached session manager"""
    
    cached_manager = CachedSessionManager(db_manager)
    
    # This will hit the database
    context1 = cached_manager.get_session_context("session123")
    
    # This will hit the cache
    context2 = cached_manager.get_session_context("session123")
    
    print(f"Contexts equal: {context1 == context2}")
```

### Batch Operations

```python
class BatchSessionOperations:
    """Efficient batch operations for session management"""
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
    
    def batch_validate_sessions(self, session_user_pairs, batch_size=50):
        """Validate multiple sessions efficiently"""
        
        results = {}
        
        # Process in batches to avoid overwhelming the database
        for i in range(0, len(session_user_pairs), batch_size):
            batch = session_user_pairs[i:i + batch_size]
            batch_results = self._validate_session_batch(batch)
            results.update(batch_results)
        
        return results
    
    def _validate_session_batch(self, session_user_pairs):
        """Validate a batch of sessions"""
        
        results = {}
        
        with self.session_manager.get_db_session() as db_session:
            # Get all session IDs in this batch
            session_ids = [pair[0] for pair in session_user_pairs]
            
            # Query all sessions at once
            from models import UserSession
            sessions = db_session.query(UserSession).filter(
                UserSession.session_id.in_(session_ids)
            ).all()
            
            # Create lookup dictionary
            session_lookup = {s.session_id: s for s in sessions}
            
            # Validate each session
            for session_id, user_id in session_user_pairs:
                session_obj = session_lookup.get(session_id)
                
                if session_obj and session_obj.user_id == user_id:
                    is_expired = self.session_manager._is_session_expired(session_obj)
                    results[session_id] = not is_expired
                else:
                    results[session_id] = False
        
        return results
    
    def batch_cleanup_user_sessions(self, user_ids, batch_size=20):
        """Clean up sessions for multiple users efficiently"""
        
        total_cleaned = 0
        
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            batch_cleaned = self._cleanup_user_batch(batch)
            total_cleaned += batch_cleaned
        
        return total_cleaned
    
    def _cleanup_user_batch(self, user_ids):
        """Clean up sessions for a batch of users"""
        
        with self.session_manager.get_db_session() as db_session:
            from models import UserSession
            
            # Find expired sessions for these users
            cutoff_time = datetime.now(timezone.utc) - self.session_manager.session_timeout
            
            expired_sessions = db_session.query(UserSession).filter(
                UserSession.user_id.in_(user_ids),
                UserSession.updated_at < cutoff_time
            ).all()
            
            # Delete expired sessions
            count = 0
            for session_obj in expired_sessions:
                db_session.delete(session_obj)
                count += 1
            
            return count

# Usage example
def use_batch_operations():
    """Example using batch session operations"""
    
    batch_ops = BatchSessionOperations(session_manager)
    
    # Validate multiple sessions
    session_pairs = [
        ("session1", 123),
        ("session2", 124),
        ("session3", 125)
    ]
    
    validation_results = batch_ops.batch_validate_sessions(session_pairs)
    print(f"Validation results: {validation_results}")
    
    # Cleanup sessions for multiple users
    user_ids = [123, 124, 125, 126]
    cleaned_count = batch_ops.batch_cleanup_user_sessions(user_ids)
    print(f"Cleaned up {cleaned_count} sessions")
```

## Testing Examples

### Unit Test Examples

```python
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from session_manager import SessionManager, SessionError, SessionDatabaseError

class TestSessionManager(unittest.TestCase):
    """Comprehensive unit tests for SessionManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_config = Mock()
        self.mock_config.timeout.session_lifetime = timedelta(hours=24)
        self.mock_config.timeout.idle_timeout = timedelta(hours=12)
        
        self.session_manager = SessionManager(self.mock_db_manager, self.mock_config)
    
    def test_create_user_session_success(self):
        """Test successful session creation"""
        # Mock database session
        mock_db_session = Mock()
        mock_user = Mock()
        mock_user.id = 123
        mock_user.is_active = True
        mock_platform = Mock()
        mock_platform.id = 456
        
        mock_db_session.query.return_value.get.return_value = mock_user
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_platform
        
        self.mock_db_manager.get_session.return_value = mock_db_session
        
        # Test session creation
        session_id = self.session_manager.create_user_session(123, 456)
        
        # Verify results
        self.assertIsNotNone(session_id)
        self.assertIsInstance(session_id, str)
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_create_user_session_invalid_user(self):
        """Test session creation with invalid user"""
        # Mock database session
        mock_db_session = Mock()
        mock_db_session.query.return_value.get.return_value = None
        
        self.mock_db_manager.get_session.return_value = mock_db_session
        
        # Test session creation should raise error
        with self.assertRaises(ValueError):
            self.session_manager.create_user_session(999, 456)
    
    def test_get_session_context_success(self):
        """Test successful session context retrieval"""
        # Mock database session and objects
        mock_db_session = Mock()
        mock_user_session = Mock()
        mock_user = Mock()
        mock_platform = Mock()
        
        # Set up mock objects
        mock_user_session.user = mock_user
        mock_user_session.active_platform = mock_platform
        mock_user_session.created_at = datetime.now(timezone.utc)
        mock_user_session.updated_at = datetime.now(timezone.utc)
        
        mock_user.id = 123
        mock_user.username = "testuser"
        mock_platform.id = 456
        mock_platform.name = "Test Platform"
        mock_platform.platform_type = "pixelfed"
        
        mock_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user_session
        
        # Mock context manager
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_db_session)
        context_manager.__exit__ = Mock(return_value=None)
        self.session_manager.get_db_session = Mock(return_value=context_manager)
        
        # Test getting session context
        context = self.session_manager.get_session_context("test-session")
        
        # Verify results
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], 123)
        self.assertEqual(context['user_username'], "testuser")
        self.assertEqual(context['platform_connection_id'], 456)
        self.assertEqual(context['platform_name'], "Test Platform")
    
    def test_get_session_context_not_found(self):
        """Test session context retrieval when session not found"""
        # Mock database session
        mock_db_session = Mock()
        mock_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = None
        
        # Mock context manager
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_db_session)
        context_manager.__exit__ = Mock(return_value=None)
        self.session_manager.get_db_session = Mock(return_value=context_manager)
        
        # Test getting session context
        context = self.session_manager.get_session_context("nonexistent-session")
        
        # Verify results
        self.assertIsNone(context)
    
    def test_update_platform_context_success(self):
        """Test successful platform context update"""
        # Mock database session
        mock_db_session = Mock()
        mock_user_session = Mock()
        mock_user_session.user_id = 123
        mock_platform = Mock()
        mock_platform.id = 789
        mock_platform.name = "New Platform"
        
        mock_db_session.query.return_value.filter_by.side_effect = [
            Mock(first=Mock(return_value=mock_user_session)),  # For user session
            Mock(first=Mock(return_value=mock_platform))       # For platform
        ]
        
        self.mock_db_manager.get_session.return_value = mock_db_session
        
        # Mock session expiration check
        with patch.object(self.session_manager, '_is_session_expired', return_value=False):
            # Test platform context update
            success = self.session_manager.update_platform_context("test-session", 789)
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(mock_user_session.active_platform_id, 789)
        mock_db_session.commit.assert_called_once()
    
    def test_validate_session_success(self):
        """Test successful session validation"""
        # Mock get_session_context
        mock_context = {
            'user_id': 123,
            'session_id': 'test-session',
            'platform_connection_id': 456
        }
        
        with patch.object(self.session_manager, 'get_session_context', return_value=mock_context):
            with patch.object(self.session_manager, '_validate_session_security', return_value=True):
                # Test session validation
                is_valid = self.session_manager.validate_session('test-session', 123)
        
        # Verify results
        self.assertTrue(is_valid)
    
    def test_validate_session_user_mismatch(self):
        """Test session validation with user ID mismatch"""
        # Mock get_session_context
        mock_context = {
            'user_id': 123,
            'session_id': 'test-session',
            'platform_connection_id': 456
        }
        
        with patch.object(self.session_manager, 'get_session_context', return_value=mock_context):
            # Test session validation with wrong user ID
            is_valid = self.session_manager.validate_session('test-session', 999)
        
        # Verify results
        self.assertFalse(is_valid)
    
    def test_cleanup_expired_sessions(self):
        """Test expired session cleanup"""
        # Mock batch cleanup
        with patch.object(self.session_manager, 'batch_cleanup_sessions', return_value=5):
            # Test cleanup
            count = self.session_manager.cleanup_expired_sessions()
        
        # Verify results
        self.assertEqual(count, 5)
    
    @patch('session_manager.datetime')
    def test_is_session_expired_idle_timeout(self, mock_datetime):
        """Test session expiration due to idle timeout"""
        # Set up mock datetime
        now = datetime.now(timezone.utc)
        mock_datetime.now.return_value = now
        
        # Create mock session that's been idle too long
        mock_session = Mock()
        mock_session.updated_at = now - timedelta(hours=13)  # Longer than 12-hour idle timeout
        mock_session.created_at = now - timedelta(hours=13)
        
        # Test expiration check
        is_expired = self.session_manager._is_session_expired(mock_session)
        
        # Verify results
        self.assertTrue(is_expired)
    
    @patch('session_manager.datetime')
    def test_is_session_expired_absolute_timeout(self, mock_datetime):
        """Test session expiration due to absolute timeout"""
        # Set up mock datetime
        now = datetime.now(timezone.utc)
        mock_datetime.now.return_value = now
        
        # Create mock session that's too old
        mock_session = Mock()
        mock_session.updated_at = now - timedelta(hours=1)   # Recent activity
        mock_session.created_at = now - timedelta(hours=25)  # Longer than 24-hour absolute timeout
        
        # Test expiration check
        is_expired = self.session_manager._is_session_expired(mock_session)
        
        # Verify results
        self.assertTrue(is_expired)
    
    def test_database_error_handling(self):
        """Test database error handling"""
        # Mock database session that raises an error
        mock_db_session = Mock()
        mock_db_session.query.side_effect = Exception("Database connection failed")
        
        # Mock context manager
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_db_session)
        context_manager.__exit__ = Mock(return_value=None)
        self.session_manager.get_db_session = Mock(return_value=context_manager)
        
        # Test that database errors are handled gracefully
        context = self.session_manager.get_session_context("test-session")
        
        # Verify results
        self.assertIsNone(context)

if __name__ == '__main__':
    unittest.main()
```

### Integration Test Examples

```python
import unittest
from flask import Flask
from flask_login import LoginManager, login_user
from session_manager import SessionManager
from flask_session_manager import FlaskSessionManager
from models import User, PlatformConnection

class TestSessionIntegration(unittest.TestCase):
    """Integration tests for session management system"""
    
    def setUp(self):
        """Set up test Flask app and session managers"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Initialize Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        
        # Initialize session managers
        self.session_manager = SessionManager(db_manager)
        self.flask_session_manager = FlaskSessionManager(db_manager)
        
        self.client = self.app.test_client()
    
    def test_login_creates_session(self):
        """Test that login creates proper session records"""
        with self.app.test_request_context():
            # Create test user and platform
            user = self.create_test_user()
            platform = self.create_test_platform(user.id)
            
            # Simulate login
            session_id = self.session_manager.create_user_session(user.id, platform.id)
            
            # Verify session was created
            self.assertIsNotNone(session_id)
            
            # Verify session context
            context = self.session_manager.get_session_context(session_id)
            self.assertIsNotNone(context)
            self.assertEqual(context['user_id'], user.id)
            self.assertEqual(context['platform_connection_id'], platform.id)
    
    def test_platform_switch_updates_context(self):
        """Test that platform switching updates session context"""
        with self.app.test_request_context():
            # Create test user and platforms
            user = self.create_test_user()
            platform1 = self.create_test_platform(user.id, name="Platform 1")
            platform2 = self.create_test_platform(user.id, name="Platform 2")
            
            # Create session with first platform
            session_id = self.session_manager.create_user_session(user.id, platform1.id)
            
            # Switch to second platform
            success = self.session_manager.update_platform_context(session_id, platform2.id)
            self.assertTrue(success)
            
            # Verify context was updated
            context = self.session_manager.get_session_context(session_id)
            self.assertEqual(context['platform_connection_id'], platform2.id)
            self.assertEqual(context['platform_name'], "Platform 2")
    
    def test_session_expiration_cleanup(self):
        """Test that expired sessions are properly cleaned up"""
        with self.app.test_request_context():
            # Create test user and platform
            user = self.create_test_user()
            platform = self.create_test_platform(user.id)
            
            # Create session
            session_id = self.session_manager.create_user_session(user.id, platform.id)
            
            # Verify session exists
            context = self.session_manager.get_session_context(session_id)
            self.assertIsNotNone(context)
            
            # Mock session as expired
            with patch.object(self.session_manager, '_is_session_expired', return_value=True):
                # Try to get context of expired session
                context = self.session_manager.get_session_context(session_id)
                self.assertIsNone(context)
    
    def test_cross_tab_synchronization(self):
        """Test session synchronization across multiple tabs"""
        with self.app.test_request_context():
            # Create test user and platforms
            user = self.create_test_user()
            platform1 = self.create_test_platform(user.id, name="Platform 1")
            platform2 = self.create_test_platform(user.id, name="Platform 2")
            
            # Create session (simulating first tab)
            session_id = self.session_manager.create_user_session(user.id, platform1.id)
            
            # Switch platform in "second tab"
            success = self.session_manager.update_platform_context(session_id, platform2.id)
            self.assertTrue(success)
            
            # Verify "first tab" sees the change
            context = self.session_manager.get_session_context(session_id)
            self.assertEqual(context['platform_connection_id'], platform2.id)
    
    def test_session_security_validation(self):
        """Test session security validation"""
        with self.app.test_request_context():
            # Create test user and platform
            user = self.create_test_user()
            platform = self.create_test_platform(user.id)
            
            # Create session
            session_id = self.session_manager.create_user_session(user.id, platform.id)
            
            # Test valid session
            is_valid = self.session_manager.validate_session(session_id, user.id)
            self.assertTrue(is_valid)
            
            # Test invalid user ID
            is_valid = self.session_manager.validate_session(session_id, 999)
            self.assertFalse(is_valid)
            
            # Test invalid session ID
            is_valid = self.session_manager.validate_session("invalid-session", user.id)
            self.assertFalse(is_valid)
    
    def create_test_user(self):
        """Create a test user"""
        with db_manager.get_session() as db_session:
            user = User(
                username="testuser",
                email="test@example.com",
                is_active=True
            )
            user.set_password("testpassword")
            
            db_session.add(user)
            db_session.commit()
            
            return user
    
    def create_test_platform(self, user_id, name="Test Platform"):
        """Create a test platform connection"""
        with db_manager.get_session() as db_session:
            platform = PlatformConnection(
                user_id=user_id,
                name=name,
                platform_type="pixelfed",
                instance_url="https://test.pixelfed.social",
                username="testuser",
                access_token="test-token",
                is_active=True
            )
            
            db_session.add(platform)
            db_session.commit()
            
            return platform

if __name__ == '__main__':
    unittest.main()
```

These comprehensive code examples demonstrate how to implement session-aware components, handle cross-tab synchronization, create custom decorators, implement error handling, optimize performance, and write thorough tests for the session management system.