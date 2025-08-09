# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Platform-Aware Caption Generator Adapter

This module adapts the existing caption generation logic to work with database-stored
credentials and provides progress callback integration for web-based generation.
"""

import logging
import asyncio
from typing import Optional, Callable, Dict, Any, Tuple
from datetime import datetime, timezone
import os

from models import PlatformConnection, GenerationResults, CaptionGenerationSettings
from database import DatabaseManager
from activitypub_client import ActivityPubClient
from image_processor import ImageProcessor
from ollama_caption_generator import OllamaCaptionGenerator
from config import Config
from security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

# Create a dedicated logger for caption generation steps
caption_step_logger = logging.getLogger('caption_generation_steps')
caption_step_logger.setLevel(logging.INFO)

# Create file handler for caption generation steps if not already exists
if not caption_step_logger.handlers:
    logs_dir = os.getenv('LOGS_DIR', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    step_handler = logging.FileHandler(os.path.join(logs_dir, 'caption_generation_steps.log'))
    step_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    step_handler.setFormatter(step_formatter)
    caption_step_logger.addHandler(step_handler)

class PlatformAwareCaptionAdapter:
    """Adapts existing caption generation logic for platform-aware web operations"""
    
    def __init__(self, platform_connection: PlatformConnection, config: Config = None):
        """
        Initialize the adapter with a platform connection
        
        Args:
            platform_connection: The platform connection to use
            config: Optional config override (uses default if not provided)
        """
        self.platform_connection = platform_connection
        self.config = config or Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Initialize components
        self.activitypub_client = None
        self.image_processor = None
        self.caption_generator = None
        
        # Statistics tracking
        self.stats = {
            'posts_processed': 0,
            'images_processed': 0,
            'captions_generated': 0,
            'errors': 0,
            'skipped_existing': 0
        }
        
    async def initialize(self) -> bool:
        """
        Initialize all components for caption generation
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            logger.info(f"Initializing caption generation for platform {sanitize_for_log(self.platform_connection.name)}")
            
            # Set platform context in database manager
            self.db_manager.set_platform_context(self.platform_connection.user_id, self.platform_connection.id)
            
            # Create ActivityPub config from platform connection
            activitypub_config = self.platform_connection.to_activitypub_config()
            if not activitypub_config:
                raise ValueError("Failed to create ActivityPub config from platform connection")
            
            # Initialize ActivityPub client
            self.activitypub_client = ActivityPubClient(activitypub_config)
            
            # Initialize image processor
            self.image_processor = ImageProcessor(self.config)
            
            # Initialize caption generator
            self.caption_generator = OllamaCaptionGenerator(self.config.ollama)
            await self.caption_generator.initialize()
            
            logger.info("Caption generation components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize caption generation: {sanitize_for_log(str(e))}")
            return False
    
    async def generate_captions_for_user(
        self, 
        settings: CaptionGenerationSettings,
        progress_callback: Optional[Callable[[str, int, Dict[str, Any]], None]] = None
    ) -> GenerationResults:
        """
        Generate captions for the user's posts on the connected platform
        
        Args:
            settings: Caption generation settings
            progress_callback: Optional callback for progress updates
            
        Returns:
            GenerationResults: Results of the caption generation process
        """
        start_time = datetime.now(timezone.utc)
        
        # Initialize results
        results = GenerationResults(
            task_id="",  # Will be set by caller
            posts_processed=0,
            images_processed=0,
            captions_generated=0,
            errors_count=0,
            skipped_existing=0,
            processing_time_seconds=0.0,
            error_details=[],
            generated_image_ids=[]
        )
        
        # Track posts without images needing captions
        posts_no_images = 0
        
        try:
            # Step 1: Initialize components
            step_msg = "Initializing caption generation components"
            caption_step_logger.info(f"STEP: {step_msg} - Platform: {self.platform_connection.name}")
            if progress_callback:
                progress_callback(step_msg, 5, {
                    'step': 'initialization',
                    'platform': self.platform_connection.name
                })
            
            if not await self.initialize():
                raise RuntimeError("Failed to initialize caption generation components")
            
            # Step 2: Authenticate with platform
            step_msg = "Authenticating with platform"
            caption_step_logger.info(f"STEP: {step_msg} - Platform: {self.platform_connection.name}")
            if progress_callback:
                progress_callback(step_msg, 8, {
                    'step': 'authentication',
                    'platform': self.platform_connection.name
                })
            
            # Step 3: Fetch posts from platform
            step_msg = "Fetching posts from platform"
            caption_step_logger.info(f"STEP: {step_msg} - Platform: {self.platform_connection.name}")
            if progress_callback:
                progress_callback(step_msg, 10, {
                    'step': 'fetching_posts',
                    'platform': self.platform_connection.name
                })
            
            # Get user's posts from the platform
            username = self.platform_connection.username
            posts = await self.activitypub_client.get_user_posts(username, settings.max_posts_per_run)
            
            if not posts:
                step_msg = "No posts found with images needing captions"
                caption_step_logger.info(f"STEP: {step_msg} - User: {sanitize_for_log(username)}")
                logger.warning(f"No posts found for user {sanitize_for_log(username)}")
                if progress_callback:
                    progress_callback(step_msg, 100, {
                        'step': 'completed',
                        'posts_found': 0
                    })
                return results
            
            step_msg = f"Found {len(posts)} posts to analyze"
            caption_step_logger.info(f"STEP: {step_msg} - User: {sanitize_for_log(username)}")
            logger.info(f"Found {len(posts)} posts to process")
            if progress_callback:
                progress_callback(step_msg, 15, {
                    'step': 'posts_found',
                    'posts_found': len(posts)
                })
            
            # Process each post
            total_posts = len(posts)
            for i, post in enumerate(posts):
                try:
                    # Update progress
                    progress_percent = 20 + int((i / total_posts) * 70)  # 20-90% for post processing
                    post_url = post.get('id', 'unknown')
                    post_short_id = post_url.split('/')[-1] if '/' in post_url else post_url[:12]
                    
                    step_msg = f"Analyzing post {i+1}/{total_posts} (ID: {post_short_id})"
                    caption_step_logger.info(f"STEP: {step_msg}")
                    if progress_callback:
                        progress_callback(step_msg, progress_percent, {
                            'step': 'processing_post',
                            'current_post': i + 1,
                            'total_posts': total_posts,
                            'post_id': post_short_id
                        })
                    
                    # Process the post
                    post_results = await self._process_post(post, settings, progress_callback, i+1, total_posts)
                    
                    # Update results
                    results.posts_processed += 1
                    results.images_processed += post_results['images_processed']
                    results.captions_generated += post_results['captions_generated']
                    results.errors_count += post_results['errors']
                    results.skipped_existing += post_results['skipped_existing']
                    results.generated_image_ids.extend(post_results['generated_image_ids'])
                    
                    # Track posts without images
                    if post_results.get('no_images', False):
                        posts_no_images += 1
                    
                    # Add any errors to details
                    if post_results['error_details']:
                        results.error_details.extend(post_results['error_details'])
                    
                    # Progress update after processing post
                    if post_results['images_processed'] > 0:
                        step_msg = f"Post {i+1}/{total_posts}: {post_results['captions_generated']} captions generated"
                        caption_step_logger.info(f"STEP: {step_msg} - Images processed: {post_results['images_processed']}")
                        if progress_callback:
                            progress_callback(step_msg, progress_percent + 2, {
                                'step': 'post_completed',
                                'current_post': i + 1,
                                'images_in_post': post_results['images_processed'],
                                'captions_generated': post_results['captions_generated']
                            })
                    
                    # Add processing delay if configured
                    if settings.processing_delay > 0 and i < total_posts - 1:
                        await asyncio.sleep(settings.processing_delay)
                        
                except Exception as e:
                    logger.error(f"Error processing post {post.get('id', 'unknown')}: {sanitize_for_log(str(e))}")
                    results.errors_count += 1
                    results.error_details.append({
                        'post_id': post.get('id', 'unknown'),
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            # Final progress update
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            step_msg = "Caption generation completed successfully"
            caption_step_logger.info(f"STEP: {step_msg} - Posts: {results.posts_processed}, Images: {results.images_processed}, Captions: {results.captions_generated}, Errors: {results.errors_count}, Posts without images: {posts_no_images}, Time: {processing_time:.1f}s")
            if progress_callback:
                progress_callback(step_msg, 100, {
                    'step': 'completed',
                    'posts_processed': results.posts_processed,
                    'images_processed': results.images_processed,
                    'captions_generated': results.captions_generated,
                    'errors': results.errors_count,
                    'skipped': results.skipped_existing,
                    'posts_no_images': posts_no_images,
                    'processing_time': f"{processing_time:.1f}s"
                })
            
        except Exception as e:
            logger.error(f"Fatal error in caption generation: {sanitize_for_log(str(e))}")
            results.errors_count += 1
            results.error_details.append({
                'error': f"Fatal error: {str(e)}",
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            step_msg = "Caption generation failed"
            caption_step_logger.error(f"STEP: {step_msg} - Error: {str(e)} - Partial results: Posts: {results.posts_processed}, Images: {results.images_processed}, Captions: {results.captions_generated}")
            if progress_callback:
                progress_callback(step_msg, 100, {
                    'step': 'failed',
                    'error': str(e),
                    'partial_results': {
                        'posts_processed': results.posts_processed,
                        'images_processed': results.images_processed,
                        'captions_generated': results.captions_generated
                    }
                })
        
        finally:
            # Calculate processing time
            end_time = datetime.now(timezone.utc)
            results.processing_time_seconds = (end_time - start_time).total_seconds()
            
            # Cleanup resources
            await self._cleanup()
        
        logger.info(f"Caption generation completed: {results.captions_generated} captions generated, {results.errors_count} errors")
        return results
    
    async def _process_post(self, post: Dict[str, Any], settings: CaptionGenerationSettings, progress_callback: Optional[Callable] = None, post_num: int = 1, total_posts: int = 1) -> Dict[str, Any]:
        """
        Process a single post for caption generation
        
        Args:
            post: The post data from ActivityPub
            settings: Caption generation settings
            
        Returns:
            Dict with processing results for this post
        """
        post_results = {
            'images_processed': 0,
            'captions_generated': 0,
            'errors': 0,
            'skipped_existing': 0,
            'generated_image_ids': [],
            'error_details': [],
            'no_images': False
        }
        
        try:
            post_id = post.get('id', 'unknown')
            user_id = post.get('attributedTo', '').split('/')[-1]
            
            logger.info(f"Processing post: {sanitize_for_log(post_id)}")
            
            # Save post to database
            db_post = self.db_manager.get_or_create_post(
                post_id=post_id,
                user_id=user_id,
                post_url=post_id,
                post_content=post.get('content', '')
            )
            
            # Extract images without alt text
            images = self.activitypub_client.extract_images_from_post(post)
            
            if not images:
                step_msg = f"Post {post_num}/{total_posts}: No images needing captions"
                caption_step_logger.info(f"STEP: {step_msg} - Post ID: {sanitize_for_log(post_id)}")
                logger.debug(f"No images without alt text found in post {sanitize_for_log(post_id)}")
                if progress_callback:
                    # Calculate progress for this specific post
                    post_progress = 20 + int(((post_num - 1) / total_posts) * 70)
                    progress_callback(step_msg, post_progress, {
                        'step': 'post_no_images',
                        'post_num': post_num
                    })
                # Mark this as a post without images (not an error)
                post_results['no_images'] = True
                return post_results
            
            step_msg = f"Post {post_num}/{total_posts}: Found {len(images)} images needing captions"
            caption_step_logger.info(f"STEP: {step_msg} - Post ID: {sanitize_for_log(post_id)}")
            logger.info(f"Found {len(images)} images without alt text in post {sanitize_for_log(post_id)}")
            if progress_callback:
                # Calculate progress for this specific post
                post_progress = 20 + int(((post_num - 1) / total_posts) * 70)
                progress_callback(step_msg, post_progress, {
                    'step': 'images_found',
                    'post_num': post_num,
                    'images_count': len(images)
                })
            
            # Process each image
            for img_idx, image_info in enumerate(images):
                try:
                    step_msg = f"Post {post_num}/{total_posts}: Processing image {img_idx+1}/{len(images)}"
                    caption_step_logger.info(f"STEP: {step_msg}")
                    if progress_callback:
                        # Calculate progress for this specific post
                        post_progress = 20 + int(((post_num - 1) / total_posts) * 70)
                        progress_callback(step_msg, post_progress, {
                            'step': 'processing_image',
                            'post_num': post_num,
                            'image_num': img_idx + 1,
                            'total_images': len(images)
                        })
                    
                    # Calculate progress for this specific post
                    post_progress = 20 + int(((post_num - 1) / total_posts) * 70)
                    image_result = await self._process_image(image_info, db_post, settings, progress_callback, post_num, img_idx+1, len(images), post_progress)
                    
                    post_results['images_processed'] += 1
                    if image_result['caption_generated']:
                        post_results['captions_generated'] += 1
                        post_results['generated_image_ids'].append(image_result['image_id'])
                        step_msg = f"Post {post_num}/{total_posts}: Generated caption for image {img_idx+1}/{len(images)}"
                        caption_step_logger.info(f"STEP: {step_msg} - Caption: {image_result.get('caption', '')[:100]}")
                        if progress_callback:
                            post_progress = 20 + int(((post_num - 1) / total_posts) * 70)
                            progress_callback(step_msg, post_progress, {
                                'step': 'caption_generated',
                                'post_num': post_num,
                                'image_num': img_idx + 1,
                                'caption_preview': image_result.get('caption', '')[:50] + '...' if image_result.get('caption', '') else ''
                            })
                    elif image_result['skipped']:
                        post_results['skipped_existing'] += 1
                        step_msg = f"Post {post_num}/{total_posts}: Skipped image {img_idx+1}/{len(images)} (already processed)"
                        caption_step_logger.info(f"STEP: {step_msg}")
                        if progress_callback:
                            post_progress = 20 + int(((post_num - 1) / total_posts) * 70)
                            progress_callback(step_msg, post_progress, {
                                'step': 'image_skipped',
                                'post_num': post_num,
                                'image_num': img_idx + 1
                            })
                    
                except Exception as e:
                    logger.error(f"Error processing image {image_info.get('url', 'unknown')}: {sanitize_for_log(str(e))}")
                    post_results['errors'] += 1
                    post_results['error_details'].append({
                        'image_url': image_info.get('url', 'unknown'),
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
        except Exception as e:
            logger.error(f"Error processing post {post.get('id', 'unknown')}: {sanitize_for_log(str(e))}")
            post_results['errors'] += 1
            post_results['error_details'].append({
                'post_id': post.get('id', 'unknown'),
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        return post_results
    
    async def _process_image(self, image_info: Dict[str, Any], db_post, settings: CaptionGenerationSettings, progress_callback: Optional[Callable] = None, post_num: int = 1, img_num: int = 1, total_images: int = 1, progress_percent: int = 50) -> Dict[str, Any]:
        """
        Process a single image to generate alt text
        
        Args:
            image_info: Image information from ActivityPub
            db_post: Database post object
            settings: Caption generation settings
            
        Returns:
            Dict with image processing results
        """
        image_result = {
            'image_id': None,
            'caption_generated': False,
            'skipped': False,
            'caption': None
        }
        
        try:
            image_url = image_info['url']
            
            # Check if image was already processed (unless reprocessing is enabled)
            if not settings.reprocess_existing and self.db_manager.is_image_processed(image_url):
                logger.info(f"Image already successfully processed, skipping: {sanitize_for_log(image_url)}")
                image_result['skipped'] = True
                return image_result
            
            logger.info(f"Processing image: {sanitize_for_log(image_url)}")
            
            # Step 1: Download image
            step_msg = f"Post {post_num}: Downloading image {img_num}/{total_images}"
            caption_step_logger.info(f"STEP: {step_msg} - URL: {sanitize_for_log(image_url)}")
            if progress_callback:
                # Use a sub-progress within the current post's range
                sub_progress = progress_percent if progress_percent else 50
                progress_callback(step_msg, sub_progress, {
                    'step': 'downloading_image',
                    'post_num': post_num,
                    'image_num': img_num
                })
            
            local_path = await self.image_processor.download_and_store_image(
                image_url, 
                image_info.get('mediaType') or 'image/jpeg'
            )
            
            if not local_path:
                raise RuntimeError(f"Failed to download/store image: {image_url}")
            
            # Step 2: Save to database
            step_msg = f"Post {post_num}: Saving image {img_num}/{total_images} to database"
            caption_step_logger.info(f"STEP: {step_msg} - Local path: {local_path}")
            if progress_callback:
                sub_progress = progress_percent if progress_percent else 50
                progress_callback(step_msg, sub_progress, {
                    'step': 'saving_image',
                    'post_num': post_num,
                    'image_num': img_num
                })
            
            # Parse the original post date if available
            original_post_date = None
            if image_info.get('post_published'):
                try:
                    from dateutil import parser
                    original_post_date = parser.parse(image_info['post_published'])
                except Exception as e:
                    logger.warning(f"Failed to parse post_published date '{image_info['post_published']}': {e}")
            
            # Save image record to database
            image_id = self.db_manager.save_image(
                post_id=db_post.id,
                image_url=image_url,
                local_path=local_path,
                attachment_index=image_info['attachment_index'],
                media_type=image_info.get('mediaType'),
                original_filename=local_path.split('/')[-1],
                image_post_id=image_info.get('image_post_id'),
                original_post_date=original_post_date
            )
            
            if image_id is None:
                raise RuntimeError(f"Failed to save image record: {image_url}")
            
            image_result['image_id'] = image_id
            
            # Step 3: Generate caption using AI
            step_msg = f"Post {post_num}: Generating caption for image {img_num}/{total_images}"
            caption_step_logger.info(f"STEP: {step_msg} - Using AI model")
            if progress_callback:
                sub_progress = progress_percent if progress_percent else 50
                progress_callback(step_msg, sub_progress, {
                    'step': 'generating_caption',
                    'post_num': post_num,
                    'image_num': img_num
                })
            
            result = await self.caption_generator.generate_caption(local_path)
            
            # Handle result format (tuple or string)
            if isinstance(result, tuple) and len(result) == 2:
                caption, quality_metrics = result
            else:
                caption = result
                quality_metrics = None
            
            if caption:
                # Apply caption length limits from settings
                if len(caption) > settings.max_caption_length:
                    caption = caption[:settings.max_caption_length].rsplit(' ', 1)[0] + '...'
                
                # Log quality metrics if available
                if quality_metrics:
                    logger.info(f"Caption quality score: {quality_metrics['overall_score']}/100 ({quality_metrics['quality_level']})")
                    if quality_metrics['needs_review']:
                        logger.warning(f"Caption flagged for special review: {quality_metrics['feedback']}")
                
                # Update the image in the database with caption and quality metrics
                success = self.db_manager.update_image_caption(
                    image_id=image_id,
                    generated_caption=caption,
                    quality_metrics=quality_metrics
                )
                
                if success:
                    image_result['caption_generated'] = True
                    image_result['caption'] = caption
                    logger.info(f"Generated caption for {sanitize_for_log(image_url)}: {sanitize_for_log(caption)}")
                    
                    # Step 4: Caption saved successfully
                    step_msg = f"Post {post_num}: Caption saved for image {img_num}/{total_images}"
                    caption_step_logger.info(f"STEP: {step_msg} - Caption length: {len(caption)} - Caption: {sanitize_for_log(caption)}")
                    if progress_callback:
                        sub_progress = progress_percent if progress_percent else 50
                        progress_callback(step_msg, sub_progress, {
                            'step': 'caption_saved',
                            'post_num': post_num,
                            'image_num': img_num,
                            'caption_length': len(caption)
                        })
                else:
                    raise RuntimeError(f"Failed to update caption for image {image_id}")
            else:
                step_msg = f"Post {post_num}: Failed to generate caption for image {img_num}/{total_images}"
                caption_step_logger.error(f"STEP: {step_msg}")
                if progress_callback:
                    sub_progress = progress_percent if progress_percent else 50
                    progress_callback(step_msg, sub_progress, {
                        'step': 'caption_failed',
                        'post_num': post_num,
                        'image_num': img_num
                    })
                raise RuntimeError(f"Failed to generate caption for image: {image_url}")
            
        except Exception as e:
            logger.error(f"Error processing image {image_info.get('url', 'unknown')}: {sanitize_for_log(str(e))}")
            raise
        
        return image_result
    
    async def _cleanup(self):
        """Clean up resources"""
        try:
            if self.caption_generator:
                # Check if cleanup is async or sync
                cleanup_method = getattr(self.caption_generator, 'cleanup', None)
                if cleanup_method:
                    if asyncio.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()
            
            if self.activitypub_client:
                close_method = getattr(self.activitypub_client, 'close', None)
                if close_method:
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
            
            if self.image_processor:
                close_method = getattr(self.image_processor, 'close', None)
                if close_method:
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {sanitize_for_log(str(e))}")
    
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Get information about the connected platform
        
        Returns:
            Dict with platform information
        """
        return {
            'name': self.platform_connection.name,
            'platform_type': self.platform_connection.platform_type,
            'instance_url': self.platform_connection.instance_url,
            'username': self.platform_connection.username,
            'is_active': self.platform_connection.is_active
        }
    
    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test the platform connection
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not await self.initialize():
                return False, "Failed to initialize components"
            
            # Test ActivityPub connection
            success, message = await self.activitypub_client.test_connection()
            
            await self._cleanup()
            return success, message
            
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"