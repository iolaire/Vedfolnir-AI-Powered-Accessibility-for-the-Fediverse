from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, g
from flask_login import login_required, current_user
from utils.response_helpers import success_response, error_response
from utils.decorators import require_platform_context
from utils.request_helpers import get_form_int, get_form_float
import asyncio

caption_bp = Blueprint('caption', __name__, url_prefix='/caption')

@caption_bp.route('/generation')
@login_required
def generation():
    """Caption generation page"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return redirect(url_for('main.index'))
        
        caption_service = WebCaptionGenerationService(db_manager)
        active_task = caption_service.get_active_task_for_user(current_user.id)
        
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
        
        return render_template('caption_generation.html',
                             form=form,
                             active_task=active_task)
                             
    except Exception as e:
        current_app.logger.error(f"Error loading caption generation: {str(e)}")
        return redirect(url_for('main.index'))

@caption_bp.route('/start', methods=['POST'])
@login_required
@require_platform_context
def start_generation():
    """Start caption generation process"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return redirect(url_for('main.index'))
        
        caption_service = WebCaptionGenerationService(db_manager)
        
        # Platform context is now available in g.platform_connection_id
        task_id = asyncio.run(
            caption_service.start_caption_generation(
                current_user.id,
                g.platform_connection_id,
                batch_size=get_form_int('batch_size', 10),
                quality_threshold=get_form_float('quality_threshold', 0.7)
            )
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
    """Get caption generation task status"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return redirect(url_for('main.index'))
        
        caption_service = WebCaptionGenerationService(db_manager)
        status = caption_service.get_task_status(task_id)
        
        if status:
            return jsonify({
                'success': True,
                'status': status.status,
                'progress': status.progress,
                'total_images': status.total_images,
                'processed_images': status.processed_images,
                'message': status.message
            })
        else:
            return error_response('Task not found', 404)
            
    except Exception as e:
        current_app.logger.error(f"Error getting task status: {str(e)}")
        return error_response('Internal server error', 500)

@caption_bp.route('/api/cancel/<task_id>', methods=['POST'])
@login_required
def cancel_generation(task_id):
    """Cancel caption generation task"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return redirect(url_for('main.index'))
        
        caption_service = WebCaptionGenerationService(db_manager)
        success = caption_service.cancel_task(task_id)
        
        if success:
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
