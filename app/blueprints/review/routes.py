from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import ProcessingStatus, Image, PlatformConnection
from wtforms import Form, HiddenField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

review_bp = Blueprint('review', __name__, url_prefix='/review')

class ReviewForm(Form):
    """Form for reviewing image captions"""
    image_id = HiddenField('Image ID', validators=[DataRequired()])
    caption = TextAreaField('Caption', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Submit Review')
    action = HiddenField('Action')
    notes = TextAreaField('Notes', validators=[Length(max=1000)])

@review_bp.route('/')
@login_required
def review_list():
    """List images pending review"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return render_template('review.html', images=[], page=1, total_pages=1, total=0, per_page=12)
        
        with unified_session_manager.get_db_session() as session:
            # Get images pending review
            query = session.query(Image).filter_by(status=ProcessingStatus.PENDING)

            # Filter by user's platforms if not admin
            if current_user.role.name != 'ADMIN':
                user_platforms = session.query(PlatformConnection).filter_by(
                    user_id=current_user.id, is_active=True
                ).all()
                platform_ids = [p.id for p in user_platforms]
                if platform_ids:
                    query = query.filter(Image.platform_connection_id.in_(platform_ids))
                else:
                    # User has no platforms, they shouldn't see any images
                    return render_template('review.html', images=[], page=1, total_pages=1, total=0, per_page=per_page)

            total = query.count()
            images = query.offset((page - 1) * per_page).limit(per_page).all()
            total_pages = (total + per_page - 1) // per_page
            
            return render_template('review.html', 
                                 images=images,
                                 page=page,
                                 total_pages=total_pages,
                                 total=total,
                                 per_page=per_page)
                                 
    except Exception as e:
        current_app.logger.error(f"Error loading review list: {str(e)}")
        return render_template('review.html', images=[], page=1, total_pages=1, total=0, per_page=12)

@review_bp.route('/<int:image_id>', methods=['GET', 'POST'])
@login_required
def review_single(image_id):
    """Review a single image - GET to view, POST to submit"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return redirect(url_for('review.review_list'))
        
        with unified_session_manager.get_db_session() as session:
            # Get image with user filtering
            query = session.query(Image).filter_by(id=image_id)

            # Filter by user's platforms if not admin
            if current_user.role.name != 'ADMIN':
                user_platforms = session.query(PlatformConnection).filter_by(
                    user_id=current_user.id, is_active=True
                ).all()
                platform_ids = [p.id for p in user_platforms]
                if platform_ids:
                    query = query.filter(Image.platform_connection_id.in_(platform_ids))
                else:
                    # User has no platforms, they shouldn't see any images
                    return redirect(url_for('review.review_list'))

            image = query.first()

            if not image:
                return redirect(url_for('review.review_list'))
                
            form = ReviewForm(request.form)
            form.image_id.data = image_id
            
            if request.method == 'POST' and form.validate():
                # Handle form submission
                caption = form.caption.data.strip()
                image.generated_caption = caption
                image.status = ProcessingStatus.APPROVED
                session.commit()
                return redirect(url_for('review.review_list'))
            else:
                # Display form for GET request
                form.caption.data = image.generated_caption or ""
                return render_template('review_single.html', image=image, form=form)
            
    except Exception as e:
        current_app.logger.error(f"Error in single review: {str(e)}")
        return redirect(url_for('review.review_list'))

@review_bp.route('/batch')
@login_required
def batch_review():
    """Batch review interface"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return render_template('batch_review.html', batches=[])
        
        with unified_session_manager.get_db_session() as session:
            # Get images grouped by platform for batch review
            query = session.query(Image).filter_by(status=ProcessingStatus.PENDING)

            # Filter by user's platforms if not admin
            if current_user.role.name != 'ADMIN':
                user_platforms = session.query(PlatformConnection).filter_by(
                    user_id=current_user.id, is_active=True
                ).all()
                platform_ids = [p.id for p in user_platforms]
                if platform_ids:
                    query = query.filter(Image.platform_connection_id.in_(platform_ids))
                else:
                    # User has no platforms, they shouldn't see any images
                    return render_template('batch_review.html', images=[])

            images = query.limit(50).all()  # Limit for batch processing
            return render_template('batch_review.html', images=images)
            
    except Exception as e:
        current_app.logger.error(f"Error loading batch review: {str(e)}")
        return render_template('batch_review.html', images=[])

@review_bp.route('/review_batches')
@login_required
def review_batches():
    """Redirect to batch review"""
    return redirect(url_for('review.batch_review'))

@review_bp.route('/review_batch/<int:batch_id>')
@login_required
def review_batch(batch_id):
    """Review specific batch - redirect to batch review for now"""
    return redirect(url_for('review.batch_review'))
