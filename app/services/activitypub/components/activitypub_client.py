# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import asyncio
import json
import logging
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
import httpx
from datetime import datetime, timezone
import hashlib
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from app.utils.helpers import utils
from app.utils.helpers.utils import async_retry, RetryConfig, get_retry_stats_summary, get_retry_stats_detailed
from app.core.security.core.rate_limiter import get_rate_limiter, extract_endpoint_from_url, rate_limited
from app.services.activitypub.components.activitypub_platforms import PlatformAdapterFactory, PlatformAdapterError
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class ActivityPubClient:
    """
    Platform-agnostic client for interacting with ActivityPub servers via API.
    
    This client uses platform adapters to handle platform-specific implementations
    while providing a consistent interface for all ActivityPub platforms.
    
    The client can be initialized either with a traditional config object or with
    a PlatformConnection object for platform-aware operations.
    """
    
    def __init__(self, config, platform_connection=None):
        """
        Initialize the ActivityPub client.
        
        Args:
            config: ActivityPubConfig object or PlatformConnection object
            platform_connection: Optional PlatformConnection for platform-aware operations
        """
        # Handle platform connection initialization
        if platform_connection is not None:
            # Use platform connection to create config
            self.platform_connection = platform_connection
            self.config = platform_connection.to_activitypub_config()
            if not self.config:
                raise PlatformAdapterError("Failed to create config from platform connection")
        elif hasattr(config, 'to_activitypub_config'):
            # Config is actually a PlatformConnection
            self.platform_connection = config
            self.config = config.to_activitypub_config()
            if not self.config:
                raise PlatformAdapterError("Failed to create config from platform connection")
        else:
            # Traditional config object
            self.config = config
            self.platform_connection = None
        
        self.session = None
        self.private_key = None
        self.public_key = None
        self._load_keys()
        
        # Initialize the platform adapter using the factory
        try:
            self.platform = PlatformAdapterFactory.create_adapter(self.config)
            logger.info(f"Initialized ActivityPub client with {self.platform.platform_name} adapter")
        except Exception as e:
            logger.error(f"Failed to create platform adapter: {e}")
            raise PlatformAdapterError(f"Failed to initialize platform adapter: {e}")
        
        # Initialize retry configuration from environment variables
        if hasattr(self.config, 'retry') and self.config.retry:
            config_retry = self.config.retry
            
            # Platform-specific retry configuration with enhanced parameters
            self.retry_config = RetryConfig(
                max_attempts=config_retry.max_attempts,
                base_delay=config_retry.base_delay,
                max_delay=config_retry.max_delay,
                backoff_factor=config_retry.backoff_factor,
                # Add specific status codes for platform API
                retry_status_codes=[
                    429,  # Too Many Requests
                    408,  # Request Timeout
                    500,  # Internal Server Error
                    502,  # Bad Gateway
                    503,  # Service Unavailable
                    504,  # Gateway Timeout
                    520,  # Unknown Error (Cloudflare)
                    521,  # Web Server Is Down (Cloudflare)
                    522,  # Connection Timed Out (Cloudflare)
                    523,  # Origin Is Unreachable (Cloudflare)
                    524,  # A Timeout Occurred (Cloudflare)
                    525,  # SSL Handshake Failed (Cloudflare)
                    526,  # Invalid SSL Certificate (Cloudflare)
                    527,  # Railgun Error (Cloudflare)
                ],
                # Add specific exceptions for network issues
                retry_exceptions=[
                    httpx.TimeoutException,
                    httpx.ConnectError,
                    httpx.ReadError,
                    httpx.WriteError,
                    httpx.NetworkError,
                    ConnectionError,
                    ConnectionRefusedError,
                    ConnectionResetError,
                    asyncio.TimeoutError,
                    OSError,  # Covers many network-related errors
                    IOError    # General I/O errors
                ],
                # Enable jitter to prevent thundering herd problem
                jitter=config_retry.jitter,
                jitter_factor=config_retry.jitter_factor,
                # Configure retry behavior based on error types
                retry_on_timeout=config_retry.retry_on_timeout,
                retry_on_connection_error=config_retry.retry_on_connection_error,
                retry_on_server_error=config_retry.retry_on_server_error,
                retry_on_rate_limit=config_retry.retry_on_rate_limit,
                # Add specific error messages to retry on
                retry_on_specific_errors=[
                    "connection reset by peer",
                    "connection refused",
                    "temporary failure in name resolution",
                    "network is unreachable",
                    "operation timed out",
                    "ssl handshake failed",
                    "too many redirects",
                    "rate limit exceeded",
                    "server overloaded",
                    "database connection error",
                    "gateway timeout",
                    "service unavailable",
                    "internal server error"
                ] + (config_retry.retry_specific_errors or [])  # Add any custom error patterns from config
            )
            
            logger.info(f"Initialized ActivityPubClient with retry configuration: max_attempts={self.retry_config.max_attempts}, "
                       f"base_delay={self.retry_config.base_delay}s, max_delay={self.retry_config.max_delay}s, "
                       f"jitter={'enabled' if self.retry_config.jitter else 'disabled'}")
        else:
            # Default retry configuration if not provided
            self.retry_config = RetryConfig()
            logger.info("Using default retry configuration for ActivityPubClient")
            
        # Initialize rate limiter if configuration is provided
        if hasattr(self.config, 'rate_limit') and self.config.rate_limit:
            # Apply platform-specific rate limits if available
            rate_limit_config = self._apply_platform_rate_limits(self.config.rate_limit)
            self.rate_limiter = get_rate_limiter(rate_limit_config)
            
            # Log rate limit configuration
            logger.info(f"Initialized ActivityPubClient with rate limiting: "
                       f"{rate_limit_config.requests_per_minute} requests/minute, "
                       f"{rate_limit_config.requests_per_hour} requests/hour, "
                       f"{rate_limit_config.requests_per_day} requests/day")
            
            # Log platform-specific rate limits
            platform_name = self.platform.platform_name
            if platform_name in rate_limit_config.platform_limits:
                logger.info(f"Platform-specific rate limits for {platform_name}: "
                           f"{rate_limit_config.platform_limits[platform_name]}")
            
            # Log endpoint-specific rate limits if configured
            if rate_limit_config.endpoint_limits:
                for endpoint, limits in rate_limit_config.endpoint_limits.items():
                    logger.info(f"Endpoint '{endpoint}' rate limits: {limits}")
        else:
            # Use default rate limiter
            self.rate_limiter = get_rate_limiter()
            logger.info("Using default rate limiting configuration for ActivityPubClient")
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized"""
        if not self.session or self.session.is_closed:
            self.session = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    'User-Agent': self.config.user_agent,
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
    
    def close(self):
        """Synchronous cleanup method to prevent resource leaks"""
        if self.session and not self.session.is_closed:
            # For synchronous cleanup, we can't await aclose()
            # This is a fallback to prevent resource warnings
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup for later
                    loop.create_task(self.session.aclose())
                else:
                    # Run cleanup in new event loop
                    asyncio.run(self.session.aclose())
            except Exception:
                # If all else fails, at least clear the reference
                pass
            finally:
                self.session = None
        
        # Clear platform adapter reference
        if hasattr(self, 'platform'):
            self.platform = None
    
    def _load_keys(self):
        """Load RSA keys for HTTP signatures if available"""
        if self.config.private_key_path:
            try:
                with open(self.config.private_key_path, 'rb') as f:
                    self.private_key = serialization.load_pem_private_key(
                        f.read(), password=None
                    )
                logger.info("Private key loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load private key: {e}")
    
    def _apply_platform_rate_limits(self, base_config):
        """Apply platform-specific rate limits to the base configuration"""
        platform_name = self.platform.platform_name
        
        # Create a copy of the base config
        import copy
        config = copy.deepcopy(base_config)
        
        # Apply platform-specific limits if available
        if platform_name in config.platform_limits:
            platform_limits = config.platform_limits[platform_name]
            
            # Override global limits with platform-specific ones
            if 'minute' in platform_limits:
                config.requests_per_minute = platform_limits['minute']
            if 'hour' in platform_limits:
                config.requests_per_hour = platform_limits['hour']
            if 'day' in platform_limits:
                config.requests_per_day = platform_limits['day']
        
        # Apply platform-specific endpoint limits
        if platform_name in config.platform_endpoint_limits:
            platform_endpoint_limits = config.platform_endpoint_limits[platform_name]
            
            # Merge with existing endpoint limits
            for endpoint, limits in platform_endpoint_limits.items():
                if endpoint not in config.endpoint_limits:
                    config.endpoint_limits[endpoint] = {}
                config.endpoint_limits[endpoint].update(limits)
        
        return config
    
    def _create_error_context(self, error, method: str, url: str, endpoint: str) -> dict:
        """Create error context for platform-aware error handling"""
        context = {
            'platform_type': self.platform.platform_name,
            'instance_url': self.config.instance_url,
            'method': method,
            'url': url,
            'endpoint': endpoint,
            'error_type': type(error).__name__,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add platform connection info if available
        if self.platform_connection:
            context.update({
                'platform_connection_id': self.platform_connection.id,
                'platform_connection_name': self.platform_connection.name,
                'username': self.platform_connection.username
            })
        
        # Add HTTP-specific context for HTTP errors
        if isinstance(error, httpx.HTTPStatusError):
            context.update({
                'status_code': error.response.status_code,
                'response_headers': dict(error.response.headers),
                'response_text': error.response.text[:500]  # Limit response text
            })
        
        return context
    
    def _handle_platform_error(self, error: httpx.HTTPStatusError, context: dict):
        """Handle platform-specific HTTP errors"""
        status_code = error.response.status_code
        platform_name = context['platform_type']
        
        # Platform-specific error handling
        if platform_name == 'mastodon':
            self._handle_mastodon_error(error, context)
        elif platform_name == 'pixelfed':
            self._handle_pixelfed_error(error, context)
        else:
            self._handle_generic_error(error, context)
        
        # Update platform connection last_used if this was a successful auth test
        if self.platform_connection and status_code < 400:
            try:
                self.platform_connection.last_used = datetime.now(timezone.utc)
                # Note: We don't commit here as we don't have session access
            except Exception as e:
                logger.warning(f"Failed to update platform connection last_used: {e}")
    
    def _handle_mastodon_error(self, error: httpx.HTTPStatusError, context: dict):
        """Handle Mastodon-specific errors"""
        status_code = error.response.status_code
        
        if status_code == 401:
            logger.error(f"Mastodon authentication failed for {context['instance_url']}: "
                        f"Invalid access token or expired credentials")
        elif status_code == 403:
            logger.error(f"Mastodon authorization failed for {context['instance_url']}: "
                        f"Access token lacks required permissions")
        elif status_code == 422:
            logger.error(f"Mastodon validation error for {context['endpoint']}: "
                        f"Invalid request data - {error.response.text[:200]}")
        elif status_code == 429:
            # Extract rate limit info from headers
            headers = error.response.headers
            reset_time = headers.get('X-RateLimit-Reset', 'unknown')
            logger.warning(f"Mastodon rate limit exceeded for {context['endpoint']}. "
                          f"Reset time: {reset_time}")
        else:
            logger.error(f"Mastodon API error {status_code} for {context['endpoint']}: "
                        f"{error.response.text[:200]}")
    
    def _handle_pixelfed_error(self, error: httpx.HTTPStatusError, context: dict):
        """Handle Pixelfed-specific errors"""
        status_code = error.response.status_code
        
        if status_code == 401:
            logger.error(f"Pixelfed authentication failed for {context['instance_url']}: "
                        f"Invalid access token")
        elif status_code == 403:
            logger.error(f"Pixelfed authorization failed for {context['instance_url']}: "
                        f"Insufficient permissions")
        elif status_code == 404:
            if 'media' in context['endpoint']:
                logger.warning(f"Pixelfed media not found for {context['endpoint']}: "
                              f"Media may have been deleted or ID is invalid")
            else:
                logger.warning(f"Pixelfed resource not found: {context['url']}")
        elif status_code == 422:
            logger.error(f"Pixelfed validation error for {context['endpoint']}: "
                        f"Invalid request data - {error.response.text[:200]}")
        elif status_code == 429:
            logger.warning(f"Pixelfed rate limit exceeded for {context['endpoint']}")
        else:
            logger.error(f"Pixelfed API error {status_code} for {context['endpoint']}: "
                        f"{error.response.text[:200]}")
    
    def _handle_generic_error(self, error: httpx.HTTPStatusError, context: dict):
        """Handle generic ActivityPub platform errors"""
        status_code = error.response.status_code
        platform_name = context['platform_type']
        
        if status_code == 401:
            logger.error(f"{platform_name} authentication failed: Invalid credentials")
        elif status_code == 403:
            logger.error(f"{platform_name} authorization failed: Insufficient permissions")
        elif status_code == 404:
            logger.warning(f"{platform_name} resource not found: {context['url']}")
        elif status_code == 429:
            logger.warning(f"{platform_name} rate limit exceeded for {context['endpoint']}")
        elif status_code >= 500:
            logger.error(f"{platform_name} server error {status_code}: {error.response.text[:200]}")
        else:
            logger.error(f"{platform_name} API error {status_code}: {error.response.text[:200]}")
    
    def _log_platform_error(self, error: Exception, context: dict):
        """Log platform-specific non-HTTP errors"""
        platform_name = context['platform_type']
        error_type = context['error_type']
        
        if isinstance(error, (httpx.ConnectError, httpx.NetworkError)):
            logger.error(f"{platform_name} network error for {context['endpoint']}: "
                        f"Cannot connect to {context['instance_url']}")
        elif isinstance(error, httpx.TimeoutException):
            logger.error(f"{platform_name} timeout error for {context['endpoint']}: "
                        f"Request timed out")
        elif isinstance(error, httpx.ReadError):
            logger.error(f"{platform_name} read error for {context['endpoint']}: "
                        f"Failed to read response")
        else:
            logger.error(f"{platform_name} {error_type} for {context['endpoint']}: {str(error)}")
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': self.config.user_agent,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
            self.session = None  # Clear reference to prevent resource leak
        
        # Cleanup platform adapter resources
        if hasattr(self.platform, 'cleanup'):
            try:
                await self.platform.cleanup()
            except Exception as e:
                logger.warning("Error during platform adapter cleanup: %s", str(e))
    
    async def _get_with_retry(self, url: str, headers: dict, params: dict = None) -> httpx.Response:
        """Make a GET request with retry logic and rate limiting"""
        # Ensure session is initialized
        await self._ensure_session()
        
        # Extract endpoint from URL for rate limiting
        endpoint = extract_endpoint_from_url(url)
        
        @async_retry(self.retry_config)
        @rate_limited(endpoint=endpoint, platform=self.platform.platform_name if self.platform else None)
        async def _get():
            try:
                response = await self.session.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                # Platform-aware error handling
                error_context = self._create_error_context(e, 'GET', url, endpoint)
                self._handle_platform_error(e, error_context)
                raise
            except Exception as e:
                # Handle other exceptions with platform context
                error_context = self._create_error_context(e, 'GET', url, endpoint)
                self._log_platform_error(e, error_context)
                raise
        
        return await _get()
    
    async def _put_with_retry(self, url: str, headers: dict, json: dict = None) -> httpx.Response:
        """Make a PUT request with retry logic and rate limiting"""
        # Ensure session is initialized
        await self._ensure_session()
        
        # Extract endpoint from URL for rate limiting
        endpoint = extract_endpoint_from_url(url)
        
        @async_retry(self.retry_config)
        @rate_limited(endpoint=endpoint, platform=self.platform.platform_name if self.platform else None)
        async def _put():
            try:
                response = await self.session.put(url, headers=headers, json=json)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                # Platform-aware error handling
                error_context = self._create_error_context(e, 'PUT', url, endpoint)
                self._handle_platform_error(e, error_context)
                raise
            except Exception as e:
                # Handle other exceptions with platform context
                error_context = self._create_error_context(e, 'PUT', url, endpoint)
                self._log_platform_error(e, error_context)
                raise
        
        return await _put()
    
    async def _post_with_retry(self, url: str, headers: dict, json: dict = None) -> httpx.Response:
        """Make a POST request with retry logic and rate limiting"""
        # Extract endpoint from URL for rate limiting
        endpoint = extract_endpoint_from_url(url)
        
        @async_retry(self.retry_config)
        @rate_limited(endpoint=endpoint, platform=self.platform.platform_name if self.platform else None)
        async def _post():
            try:
                response = await self.session.post(url, headers=headers, json=json)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                # Platform-aware error handling
                error_context = self._create_error_context(e, 'POST', url, endpoint)
                self._handle_platform_error(e, error_context)
                raise
            except Exception as e:
                # Handle other exceptions with platform context
                error_context = self._create_error_context(e, 'POST', url, endpoint)
                self._log_platform_error(e, error_context)
                raise
        
        return await _post()
        
    async def _delete_with_retry(self, url: str, headers: dict) -> httpx.Response:
        """Make a DELETE request with retry logic and rate limiting"""
        # Extract endpoint from URL for rate limiting
        endpoint = extract_endpoint_from_url(url)
        
        @async_retry(self.retry_config)
        @rate_limited(endpoint=endpoint, platform=self.platform.platform_name if self.platform else None)
        async def _delete():
            try:
                response = await self.session.delete(url, headers=headers)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                # Platform-aware error handling
                error_context = self._create_error_context(e, 'DELETE', url, endpoint)
                self._handle_platform_error(e, error_context)
                raise
            except Exception as e:
                # Handle other exceptions with platform context
                error_context = self._create_error_context(e, 'DELETE', url, endpoint)
                self._log_platform_error(e, error_context)
                raise
        
        return await _delete()
    
    async def get_user_posts(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve user's posts from ActivityPub platform using API.
        
        Args:
            user_id: The user ID to fetch posts for
            limit: Maximum number of posts to fetch
            
        Returns:
            List of posts in ActivityPub format
            
        Raises:
            PlatformAdapterError: If the platform adapter fails
        """
        try:
            # Delegate to the platform-specific adapter
            posts = await self.platform.get_user_posts(self, user_id, limit)
            
            logger.info(f"Retrieved {len(posts)} {self.platform.platform_name} posts for user {sanitize_for_log(user_id)}")
            return posts
            
        except PlatformAdapterError:
            # Re-raise platform adapter errors
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve posts for user {sanitize_for_log(user_id)}: {e}")
            raise PlatformAdapterError(f"Failed to retrieve posts for user {sanitize_for_log(user_id)}: {e}")
    
    async def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific post by ID.
        
        Args:
            post_id: The ID of the post to retrieve
            
        Returns:
            Post data in ActivityPub format, or None if not found
            
        Raises:
            PlatformAdapterError: If the platform adapter fails
        """
        try:
            # Delegate to the platform-specific adapter
            post = await self.platform.get_post_by_id(self, post_id)
            
            if post:
                logger.info(f"Retrieved {self.platform.platform_name} post {sanitize_for_log(post_id)}")
            else:
                logger.warning(f"Post {sanitize_for_log(post_id)} not found on {self.platform.platform_name}")
                
            return post
            
        except PlatformAdapterError:
            # Re-raise platform adapter errors
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve post {sanitize_for_log(post_id)}: {e}")
            raise PlatformAdapterError(f"Failed to retrieve post {sanitize_for_log(post_id)}: {e}")
    
    async def update_post(self, post_id: str, updated_post: Dict[str, Any]) -> bool:
        """
        Update a post with new content (primarily for alt text).
        
        Args:
            post_id: The ID of the post to update
            updated_post: The updated post data
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            PlatformAdapterError: If the platform adapter fails
        """
        try:
            # Delegate to the platform-specific adapter
            result = await self.platform.update_post(self, post_id, updated_post)
            
            if result:
                logger.info(f"Successfully updated {self.platform.platform_name} post {sanitize_for_log(post_id)}")
            else:
                logger.warning(f"Failed to update {self.platform.platform_name} post {sanitize_for_log(post_id)}")
                
            return result
            
        except PlatformAdapterError:
            # Re-raise platform adapter errors
            raise
        except Exception as e:
            logger.error(f"Failed to update post {sanitize_for_log(post_id)}: {e}")
            raise PlatformAdapterError(f"Failed to update post {sanitize_for_log(post_id)}: {e}")
            
    async def update_media_caption(self, image_post_id: str, caption: str) -> bool:
        """
        Update a specific media attachment's caption/description.
        
        Args:
            image_post_id: The ID of the media attachment to update
            caption: The new caption text
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            PlatformAdapterError: If the platform adapter fails
        """
        try:
            if not image_post_id:
                logger.error("No image_post_id provided for caption update")
                return False
            
            # Delegate to the platform-specific adapter
            result = await self.platform.update_media_caption(self, image_post_id, caption)
            
            if result:
                logger.info(f"Successfully updated {self.platform.platform_name} media caption for {sanitize_for_log(image_post_id)}")
            else:
                logger.warning(f"Failed to update {self.platform.platform_name} media caption for {sanitize_for_log(image_post_id)}")
                
            return result
            
        except PlatformAdapterError:
            # Re-raise platform adapter errors
            raise
        except Exception as e:
            logger.error(f"Failed to update media caption for {sanitize_for_log(image_post_id)}: {e}")
            raise PlatformAdapterError(f"Failed to update media caption for {sanitize_for_log(image_post_id)}: {e}")
    
    def extract_images_from_post(self, post: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract image attachments from a post.
        
        Args:
            post: The post data in ActivityPub format
            
        Returns:
            List of image attachment dictionaries
            
        Raises:
            PlatformAdapterError: If the platform adapter fails
        """
        try:
            # Delegate to the platform-specific adapter
            images = self.platform.extract_images_from_post(post)
            
            logger.debug(f"Extracted {len(images)} images from {self.platform.platform_name} post")
            return images
            
        except Exception as e:
            logger.error(f"Failed to extract images from post: {e}")
            raise PlatformAdapterError(f"Failed to extract images from post: {e}")
        
    def get_platform_name(self) -> str:
        """
        Get the name of the current platform.
        
        Returns:
            String with the platform name (e.g., 'pixelfed', 'mastodon')
        """
        return self.platform.platform_name
    
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Get information about the current platform adapter.
        
        Returns:
            Dictionary with platform information
        """
        return {
            "platform_name": self.platform.platform_name,
            "platform_class": self.platform.__class__.__name__,
            "instance_url": self.config.instance_url,
            "api_type": getattr(self.config, 'api_type', 'unknown')
        }
    
    async def authenticate(self) -> bool:
        """
        Authenticate with the platform if required.
        
        Returns:
            True if authentication successful or not required, False otherwise
        """
        try:
            # Check if the platform adapter has an authenticate method
            if hasattr(self.platform, 'authenticate'):
                result = await self.platform.authenticate(self)
                logger.info(f"Authentication with {self.platform.platform_name}: {'successful' if result else 'failed'}")
                return result
            else:
                # Platform doesn't require explicit authentication
                logger.debug(f"Platform {self.platform.platform_name} doesn't require explicit authentication")
                return True
                
        except Exception as e:
            logger.error(f"Authentication failed with {self.platform.platform_name}: {e}")
            return False
    
    async def test_connection(self) -> tuple[bool, str]:
        """
        Test the connection to the platform.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # First test authentication
            auth_result = await self.authenticate()
            if not auth_result:
                return False, "Authentication failed"
            
            # Try to make a simple API call to verify connectivity
            # Use minimal headers for better compatibility
            headers = {
                'Authorization': f'Bearer {self.config.access_token}'
            }
            
            # Use verify_credentials endpoint as it's available on most platforms
            verify_url = f"{self.config.instance_url}/api/v1/accounts/verify_credentials"
            
            try:
                response = await self._get_with_retry(verify_url, headers)
                user_data = response.json()
                username = user_data.get('username', 'unknown')
                return True, f"Connection successful - authenticated as {username}"
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    return False, "Invalid access token"
                elif e.response.status_code == 403:
                    return False, "Access token lacks required permissions"
                else:
                    return False, f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                return False, f"Connection test failed: {str(e)}"
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False, f"Connection test error: {str(e)}"
    
    async def validate_platform_connection(self) -> dict:
        """
        Validate the platform connection and return detailed status.
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': False,
            'platform_type': self.platform.platform_name,
            'instance_url': self.config.instance_url,
            'username': getattr(self.config, 'username', None),
            'tests': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Test 1: Basic configuration validation
            validation_result['tests']['config_validation'] = True
            
            # Test 2: Network connectivity
            try:
                # Simple HTTP request to instance
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.config.instance_url}/api/v1/instance")
                    if response.status_code == 200:
                        validation_result['tests']['network_connectivity'] = True
                        instance_info = response.json()
                        validation_result['instance_info'] = {
                            'title': instance_info.get('title', 'Unknown'),
                            'version': instance_info.get('version', 'Unknown'),
                            'description': instance_info.get('description', '')[:100]
                        }
                    else:
                        validation_result['tests']['network_connectivity'] = False
                        validation_result['errors'].append(f"Instance API returned {response.status_code}")
            except Exception as e:
                validation_result['tests']['network_connectivity'] = False
                validation_result['errors'].append(f"Network connectivity failed: {str(e)}")
            
            # Test 3: Authentication
            auth_success, auth_message = await self.test_connection()
            validation_result['tests']['authentication'] = auth_success
            if not auth_success:
                validation_result['errors'].append(f"Authentication failed: {auth_message}")
            else:
                # Extract username from successful auth message
                if "authenticated as" in auth_message:
                    username = auth_message.split("authenticated as ")[-1]
                    validation_result['authenticated_username'] = username
            
            # Test 4: Platform-specific validation
            if hasattr(self.platform, 'validate_connection'):
                try:
                    platform_validation = await self.platform.validate_connection(self)
                    validation_result['tests']['platform_specific'] = platform_validation.get('success', False)
                    if not platform_validation.get('success', False):
                        validation_result['errors'].extend(platform_validation.get('errors', []))
                    validation_result['warnings'].extend(platform_validation.get('warnings', []))
                except Exception as e:
                    validation_result['tests']['platform_specific'] = False
                    validation_result['errors'].append(f"Platform validation failed: {str(e)}")
            else:
                validation_result['tests']['platform_specific'] = True  # No specific validation needed
            
            # Overall validation result
            validation_result['is_valid'] = all(validation_result['tests'].values())
            
            # Add rate limit information if available
            if hasattr(self, 'rate_limiter'):
                validation_result['rate_limit_stats'] = self.get_rate_limit_stats()
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")
            logger.error(f"Platform connection validation failed: {e}")
        
        return validation_result
    
    async def health_check(self) -> dict:
        """
        Perform a comprehensive health check of the platform connection.
        
        Returns:
            Dictionary with health check results
        """
        health_status = {
            'status': 'unknown',
            'timestamp': datetime.now().isoformat(),
            'platform_info': self.get_platform_info(),
            'checks': {},
            'metrics': {},
            'issues': []
        }
        
        try:
            # Check 1: Connection validation
            validation_result = await self.validate_platform_connection()
            health_status['checks']['connection_valid'] = validation_result['is_valid']
            if not validation_result['is_valid']:
                health_status['issues'].extend(validation_result['errors'])
            
            # Check 2: API response time
            start_time = datetime.now()
            try:
                success, message = await self.test_connection()
                response_time = (datetime.now() - start_time).total_seconds()
                health_status['metrics']['api_response_time'] = response_time
                health_status['checks']['api_responsive'] = success
                
                if response_time > 5.0:
                    health_status['issues'].append(f"Slow API response time: {response_time:.2f}s")
                elif response_time > 2.0:
                    health_status['issues'].append(f"Moderate API response time: {response_time:.2f}s")
                    
            except Exception as e:
                health_status['checks']['api_responsive'] = False
                health_status['issues'].append(f"API not responsive: {str(e)}")
            
            # Check 3: Rate limiting status
            if hasattr(self, 'rate_limiter'):
                rate_stats = self.get_rate_limit_stats()
                health_status['metrics']['rate_limit'] = rate_stats
                
                # Check if we're close to rate limits
                requests_info = rate_stats.get('requests', {})
                if requests_info.get('requests_per_minute', 0) > 50:  # Assuming 60 req/min limit
                    health_status['issues'].append("Approaching rate limit")
                
                health_status['checks']['rate_limit_ok'] = len([
                    issue for issue in health_status['issues'] 
                    if 'rate limit' in issue.lower()
                ]) == 0
            else:
                health_status['checks']['rate_limit_ok'] = True
            
            # Check 4: Platform connection freshness
            if self.platform_connection:
                last_used = self.platform_connection.last_used
                if last_used:
                    time_since_use = (datetime.now(datetime.UTC)- last_used).total_seconds()
                    health_status['metrics']['time_since_last_use'] = time_since_use
                    
                    if time_since_use > 86400:  # 24 hours
                        health_status['issues'].append("Platform connection not used recently")
                
                health_status['checks']['connection_fresh'] = last_used is not None
            else:
                health_status['checks']['connection_fresh'] = True  # Legacy config
            
            # Determine overall status
            all_checks_passed = all(health_status['checks'].values())
            has_critical_issues = any(
                'authentication' in issue.lower() or 'connection' in issue.lower() 
                for issue in health_status['issues']
            )
            
            if all_checks_passed and not has_critical_issues:
                health_status['status'] = 'healthy'
            elif not has_critical_issues:
                health_status['status'] = 'degraded'
            else:
                health_status['status'] = 'unhealthy'
                
        except Exception as e:
            health_status['status'] = 'error'
            health_status['issues'].append(f"Health check error: {str(e)}")
            logger.error(f"Health check failed: {e}")
        
        return health_status
    
    def get_retry_stats(self) -> str:
        """Get statistics about API call retries"""
        return get_retry_stats_summary()
        
    def get_detailed_retry_stats(self) -> dict:
        """Get detailed statistics about API call retries in JSON format"""
        return get_retry_stats_detailed()
        
    def get_platform_specific_retry_info(self) -> dict:
        """Get platform-specific retry information and statistics"""
        stats = get_retry_stats_detailed()
        
        # Extract platform-specific information
        platform_stats = {
            f"{self.platform.platform_name}_api_calls": {
                "total": 0,
                "retried": 0,
                "success_rate": 0
            },
            "endpoints": {},
            "status_codes": {},
            "common_errors": {}
        }
        
        # Count API calls for this platform
        for endpoint, count in stats.get("by_endpoint", {}).items():
            if "/api/v1/" in endpoint:  # Most ActivityPub platforms use /api/v1/
                platform_stats[f"{self.platform.platform_name}_api_calls"]["total"] += count
                platform_stats["endpoints"][endpoint] = count
        
        # Extract status codes
        for status_code, count in stats.get("by_status_code", {}).items():
            platform_stats["status_codes"][str(status_code)] = count
            
        # Extract common errors
        for exception, count in stats.get("by_exception", {}).items():
            platform_stats["common_errors"][exception] = count
            
        # Calculate success rate if there are any retried operations
        if stats.get("summary", {}).get("retried_operations", 0) > 0:
            success_rate = (stats.get("summary", {}).get("successful_retries", 0) / 
                           stats.get("summary", {}).get("retried_operations", 1)) * 100
            platform_stats[f"{self.platform.platform_name}_api_calls"]["retried"] = stats.get("summary", {}).get("retried_operations", 0)
            platform_stats[f"{self.platform.platform_name}_api_calls"]["success_rate"] = round(success_rate, 1)
            
        return platform_stats
        
    def get_rate_limit_stats(self) -> dict:
        """Get statistics about API rate limiting"""
        if hasattr(self, 'rate_limiter'):
            return self.rate_limiter.get_stats()
        return {"error": "Rate limiter not initialized"}
    
    def reset_rate_limit_stats(self) -> None:
        """Reset rate limiting statistics"""
        if hasattr(self, 'rate_limiter'):
            self.rate_limiter.reset_stats()
            
    def get_api_usage_report(self) -> dict:
        """
        Get a comprehensive report of API usage including both retry and rate limit statistics
        
        Returns:
            Dictionary with API usage statistics
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "platform_info": self.get_platform_info(),
            "instance": self.config.instance_url,
            "retry_stats": self.get_detailed_retry_stats(),
            "rate_limit_stats": self.get_rate_limit_stats(),
            "platform_specific": self.get_platform_specific_retry_info()
        }
        
        # Add summary section with key metrics
        retry_summary = report["retry_stats"].get("summary", {})
        rate_limit_summary = report["rate_limit_stats"].get("requests", {})
        
        report["summary"] = {
            "total_api_calls": retry_summary.get("total_operations", 0),
            "retried_calls": retry_summary.get("retried_operations", 0),
            "throttled_calls": rate_limit_summary.get("throttled", 0),
            "retry_success_rate": retry_summary.get("success_rate", 0),
            "average_retry_time": report["retry_stats"].get("timing", {}).get("avg_retry_time", 0),
            "average_rate_limit_wait": report["rate_limit_stats"].get("wait_time", {}).get("average", 0),
            "requests_per_minute": rate_limit_summary.get("requests_per_minute", 0)
        }
        
        return report