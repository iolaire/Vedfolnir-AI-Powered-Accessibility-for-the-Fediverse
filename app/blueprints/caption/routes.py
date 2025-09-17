from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, g
from flask_login import login_required, current_user
from app.utils.web.response_helpers import success_response, error_response
from app.utils.web.decorators import require_platform_context
from app.utils.web.request_helpers import get_form_int, get_form_float

caption_bp = Blueprint('caption', __name__, url_prefix='/caption')

@caption_bp.route('/generation')
@login_required
def generation():
    """Caption generation page"""
    try:
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return redirect(url_for('main.index'))
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        active_task = caption_service.get_active_task_for_user(current_user.id)

        # Get task history using the same approach as admin job history
        task_history = []
        try:
            with db_manager.get_session() as session:
                from models import CaptionGenerationTask

                # Get task history for the user
                tasks = session.query(CaptionGenerationTask)\
                             .filter(CaptionGenerationTask.user_id == current_user.id)\
                             .order_by(CaptionGenerationTask.created_at.desc())\
                             .limit(10)\
                             .all()

                for task in tasks:
                    task_info = {
                        'task_id': task.id,
                        'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                        'created_at': task.created_at.isoformat() if task.created_at else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        'progress_percent': task.progress_percent or 0,
                        'current_step': task.current_step,
                        'error_message': task.error_message
                    }
                    task_history.append(task_info)

                current_app.logger.info(f"Found {len(task_history)} tasks for user {current_user.id}")
        except Exception as e:
            current_app.logger.error(f"Error getting task history: {str(e)}")
            task_history = []
        
        # Handle both dictionary and object cases for active_task data
        if active_task and isinstance(active_task, dict):
            # Convert dictionary to object for template compatibility
            class TaskObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            active_task = TaskObj(active_task)
        
        # Create form
        from wtforms import Form, SelectField, IntegerField, FloatField, BooleanField, SubmitField
        from wtforms.validators import DataRequired, NumberRange
        
        class CaptionGenerationForm(Form):
            max_posts_per_run = IntegerField('Max Posts Per Run', default=10, validators=[DataRequired(), NumberRange(min=1, max=100)])
            processing_delay = FloatField('Processing Delay (seconds)', default=1.0, validators=[NumberRange(min=0.1, max=10.0)])
            max_caption_length = IntegerField('Max Caption Length', default=500, validators=[DataRequired(), NumberRange(min=50, max=2000)])
            optimal_min_length = IntegerField('Optimal Min Length', default=100, validators=[DataRequired(), NumberRange(min=20, max=500)])
            optimal_max_length = IntegerField('Optimal Max Length', default=300, validators=[DataRequired(), NumberRange(min=50, max=1000)])
            reprocess_existing = SelectField('Reprocess Existing', choices=[('false', 'No'), ('true', 'Yes')], default='false')
            submit = SubmitField('Start Generation')
        
        form = CaptionGenerationForm()
        
        # Get current platform context using the same method as platform management
        from app.services.platform.components.platform_service import PlatformService
        platform_service = PlatformService()
        platform_data = platform_service.get_user_platforms(include_stats=False)
        current_platform = platform_data['current_platform']
        
        # Ensure session context is updated with platform data
        if current_platform:
            # Handle both object and dictionary cases for platform data
            if isinstance(current_platform, dict):
                platform_id = current_platform.get('id')
                platform_name = current_platform.get('name')
                platform_type = current_platform.get('platform_type')
                platform_instance_url = current_platform.get('instance_url', '')
            else:
                platform_id = getattr(current_platform, 'id', None)
                platform_name = getattr(current_platform, 'name', None)
                platform_type = getattr(current_platform, 'platform_type', None)
                platform_instance_url = getattr(current_platform, 'instance_url', '')
            
            # Initialize g.session_context if it doesn't exist
            if not hasattr(g, 'session_context'):
                g.session_context = {}
            
            # Update g.session_context
            g.session_context.update({
                'platform_connection_id': platform_id,
                'platform_name': platform_name,
                'platform_type': platform_type,
                'platform_instance_url': platform_instance_url
            })
            
            # Also update Flask session for persistence
            from flask import session
            session['platform_connection_id'] = platform_id
            session['platform_name'] = platform_name
            session['platform_type'] = platform_type
            session['platform_instance_url'] = getattr(current_platform, 'instance_url', '')
            session.modified = True
            
            # Also update Redis session manager if available
            session_manager = getattr(current_app, 'session_manager', None)
            if session_manager and hasattr(session_manager, 'switch_platform'):
                try:
                    session_id = getattr(session, 'sid', None)
                    if session_id and platform_id:
                        session_manager.switch_platform(session_id, platform_id)
                except Exception as e:
                    current_app.logger.debug(f"Could not update Redis session: {e}")
        
        # Create a normalized platform object for the template
        template_platform = None
        if current_platform:
            if isinstance(current_platform, dict):
                template_platform = current_platform
            else:
                # Convert SQLAlchemy object to dict for template consistency
                template_platform = {
                    'id': getattr(current_platform, 'id', None),
                    'name': getattr(current_platform, 'name', None),
                    'platform_type': getattr(current_platform, 'platform_type', None),
                    'instance_url': getattr(current_platform, 'instance_url', ''),
                    'username': getattr(current_platform, 'username', '')
                }
        
        return render_template('caption_generation.html',
                             form=form,
                             active_task=active_task,
                             active_platform=template_platform,
                             task_history=task_history)
                             
    except Exception as e:
        current_app.logger.error(f"Error loading caption generation: {str(e)}")
        return redirect(url_for('main.index'))

@caption_bp.route('/start', methods=['POST'])
@login_required
@require_platform_context
def start_generation():
    """Start caption generation process with RQ support"""
    try:
        # Import RQ-aware service
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        from app.services.task.rq.rq_config import TaskPriority
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return redirect(url_for('main.index'))
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        
        # Platform context is now available in g.session_context
        platform_connection_id = g.session_context.get('platform_connection_id')
        if not platform_connection_id:
            current_app.logger.error("No platform connection ID available in session context")
            return error_response("No platform connection available", 400)
        from models import CaptionGenerationSettings
        
        # Create settings object from form data
        settings = CaptionGenerationSettings(
            max_posts_per_run=get_form_int('max_posts_per_run', 10),
            processing_delay=get_form_float('processing_delay', 1.0),
            max_caption_length=get_form_int('max_caption_length', 500),
            optimal_min_length=get_form_int('optimal_min_length', 100),
            optimal_max_length=get_form_int('optimal_max_length', 300),
            reprocess_existing=get_form_int('reprocess_existing', 0) == 1
        )
        
        # Determine task priority based on user role
        priority = TaskPriority.HIGH if current_user.role.name == 'ADMIN' else TaskPriority.NORMAL
        
        # Use RQ-aware synchronous execution
        task_id = caption_service.start_caption_generation_sync(
            current_user.id,
            platform_connection_id,
            settings=settings,
            priority=priority
        )
        
        if task_id:
            return success_response({
                'task_id': task_id
            }, 'Caption generation started successfully')
        else:
            return error_response('Failed to start caption generation', 500)
            
    except Exception as e:
        current_app.logger.error(f"Error in caption generation: {str(e)}")
        return error_response('Internal server error', 500)

@caption_bp.route('/api/status/<task_id>')
@login_required
def get_status(task_id):
    """Get caption generation task status with RQ support"""
    try:
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return redirect(url_for('main.index'))
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        status = caption_service.get_task_status(task_id, current_user.id)
        
        if status:
            return jsonify({
                'success': True,
                'status': status.get('status'),
                'progress': status.get('progress_percent', 0),
                'current_step': status.get('current_step'),
                'message': status.get('error_message') or 'Processing...'
            })
        else:
            return error_response('Task not found', 404)
            
    except Exception as e:
        current_app.logger.error(f"Error getting task status: {str(e)}")
        return error_response('Internal server error', 500)

@caption_bp.route('/api/cancel/<task_id>', methods=['POST'])
@login_required
def cancel_generation(task_id):
    """Cancel caption generation task with RQ support"""
    try:
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return error_response('Database manager not available', 500)
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        
        # Validate that the task belongs to the current user
        task_status = caption_service.get_task_status(task_id, current_user.id)
        if not task_status:
            return error_response('Task not found or access denied', 404)
        
        # Use the correct method name
        success = caption_service.cancel_generation(task_id, current_user.id)
        
        if success:
            current_app.logger.info(f"User {current_user.id} cancelled task {task_id}")
            return success_response(message='Task cancelled successfully')
        else:
            return error_response('Failed to cancel task', 500)
            
    except Exception as e:
        current_app.logger.error(f"Error cancelling task: {str(e)}")
        return error_response('Internal server error', 500)

@caption_bp.route('/settings')
@login_required
def settings():
    """Caption settings page"""
    return render_template('caption_settings.html')
