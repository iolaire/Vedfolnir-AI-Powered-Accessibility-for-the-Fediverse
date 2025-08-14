# web_app

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/web_app.py`

## Classes

### LoginForm

```python
class LoginForm(FlaskForm)
```

Form for user login

**Class Variables:**
- `username`
- `password`
- `remember`
- `submit`

### UserForm

```python
class UserForm(FlaskForm)
```

Base form for user management

**Class Variables:**
- `username`
- `email`
- `password`
- `confirm_password`
- `role`



### EditUserForm

```python
class EditUserForm(UserForm)
```

Form for editing an existing user

**Class Variables:**
- `user_id`
- `is_active`
- `submit`

### DeleteUserForm

```python
class DeleteUserForm(FlaskForm)
```

Form for deleting a user

**Class Variables:**
- `user_id`
- `submit`

### ReviewForm

```python
class ReviewForm(FlaskForm)
```

Form for reviewing image captions

**Class Variables:**
- `image_id`
- `caption`
- `action`
- `notes`
- `submit`

### CaptionGenerationForm

```python
class CaptionGenerationForm(FlaskForm)
```

Form for starting caption generation

**Class Variables:**
- `max_posts_per_run`
- `max_caption_length`
- `optimal_min_length`
- `optimal_max_length`
- `reprocess_existing`
- `processing_delay`
- `submit`

### CaptionSettingsForm

```python
class CaptionSettingsForm(FlaskForm)
```

Form for managing caption generation settings

**Class Variables:**
- `max_posts_per_run`
- `max_caption_length`
- `optimal_min_length`
- `optimal_max_length`
- `reprocess_existing`
- `processing_delay`
- `submit`

## Functions

### add_security_headers

```python
def add_security_headers(response)
```

Add comprehensive security headers to all responses

**Decorators:**
- `@app.after_request`

### validate_favicon_assets

```python
def validate_favicon_assets()
```

Validate that required favicon and logo assets exist

### inject_config

```python
def inject_config()
```

**Decorators:**
- `@app.context_processor`

### load_user

```python
def load_user(user_id)
```

Load user for Flask-Login with proper session attachment to prevent DetachedInstanceError.
Returns SessionAwareUser instance that maintains session context throughout request.
Only returns active users as required by Flask-Login security best practices.

**Decorators:**
- `@login_manager.user_loader`

### role_required

```python
def role_required(role)
```

### platform_required

```python
def platform_required(f)
```

Decorator to ensure user has at least one active platform connection

### platform_access_required

```python
def platform_access_required(platform_type, instance_url)
```

Decorator to validate access to specific platform type or instance

### nl2br_filter

```python
def nl2br_filter(text)
```

Convert newlines to <br> tags

**Decorators:**
- `@app.template_filter('nl2br')`

### inject_user_role

```python
def inject_user_role()
```

Make UserRole available in all templates

**Decorators:**
- `@app.context_processor`

### login

```python
def login()
```

User login with integrated session management system

**Decorators:**
- `@app.route('/login', methods=['GET', 'POST'])`
- `@rate_limit(limit=10, window_seconds=300)`
- `@validate_input_length()`
- `@with_session_error_handling`

### first_time_setup

```python
def first_time_setup()
```

First-time platform setup for new users

**Decorators:**
- `@app.route('/first_time_setup')`
- `@login_required`
- `@with_session_error_handling`

### logout

```python
def logout()
```

User logout with integrated session management - cleans up all session data and notifies tabs

**Decorators:**
- `@app.route('/logout')`
- `@login_required`

### logout_all

```python
def logout_all()
```

Logout from all sessions with integrated session management

**Decorators:**
- `@app.route('/logout_all')`
- `@login_required`

### app_management

```python
def app_management()
```

App management interface for administrators

**Decorators:**
- `@app.route('/app_management')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### user_management

```python
def user_management()
```

User management interface

**Decorators:**
- `@app.route('/user_management')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`



### edit_user

```python
def edit_user()
```

Edit an existing user

**Decorators:**
- `@app.route('/edit_user', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@require_secure_connection`
- `@validate_input_length()`
- `@enhanced_input_validation`
- `@with_session_error_handling`

### delete_user

```python
def delete_user()
```

Delete a user

**Decorators:**
- `@app.route('/delete_user', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@require_secure_connection`
- `@with_session_error_handling`

### health_check

```python
def health_check()
```

Basic health check endpoint

**Decorators:**
- `@app.route('/health')`
- `@login_required`

### health_check_detailed

```python
def health_check_detailed()
```

Detailed health check endpoint including session management

**Decorators:**
- `@app.route('/health/detailed')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### health_dashboard

```python
def health_dashboard()
```

Health dashboard for system administrators

**Decorators:**
- `@app.route('/health/dashboard')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### health_check_component

```python
def health_check_component(component_name)
```

Health check for a specific component

**Decorators:**
- `@app.route('/health/components/<component_name>')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### index

```python
def index()
```

Main dashboard with platform-aware statistics and session management

**Decorators:**
- `@app.route('/')`
- `@login_required`
- `@with_db_session`
- `@require_platform_context`
- `@with_session_error_handling`

### admin_cleanup

```python
def admin_cleanup()
```

Admin interface for data cleanup

**Decorators:**
- `@app.route('/admin/cleanup')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### admin_cleanup_runs

```python
def admin_cleanup_runs()
```

Archive old processing runs

**Decorators:**
- `@app.route('/admin/cleanup/runs', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### admin_cleanup_images

```python
def admin_cleanup_images()
```

Clean up old images

**Decorators:**
- `@app.route('/admin/cleanup/images', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### admin_cleanup_posts

```python
def admin_cleanup_posts()
```

Clean up orphaned posts

**Decorators:**
- `@app.route('/admin/cleanup/posts', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### admin_cleanup_orphan_runs

```python
def admin_cleanup_orphan_runs()
```

Clean up orphan processing runs

**Decorators:**
- `@app.route('/admin/cleanup/orphan_runs', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### admin_cleanup_user

```python
def admin_cleanup_user()
```

Clean up all data for a specific user

**Decorators:**
- `@app.route('/admin/cleanup/user', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### admin_cleanup_all

```python
def admin_cleanup_all()
```

Run full cleanup

**Decorators:**
- `@app.route('/admin/cleanup/all', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### serve_image

```python
def serve_image(filename)
```

Serve stored images

**Decorators:**
- `@app.route('/images/<path:filename>')`

### review_list

```python
def review_list()
```

List images pending review (platform-aware)

**Decorators:**
- `@app.route('/review')`
- `@login_required`
- `@platform_required`
- `@with_session_error_handling`

### review_single

```python
def review_single(image_id)
```

Review a single image

**Decorators:**
- `@app.route('/review/<int:image_id>')`
- `@login_required`
- `@with_session_error_handling`

### review_submit

```python
def review_submit(image_id)
```

Submit review for an image

**Decorators:**
- `@app.route('/review/<int:image_id>', methods=['POST'])`
- `@login_required`
- `@validate_input_length()`
- `@with_session_error_handling`

### batch_review

```python
def batch_review()
```

Batch review interface with filtering, sorting, and pagination

**Decorators:**
- `@app.route('/batch_review')`
- `@login_required`
- `@platform_required`
- `@with_session_error_handling`

### api_batch_review

```python
def api_batch_review()
```

API endpoint for batch review

**Decorators:**
- `@app.route('/api/batch_review', methods=['POST'])`
- `@login_required`
- `@with_session_error_handling`

### api_update_caption

```python
def api_update_caption(image_id)
```

API endpoint for updating and optionally posting a caption

**Decorators:**
- `@app.route('/api/update_caption/<int:image_id>', methods=['POST'])`
- `@login_required`
- `@enhanced_input_validation`
- `@with_session_error_handling`

### api_regenerate_caption

```python
def api_regenerate_caption(image_id)
```

API endpoint to regenerate caption for an image

**Decorators:**
- `@app.route('/api/regenerate_caption/<int:image_id>', methods=['POST'])`
- `@login_required`
- `@with_session_error_handling`

### post_approved

```python
def post_approved()
```

Post approved captions to platform

**Decorators:**
- `@app.route('/post_approved')`
- `@login_required`
- `@with_session_error_handling`

### update_platform_media_description

```python
def update_platform_media_description(image_data, platform_config)
```

Update media description on platform using platform config

### platform_management

```python
def platform_management()
```

Platform management interface

**Decorators:**
- `@app.route('/platform_management')`
- `@login_required`
- `@with_session_error_handling`

### switch_platform

```python
def switch_platform(platform_id)
```

Switch to a different platform

**Decorators:**
- `@app.route('/switch_platform/<int:platform_id>')`
- `@login_required`
- `@with_session_error_handling`

### api_add_platform

```python
def api_add_platform()
```

Add a new platform connection

**Decorators:**
- `@app.route('/api/add_platform', methods=['POST'])`
- `@login_required`
- `@validate_csrf_token`
- `@enhanced_input_validation`
- `@with_session_error_handling`

### api_switch_platform

```python
def api_switch_platform(platform_id)
```

Switch to a different platform with integrated session management

**Decorators:**
- `@app.route('/api/switch_platform/<int:platform_id>', methods=['POST'])`
- `@login_required`
- `@with_db_session`
- `@validate_csrf_token`
- `@with_session_error_handling`

### api_test_platform

```python
def api_test_platform(platform_id)
```

Test a platform connection

**Decorators:**
- `@app.route('/api/test_platform/<int:platform_id>', methods=['POST'])`
- `@login_required`
- `@with_session_error_handling`

### api_get_platform

```python
def api_get_platform(platform_id)
```

Get platform connection data for editing

**Decorators:**
- `@app.route('/api/get_platform/<int:platform_id>', methods=['GET'])`
- `@login_required`
- `@with_session_error_handling`

### api_edit_platform

```python
def api_edit_platform(platform_id)
```

Edit an existing platform connection

**Decorators:**
- `@app.route('/api/edit_platform/<int:platform_id>', methods=['PUT'])`
- `@login_required`
- `@with_session_error_handling`

### api_session_state

```python
def api_session_state()
```

Get current session state for cross-tab synchronization with integrated session management

**Decorators:**
- `@app.route('/api/session_state', methods=['GET'])`
- `@login_required`
- `@with_session_error_handling`

### api_session_cleanup

```python
def api_session_cleanup()
```

Clean up expired sessions and notify tabs - integrated session management

**Decorators:**
- `@app.route('/api/session/cleanup', methods=['POST'])`
- `@login_required`
- `@validate_csrf_token`
- `@rate_limit(limit=5, window_seconds=60)`
- `@with_session_error_handling`

### api_session_validate

```python
def api_session_validate()
```

Validate current session with integrated session management

**Decorators:**
- `@app.route('/api/session/validate', methods=['POST'])`
- `@login_required`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### api_session_notify_logout

```python
def api_session_notify_logout()
```

Notify other tabs about logout - for cross-tab session synchronization

**Decorators:**
- `@app.route('/api/session/notify_logout', methods=['POST'])`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### api_delete_platform

```python
def api_delete_platform(platform_id)
```

Delete a platform connection with comprehensive validation

**Decorators:**
- `@app.route('/api/delete_platform/<int:platform_id>', methods=['DELETE'])`
- `@login_required`
- `@with_session_error_handling`

### caption_generation

```python
def caption_generation()
```

Caption generation page

**Decorators:**
- `@app.route('/caption_generation')`
- `@login_required`
- `@platform_required`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### start_caption_generation

```python
def start_caption_generation()
```

Start caption generation process

**Decorators:**
- `@app.route('/start_caption_generation', methods=['POST'])`
- `@login_required`
- `@platform_required`
- `@caption_generation_rate_limit(limit=3, window_minutes=60)`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=3, window_seconds=300)`
- `@validate_input_length()`
- `@with_session_error_handling`

### get_caption_generation_status

```python
def get_caption_generation_status(task_id)
```

Get caption generation task status

**Decorators:**
- `@app.route('/api/caption_generation/status/<task_id>')`
- `@login_required`
- `@platform_required`
- `@validate_task_access`
- `@rate_limit(limit=30, window_seconds=60)`
- `@with_session_error_handling`

### cancel_caption_generation

```python
def cancel_caption_generation(task_id)
```

Cancel caption generation task

**Decorators:**
- `@app.route('/api/caption_generation/cancel/<task_id>', methods=['POST'])`
- `@login_required`
- `@platform_required`
- `@validate_task_access`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### get_caption_generation_results

```python
def get_caption_generation_results(task_id)
```

Get caption generation results

**Decorators:**
- `@app.route('/api/caption_generation/results/<task_id>')`
- `@login_required`
- `@platform_required`
- `@validate_task_access`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### caption_settings

```python
def caption_settings()
```

Caption generation settings page

**Decorators:**
- `@app.route('/caption_settings')`
- `@login_required`
- `@platform_required`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### api_get_caption_settings

```python
def api_get_caption_settings()
```

API endpoint to get caption generation settings

**Decorators:**
- `@app.route('/api/caption_settings', methods=['GET'])`
- `@login_required`
- `@platform_required`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### save_caption_settings

```python
def save_caption_settings()
```

Save caption generation settings

**Decorators:**
- `@app.route('/save_caption_settings', methods=['POST'])`
- `@login_required`
- `@platform_required`
- `@validate_caption_settings_input`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=10, window_seconds=60)`
- `@validate_input_length()`
- `@enhanced_input_validation`
- `@with_session_error_handling`

### api_validate_caption_settings

```python
def api_validate_caption_settings()
```

API endpoint to validate caption generation settings

**Decorators:**
- `@app.route('/api/validate_caption_settings', methods=['POST'])`
- `@login_required`
- `@platform_required`
- `@validate_caption_settings_input`
- `@rate_limit(limit=30, window_seconds=60)`
- `@validate_input_length()`
- `@with_session_error_handling`

### api_get_error_statistics

```python
def api_get_error_statistics()
```

Get error statistics for admin monitoring

**Decorators:**
- `@app.route('/api/admin/error_statistics')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### api_get_session_error_statistics

```python
def api_get_session_error_statistics()
```

Get session error statistics for monitoring

**Decorators:**
- `@app.route('/api/admin/session_error_statistics')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@with_session_error_handling`

### api_mark_notification_read

```python
def api_mark_notification_read(notification_id)
```

Mark admin notification as read

**Decorators:**
- `@app.route('/api/admin/notifications/<int:notification_id>/read', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### review_batches

```python
def review_batches()
```

List recent caption generation batches for review

**Decorators:**
- `@app.route('/review/batches')`
- `@login_required`
- `@platform_required`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### review_batch

```python
def review_batch(batch_id)
```

Review images in a specific batch

**Decorators:**
- `@app.route('/review/batch/<batch_id>')`
- `@login_required`
- `@platform_required`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### api_bulk_approve_batch

```python
def api_bulk_approve_batch(batch_id)
```

Bulk approve images in a batch

**Decorators:**
- `@app.route('/api/review/batch/<batch_id>/bulk_approve', methods=['POST'])`
- `@login_required`
- `@platform_required`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=10, window_seconds=60)`
- `@validate_input_length()`
- `@with_session_error_handling`

### api_bulk_reject_batch

```python
def api_bulk_reject_batch(batch_id)
```

Bulk reject images in a batch

**Decorators:**
- `@app.route('/api/review/batch/<batch_id>/bulk_reject', methods=['POST'])`
- `@login_required`
- `@platform_required`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=10, window_seconds=60)`
- `@validate_input_length()`
- `@with_session_error_handling`

### api_update_batch_image_caption

```python
def api_update_batch_image_caption(image_id)
```

Update caption for an image in batch review context

**Decorators:**
- `@app.route('/api/review/batch/image/<int:image_id>/caption', methods=['PUT'])`
- `@login_required`
- `@platform_required`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=30, window_seconds=60)`
- `@validate_input_length()`
- `@with_session_error_handling`

### api_get_batch_statistics

```python
def api_get_batch_statistics(batch_id)
```

Get statistics for a review batch

**Decorators:**
- `@app.route('/api/review/batch/<batch_id>/statistics')`
- `@login_required`
- `@platform_required`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### admin_monitoring_dashboard

```python
def admin_monitoring_dashboard()
```

Administrative monitoring dashboard

**Decorators:**
- `@app.route('/admin/monitoring')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### api_admin_system_overview

```python
def api_admin_system_overview()
```

Get real-time system overview

**Decorators:**
- `@app.route('/api/admin/system_overview')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=30, window_seconds=60)`
- `@with_session_error_handling`

### api_admin_active_tasks

```python
def api_admin_active_tasks()
```

Get active caption generation tasks

**Decorators:**
- `@app.route('/api/admin/active_tasks')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### api_admin_task_history

```python
def api_admin_task_history()
```

Get task history

**Decorators:**
- `@app.route('/api/admin/task_history')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### api_admin_performance_metrics

```python
def api_admin_performance_metrics()
```

Get performance metrics

**Decorators:**
- `@app.route('/api/admin/performance_metrics')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### api_admin_cancel_task

```python
def api_admin_cancel_task(task_id)
```

Cancel a task as administrator

**Decorators:**
- `@app.route('/api/admin/cancel_task/<task_id>', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### api_admin_cleanup_tasks

```python
def api_admin_cleanup_tasks()
```

Clean up old tasks

**Decorators:**
- `@app.route('/api/admin/cleanup_tasks', methods=['POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=5, window_seconds=300)`
- `@with_session_error_handling`

### api_get_csrf_token

```python
def api_get_csrf_token()
```

Get a fresh CSRF token for AJAX requests

**Decorators:**
- `@app.route('/api/csrf-token', methods=['GET'])`
- `@login_required`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### api_update_user_settings

```python
def api_update_user_settings()
```

Update user settings for the current platform

**Decorators:**
- `@app.route('/api/update_user_settings', methods=['POST'])`
- `@login_required`
- `@require_secure_connection`
- `@validate_csrf_token`
- `@rate_limit(limit=10, window_seconds=60)`
- `@validate_input_length()`
- `@with_session_error_handling`

### api_admin_user_activity

```python
def api_admin_user_activity()
```

Get user activity statistics

**Decorators:**
- `@app.route('/api/admin/user_activity')`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=20, window_seconds=60)`
- `@with_session_error_handling`

### api_admin_system_limits

```python
def api_admin_system_limits()
```

Get or update system limits

**Decorators:**
- `@app.route('/api/admin/system_limits', methods=['GET', 'POST'])`
- `@login_required`
- `@role_required(UserRole.ADMIN)`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### profile

```python
def profile()
```

User profile page with platform management and settings

**Decorators:**
- `@app.route('/profile')`
- `@login_required`
- `@with_session_error_handling`

### api_terminate_session

```python
def api_terminate_session(session_id)
```

Terminate a specific session

**Decorators:**
- `@app.route('/api/sessions/<session_id>', methods=['DELETE'])`
- `@login_required`
- `@validate_csrf_token`
- `@rate_limit(limit=10, window_seconds=60)`
- `@with_session_error_handling`

### favicon

```python
def favicon()
```

Serve favicon.ico with proper caching

**Decorators:**
- `@app.route('/favicon.ico')`
- `@with_session_error_handling`

### add_favicon_cache_headers

```python
def add_favicon_cache_headers(response)
```

Add cache headers for favicon assets

**Decorators:**
- `@app.after_request`

### progress_stream

```python
def progress_stream(task_id)
```

Server-Sent Events endpoint for real-time progress updates

**Decorators:**
- `@app.route('/api/progress_stream/<task_id>')`
- `@login_required`
- `@with_session_error_handling`

