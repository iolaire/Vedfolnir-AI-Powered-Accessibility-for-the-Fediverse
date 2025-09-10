# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Enhanced version of the PixelfedPlatform class with pagination support.
This file contains only the modified PixelfedPlatform class with pagination support.
"""

import logging
from typing import Dict, List, Any, Optional
import httpx
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class PixelfedPlatformWithPagination:
    """Enhanced adapter for Pixelfed platform with pagination support"""
    
    def __init__(self, config):
        self.config = config
        
    async def get_user_posts(self, client, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve user's posts from Pixelfed using API with pagination support
        
        Args:
            client: The ActivityPubClient instance
            user_id: The user ID to fetch posts for
            limit: Maximum number of posts to fetch
            
        Returns:
            List of posts in ActivityPub format
        """
        try:
            # Use Pixelfed API to get user account ID first
            headers = {
                'Authorization': f'Bearer {self.config.access_token}',
                'Accept': 'application/json'
            }
            
            # Get user account ID
            verify_url = f"{self.config.instance_url}/api/v1/accounts/verify_credentials"
            response = await client._get_with_retry(verify_url, headers)
            user_data = response.json()
            account_id = user_data['id']
            
            # Initialize variables for pagination
            all_posts = []
            page_size = 40  # Pixelfed API typically returns 40 posts per page
            max_pages = (limit + page_size - 1) // page_size  # Ceiling division
            next_page_url = f"{self.config.instance_url}/api/v1/accounts/{account_id}/statuses"
            
            logger.info(f"Fetching up to {limit} posts for user {sanitize_for_log(user_id)} (max {max_pages} pages)")
            
            # Fetch posts page by page
            for page in range(1, max_pages + 1):
                # Prepare parameters for the request
                params = {'limit': page_size}
                
                # If we have a max_id from a previous page, use it for pagination
                if page > 1 and 'max_id' in locals():
                    params['max_id'] = max_id
                
                # Make the request
                logger.info(f"Fetching page {page} of posts for user {sanitize_for_log(user_id)}")
                response = await client._get_with_retry(next_page_url, headers, params=params)
                statuses = response.json()
                
                # If no statuses returned, we've reached the end
                if not statuses:
                    logger.info(f"No more posts found for user {sanitize_for_log(user_id)} after page {page-1}")
                    break
                
                # Get the ID of the last status for pagination
                max_id = statuses[-1]['id']
                
                # Convert Pixelfed statuses to ActivityPub format
                for status in statuses:
                    if status.get('media_attachments'):
                        # Convert to ActivityPub Note format
                        attachments = []
                        for media in status['media_attachments']:
                            if media.get('type') == 'image':
                                attachments.append({
                                    "type": "Document",
                                    "mediaType": "image/jpeg",
                                    "url": media.get('url'),
                                    "name": media.get('description', ''),
                                    "id": media.get('id')  # Store Pixelfed ID
                                })
                        
                        if attachments:
                            all_posts.append({
                                "id": status.get('url'),
                                "type": "Note",
                                "content": status.get('content', ''),
                                "attributedTo": f"{self.config.instance_url}/users/{user_id}",
                                "published": status.get('created_at'),
                                "attachment": attachments
                            })
                
                # If we've reached the desired limit, stop fetching more pages
                if len(all_posts) >= limit:
                    all_posts = all_posts[:limit]  # Trim to exact limit
                    logger.info(f"Reached desired limit of {limit} posts for user {sanitize_for_log(user_id)}")
                    break
                
                # If we got fewer posts than the page size, we've reached the end
                if len(statuses) < page_size:
                    logger.info(f"Reached end of posts for user {sanitize_for_log(user_id)} on page {page}")
                    break
            
            logger.info(f"Retrieved {len(all_posts)} Pixelfed posts for user {sanitize_for_log(user_id)}")
            return all_posts
            
        except Exception as e:
            logger.error(f"Failed to retrieve Pixelfed posts for user {sanitize_for_log(user_id)}: {sanitize_for_log(str(e))}")
            return []