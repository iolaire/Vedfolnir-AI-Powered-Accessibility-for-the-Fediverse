# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Caption Review Integration

This module provides integration between caption generation and the review interface,
including batch grouping, bulk operations, and enhanced review workflows.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from app.core.database.core.database_manager import DatabaseManager
from models import Image, Post, ProcessingStatus, CaptionGenerationTask, TaskStatus
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class CaptionReviewIntegration:
    """Integration service for caption generation and review workflows"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_review_batch_from_task(self, task_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Create a review batch from completed caption generation task
        
        Args:
            task_id: The completed task ID
            user_id: The user ID for authorization
            
        Returns:
            Dict with batch information or None if task not found
        """
        session = self.db_manager.get_session()
        try:
            # Get the completed task
            task = session.query(CaptionGenerationTask).filter_by(
                id=task_id,
                user_id=user_id,
                status=TaskStatus.COMPLETED
            ).first()
            
            if not task or not task.results:
                return None
            
            # Get images generated in this task
            generated_image_ids = task.results.generated_image_ids or []
            
            if not generated_image_ids:
                return None
            
            # Get images with eager loading
            images = session.query(Image).options(
                joinedload(Image.platform_connection),
                joinedload(Image.post)
            ).filter(
                Image.id.in_(generated_image_ids),
                Image.status == ProcessingStatus.PENDING
            ).order_by(Image.created_at.desc()).all()
            
            # Create batch metadata
            batch_info = {
                'batch_id': task_id,
                'task_id': task_id,
                'generation_timestamp': task.completed_at.isoformat() if task.completed_at else None,
                'total_images': len(images),
                'platform_connection_id': task.platform_connection_id,
                'user_id': user_id,
                'images': [self._image_to_dict(img) for img in images]
            }
            
            logger.info(f"Created review batch from task {sanitize_for_log(task_id)} with {len(images)} images")
            return batch_info
            
        except Exception as e:
            logger.error(f"Error creating review batch from task: {sanitize_for_log(str(e))}")
            return None
        finally:
            session.close()
    
    def get_review_batches(
        self, 
        user_id: int, 
        platform_connection_id: Optional[int] = None,
        days_back: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent review batches for a user
        
        Args:
            user_id: The user ID
            platform_connection_id: Optional platform filter
            days_back: Number of days to look back
            limit: Maximum number of batches to return
            
        Returns:
            List of batch information dictionaries
        """
        session = self.db_manager.get_session()
        try:
            # Calculate date threshold
            date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Query for completed tasks with results
            query = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.user_id == user_id,
                CaptionGenerationTask.status == TaskStatus.COMPLETED,
                CaptionGenerationTask.completed_at >= date_threshold,
                CaptionGenerationTask.results_json.isnot(None)
            )
            
            if platform_connection_id:
                query = query.filter(CaptionGenerationTask.platform_connection_id == platform_connection_id)
            
            tasks = query.order_by(desc(CaptionGenerationTask.completed_at)).limit(limit).all()
            
            batches = []
            for task in tasks:
                if task.results and task.results.generated_image_ids:
                    # Count pending images in this batch
                    pending_count = session.query(Image).filter(
                        Image.id.in_(task.results.generated_image_ids),
                        Image.status == ProcessingStatus.PENDING
                    ).count()
                    
                    # Count total images in this batch
                    total_count = len(task.results.generated_image_ids)
                    
                    batch_info = {
                        'batch_id': task.id,
                        'task_id': task.id,
                        'generation_timestamp': task.completed_at.isoformat() if task.completed_at else None,
                        'total_images': total_count,
                        'pending_images': pending_count,
                        'reviewed_images': total_count - pending_count,
                        'platform_connection_id': task.platform_connection_id,
                        'captions_generated': task.results.captions_generated,
                        'processing_time': task.results.processing_time_seconds
                    }
                    batches.append(batch_info)
            
            return batches
            
        except Exception as e:
            logger.error(f"Error getting review batches: {sanitize_for_log(str(e))}")
            return []
        finally:
            session.close()
    
    def get_batch_images(
        self, 
        batch_id: str, 
        user_id: int,
        status_filter: Optional[ProcessingStatus] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc',
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Get images from a specific batch with filtering and pagination
        
        Args:
            batch_id: The batch ID (task ID)
            user_id: The user ID for authorization
            status_filter: Optional status filter
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            page: Page number (1-based)
            per_page: Items per page
            
        Returns:
            Dict with images and pagination info
        """
        session = self.db_manager.get_session()
        try:
            # Get the task to verify ownership and get image IDs
            task = session.query(CaptionGenerationTask).filter_by(
                id=batch_id,
                user_id=user_id
            ).first()
            
            if not task or not task.results or not task.results.generated_image_ids:
                return {'images': [], 'total': 0, 'page': page, 'per_page': per_page}
            
            # Build query for images in this batch
            query = session.query(Image).options(
                joinedload(Image.platform_connection),
                joinedload(Image.post)
            ).filter(Image.id.in_(task.results.generated_image_ids))
            
            # Apply status filter
            if status_filter:
                query = query.filter(Image.status == status_filter)
            
            # Apply sorting
            sort_field = getattr(Image, sort_by, Image.created_at)
            if sort_order == 'asc':
                query = query.order_by(asc(sort_field))
            else:
                query = query.order_by(desc(sort_field))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            images = query.offset(offset).limit(per_page).all()
            
            return {
                'images': [self._image_to_dict(img) for img in images],
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': (page * per_page) < total,
                'batch_info': {
                    'batch_id': batch_id,
                    'generation_timestamp': task.completed_at.isoformat() if task.completed_at else None,
                    'platform_connection_id': task.platform_connection_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting batch images: {sanitize_for_log(str(e))}")
            return {'images': [], 'total': 0, 'page': page, 'per_page': per_page}
        finally:
            session.close()
    
    def bulk_approve_batch(
        self, 
        batch_id: str, 
        user_id: int,
        image_ids: Optional[List[int]] = None,
        reviewer_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk approve images in a batch
        
        Args:
            batch_id: The batch ID (task ID)
            user_id: The user ID for authorization
            image_ids: Optional list of specific image IDs (approves all if None)
            reviewer_notes: Optional notes for all approved images
            
        Returns:
            Dict with operation results
        """
        session = self.db_manager.get_session()
        try:
            # Verify batch ownership
            task = session.query(CaptionGenerationTask).filter_by(
                id=batch_id,
                user_id=user_id
            ).first()
            
            if not task or not task.results or not task.results.generated_image_ids:
                return {'success': False, 'error': 'Batch not found or access denied'}
            
            # Determine which images to approve
            if image_ids:
                # Verify all image IDs are in this batch
                valid_ids = set(task.results.generated_image_ids) & set(image_ids)
                target_image_ids = list(valid_ids)
            else:
                target_image_ids = task.results.generated_image_ids
            
            if not target_image_ids:
                return {'success': False, 'error': 'No valid images to approve'}
            
            # Update images to approved status
            updated_count = session.query(Image).filter(
                Image.id.in_(target_image_ids),
                Image.status == ProcessingStatus.PENDING
            ).update({
                'status': ProcessingStatus.APPROVED,
                'reviewed_at': datetime.now(timezone.utc),
                'reviewer_notes': reviewer_notes,
                'final_caption': Image.generated_caption  # Use generated caption as final
            }, synchronize_session=False)
            
            session.commit()
            
            logger.info(f"Bulk approved {updated_count} images in batch {sanitize_for_log(batch_id)}")
            
            return {
                'success': True,
                'approved_count': updated_count,
                'batch_id': batch_id
            }
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in bulk approve: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': 'Database error occurred'}
        except Exception as e:
            session.rollback()
            logger.error(f"Error in bulk approve: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': str(e)}
        finally:
            session.close()
    
    def bulk_reject_batch(
        self, 
        batch_id: str, 
        user_id: int,
        image_ids: Optional[List[int]] = None,
        reviewer_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk reject images in a batch
        
        Args:
            batch_id: The batch ID (task ID)
            user_id: The user ID for authorization
            image_ids: Optional list of specific image IDs (rejects all if None)
            reviewer_notes: Optional notes for all rejected images
            
        Returns:
            Dict with operation results
        """
        session = self.db_manager.get_session()
        try:
            # Verify batch ownership
            task = session.query(CaptionGenerationTask).filter_by(
                id=batch_id,
                user_id=user_id
            ).first()
            
            if not task or not task.results or not task.results.generated_image_ids:
                return {'success': False, 'error': 'Batch not found or access denied'}
            
            # Determine which images to reject
            if image_ids:
                # Verify all image IDs are in this batch
                valid_ids = set(task.results.generated_image_ids) & set(image_ids)
                target_image_ids = list(valid_ids)
            else:
                target_image_ids = task.results.generated_image_ids
            
            if not target_image_ids:
                return {'success': False, 'error': 'No valid images to reject'}
            
            # Update images to rejected status
            updated_count = session.query(Image).filter(
                Image.id.in_(target_image_ids),
                Image.status == ProcessingStatus.PENDING
            ).update({
                'status': ProcessingStatus.REJECTED,
                'reviewed_at': datetime.now(timezone.utc),
                'reviewer_notes': reviewer_notes
            }, synchronize_session=False)
            
            session.commit()
            
            logger.info(f"Bulk rejected {updated_count} images in batch {sanitize_for_log(batch_id)}")
            
            return {
                'success': True,
                'rejected_count': updated_count,
                'batch_id': batch_id
            }
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in bulk reject: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': 'Database error occurred'}
        except Exception as e:
            session.rollback()
            logger.error(f"Error in bulk reject: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': str(e)}
        finally:
            session.close()
    
    def update_batch_image_caption(
        self, 
        image_id: int, 
        user_id: int,
        new_caption: str,
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update caption for a single image in a batch
        
        Args:
            image_id: The image ID
            user_id: The user ID for authorization
            new_caption: The new caption text
            batch_id: Optional batch ID for additional validation
            
        Returns:
            Dict with operation results
        """
        session = self.db_manager.get_session()
        try:
            # Get the image
            image = session.query(Image).options(
                joinedload(Image.platform_connection)
            ).filter_by(id=image_id).first()
            
            if not image:
                return {'success': False, 'error': 'Image not found'}
            
            # Verify user has access to this image's platform
            if image.platform_connection and image.platform_connection.user_id != user_id:
                return {'success': False, 'error': 'Access denied'}
            
            # Additional batch validation if provided
            if batch_id:
                task = session.query(CaptionGenerationTask).filter_by(
                    id=batch_id,
                    user_id=user_id
                ).first()
                
                if not task or not task.results or image_id not in (task.results.generated_image_ids or []):
                    return {'success': False, 'error': 'Image not in specified batch'}
            
            # Update the caption
            image.reviewed_caption = new_caption
            image.final_caption = new_caption
            image.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            
            logger.info(f"Updated caption for image {sanitize_for_log(str(image_id))} in batch context")
            
            return {
                'success': True,
                'image_id': image_id,
                'updated_caption': new_caption
            }
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating image caption: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': 'Database error occurred'}
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating image caption: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': str(e)}
        finally:
            session.close()
    
    def get_batch_statistics(self, batch_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a review batch
        
        Args:
            batch_id: The batch ID (task ID)
            user_id: The user ID for authorization
            
        Returns:
            Dict with batch statistics or None if not found
        """
        session = self.db_manager.get_session()
        try:
            # Get the task
            task = session.query(CaptionGenerationTask).filter_by(
                id=batch_id,
                user_id=user_id
            ).first()
            
            if not task or not task.results or not task.results.generated_image_ids:
                return None
            
            image_ids = task.results.generated_image_ids
            
            # Count images by status
            status_counts = {}
            for status in ProcessingStatus:
                count = session.query(Image).filter(
                    Image.id.in_(image_ids),
                    Image.status == status
                ).count()
                status_counts[status.value] = count
            
            # Calculate quality metrics
            quality_scores = session.query(Image.caption_quality_score).filter(
                Image.id.in_(image_ids),
                Image.caption_quality_score.isnot(None)
            ).all()
            
            quality_scores = [score[0] for score in quality_scores if score[0] is not None]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            # Count images needing special review
            special_review_count = session.query(Image).filter(
                Image.id.in_(image_ids),
                Image.needs_special_review == True
            ).count()
            
            return {
                'batch_id': batch_id,
                'total_images': len(image_ids),
                'status_counts': status_counts,
                'average_quality_score': round(avg_quality, 1),
                'special_review_count': special_review_count,
                'generation_time': task.results.processing_time_seconds,
                'generation_timestamp': task.completed_at.isoformat() if task.completed_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting batch statistics: {sanitize_for_log(str(e))}")
            return None
        finally:
            session.close()
    
    def _image_to_dict(self, image: Image) -> Dict[str, Any]:
        """Convert Image object to dictionary for JSON serialization"""
        return {
            'id': image.id,
            'image_url': image.image_url,
            'local_path': image.local_path,
            'generated_caption': image.generated_caption,
            'reviewed_caption': image.reviewed_caption,
            'final_caption': image.final_caption,
            'status': image.status.value,
            'created_at': image.created_at.isoformat() if image.created_at else None,
            'updated_at': image.updated_at.isoformat() if image.updated_at else None,
            'reviewed_at': image.reviewed_at.isoformat() if image.reviewed_at else None,
            'caption_quality_score': image.caption_quality_score,
            'needs_special_review': image.needs_special_review,
            'reviewer_notes': image.reviewer_notes,
            'post': {
                'id': image.post.id,
                'post_id': image.post.post_id,
                'post_url': image.post.post_url
            } if image.post else None,
            'platform_connection': {
                'id': image.platform_connection.id,
                'name': image.platform_connection.name,
                'platform_type': image.platform_connection.platform_type
            } if image.platform_connection else None
        }
    
    def get_job_quality_metrics(self, batch_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get quality metrics and improvement suggestions for a job
        
        Args:
            batch_id: The batch ID (task ID)
            user_id: The user ID for authorization
            
        Returns:
            Dict with quality metrics and suggestions or None if not found
        """
        session = self.db_manager.get_session()
        try:
            # Verify batch ownership
            task = session.query(CaptionGenerationTask).filter_by(
                id=batch_id,
                user_id=user_id
            ).first()
            
            if not task or not task.results or not task.results.generated_image_ids:
                return None
            
            image_ids = task.results.generated_image_ids
            
            # Get images with quality scores
            images = session.query(Image).filter(
                Image.id.in_(image_ids),
                Image.caption_quality_score.isnot(None)
            ).all()
            
            if not images:
                return None
            
            # Calculate quality metrics
            quality_scores = [img.caption_quality_score for img in images if img.caption_quality_score is not None]
            
            if not quality_scores:
                return None
            
            avg_quality = sum(quality_scores) / len(quality_scores)
            min_quality = min(quality_scores)
            max_quality = max(quality_scores)
            
            # Quality distribution
            excellent_count = len([s for s in quality_scores if s >= 80])
            good_count = len([s for s in quality_scores if 60 <= s < 80])
            fair_count = len([s for s in quality_scores if 40 <= s < 60])
            poor_count = len([s for s in quality_scores if s < 40])
            
            # Generate improvement suggestions
            suggestions = []
            
            if avg_quality < 60:
                suggestions.append("Consider adjusting caption generation settings for better quality")
                suggestions.append("Review images with low quality scores for common issues")
            
            if poor_count > len(quality_scores) * 0.2:  # More than 20% poor quality
                suggestions.append("High number of poor quality captions - consider regenerating")
            
            if min_quality < 30:
                suggestions.append("Some captions have very low quality scores - manual review recommended")
            
            # Check for special review needs
            special_review_count = len([img for img in images if img.needs_special_review])
            if special_review_count > 0:
                suggestions.append(f"{special_review_count} images flagged for special review")
            
            return {
                'batch_id': batch_id,
                'total_images': len(images),
                'quality_metrics': {
                    'average_quality': round(avg_quality, 1),
                    'min_quality': min_quality,
                    'max_quality': max_quality,
                    'quality_distribution': {
                        'excellent': excellent_count,  # 80+
                        'good': good_count,           # 60-79
                        'fair': fair_count,           # 40-59
                        'poor': poor_count            # <40
                    }
                },
                'improvement_suggestions': suggestions,
                'special_review_count': special_review_count,
                'generation_timestamp': task.completed_at.isoformat() if task.completed_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting job quality metrics: {sanitize_for_log(str(e))}")
            return None
        finally:
            session.close()
    
    def get_approval_rate_tracking(self, user_id: int, days_back: int = 30) -> Dict[str, Any]:
        """
        Get approval rate tracking and feedback for job optimization
        
        Args:
            user_id: The user ID
            days_back: Number of days to look back for tracking
            
        Returns:
            Dict with approval rate tracking data
        """
        session = self.db_manager.get_session()
        try:
            # Calculate date threshold
            date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Get completed tasks for the user
            tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.user_id == user_id,
                CaptionGenerationTask.status == TaskStatus.COMPLETED,
                CaptionGenerationTask.completed_at >= date_threshold,
                CaptionGenerationTask.results_json.isnot(None)
            ).all()
            
            if not tasks:
                return {
                    'total_batches': 0,
                    'total_images': 0,
                    'approval_rates': {},
                    'trends': {},
                    'recommendations': []
                }
            
            # Collect all image IDs from tasks
            all_image_ids = []
            batch_data = []
            
            for task in tasks:
                if task.results and task.results.generated_image_ids:
                    image_ids = task.results.generated_image_ids
                    all_image_ids.extend(image_ids)
                    
                    batch_data.append({
                        'task_id': task.id,
                        'image_ids': image_ids,
                        'completed_at': task.completed_at
                    })
            
            if not all_image_ids:
                return {
                    'total_batches': len(tasks),
                    'total_images': 0,
                    'approval_rates': {},
                    'trends': {},
                    'recommendations': []
                }
            
            # Get image status counts
            status_counts = {}
            for status in ProcessingStatus:
                count = session.query(Image).filter(
                    Image.id.in_(all_image_ids),
                    Image.status == status
                ).count()
                status_counts[status.value] = count
            
            total_images = len(all_image_ids)
            total_reviewed = status_counts.get('approved', 0) + status_counts.get('rejected', 0)
            
            # Calculate approval rates
            approval_rate = (status_counts.get('approved', 0) / total_reviewed * 100) if total_reviewed > 0 else 0
            rejection_rate = (status_counts.get('rejected', 0) / total_reviewed * 100) if total_reviewed > 0 else 0
            pending_rate = (status_counts.get('pending', 0) / total_images * 100) if total_images > 0 else 0
            
            # Calculate trends (compare first half vs second half of period)
            mid_date = date_threshold + timedelta(days=days_back//2)
            
            early_tasks = [t for t in tasks if t.completed_at < mid_date]
            recent_tasks = [t for t in tasks if t.completed_at >= mid_date]
            
            # Calculate early vs recent approval rates
            early_image_ids = []
            recent_image_ids = []
            
            for task in early_tasks:
                if task.results and task.results.generated_image_ids:
                    early_image_ids.extend(task.results.generated_image_ids)
            
            for task in recent_tasks:
                if task.results and task.results.generated_image_ids:
                    recent_image_ids.extend(task.results.generated_image_ids)
            
            early_approved = session.query(Image).filter(
                Image.id.in_(early_image_ids),
                Image.status == ProcessingStatus.APPROVED
            ).count() if early_image_ids else 0
            
            early_total_reviewed = session.query(Image).filter(
                Image.id.in_(early_image_ids),
                Image.status.in_([ProcessingStatus.APPROVED, ProcessingStatus.REJECTED])
            ).count() if early_image_ids else 0
            
            recent_approved = session.query(Image).filter(
                Image.id.in_(recent_image_ids),
                Image.status == ProcessingStatus.APPROVED
            ).count() if recent_image_ids else 0
            
            recent_total_reviewed = session.query(Image).filter(
                Image.id.in_(recent_image_ids),
                Image.status.in_([ProcessingStatus.APPROVED, ProcessingStatus.REJECTED])
            ).count() if recent_image_ids else 0
            
            early_approval_rate = (early_approved / early_total_reviewed * 100) if early_total_reviewed > 0 else 0
            recent_approval_rate = (recent_approved / recent_total_reviewed * 100) if recent_total_reviewed > 0 else 0
            
            trend_direction = "improving" if recent_approval_rate > early_approval_rate else "declining" if recent_approval_rate < early_approval_rate else "stable"
            
            # Generate recommendations
            recommendations = []
            
            if approval_rate < 60:
                recommendations.append("Low approval rate - consider adjusting caption generation settings")
            elif approval_rate > 90:
                recommendations.append("Excellent approval rate - current settings are working well")
            
            if pending_rate > 50:
                recommendations.append("Many captions still pending review - consider bulk review tools")
            
            if trend_direction == "declining":
                recommendations.append("Approval rate is declining - review recent caption quality")
            elif trend_direction == "improving":
                recommendations.append("Approval rate is improving - keep current approach")
            
            if rejection_rate > 30:
                recommendations.append("High rejection rate - consider regenerating rejected captions")
            
            return {
                'total_batches': len(tasks),
                'total_images': total_images,
                'approval_rates': {
                    'approved_percent': round(approval_rate, 1),
                    'rejected_percent': round(rejection_rate, 1),
                    'pending_percent': round(pending_rate, 1),
                    'reviewed_percent': round((total_reviewed / total_images * 100) if total_images > 0 else 0, 1)
                },
                'status_counts': status_counts,
                'trends': {
                    'direction': trend_direction,
                    'early_approval_rate': round(early_approval_rate, 1),
                    'recent_approval_rate': round(recent_approval_rate, 1),
                    'change_percent': round(recent_approval_rate - early_approval_rate, 1)
                },
                'recommendations': recommendations,
                'period_days': days_back
            }
            
        except Exception as e:
            logger.error(f"Error getting approval rate tracking: {sanitize_for_log(str(e))}")
            return {
                'total_batches': 0,
                'total_images': 0,
                'approval_rates': {},
                'trends': {},
                'recommendations': ['Error retrieving approval rate data']
            }
        finally:
            session.close()
    
    def queue_caption_regeneration(self, image_ids: List[int], user_id: int, 
                                 reason: str = "Manual regeneration request") -> Dict[str, Any]:
        """
        Queue individual images for caption regeneration
        
        Args:
            image_ids: List of image IDs to regenerate
            user_id: The user ID for authorization
            reason: Reason for regeneration
            
        Returns:
            Dict with operation results
        """
        session = self.db_manager.get_session()
        try:
            # Verify user has access to all images
            images = session.query(Image).options(
                joinedload(Image.platform_connection)
            ).filter(
                Image.id.in_(image_ids)
            ).all()
            
            if not images:
                return {'success': False, 'error': 'No images found'}
            
            # Check authorization for all images
            unauthorized_images = [
                img for img in images 
                if img.platform_connection and img.platform_connection.user_id != user_id
            ]
            
            if unauthorized_images:
                return {'success': False, 'error': 'Access denied to some images'}
            
            # Mark images for regeneration
            updated_count = 0
            for image in images:
                # Reset to pending status for regeneration
                image.status = ProcessingStatus.PENDING
                image.generated_caption = None
                image.reviewed_caption = None
                image.final_caption = None
                image.caption_quality_score = None
                image.needs_special_review = False
                image.reviewer_notes = f"Queued for regeneration: {reason}"
                image.updated_at = datetime.now(timezone.utc)
                updated_count += 1
            
            session.commit()
            
            logger.info(f"Queued {updated_count} images for regeneration by user {sanitize_for_log(str(user_id))}")
            
            return {
                'success': True,
                'queued_count': updated_count,
                'image_ids': image_ids,
                'reason': reason
            }
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error queuing regeneration: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': 'Database error occurred'}
        except Exception as e:
            session.rollback()
            logger.error(f"Error queuing regeneration: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': str(e)}
        finally:
            session.close()