# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import asyncio
from logging import getLogger
import sys
import os
import argparse
import json
from typing import List, Dict, Any
from datetime import datetime, timezone
from config import Config
from database import DatabaseManager
from activitypub_client import ActivityPubClient
from image_processor import ImageProcessor
from ollama_caption_generator import OllamaCaptionGenerator
from models import ProcessingRun, ProcessingStatus, Image
from utils import get_retry_stats_summary, get_retry_stats_detailed
from logger import (
    setup_logging, log_with_context, log_error, log_error_summary,
    get_error_summary, get_error_report, reset_error_collector
)

# Logger will be configured in main() based on command line arguments
logger = getLogger(__name__)

class Vedfolnir:
    """Main bot class that orchestrates the alt text generation process"""
    
    def __init__(self, config: Config, reprocess_all: bool = False):
        self.config = config
        self.db = DatabaseManager(config)
        self.current_run = None
        self.reprocess_all = reprocess_all
        self.stats = {
            'posts_processed': 0,
            'images_processed': 0,
            'captions_generated': 0,
            'errors': 0,
            'skipped_existing': 0
        }
    
    async def run_multi_user(self, user_ids: List[str], skip_ollama=False):
        """Process multiple users in a single run"""
        logger.info("Starting Vedfolnir in multi-user mode")
        
        # Enforce max users per run limit
        if len(user_ids) > self.config.max_users_per_run:
            logger.warning(f"Number of users ({len(user_ids)}) exceeds max_users_per_run ({self.config.max_users_per_run})")
            logger.warning(f"Processing only the first {self.config.max_users_per_run} users")
            user_ids = user_ids[:self.config.max_users_per_run]
        
        logger.info(f"Processing {len(user_ids)} users: {', '.join(user_ids)}")
        
        # Generate a batch ID for this multi-user run
        batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Created batch ID: {batch_id}")
        
        # Initialize components once for all users
        try:
            async with ActivityPubClient(self.config.activitypub) as ap_client, \
                       ImageProcessor(self.config) as image_processor:
                
                caption_generator = None
                if not skip_ollama:
                    caption_generator = OllamaCaptionGenerator(self.config.ollama)
                    
                    try:
                        # Initialize the caption generator
                        logger.info("Initializing Ollama caption generator...")
                        await caption_generator.initialize()
                    except Exception as e:
                        logger.error(f"Failed to initialize Ollama caption generator: {e}")
                        logger.warning("Continuing without Ollama caption generator")
                        caption_generator = None
                else:
                    logger.info("Skipping Ollama initialization (--no-ollama flag set)")
                
                try:
                    # Process each user sequentially
                    for i, user_id in enumerate(user_ids):
                        # Add delay between users (except for the first one)
                        if i > 0 and self.config.user_processing_delay > 0:
                            logger.info(f"Waiting {self.config.user_processing_delay} seconds before processing next user")
                            await asyncio.sleep(self.config.user_processing_delay)
                        
                        await self._process_user(user_id, ap_client, image_processor, caption_generator, batch_id)
                finally:
                    # Clean up model resources
                    if caption_generator:
                        caption_generator.cleanup()
            
            # Print overall statistics
            self._print_statistics()
            
            # Print Ollama API retry statistics if caption generator is available
            if caption_generator:
                logger.info("Ollama API Statistics:")
                logger.info(caption_generator.get_retry_stats_summary())
            else:
                logger.info("Ollama API Statistics: Not available (no caption generator)")
            
            # Log error summary if there were any errors
            if self.stats['errors'] > 0:
                log_error_summary(logger)
                
            logger.info(f"Completed batch {batch_id} with {len(user_ids)} users")
            
        except Exception as e:
            log_error(logger, "Fatal", "Fatal error in bot execution", "Vedfolnir", 
                     details={"batch_id": batch_id, "users_count": len(user_ids)}, exception=e)
            self.stats['errors'] += 1
            
            # Log error summary before exiting
            log_error_summary(logger)
            logger.error("Stopping execution due to fatal error")
            sys.exit(1)
    
    async def run(self, user_id: str):
        """Main execution method for a single user (for backward compatibility)"""
        await self.run_multi_user([user_id])
    
    async def _process_user(self, user_id: str, ap_client: ActivityPubClient, 
                          image_processor: ImageProcessor, caption_generator,
                          batch_id: str = None):
        """Process a single user's posts
        
        Args:
            user_id: The ID of the user to process
            ap_client: ActivityPub client instance
            image_processor: Image processor instance
            caption_generator: Caption generator instance (can be None if --no-ollama is set)
            batch_id: Optional batch ID to group runs that are part of the same batch
        """
        logger.info(f"Processing user: {user_id}")
        
        # Create processing run record for this user
        self.current_run = self._create_processing_run(user_id, batch_id)
        
        try:
            # Get user's posts
            logger.info(f"Fetching posts for user: {user_id}")
            posts = await ap_client.get_user_posts(user_id, self.config.max_posts_per_run)
            
            if not posts:
                logger.warning(f"No posts found for user {user_id}")
                self._complete_processing_run()
                return
            
            # Process each post
            user_posts_count = 0
            for post in posts:
                await self._process_post(post, ap_client, image_processor, caption_generator)
                self.stats['posts_processed'] += 1
                user_posts_count += 1
            
            logger.info(f"Processed {user_posts_count} posts for user {user_id}")
            
            # Update processing run for this user
            self._complete_processing_run()
            
        except Exception as e:
            log_error(logger, "Processing", f"Error processing user {user_id}", "Vedfolnir", 
                     details={"user_id": user_id, "batch_id": batch_id}, exception=e)
            self.stats['errors'] += 1
            self._complete_processing_run(error=str(e))
    
    def _create_processing_run(self, user_id: str, batch_id: str = None) -> ProcessingRun:
        """Create a new processing run record
        
        Args:
            user_id: The ID of the user being processed
            batch_id: Optional batch ID to group runs that are part of the same batch
        """
        session = self.db.get_session()
        try:
            run = ProcessingRun(user_id=user_id, batch_id=batch_id)
            session.add(run)
            session.commit()
            logger.info(f"Created processing run {run.id} for user {user_id}" + 
                       (f" in batch {batch_id}" if batch_id else ""))
            return run
        except Exception as e:
            session.rollback()
            log_error(logger, "Database", "Failed to create processing run", "DatabaseManager", 
                     details={"user_id": user_id, "batch_id": batch_id}, exception=e)
            raise
        finally:
            session.close()
    
    def _complete_processing_run(self, error: str = None):
        """Complete the processing run record"""
        if not self.current_run:
            return
            
        session = self.db.get_session()
        try:
            run = session.get(ProcessingRun, self.current_run.id)
            if run:
                # Get retry statistics
                retry_stats_detailed = get_retry_stats_detailed()
                
                # Update processing run with basic stats
                run.completed_at = datetime.now(timezone.utc)
                run.posts_processed = self.stats['posts_processed']
                run.images_processed = self.stats['images_processed']
                run.captions_generated = self.stats['captions_generated']
                run.errors_count = self.stats['errors']
                run.status = "error" if error else "completed"
                
                # Add retry statistics to the processing run
                run.retry_attempts = retry_stats_detailed['summary']['retry_attempts']
                run.retry_successes = retry_stats_detailed['summary']['successful_retries']
                run.retry_failures = retry_stats_detailed['summary']['failed_retries']
                run.retry_total_time = int(retry_stats_detailed['timing']['total_retry_time'])
                
                # Store detailed retry statistics as JSON
                run.retry_stats_json = json.dumps(retry_stats_detailed)
                
                session.commit()
                logger.info(f"Completed processing run {run.id}")
                
                # Log retry statistics summary
                self._log_retry_statistics()
        except Exception as e:
            session.rollback()
            log_error(logger, "Database", "Failed to complete processing run", "DatabaseManager", 
                     details={"run_id": self.current_run.id}, exception=e)
        finally:
            session.close()
    
    async def _process_post(self, post: Dict[str, Any], ap_client: ActivityPubClient, 
                          image_processor: ImageProcessor, caption_generator):
        """Process a single post for alt text generation"""
        try:
            post_id = post.get('id', 'unknown')
            user_id = post.get('attributedTo', '').split('/')[-1]
            
            logger.info(f"Processing post: {post_id}")
            
            # Save post to database
            db_post = self.db.get_or_create_post(
                post_id=post_id,
                user_id=user_id,
                post_url=post_id,
                post_content=post.get('content', '')
            )
            
            # Extract images without alt text
            images = ap_client.extract_images_from_post(post)
            
            if not images:
                logger.debug(f"No images without alt text found in post {post_id}")
                return
            
            logger.info(f"Found {len(images)} images without alt text in post {post_id}")
            
            # Check if caption generator is available
            if caption_generator is None:
                from security.core.security_utils import sanitize_for_log
                logger.warning(f"Skipping image processing for post {sanitize_for_log(post_id)} - no caption generator available")
                return
            
            # Process each image
            for image_info in images:
                await self._process_image(image_info, db_post, image_processor, caption_generator)
                self.stats['images_processed'] += 1
            
        except Exception as e:
            post_id = post.get('id', 'unknown')
            log_error(logger, "Processing", f"Error processing post {post_id}", "PostProcessor", 
                     details={"post_id": post_id}, exception=e)
            self.stats['errors'] += 1
    
    async def _process_image(self, image_info: Dict[str, Any], db_post, 
                           image_processor: ImageProcessor, caption_generator: OllamaCaptionGenerator):
        """Process a single image to generate alt text"""
        try:
            image_url = image_info['url']
            
            # Check if image was already processed (has POSTED or APPROVED status)
            if not self.reprocess_all and self.db.is_image_processed(image_url):
                logger.info(f"Image already successfully processed (POSTED or APPROVED), skipping: {image_url}")
                self.stats['skipped_existing'] += 1
                return
            
            logger.info(f"Processing image: {image_url}")
            
            # Download and store image
            local_path = await image_processor.download_and_store_image(
                image_url, 
                image_info.get('mediaType')
            )
            
            if not local_path:
                log_error(logger, "Download", f"Failed to download/store image", "ImageProcessor", 
                         details={"image_url": image_url})
                return
                
            # Debug log for image_post_id
            logger.info(f"ID from image_info: {image_info.get('image_post_id')}")
            
            # Parse the original post date if available
            original_post_date = None
            if image_info.get('post_published'):
                try:
                    from dateutil import parser
                    original_post_date = parser.parse(image_info['post_published'])
                except Exception as e:
                    logger.warning(f"Failed to parse post_published date '{image_info['post_published']}': {e}")
            
            # Save image record to database and get the image ID directly
            image_id = self.db.save_image(
                post_id=db_post.id,
                image_url=image_url,
                local_path=local_path,
                attachment_index=image_info['attachment_index'],
                media_type=image_info.get('mediaType'),
                original_filename=os.path.basename(local_path),
                image_post_id=image_info.get('image_post_id'),  # Use image_post_id parameter
                original_post_date=original_post_date
            )
            
            if image_id is None:
                log_error(logger, "Database", f"Failed to save image record: {image_url}", "ImageProcessor")
                return
            
            # Generate caption using general prompt
            result = await caption_generator.generate_caption(local_path)
            
            # The generate_caption method now returns a tuple of (caption, quality_metrics)
            if isinstance(result, tuple) and len(result) == 2:
                caption, quality_metrics = result
            else:
                # Handle backward compatibility with older versions
                caption = result
                quality_metrics = None
            
            if caption:
                # Log quality metrics if available
                if quality_metrics:
                    logger.info(f"Caption quality score: {quality_metrics['overall_score']}/100 ({quality_metrics['quality_level']})")
                    if quality_metrics['needs_review']:
                        logger.warning(f"Caption flagged for special review: {quality_metrics['feedback']}")
                
                # Update the image in the database with caption and quality metrics
                # Use the stored image_id instead of accessing db_image.id to avoid detached instance issues
                success = self.db.update_image_caption(
                    image_id=image_id,
                    generated_caption=caption,
                    quality_metrics=quality_metrics
                )
                
                if success:
                    self.stats['captions_generated'] += 1
                    logger.info(f"Generated caption for {image_url}: {caption}")
                else:
                    log_error(logger, "Database", f"Failed to update caption for image {image_id}", "ImageProcessor", 
                            details={"image_id": image_id, "image_url": image_url})
                    self.stats['errors'] += 1
            else:
                log_error(logger, "Caption", f"Failed to generate caption for image", "CaptionGenerator", 
                         details={"image_url": image_url, "local_path": local_path})
                self.stats['errors'] += 1
            
        except Exception as e:
            log_error(logger, "Processing", "Error processing image", "ImageProcessor", 
                     details={"image_url": image_info.get('url', 'unknown')}, exception=e)
    
    def _log_retry_statistics(self):
        """Log retry statistics after processing run"""
        # Get retry statistics summary
        retry_summary = get_retry_stats_summary()
        
        # Log the summary at INFO level
        logger.info("=== Retry Statistics ===")
        for line in retry_summary.split('\n'):
            logger.info(line)
        
        # Get detailed statistics for DEBUG level
        retry_detailed = get_retry_stats_detailed()
        
        # Log more detailed information at DEBUG level
        logger.debug("=== Detailed Retry Information ===")
        logger.debug(f"Retry attempts by endpoint: {json.dumps(retry_detailed['by_endpoint'], indent=2)}")
        logger.debug(f"Retry attempts by status code: {json.dumps(retry_detailed['by_status_code'], indent=2)}")
        logger.debug(f"Retry attempts by exception: {json.dumps(retry_detailed['by_exception'], indent=2)}")
        logger.debug(f"Retry time distribution: {json.dumps(retry_detailed['timing']['distribution'], indent=2)}")
        
        # If there were any retries, add a note about checking the database for more details
        if retry_detailed['summary']['retry_attempts'] > 0:
            logger.info(f"Detailed retry statistics stored in database for processing run {self.current_run.id}")

    def _print_statistics(self):
        """Print execution statistics"""
        logger.info("=== Execution Statistics ===")
        for key, value in self.stats.items():
            logger.info(f"{key.replace('_', ' ').title()}: {value}")
        logger.info("============================")

async def main():
    """Main entry point"""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Vedfolnir - Generate and manage alt text for Pixelfed posts')
    parser.add_argument('--users', '-u', nargs='+', help='One or more user IDs to process')
    parser.add_argument('--file', '-f', help='Path to a file containing user IDs (one per line)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                        help='Set logging level (overrides config)')
    parser.add_argument('--show-retry-stats', action='store_true', 
                        help='Display current retry statistics and exit')
    parser.add_argument('--json-logs', action='store_true',
                        help='Output logs in JSON format')
    parser.add_argument('--show-error-summary', action='store_true',
                        help='Display error summary and exit')
    parser.add_argument('--reprocess-all', action='store_true',
                        help='Reprocess all images, even those that have been processed before')
    parser.add_argument('--no-ollama', action='store_true',
                        help='Skip Ollama initialization (for testing without Ollama server)')
    args = parser.parse_args()
    
    config = Config()
    
    # Set up logging with structured formatter
    log_level = args.log_level if args.log_level else config.log_level
    setup_logging(
        log_level=log_level,
        log_file=os.path.join(config.storage.logs_dir, 'vedfolnir.log'),
        use_json=args.json_logs,
        include_traceback=True
    )
    
    # Reset error collector at the start of a new run
    reset_error_collector()
    
    # Validate configuration
    if not config.activitypub.instance_url:
        log_error(logger, "Configuration", "ACTIVITYPUB_INSTANCE_URL environment variable is required", 
                 "Config", details={"missing_var": "ACTIVITYPUB_INSTANCE_URL"})
        sys.exit(1)
    
    if not config.activitypub.access_token:
        log_error(logger, "Configuration", "ACTIVITYPUB_ACCESS_TOKEN environment variable is required", 
                 "Config", details={"missing_var": "ACTIVITYPUB_ACCESS_TOKEN"})
        sys.exit(1)
    
    # Get user IDs from arguments, file, or prompt
    user_ids = []
    
    if args.users:
        user_ids.extend(args.users)
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_users = [line.strip() for line in f if line.strip()]
                user_ids.extend(file_users)
                logger.info(f"Loaded {len(file_users)} user IDs from {args.file}")
        except Exception as e:
            logger.error(f"Error reading user IDs from file {args.file}: {e}")
            sys.exit(1)
    
    # If no users specified, prompt for input
    if not user_ids:
        user_input = input("Enter user ID(s) to process (comma-separated): ").strip()
        if user_input:
            user_ids = [u.strip() for u in user_input.split(',') if u.strip()]
    
    # Check if we should just display retry stats and exit
    if args.show_retry_stats:
        retry_summary = get_retry_stats_summary()
        print(retry_summary)
        sys.exit(0)
        
    # Check if we should just display error summary and exit
    if args.show_error_summary:
        error_summary = get_error_summary()
        print(error_summary)
        sys.exit(0)
    
    # Validate we have at least one user ID
    if not user_ids:
        logger.error("At least one user ID is required")
        sys.exit(1)
    
    # Remove duplicates while preserving order
    user_ids = list(dict.fromkeys(user_ids))
    
    # Run the bot
    bot = Vedfolnir(config, reprocess_all=args.reprocess_all)
    await bot.run_multi_user(user_ids, skip_ollama=args.no_ollama)

if __name__ == "__main__":
    asyncio.run(main())