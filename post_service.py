# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import asyncio
import logging
from typing import List
from datetime import datetime
from config import Config
from database import DatabaseManager
from activitypub_client import ActivityPubClient
from models import ProcessingStatus, Image
from batch_update_service import BatchUpdateService

logger = logging.getLogger(__name__)

class PostingService:
    """Service for posting approved captions to ActivityPub"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager(config)
        self.batch_service = BatchUpdateService(config)
        self.use_batch_updates = getattr(config, 'use_batch_updates', True)
    
    async def post_approved_captions(self, limit: int = 10) -> dict:
        """Post approved captions to ActivityPub server"""
        # Use batch update service if enabled
        if self.use_batch_updates:
            logger.info(f"Using batch update service for {limit} images")
            return await self.batch_service.batch_update_captions(limit)
        
        # Otherwise use the legacy single-image approach
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # Get approved images
            approved_images = self.db.get_approved_images(limit)
            
            if not approved_images:
                logger.info("No approved images to post")
                return stats
            
            logger.info(f"Found {len(approved_images)} approved images to post")
            
            async with ActivityPubClient(self.config.activitypub) as ap_client:
                for image in approved_images:
                    stats['processed'] += 1
                    
                    try:
                        success = await self._post_single_image(ap_client, image)
                        if success:
                            stats['successful'] += 1
                            self.db.mark_image_posted(image.id)
                            logger.info(f"Successfully posted caption for image {image.id}")
                        else:
                            stats['failed'] += 1
                            logger.error(f"Failed to post caption for image {image.id}")
                    
                    except Exception as e:
                        stats['failed'] += 1
                        error_msg = f"Error posting image {image.id}: {str(e)}"
                        stats['errors'].append(error_msg)
                        logger.error(error_msg)
                    
                    # Small delay between posts
                    await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Fatal error in post_approved_captions: {e}")
            stats['errors'].append(str(e))
        
        logger.info(f"Posting complete. Processed: {stats['processed']}, "
                   f"Successful: {stats['successful']}, Failed: {stats['failed']}")
        
        return stats
    
    async def _post_single_image(self, ap_client: ActivityPubClient, image: Image) -> bool:
        """Post a single image's caption"""
        try:
            # Check if we have an image_post_id for direct API update
            if image.image_post_id:
                # Use the direct media update API
                caption = image.final_caption or image.reviewed_caption
                return await ap_client.update_media_caption(image.image_post_id, caption)
            
            # Fallback to the old method if no id is available
            # Get the post
            post = await ap_client.get_post_by_id(image.post.post_id)
            if not post:
                logger.error(f"Could not retrieve post {image.post.post_id}")
                return False
            
            # Update the attachment with new alt text
            attachments = post.get('attachment', [])
            if not isinstance(attachments, list):
                attachments = [attachments]
            
            if image.attachment_index < len(attachments):
                attachments[image.attachment_index]['name'] = image.final_caption
                post['attachment'] = attachments
                
                # Update the post
                return await ap_client.update_post(image.post.post_id, post)
            else:
                logger.error(f"Attachment index {image.attachment_index} out of range")
                return False
                
        except Exception as e:
            logger.error(f"Error posting single image {image.id}: {e}")
            return False

async def main():
    """CLI interface for posting service"""
    config = Config()
    service = PostingService(config)
    
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    
    stats = await service.post_approved_captions(limit)
    print(f"Posting completed: {stats}")

if __name__ == "__main__":
    asyncio.run(main())