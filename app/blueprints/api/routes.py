from flask import Blueprint, request, current_app
from flask_login import login_required, current_user
from security.core.security_middleware import rate_limit, generate_secure_token
from app.utils.decorators import api_route
from app.utils.responses import success_response, error_response
from app.utils.validation import ValidationUtils

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/csrf-token', methods=['GET'])
@login_required
@rate_limit(limit=20, window_seconds=60)
def get_csrf_token():
    """Get CSRF token for forms"""
    try:
        csrf_token = generate_secure_token()
        return success_response({'csrf_token': csrf_token})
    except Exception as e:
        current_app.logger.error(f"Error generating CSRF token: {str(e)}")
        return error_response('Failed to generate CSRF token', 500)

@api_bp.route('/update_caption/<int:image_id>', methods=['POST'])
@login_required
@api_route
def update_caption(image_id):
    """Update image caption"""
    try:
        from models import Image
        from database import DatabaseManager
        
        # Validate input
        new_caption = request.json.get('caption', '').strip()
        if not new_caption:
            return error_response('Caption cannot be empty', 400)
        
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            image = session.query(Image).filter_by(id=image_id).first()
            
            # Validate ownership
            is_valid, error_msg = ValidationUtils.validate_user_owns_resource(image)
            if not is_valid:
                return error_response(error_msg, 404 if 'not found' in error_msg else 403)
            
            image.generated_caption = new_caption
            session.commit()
            
            current_app.logger.info(f"Updated caption for image {image_id} by user {current_user.id}")
            return success_response({'message': 'Caption updated successfully'})
            
    except Exception as e:
        current_app.logger.error(f"Error updating caption: {str(e)}")
        return error_response('Failed to update caption', 500)

@api_bp.route('/regenerate_caption/<int:image_id>', methods=['POST'])
@login_required
@api_route
def regenerate_caption(image_id):
    """Regenerate caption for an image"""
    try:
        from models import Image
        from database import DatabaseManager
        from ollama_caption_generator import OllamaCaptionGenerator
        
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            image = session.query(Image).filter_by(id=image_id).first()
            
            # Validate ownership
            is_valid, error_msg = ValidationUtils.validate_user_owns_resource(image)
            if not is_valid:
                return error_response(error_msg, 404 if 'not found' in error_msg else 403)
            
            # Regenerate caption
            caption_generator = OllamaCaptionGenerator()
            new_caption = caption_generator.generate_caption(image.image_path)
            
            if new_caption:
                image.generated_caption = new_caption
                session.commit()
                return success_response({
                    'message': 'Caption regenerated successfully',
                    'caption': new_caption
                })
            else:
                return error_response('Failed to generate new caption', 500)
                
    except Exception as e:
        current_app.logger.error(f"Error regenerating caption: {str(e)}")
        return error_response('Failed to regenerate caption', 500)
