# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import logging
from logging import getLogger
import os
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import create_engine, event, and_, or_, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from models import Base, Post, Image, ProcessingRun, ProcessingStatus, UserRole, User, PlatformConnection
from config import Config
from platform_context import PlatformContextManager, PlatformContextError
from security.core.security_utils import sanitize_for_log

logger = getLogger(__name__)


class DatabaseOperationError(Exception):
    """Raised when database operations fail due to invalid conditions"""
    pass


class PlatformValidationError(Exception):
    """Raised when platform-related validation fails"""
    pass

# Create a query logger
query_logger = getLogger('sqlalchemy.query')
query_logger.setLevel(logging.INFO)

class DatabaseManager:
    """Handles platform-aware database operations"""
    
    def __init__(self, config: Config):
        self.config = config
        db_config = config.storage.db_config
        
        # Configure SQLAlchemy engine with optimized settings for SQLite
        engine_kwargs = {
            'echo': False,
            'pool_pre_ping': True,
            'pool_recycle': db_config.pool_recycle,
        }
        
        # For SQLite, use different connection settings
        if 'sqlite' in config.storage.database_url:
            engine_kwargs.update({
                'poolclass': None,  # Disable connection pooling for SQLite
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 30,  # 30 second timeout for SQLite
                    'isolation_level': None,  # Enable autocommit mode
                }
            })
        else:
            # For other databases, use connection pooling
            engine_kwargs.update({
                'poolclass': QueuePool,
                'pool_size': db_config.pool_size,
                'max_overflow': db_config.max_overflow,
                'pool_timeout': db_config.pool_timeout,
            })
        
        self.engine = create_engine(config.storage.database_url, **engine_kwargs)
        
        # Set up query logging
        if db_config.query_logging:
            self._setup_query_logging()
        
        # Use sessionmaker instead of scoped_session for better control
        self.SessionFactory = sessionmaker(bind=self.engine)
        
        # Initialize platform context manager
        self._context_manager = None
        
        # Create tables on initialization
        self.create_tables()
    
    def _setup_query_logging(self):
        """Set up query logging for performance analysis"""
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
            query_logger.debug("Start Query: %s", statement)
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            query_logger.info("Query Complete: %s", statement)
            query_logger.info("Query Time: %f", total)
    
    def create_tables(self):
        """Create database tables"""
        connection = None
        try:
            connection = self.engine.connect()
            Base.metadata.create_all(connection)
            self._create_performance_indexes()
            # logger.info("Database tables and indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def _create_performance_indexes(self):
        """Create additional indexes for better performance"""
        connection = None
        try:
            from sqlalchemy import text
            connection = self.engine.connect()
            
            connection.commit()
            logger.debug("Performance indexes created successfully")
        except Exception as e:
            logger.warning(f"Could not create performance indexes: {e}")
        finally:
            # Ensure connection is properly closed
            if connection:
                connection.close()
    
    def get_session(self):
        """Get database session - caller is responsible for closing"""
        return self.SessionFactory()
    
    def close_session(self, session):
        """Close database session"""
        if session:
            try:
                session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
    
    def get_context_manager(self) -> PlatformContextManager:
        """Get or create platform context manager"""
        if self._context_manager is None:
            # Create a session for the context manager
            session = self.get_session()
            self._context_manager = PlatformContextManager(session)
        return self._context_manager
    
    def set_platform_context(self, user_id: int, platform_connection_id: Optional[int] = None, 
                           session_id: Optional[str] = None):
        """Set platform context for database operations"""
        context_manager = self.get_context_manager()
        return context_manager.set_context(user_id, platform_connection_id, session_id)
    
    def clear_platform_context(self):
        """Clear platform context"""
        if self._context_manager:
            self._context_manager.clear_context()
    
    def require_platform_context(self):
        """Require platform context for operations"""
        context_manager = self.get_context_manager()
        return context_manager.require_context()
    
    def _apply_platform_filter(self, query, model_class):
        """Apply platform filtering to a query"""
        try:
            context_manager = self.get_context_manager()
            return context_manager.apply_platform_filter(query, model_class)
        except PlatformContextError:
            # If no context is set, return unfiltered query
            logger.debug(f"No platform context set for {model_class.__name__} query")
            return query
    
    def _inject_platform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inject platform data into a dictionary"""
        try:
            context_manager = self.get_context_manager()
            return context_manager.inject_platform_data(data)
        except PlatformContextError:
            logger.debug("No platform context set for data injection")
            return data
    
    def get_or_create_post(self, post_id: str, user_id: str, post_url: str, post_content: str = None):
        """
        Get existing post or create new one with platform validation.
        
        Args:
            post_id: Platform-specific post ID
            user_id: User ID who owns the post
            post_url: URL of the post
            post_content: Optional post content
            
        Returns:
            Post object
            
        Raises:
            PlatformValidationError: If validation fails
            DatabaseOperationError: If database operation fails
        """
        # Input validation
        if not post_id or not post_id.strip():
            raise PlatformValidationError("Post ID cannot be empty")
        
        if not user_id or not user_id.strip():
            raise PlatformValidationError("User ID cannot be empty")
        
        if not post_url or not post_url.strip():
            raise PlatformValidationError("Post URL cannot be empty")
        
        # Validate URL format
        post_url = post_url.strip()
        if not post_url.startswith(('http://', 'https://')):
            raise PlatformValidationError("Post URL must start with http:// or https://")
        
        session = self.get_session()
        try:
            # Ensure we have platform context for data operations
            try:
                context_manager = self.get_context_manager()
                context = context_manager.require_context()
            except PlatformContextError as e:
                raise PlatformValidationError(f"Platform context required for post operations: {e}")
            
            # Apply platform filtering to the query
            query = session.query(Post).filter_by(post_id=post_id.strip())
            query = self._apply_platform_filter(query, Post)
            post = query.first()
            
            if not post:
                # Inject platform data when creating
                post_data = {
                    'post_id': post_id.strip(),
                    'user_id': user_id.strip(),
                    'post_url': post_url,
                    'post_content': post_content.strip() if post_content else None
                }
                
                try:
                    post_data = self._inject_platform_data(post_data)
                except PlatformContextError as e:
                    raise PlatformValidationError(f"Failed to inject platform data: {e}")
                
                post = Post(**post_data)
                session.add(post)
                session.commit()
                
                # Refresh the post to ensure it's attached to the session
                query = session.query(Post).filter_by(post_id=post_id.strip())
                query = self._apply_platform_filter(query, Post)
                post = query.first()
                
                if not post:
                    raise DatabaseOperationError("Failed to create or retrieve post after creation")
                
                logger.info("Created new post record: %s for platform %s", 
                           sanitize_for_log(str(post_id)), 
                           sanitize_for_log(str(context.platform_info.get('name', 'unknown'))))
            else:
                logger.debug(f"Retrieved existing post record: {post_id}")
            
            return post
            
        except (PlatformValidationError, DatabaseOperationError):
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in get_or_create_post: {e}")
            raise DatabaseOperationError(f"Database error creating/retrieving post: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in get_or_create_post: {e}")
            raise DatabaseOperationError(f"Unexpected error creating/retrieving post: {e}")
        finally:
            session.close()
    
    def save_image(self, post_id: int, image_url: str, local_path: str, 
                   attachment_index: int, media_type: str = None, 
                   original_filename: str = None, image_post_id: str = None,
                   original_post_date = None):
        """Save image record to database and return the image ID (platform-aware)"""
        session = self.get_session()
        try:
            # Check if image already exists (with platform filtering)
            query = session.query(Image).filter_by(
                post_id=post_id,
                image_url=image_url
            )
            query = self._apply_platform_filter(query, Image)
            existing = query.first()
            
            if existing:
                logger.info(f"Image already exists: {image_url}")
                return existing.id
            
            # Get the post object from the database to ensure it's attached to this session
            post = session.query(Post).get(post_id)
            if not post:
                logger.error(f"Post with ID {post_id} not found")
                return None
            
            # Prepare image data with platform information
            image_data = {
                'post_id': post_id,
                'image_url': image_url,
                'local_path': local_path,
                'attachment_index': attachment_index,
                'media_type': media_type,
                'original_filename': original_filename,
                'image_post_id': image_post_id,
                'original_post_date': original_post_date,
                'status': ProcessingStatus.PENDING
            }
            image_data = self._inject_platform_data(image_data)
            
            try:
                # Try using the ORM
                image = Image(**image_data)
                session.add(image)
                session.commit()
                logger.info(f"Saved image record: {image_url}")
                return image.id
                
            except Exception as enum_error:
                # If there's an enum validation error, try using raw SQL
                logger.warning(f"Error using ORM to save image, falling back to raw SQL: {enum_error}")
                session.rollback()
                
                from sqlalchemy import text
                
                # Build SQL with platform data
                platform_fields = ""
                platform_values = ""
                
                if 'platform_connection_id' in image_data and image_data['platform_connection_id']:
                    platform_fields += ", platform_connection_id"
                    platform_values += f", {image_data['platform_connection_id']}"
                
                if 'platform_type' in image_data and image_data['platform_type']:
                    platform_fields += ", platform_type"
                    platform_values += f", '{image_data['platform_type']}'"
                
                if 'instance_url' in image_data and image_data['instance_url']:
                    platform_fields += ", instance_url"
                    platform_values += f", '{image_data['instance_url']}'"
                
                # Use parameterized query to prevent SQL injection
                base_query = """
                    INSERT INTO images (post_id, image_url, local_path, attachment_index, 
                                      media_type, original_filename, image_post_id, status, 
                                      created_at, updated_at
                """
                
                values_query = """
                    VALUES (:post_id, :image_url, :local_path, :attachment_index, 
                           :media_type, :original_filename, :image_post_id, 
                           'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                """
                
                params = {
                    'post_id': post_id,
                    'image_url': image_url,
                    'local_path': local_path,
                    'attachment_index': attachment_index,
                    'media_type': media_type or '',
                    'original_filename': original_filename or '',
                    'image_post_id': image_post_id or ''
                }
                
                # Add platform fields safely
                if 'platform_connection_id' in image_data and image_data['platform_connection_id']:
                    base_query += ", platform_connection_id"
                    values_query += ", :platform_connection_id"
                    params['platform_connection_id'] = image_data['platform_connection_id']
                
                if 'platform_type' in image_data and image_data['platform_type']:
                    base_query += ", platform_type"
                    values_query += ", :platform_type"
                    params['platform_type'] = image_data['platform_type']
                
                if 'instance_url' in image_data and image_data['instance_url']:
                    base_query += ", instance_url"
                    values_query += ", :instance_url"
                    params['instance_url'] = image_data['instance_url']
                
                full_query = base_query + ")" + values_query + ") RETURNING id"
                
                result = session.execute(text(full_query), params)
                
                image_id = result.scalar()
                session.commit()
                logger.info(f"Saved image record using raw SQL: {image_url}")
                return image_id
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in save_image: {e}")
            raise
        finally:
            session.close()
    
    def update_image_caption(self, image_id: int, generated_caption: str, 
                           quality_metrics: dict = None, prompt_used: str = None):
        """
        Update image with generated caption and quality metrics with validation.
        
        Args:
            image_id: ID of the image to update
            generated_caption: Generated caption text
            quality_metrics: Optional quality metrics dictionary
            prompt_used: Optional prompt that was used for generation
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            PlatformValidationError: If validation fails
            DatabaseOperationError: If database operation fails
        """
        # Input validation
        if not image_id or image_id <= 0:
            raise PlatformValidationError("Invalid image_id provided")
        
        if not generated_caption or not generated_caption.strip():
            raise PlatformValidationError("Generated caption cannot be empty")
        
        # Validate caption length
        max_caption_length = 500  # From config
        if len(generated_caption) > max_caption_length:
            logger.warning(f"Caption length {len(generated_caption)} exceeds maximum {max_caption_length}, truncating")
            generated_caption = generated_caption[:max_caption_length].strip()
        
        session = self.get_session()
        try:
            # Ensure we have platform context
            try:
                context_manager = self.get_context_manager()
                context = context_manager.require_context()
            except PlatformContextError as e:
                raise PlatformValidationError(f"Platform context required for image operations: {e}")
            
            # Get the image with platform filtering
            query = session.query(Image).filter_by(id=image_id)
            query = self._apply_platform_filter(query, Image)
            image = query.first()
            
            if not image:
                raise PlatformValidationError(f"Image {image_id} not found or not accessible in current platform context")
            
            # Validate that the image is in a state that allows caption updates
            if image.status == ProcessingStatus.APPROVED:
                logger.warning(f"Updating caption for already approved image {image_id}")
            
            try:
                # Update the image
                image.generated_caption = generated_caption.strip()
                image.final_caption = generated_caption.strip()  # Default to generated
                
                # Update prompt if provided
                if prompt_used:
                    if len(prompt_used) > 1000:  # Reasonable limit for prompt storage
                        logger.warning(f"Prompt length {len(prompt_used)} is very long, truncating")
                        prompt_used = prompt_used[:1000]
                    image.prompt_used = prompt_used.strip()
                
                # Update quality metrics if provided
                if quality_metrics:
                    if not isinstance(quality_metrics, dict):
                        raise PlatformValidationError("Quality metrics must be a dictionary")
                    
                    # Validate quality score
                    overall_score = quality_metrics.get('overall_score', 0)
                    if not isinstance(overall_score, (int, float)) or overall_score < 0 or overall_score > 100:
                        logger.warning(f"Invalid quality score {overall_score}, setting to 0")
                        overall_score = 0
                    
                    image.caption_quality_score = overall_score
                    image.needs_special_review = bool(quality_metrics.get('needs_review', False))
                    
                    # Store detailed quality metrics as JSON in reviewer_notes if not already set
                    if not image.reviewer_notes:
                        feedback = quality_metrics.get('feedback', '')
                        if feedback and len(feedback) > 2000:  # Reasonable limit
                            logger.warning(f"Feedback length {len(feedback)} is very long, truncating")
                            feedback = feedback[:2000]
                        image.reviewer_notes = feedback
                
                # Update timestamp
                image.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                logger.info("Updated caption for image %s in platform %s", 
                           sanitize_for_log(str(image_id)), 
                           sanitize_for_log(str(context.platform_info.get('name', 'unknown'))))
                return True
                
            except Exception as orm_error:
                # If ORM approach fails, try raw SQL with platform filtering
                logger.warning(f"Error using ORM to update caption, falling back to raw SQL: {orm_error}")
                session.rollback()
                
                from sqlalchemy import text
                
                # Escape single quotes in text fields
                safe_caption = generated_caption.replace("'", "''") if generated_caption else ""
                safe_prompt = prompt_used.replace("'", "''") if prompt_used else ""
                
                # Build quality metrics fields
                quality_score = 0
                needs_review = False
                feedback = ""
                
                if quality_metrics:
                    quality_score = quality_metrics.get('overall_score', 0)
                    needs_review = quality_metrics.get('needs_review', False)
                    feedback = quality_metrics.get('feedback', '').replace("'", "''")
                
                # Build platform filter for raw SQL
                platform_filter = ""
                try:
                    platform_type = context.platform_info['platform_type'].replace("'", "''")
                    instance_url = context.platform_info['instance_url'].replace("'", "''")
                    platform_filter = f" AND platform_type = '{platform_type}' AND instance_url = '{instance_url}'"
                except (KeyError, AttributeError):
                    if context.platform_connection_id:
                        platform_filter = f" AND platform_connection_id = {context.platform_connection_id}"
                
                # Use parameterized query to prevent SQL injection
                update_query = """
                    UPDATE images 
                    SET generated_caption = :caption,
                        final_caption = :caption,
                        prompt_used = :prompt,
                        caption_quality_score = :quality_score,
                        needs_special_review = :needs_review,
                        reviewer_notes = :feedback,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :image_id
                """
                
                params = {
                    'caption': generated_caption,
                    'prompt': prompt_used or '',
                    'quality_score': quality_score,
                    'needs_review': needs_review,
                    'feedback': feedback,
                    'image_id': image_id
                }
                
                # Add platform filtering safely
                if context.platform_connection_id:
                    update_query += " AND platform_connection_id = :platform_connection_id"
                    params['platform_connection_id'] = context.platform_connection_id
                elif context.platform_info.get('platform_type') and context.platform_info.get('instance_url'):
                    update_query += " AND platform_type = :platform_type AND instance_url = :instance_url"
                    params['platform_type'] = context.platform_info['platform_type']
                    params['instance_url'] = context.platform_info['instance_url']
                
                result = session.execute(text(update_query), params)
                
                if result.rowcount == 0:
                    raise DatabaseOperationError(f"No image updated - image {image_id} may not exist or not accessible in current platform context")
                
                session.commit()
                logger.info(f"Updated caption for image {image_id} using raw SQL with platform filtering")
                return True
                
        except (PlatformValidationError, DatabaseOperationError):
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in update_image_caption: {e}")
            raise DatabaseOperationError(f"Database error updating image caption: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in update_image_caption: {e}")
            raise DatabaseOperationError(f"Unexpected error updating image caption: {e}")
        finally:
            session.close()

    
    def get_pending_images(self, limit: int = 50):
        """Get images pending review (platform-aware)"""
        session = self.get_session()
        try:
            query = session.query(Image).filter_by(status=ProcessingStatus.PENDING)
            query = self._apply_platform_filter(query, Image)
            images = query.order_by(
                Image.original_post_date.desc().nullslast(), 
                Image.updated_at.desc()
            ).limit(limit).all()
            return images
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_pending_images: {e}")
            raise
        finally:
            session.close()
    
    def get_approved_images(self, limit: int = 50):
        """Get images approved for posting (platform-aware)"""
        session = self.get_session()
        try:
            query = session.query(Image).filter_by(status=ProcessingStatus.APPROVED)
            query = self._apply_platform_filter(query, Image)
            images = query.order_by(
                Image.original_post_date.desc().nullslast(), 
                Image.updated_at.desc()
            ).limit(limit).all()
            return images
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_approved_images: {e}")
            raise
        finally:
            session.close()
    
    def review_image(self, image_id: int, reviewed_caption: str, 
                     status: ProcessingStatus, reviewer_notes: str = None):
        """Update image with review results"""
        session = self.get_session()
        try:
            image = session.query(Image).get(image_id)
            if image:
                image.reviewed_caption = reviewed_caption
                image.final_caption = reviewed_caption
                image.status = status
                image.reviewer_notes = reviewer_notes
                image.reviewed_at = datetime.now(timezone.utc)
                session.commit()
                logger.info(f"Reviewed image {image_id} with status {status}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in review_image: {e}")
            raise
        finally:
            session.close()
    
    def mark_image_posted(self, image_id: int):
        """Mark image as posted"""
        session = self.get_session()
        try:
            image = session.query(Image).get(image_id)
            if image:
                image.status = ProcessingStatus.POSTED
                image.posted_at = datetime.now(timezone.utc)
                session.commit()
                logger.info(f"Marked image {image_id} as posted")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in mark_image_posted: {e}")
            raise
        finally:
            session.close()
    
    def is_image_processed(self, image_url: str) -> bool:
        """Check if image has been processed before (platform-aware)"""
        session = self.get_session()
        try:
            try:
                # Try using ORM first with platform filtering
                query = session.query(Image).filter_by(image_url=image_url)
                query = self._apply_platform_filter(query, Image)
                image = query.first()
                
                # Only consider an image as processed if it has been successfully posted or approved
                if image and image.status in [ProcessingStatus.POSTED, ProcessingStatus.APPROVED]:
                    return True
                # For all other statuses (PENDING, REJECTED, ERROR), we'll reprocess the image
                return False
                
            except Exception as orm_error:
                # If ORM approach fails, try raw SQL with platform filtering
                logger.warning(f"Error using ORM to check image status, falling back to raw SQL: {orm_error}")
                
                from sqlalchemy import text
                # Escape single quotes in URL
                safe_url = image_url.replace("'", "''")
                
                # Build platform filter for raw SQL
                platform_filter = ""
                try:
                    context = self.require_platform_context()
                    if context.platform_connection_id:
                        platform_filter = f" AND platform_connection_id = {context.platform_connection_id}"
                    elif context.platform_info.get('platform_type') and context.platform_info.get('instance_url'):
                        platform_type = context.platform_info['platform_type']
                        instance_url = context.platform_info['instance_url'].replace("'", "''")
                        platform_filter = f" AND platform_type = '{platform_type}' AND instance_url = '{instance_url}'"
                except PlatformContextError:
                    pass  # No platform filtering if no context
                
                # Use parameterized query to prevent SQL injection
                check_query = "SELECT status FROM images WHERE image_url = :image_url"
                params = {'image_url': image_url}
                
                # Add platform filtering safely
                if context.platform_connection_id:
                    check_query += " AND platform_connection_id = :platform_connection_id"
                    params['platform_connection_id'] = context.platform_connection_id
                elif context.platform_info.get('platform_type') and context.platform_info.get('instance_url'):
                    check_query += " AND platform_type = :platform_type AND instance_url = :instance_url"
                    params['platform_type'] = context.platform_info['platform_type']
                    params['instance_url'] = context.platform_info['instance_url']
                
                result = session.execute(text(check_query), params).fetchone()
                
                if result and result[0] in ['posted', 'approved']:
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Database error in is_image_processed: {e}")
            return False
        finally:
            session.close()
    
    def get_processing_stats(self, platform_aware: bool = True):
        """Get processing statistics (optionally platform-aware)"""
        session = self.get_session()
        try:
            if platform_aware:
                # Get platform-specific statistics
                post_query = self._apply_platform_filter(session.query(Post), Post)
                image_query = self._apply_platform_filter(session.query(Image), Image)
                
                stats = {
                    'total_posts': post_query.count(),
                    'total_images': image_query.count(),
                    'pending_review': self._apply_platform_filter(
                        session.query(Image).filter_by(status=ProcessingStatus.PENDING), Image
                    ).count(),
                    'approved': self._apply_platform_filter(
                        session.query(Image).filter_by(status=ProcessingStatus.APPROVED), Image
                    ).count(),
                    'posted': self._apply_platform_filter(
                        session.query(Image).filter_by(status=ProcessingStatus.POSTED), Image
                    ).count(),
                    'rejected': self._apply_platform_filter(
                        session.query(Image).filter_by(status=ProcessingStatus.REJECTED), Image
                    ).count(),
                }
                
                # Add platform information if context is available
                try:
                    context = self.require_platform_context()
                    stats['platform_info'] = context.platform_info
                except PlatformContextError:
                    stats['platform_info'] = None
                    
            else:
                # Get global statistics
                stats = {
                    'total_posts': session.query(Post).count(),
                    'total_images': session.query(Image).count(),
                    'pending_review': session.query(Image).filter_by(status=ProcessingStatus.PENDING).count(),
                    'approved': session.query(Image).filter_by(status=ProcessingStatus.APPROVED).count(),
                    'posted': session.query(Image).filter_by(status=ProcessingStatus.POSTED).count(),
                    'rejected': session.query(Image).filter_by(status=ProcessingStatus.REJECTED).count(),
                }
            
            return stats
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_processing_stats: {e}")
            return {}
        finally:
            session.close()
    
    def get_platform_processing_stats(self, platform_connection_id: int):
        """Get processing statistics for a specific platform"""
        session = self.get_session()
        try:
            # Get statistics for the specific platform
            stats = {
                'total_posts': session.query(Post).filter_by(platform_connection_id=platform_connection_id).count(),
                'total_images': session.query(Image).filter_by(platform_connection_id=platform_connection_id).count(),
                'pending_review': session.query(Image).filter_by(
                    platform_connection_id=platform_connection_id,
                    status=ProcessingStatus.PENDING
                ).count(),
                'approved': session.query(Image).filter_by(
                    platform_connection_id=platform_connection_id,
                    status=ProcessingStatus.APPROVED
                ).count(),
                'posted': session.query(Image).filter_by(
                    platform_connection_id=platform_connection_id,
                    status=ProcessingStatus.POSTED
                ).count(),
                'rejected': session.query(Image).filter_by(
                    platform_connection_id=platform_connection_id,
                    status=ProcessingStatus.REJECTED
                ).count(),
            }
            
            return stats
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_platform_processing_stats: {e}")
            return {}
        finally:
            session.close()
    
    def get_platform_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics for all platforms (for a specific user or globally)"""
        session = self.get_session()
        try:
            platform_stats = {}
            
            if user_id:
                # Get statistics for a specific user's platforms
                platforms = session.query(PlatformConnection).filter_by(
                    user_id=user_id,
                    is_active=True
                ).all()
            else:
                # Get statistics for all platforms
                platforms = session.query(PlatformConnection).filter_by(is_active=True).all()
            
            for platform in platforms:
                # Get platform-specific statistics directly
                stats = self.get_platform_processing_stats(platform.id)
                platform_stats[f"{platform.name} ({platform.platform_type})"] = stats
            
            return platform_stats
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_platform_statistics: {e}")
            return {}
        finally:
            session.close()
    
    def get_user_platform_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of user's platform connections and their activity"""
        session = self.get_session()
        try:
            platforms = session.query(PlatformConnection).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            summary = {
                'total_platforms': len(platforms),
                'platforms': [],
                'combined_stats': {
                    'total_posts': 0,
                    'total_images': 0,
                    'pending_review': 0,
                    'approved': 0,
                    'posted': 0,
                    'rejected': 0
                }
            }
            
            for platform in platforms:
                # Get stats for this platform
                with self.get_context_manager().context_scope(user_id, platform.id):
                    stats = self.get_processing_stats(platform_aware=True)
                
                platform_info = {
                    'id': platform.id,
                    'name': platform.name,
                    'platform_type': platform.platform_type,
                    'instance_url': platform.instance_url,
                    'username': platform.username,
                    'is_default': platform.is_default,
                    'last_used': platform.last_used,
                    'stats': stats
                }
                
                summary['platforms'].append(platform_info)
                
                # Add to combined stats
                for key in summary['combined_stats']:
                    if key in stats:
                        summary['combined_stats'][key] += stats[key]
            
            return summary
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_user_platform_summary: {e}")
            return {}
        finally:
            session.close()
            
    # User management functions
    def get_user_by_username(self, username):
        """Get user by username"""
        session = self.get_session()
        try:
            return session.query(User).filter_by(username=username).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_user_by_username: {e}")
            return None
        finally:
            session.close()
            
    def get_user_by_email(self, email):
        """Get user by email"""
        session = self.get_session()
        try:
            return session.query(User).filter_by(email=email).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_user_by_email: {e}")
            return None
        finally:
            session.close()
            
    def create_user(self, username, email, password, role=UserRole.VIEWER):
        """Create a new user"""
        session = self.get_session()
        try:
            # Check if username or email already exists
            existing = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing:
                logger.warning(f"User with username '{sanitize_for_log(username)}' or email '{sanitize_for_log(email)}' already exists")
                return None
                
            user = User(
                username=username,
                email=email,
                role=role,
                is_active=True
            )
            user.set_password(password)
            
            session.add(user)
            session.commit()
            
            # Refresh the user to ensure it's properly attached
            session.refresh(user)
            user_id = user.id
            username_copy = user.username
            
            logger.info(f"Created new user: {sanitize_for_log(username)}")
            
            # Return the user ID instead of the object to avoid session issues
            return user_id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in create_user: {e}")
            return None
        finally:
            session.close()
            
    def update_user(self, user_id, username=None, email=None, password=None, role=None, is_active=None):
        """Update an existing user"""
        session = self.get_session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                logger.warning(f"User with ID {user_id} not found")
                return False
                
            if username is not None:
                # Check if username is already taken by another user
                existing = session.query(User).filter(
                    (User.username == username) & (User.id != user_id)
                ).first()
                if existing:
                    logger.warning(f"Username '{sanitize_for_log(username)}' is already taken")
                    return False
                user.username = username
                
            if email is not None:
                # Check if email is already taken by another user
                existing = session.query(User).filter(
                    (User.email == email) & (User.id != user_id)
                ).first()
                if existing:
                    logger.warning(f"Email '{sanitize_for_log(email)}' is already taken")
                    return False
                user.email = email
                
            if password is not None:
                user.set_password(password)
                
            if role is not None:
                user.role = role
                
            if is_active is not None:
                user.is_active = is_active
                
            session.commit()
            logger.info(f"Updated user: {sanitize_for_log(user.username)}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in update_user: {e}")
            return False
        finally:
            session.close()
            
    def delete_user(self, user_id):
        """Delete a user"""
        session = self.get_session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                logger.warning(f"User with ID {user_id} not found")
                return False
                
            username = user.username
            session.delete(user)
            session.commit()
            logger.info(f"Deleted user: {sanitize_for_log(username)}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in delete_user: {e}")
            return False
        finally:
            session.close()
            
    def get_all_users(self):
        """Get all users"""
        session = self.get_session()
        try:
            return session.query(User).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_all_users: {e}")
            return []
        finally:
            session.close()
    
    # Platform Connection Management
    def create_platform_connection(self, user_id: int, name: str, platform_type: str, 
                                 instance_url: str, username: str, access_token: str,
                                 client_key: Optional[str] = None, client_secret: Optional[str] = None,
                                 is_default: bool = False) -> Optional[PlatformConnection]:
        """
        Create a new platform connection with comprehensive validation.
        
        Args:
            user_id: ID of the user creating the connection
            name: Friendly name for the connection
            platform_type: Type of platform ('pixelfed', 'mastodon')
            instance_url: URL of the platform instance
            username: Username on the platform
            access_token: API access token
            client_key: Optional client key (for Mastodon)
            client_secret: Optional client secret (for Mastodon)
            is_default: Whether this should be the default platform
            
        Returns:
            Created PlatformConnection object or None if creation failed
            
        Raises:
            PlatformValidationError: If validation fails
            DatabaseOperationError: If database operation fails
        """
        # Input validation
        if not user_id or user_id <= 0:
            raise PlatformValidationError("Invalid user_id provided")
        
        if not name or not name.strip():
            raise PlatformValidationError("Platform connection name cannot be empty")
        
        if platform_type not in ['pixelfed', 'mastodon']:
            raise PlatformValidationError(f"Invalid platform_type: {platform_type}. Must be 'pixelfed' or 'mastodon'")
        
        if not instance_url or not instance_url.strip():
            raise PlatformValidationError("Instance URL cannot be empty")
        
        # Normalize instance URL
        instance_url = instance_url.strip().rstrip('/')
        if not instance_url.startswith(('http://', 'https://')):
            raise PlatformValidationError("Instance URL must start with http:// or https://")
        
        if not access_token or not access_token.strip():
            raise PlatformValidationError("Access token cannot be empty")
        
        # Validate Mastodon-specific requirements
        if platform_type == 'mastodon':
            if not client_key or not client_secret:
                logger.warning(f"Mastodon platform connection created without client credentials")
        
        session = self.get_session()
        try:
            # Check if user exists and is active
            user = session.query(User).get(user_id)
            if not user:
                raise PlatformValidationError(f"User with ID {user_id} not found")
            
            if not user.is_active:
                raise PlatformValidationError(f"User {user.username} is not active")
            
            # Check for duplicate names for this user
            existing = session.query(PlatformConnection).filter_by(
                user_id=user_id,
                name=name.strip()
            ).first()
            
            if existing:
                raise PlatformValidationError(f"Platform connection with name '{name}' already exists for user {user.username}")
            
            # Check for duplicate instance/username combination
            if username:
                existing = session.query(PlatformConnection).filter_by(
                    user_id=user_id,
                    instance_url=instance_url,
                    username=username.strip()
                ).first()
                
                if existing:
                    raise PlatformValidationError(f"Platform connection for {username}@{instance_url} already exists for user {user.username}")
            
            # If this is set as default, unset other defaults
            if is_default:
                updated_count = session.query(PlatformConnection).filter_by(
                    user_id=user_id,
                    is_default=True
                ).update({'is_default': False})
                
                if updated_count > 0:
                    logger.info(f"Unset {updated_count} existing default platform(s) for user {user.username}")
            
            # Create platform connection
            platform_connection = PlatformConnection(
                user_id=user_id,
                name=name.strip(),
                platform_type=platform_type,
                instance_url=instance_url,
                username=username.strip() if username else None,
                access_token=access_token.strip(),
                client_key=client_key.strip() if client_key else None,
                client_secret=client_secret.strip() if client_secret else None,
                is_default=is_default,
                is_active=True
            )
            
            session.add(platform_connection)
            session.flush()  # Flush to get the ID without committing
            
            # Test the connection if possible
            try:
                success, message = platform_connection.test_connection()
                if not success:
                    logger.warning(f"Platform connection test failed: {message}")
                    # Don't fail creation, but log the warning
            except Exception as test_error:
                logger.warning(f"Could not test platform connection: {test_error}")
            
            session.commit()
            
            logger.info(f"Created platform connection '{sanitize_for_log(name)}' for user {sanitize_for_log(user.username)} (ID: {platform_connection.id})")
            return platform_connection
            
        except (PlatformValidationError, DatabaseOperationError):
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in create_platform_connection: {e}")
            raise DatabaseOperationError(f"Failed to create platform connection: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in create_platform_connection: {e}")
            raise DatabaseOperationError(f"Unexpected error creating platform connection: {e}")
        finally:
            session.close()
    
    def get_platform_connection(self, connection_id: int) -> Optional[PlatformConnection]:
        """Get platform connection by ID"""
        session = self.get_session()
        try:
            return session.query(PlatformConnection).get(connection_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_platform_connection: {e}")
            return None
        finally:
            session.close()
    
    def get_user_platform_connections(self, user_id: int, active_only: bool = True) -> List[PlatformConnection]:
        """Get all platform connections for a user"""
        session = self.get_session()
        try:
            query = session.query(PlatformConnection).filter_by(user_id=user_id)
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            return query.order_by(
                PlatformConnection.is_default.desc(),
                PlatformConnection.name
            ).all()
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_user_platform_connections: {e}")
            return []
        finally:
            session.close()
    
    def update_platform_connection(self, connection_id: int, user_id: Optional[int] = None, **kwargs) -> bool:
        """
        Update platform connection with validation.
        
        Args:
            connection_id: ID of the platform connection to update
            user_id: Optional user ID for additional validation
            **kwargs: Fields to update
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            PlatformValidationError: If validation fails
            DatabaseOperationError: If database operation fails
        """
        if not connection_id or connection_id <= 0:
            raise PlatformValidationError("Invalid connection_id provided")
        
        # Validate updatable fields
        allowed_fields = {
            'name', 'platform_type', 'instance_url', 'username', 
            'access_token', 'client_key', 'client_secret', 
            'is_active', 'is_default'
        }
        
        invalid_fields = set(kwargs.keys()) - allowed_fields
        if invalid_fields:
            raise PlatformValidationError(f"Invalid fields for update: {invalid_fields}")
        
        session = self.get_session()
        try:
            platform_connection = session.query(PlatformConnection).get(connection_id)
            if not platform_connection:
                raise PlatformValidationError(f"Platform connection {connection_id} not found")
            
            # Verify user ownership if user_id provided
            if user_id and platform_connection.user_id != user_id:
                raise PlatformValidationError(f"Platform connection {connection_id} does not belong to user {user_id}")
            
            # Validate specific field updates
            if 'name' in kwargs:
                new_name = kwargs['name']
                if not new_name or not new_name.strip():
                    raise PlatformValidationError("Platform connection name cannot be empty")
                
                # Check for duplicate names (excluding current connection)
                existing = session.query(PlatformConnection).filter(
                    PlatformConnection.user_id == platform_connection.user_id,
                    PlatformConnection.name == new_name.strip(),
                    PlatformConnection.id != connection_id
                ).first()
                
                if existing:
                    raise PlatformValidationError(f"Platform connection with name '{new_name}' already exists")
                
                kwargs['name'] = new_name.strip()
            
            if 'platform_type' in kwargs:
                if kwargs['platform_type'] not in ['pixelfed', 'mastodon']:
                    raise PlatformValidationError(f"Invalid platform_type: {kwargs['platform_type']}")
            
            if 'instance_url' in kwargs:
                instance_url = kwargs['instance_url']
                if not instance_url or not instance_url.strip():
                    raise PlatformValidationError("Instance URL cannot be empty")
                
                instance_url = instance_url.strip().rstrip('/')
                if not instance_url.startswith(('http://', 'https://')):
                    raise PlatformValidationError("Instance URL must start with http:// or https://")
                
                kwargs['instance_url'] = instance_url
            
            if 'access_token' in kwargs:
                if not kwargs['access_token'] or not kwargs['access_token'].strip():
                    raise PlatformValidationError("Access token cannot be empty")
                kwargs['access_token'] = kwargs['access_token'].strip()
            
            # Handle setting as default
            if kwargs.get('is_default', False):
                # Unset other defaults for this user
                updated_count = session.query(PlatformConnection).filter(
                    PlatformConnection.user_id == platform_connection.user_id,
                    PlatformConnection.is_default == True,
                    PlatformConnection.id != connection_id
                ).update({'is_default': False})
                
                if updated_count > 0:
                    logger.info(f"Unset {updated_count} existing default platform(s) for user {platform_connection.user_id}")
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(platform_connection, key):
                    setattr(platform_connection, key, value)
            
            platform_connection.updated_at = datetime.now(timezone.utc)
            
            # Test connection if credentials were updated
            if any(field in kwargs for field in ['access_token', 'client_key', 'client_secret', 'instance_url']):
                try:
                    success, message = platform_connection.test_connection()
                    if not success:
                        logger.warning(f"Updated platform connection test failed: {message}")
                except Exception as test_error:
                    logger.warning(f"Could not test updated platform connection: {test_error}")
            
            session.commit()
            
            logger.info(f"Updated platform connection {sanitize_for_log(str(connection_id))}")
            return True
            
        except (PlatformValidationError, DatabaseOperationError):
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in update_platform_connection: {e}")
            raise DatabaseOperationError(f"Failed to update platform connection: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in update_platform_connection: {e}")
            raise DatabaseOperationError(f"Unexpected error updating platform connection: {e}")
        finally:
            session.close()
    
    def delete_platform_connection(self, connection_id: int, user_id: Optional[int] = None, 
                                  force: bool = False) -> bool:
        """
        Delete platform connection with validation and data protection.
        
        Args:
            connection_id: ID of the platform connection to delete
            user_id: Optional user ID for additional validation
            force: If True, delete even if there's associated data
            
        Returns:
            True if deletion successful, False otherwise
            
        Raises:
            PlatformValidationError: If validation fails
            DatabaseOperationError: If database operation fails
        """
        if not connection_id or connection_id <= 0:
            raise PlatformValidationError("Invalid connection_id provided")
        
        session = self.get_session()
        try:
            platform_connection = session.query(PlatformConnection).get(connection_id)
            if not platform_connection:
                raise PlatformValidationError(f"Platform connection {connection_id} not found")
            
            # Verify user ownership if user_id provided
            if user_id and platform_connection.user_id != user_id:
                raise PlatformValidationError(f"Platform connection {connection_id} does not belong to user {user_id}")
            
            user_id = platform_connection.user_id
            was_default = platform_connection.is_default
            platform_name = platform_connection.name
            
            # Check for associated data unless force is True
            if not force:
                # Check for posts
                post_count = session.query(Post).filter_by(
                    platform_connection_id=connection_id
                ).count()
                
                # Check for images
                image_count = session.query(Image).filter_by(
                    platform_connection_id=connection_id
                ).count()
                
                # Check for processing runs
                run_count = session.query(ProcessingRun).filter_by(
                    platform_connection_id=connection_id
                ).count()
                
                if post_count > 0 or image_count > 0 or run_count > 0:
                    raise PlatformValidationError(
                        f"Cannot delete platform connection '{platform_name}': "
                        f"has {post_count} posts, {image_count} images, and {run_count} processing runs. "
                        f"Use force=True to delete anyway."
                    )
            
            # Check if this is the user's only platform connection
            other_platforms = session.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.id != connection_id,
                PlatformConnection.is_active == True
            ).count()
            
            if other_platforms == 0:
                logger.warning(f"Deleting the last platform connection for user {user_id}")
            
            # Delete the platform connection
            session.delete(platform_connection)
            
            # If this was the default, set another active platform as default
            if was_default and other_platforms > 0:
                other_platform = session.query(PlatformConnection).filter(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.is_active == True,
                    PlatformConnection.id != connection_id
                ).first()
                
                if other_platform:
                    other_platform.is_default = True
                    logger.info(f"Set platform {sanitize_for_log(other_platform.name)} as new default for user {sanitize_for_log(str(user_id))}")
            
            session.commit()
            logger.info(f"Deleted platform connection '{sanitize_for_log(platform_name)}' (ID: {connection_id})")
            return True
            
        except (PlatformValidationError, DatabaseOperationError):
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in delete_platform_connection: {e}")
            raise DatabaseOperationError(f"Failed to delete platform connection: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in delete_platform_connection: {e}")
            raise DatabaseOperationError(f"Unexpected error deleting platform connection: {e}")
        finally:
            session.close()
    
    def set_default_platform(self, user_id: int, connection_id: int) -> bool:
        """Set a platform connection as default for a user"""
        session = self.get_session()
        try:
            # Verify the platform belongs to the user
            platform_connection = session.query(PlatformConnection).filter_by(
                id=connection_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not platform_connection:
                logger.error(f"Platform connection {connection_id} not found or not accessible for user {user_id}")
                return False
            
            # Unset other defaults
            session.query(PlatformConnection).filter_by(
                user_id=user_id,
                is_default=True
            ).update({'is_default': False})
            
            # Set new default
            platform_connection.is_default = True
            session.commit()
            
            logger.info(f"Set platform {sanitize_for_log(platform_connection.name)} as default for user {sanitize_for_log(str(user_id))}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in set_default_platform: {e}")
            return False
        finally:
            session.close()
    
    def test_platform_connection(self, connection_id: int, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Test a platform connection with validation.
        
        Args:
            connection_id: ID of the platform connection to test
            user_id: Optional user ID for ownership validation
            
        Returns:
            Tuple of (success, message)
            
        Raises:
            PlatformValidationError: If validation fails
        """
        if not connection_id or connection_id <= 0:
            raise PlatformValidationError("Invalid connection_id provided")
        
        session = self.get_session()
        try:
            platform_connection = session.query(PlatformConnection).get(connection_id)
            if not platform_connection:
                return False, f"Platform connection {connection_id} not found"
            
            # Verify user ownership if user_id provided
            if user_id and platform_connection.user_id != user_id:
                raise PlatformValidationError(f"Platform connection {connection_id} does not belong to user {user_id}")
            
            if not platform_connection.is_active:
                return False, f"Platform connection {platform_connection.name} is not active"
            
            # Validate required fields
            if not platform_connection.instance_url:
                return False, "Platform connection missing instance URL"
            
            if not platform_connection.access_token:
                return False, "Platform connection missing access token"
            
            # Test the connection
            try:
                success, message = platform_connection.test_connection()
                
                # Update the connection status based on test result
                if success:
                    platform_connection.last_used = datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"Platform connection test successful: {platform_connection.name}")
                else:
                    logger.warning(f"Platform connection test failed: {platform_connection.name} - {message}")
                
                return success, message
                
            except Exception as test_error:
                error_msg = f"Connection test failed with error: {str(test_error)}"
                logger.error(f"Error testing platform connection {connection_id}: {test_error}")
                return False, error_msg
            
        except PlatformValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error in test_platform_connection: {e}")
            return False, f"Database error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error testing platform connection {connection_id}: {e}")
            return False, f"Unexpected error: {str(e)}"
        finally:
            session.close()
    
    # Platform Switching and Session Management
    def switch_platform_context(self, user_id: int, platform_connection_id: int, 
                              session_id: Optional[str] = None) -> bool:
        """
        Switch platform context for a user with validation.
        
        Args:
            user_id: ID of the user
            platform_connection_id: ID of the platform connection to switch to
            session_id: Optional session ID for tracking
            
        Returns:
            True if switch successful, False otherwise
            
        Raises:
            PlatformValidationError: If validation fails
            DatabaseOperationError: If database operation fails
        """
        if not user_id or user_id <= 0:
            raise PlatformValidationError("Invalid user_id provided")
        
        if not platform_connection_id or platform_connection_id <= 0:
            raise PlatformValidationError("Invalid platform_connection_id provided")
        
        session = self.get_session()
        try:
            # Verify the platform connection exists and belongs to the user
            platform_connection = session.query(PlatformConnection).filter_by(
                id=platform_connection_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not platform_connection:
                raise PlatformValidationError(
                    f"Platform connection {platform_connection_id} not found or not accessible for user {user_id}"
                )
            
            # Verify user exists and is active
            user = session.query(User).get(user_id)
            if not user:
                raise PlatformValidationError(f"User {user_id} not found")
            
            if not user.is_active:
                raise PlatformValidationError(f"User {user.username} is not active")
            
            # Test the platform connection before switching
            try:
                success, message = platform_connection.test_connection()
                if not success:
                    logger.warning(f"Platform connection test failed during switch: {message}")
                    # Don't fail the switch, but log the warning
            except Exception as test_error:
                logger.warning(f"Could not test platform connection during switch: {test_error}")
            
            # Switch the context
            context_manager = self.get_context_manager()
            context_manager.set_context(user_id, platform_connection_id, session_id)
            
            # Update last_used timestamp for the platform
            platform_connection.last_used = datetime.now(timezone.utc)
            session.commit()
            
            logger.info(f"Switched platform context for user {sanitize_for_log(user.username)} to platform {sanitize_for_log(platform_connection.name)}")
            return True
            
        except (PlatformValidationError, DatabaseOperationError):
            session.rollback()
            raise
        except PlatformContextError as e:
            session.rollback()
            logger.error(f"Failed to switch platform context: {e}")
            raise DatabaseOperationError(f"Failed to switch platform context: {e}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in switch_platform_context: {e}")
            raise DatabaseOperationError(f"Database error switching platform context: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in switch_platform_context: {e}")
            raise DatabaseOperationError(f"Unexpected error switching platform context: {e}")
        finally:
            session.close()
    
    # UserSession methods removed - using Flask-based session management
    
    # Data Isolation Validation
    def validate_data_isolation(self, user_id: int) -> Dict[str, Any]:
        """Validate that data isolation is working correctly for a user's platforms"""
        session = self.get_session()
        try:
            validation_results = {
                'user_id': user_id,
                'platforms_tested': 0,
                'isolation_issues': [],
                'cross_platform_data': [],
                'validation_passed': True
            }
            
            # Get user's platforms
            platforms = session.query(PlatformConnection).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            validation_results['platforms_tested'] = len(platforms)
            
            # Test each platform's data isolation
            for platform in platforms:
                with self.get_context_manager().context_scope(user_id, platform.id):
                    # Get platform-specific data
                    posts = self._apply_platform_filter(session.query(Post), Post).all()
                    images = self._apply_platform_filter(session.query(Image), Image).all()
                    
                    # Check if any data belongs to other platforms
                    for post in posts:
                        if (post.platform_connection_id and 
                            post.platform_connection_id != platform.id):
                            validation_results['isolation_issues'].append({
                                'type': 'post',
                                'id': post.id,
                                'expected_platform': platform.id,
                                'actual_platform': post.platform_connection_id
                            })
                            validation_results['validation_passed'] = False
                    
                    for image in images:
                        if (image.platform_connection_id and 
                            image.platform_connection_id != platform.id):
                            validation_results['isolation_issues'].append({
                                'type': 'image',
                                'id': image.id,
                                'expected_platform': platform.id,
                                'actual_platform': image.platform_connection_id
                            })
                            validation_results['validation_passed'] = False
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating data isolation: {e}")
            validation_results['validation_passed'] = False
            validation_results['error'] = str(e)
            return validation_results
        finally:
            session.close()