# Copyright (C) 2025 iolaire mcfadden.
# Database Query Helper Utilities

from typing import Optional, Dict, Any, List
from flask import current_app
from flask_login import current_user
from models import PlatformConnection, User, Image, Post, ProcessingStatus
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case

def get_user_platform_or_404(user_id: int, platform_id: int, db_session):
    """
    Get user platform with proper error handling
    
    Args:
        user_id: User ID
        platform_id: Platform connection ID
        db_session: Database session
        
    Returns:
        PlatformConnection object
        
    Raises:
        ValueError: If platform not found or access denied
    """
    platform = db_session.query(PlatformConnection).filter_by(
        id=platform_id,
        user_id=user_id,
        is_active=True
    ).first()
    
    if not platform:
        raise ValueError("Platform not found or access denied")
    
    return platform

def get_dashboard_statistics(db_session, user_role: str) -> Dict[str, Any]:
    """
    Get optimized dashboard statistics in single query
    
    Args:
        db_session: Database session
        user_role: User role for filtering
        
    Returns:
        Dictionary of statistics
    """
    from datetime import datetime, timedelta
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    # Single aggregated query for user statistics
    user_stats = db_session.query(
        func.count(User.id).label('total_users'),
        func.sum(case((User.is_active == True, 1), else_=0)).label('active_users'),
        func.sum(case((User.created_at >= yesterday, 1), else_=0)).label('new_users_24h'),
        func.sum(case((User.last_login >= yesterday, 1), else_=0)).label('recent_logins')
    ).first()
    
    # Single query for platform count
    platform_count = db_session.query(func.count(PlatformConnection.id)).scalar()
    
    # Single query for content statistics
    content_stats = db_session.query(
        func.count(Image.id).label('total_images'),
        func.count(Post.id).label('total_posts'),
        func.sum(case((Image.status == ProcessingStatus.PENDING, 1), else_=0)).label('pending_review'),
        func.sum(case((Image.status == ProcessingStatus.APPROVED, 1), else_=0)).label('approved')
    ).select_from(Image).outerjoin(Post).first()
    
    return {
        'total_users': user_stats.total_users or 0,
        'active_users': user_stats.active_users or 0,
        'new_users_24h': user_stats.new_users_24h or 0,
        'recent_logins': user_stats.recent_logins or 0,
        'total_platforms': platform_count or 0,
        'total_images': content_stats.total_images or 0,
        'total_posts': content_stats.total_posts or 0,
        'pending_review': content_stats.pending_review or 0,
        'approved': content_stats.approved or 0
    }

def batch_update_images(image_ids: List[int], updates: Dict[str, Any], db_session) -> int:
    """
    Efficient batch update operations
    
    Args:
        image_ids: List of image IDs to update
        updates: Dictionary of field updates
        db_session: Database session
        
    Returns:
        Number of updated records
    """
    if not image_ids or not updates:
        return 0
    
    try:
        result = db_session.query(Image).filter(
            Image.id.in_(image_ids)
        ).update(updates, synchronize_session=False)
        
        db_session.commit()
        return result
        
    except SQLAlchemyError as e:
        db_session.rollback()
        current_app.logger.error(f"Batch update failed: {e}")
        raise

def get_user_platform_stats(user_id: int, platform_id: int, db_session) -> Dict[str, Any]:
    """
    Get platform-specific statistics for user
    
    Args:
        user_id: User ID
        platform_id: Platform connection ID
        db_session: Database session
        
    Returns:
        Dictionary of platform statistics
    """
    # Single query for platform statistics
    stats = db_session.query(
        func.count(Post.id).label('total_posts'),
        func.count(Image.id).label('total_images'),
        func.sum(case((Image.status == ProcessingStatus.PENDING, 1), else_=0)).label('pending'),
        func.sum(case((Image.status == ProcessingStatus.APPROVED, 1), else_=0)).label('approved'),
        func.sum(case((Image.status == ProcessingStatus.POSTED, 1), else_=0)).label('posted'),
        func.sum(case((Image.status == ProcessingStatus.REJECTED, 1), else_=0)).label('rejected')
    ).select_from(Post).outerjoin(Image).filter(
        Post.user_id == user_id,
        Post.platform_connection_id == platform_id
    ).first()
    
    return {
        'total_posts': stats.total_posts or 0,
        'total_images': stats.total_images or 0,
        'pending': stats.pending or 0,
        'approved': stats.approved or 0,
        'posted': stats.posted or 0,
        'rejected': stats.rejected or 0
    }
