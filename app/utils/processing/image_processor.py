# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import asyncio
import logging
import os
import hashlib
import io
from typing import Optional, Tuple, List
from PIL import Image, UnidentifiedImageError
import httpx
import aiofiles
from urllib.parse import urlparse
from config import Config

# Check if pillow-heif is available for HEIC/HEIF support
try:
    import pillow_heif
    HAS_HEIF_SUPPORT = True
    pillow_heif.register_heif_opener()
except ImportError:
    HAS_HEIF_SUPPORT = False
    logger = logging.getLogger(__name__)
    logger.warning("pillow-heif not installed. HEIC/HEIF support will be limited.")

# Check if pillow-avif-plugin is available for AVIF support
try:
    from pillow_avif import AvifImagePlugin
    HAS_AVIF_SUPPORT = True
except ImportError:
    HAS_AVIF_SUPPORT = False
    logger = logging.getLogger(__name__)
    logger.warning("pillow-avif-plugin not installed. AVIF support will be limited.")

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Handle image downloading and processing with persistent storage"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = None
        self.storage_dir = config.storage.images_dir
        os.makedirs(self.storage_dir, exist_ok=True)
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    def _get_image_filename(self, url: str, media_type: str = None) -> str:
        """Generate consistent filename for image URL"""
        # Create hash of URL for consistent naming
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        
        # Try to get extension from URL or media type
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Extended list of supported image extensions
        if path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif', '.avif')):
            ext = os.path.splitext(path)[1]
        elif media_type:
            # Extended media type mapping
            ext_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/heic': '.heic',
                'image/heif': '.heif',
                'image/avif': '.avif',
                # Additional MIME types
                'image/heic-sequence': '.heic',
                'image/heif-sequence': '.heif'
            }
            ext = ext_map.get(media_type.lower(), '.jpg')
        else:
            ext = '.jpg'
        
        return f"{url_hash}{ext}"
    
    def validate_image(self, image_path: str) -> Tuple[bool, str]:
        """
        Validate an image file to ensure it's a valid image and meets requirements
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.exists(image_path):
            return False, f"Image file does not exist: {image_path}"
            
        # Check file size
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            return False, f"Image file is empty: {image_path}"
            
        # Maximum file size (20MB)
        max_file_size = 20 * 1024 * 1024
        if file_size > max_file_size:
            return False, f"Image file is too large ({file_size / 1024 / 1024:.2f}MB > {max_file_size / 1024 / 1024:.2f}MB): {image_path}"
            
        # Try to open and validate the image
        try:
            with Image.open(image_path) as img:
                # Check image dimensions
                width, height = img.size
                
                # Minimum dimensions
                min_dimension = 50
                if width < min_dimension or height < min_dimension:
                    return False, f"Image dimensions too small ({width}x{height} < {min_dimension}x{min_dimension}): {image_path}"
                    
                # Maximum dimensions
                max_dimension = 10000
                if width > max_dimension or height > max_dimension:
                    return False, f"Image dimensions too large ({width}x{height} > {max_dimension}x{max_dimension}): {image_path}"
                    
                # Check if image data can be loaded
                img.load()
                
                # Image is valid
                return True, ""
                
        except UnidentifiedImageError:
            return False, f"File is not a valid image: {image_path}"
        except Exception as e:
            return False, f"Error validating image: {str(e)}"
    
    async def download_and_store_image(self, url: str, media_type: str = None) -> Optional[str]:
        """Download image and store it permanently"""
        try:
            # Ensure session is initialized
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)
            
            filename = self._get_image_filename(url, media_type)
            filepath = os.path.join(self.storage_dir, filename)
            
            # Check if file already exists
            if os.path.exists(filepath):
                logger.debug(f"Image already exists: {filepath}")
                # Validate existing image
                is_valid, error_message = self.validate_image(filepath)
                if not is_valid:
                    logger.warning(f"Existing image is invalid: {error_message}. Will re-download.")
                    # Continue with download to replace invalid image
                else:
                    return filepath
            
            # Download image with redirect following
            response = await self.session.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # Check if we got an image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Downloaded content is not an image: {content_type}")
                # Continue anyway, we'll validate with PIL later
            
            # Create a temporary file first for validation
            temp_filepath = f"{filepath}.tmp"
            
            # Save image to temporary file
            async with aiofiles.open(temp_filepath, 'wb') as f:
                await f.write(response.content)
            
            # Validate the downloaded image
            is_valid, error_message = self.validate_image(temp_filepath)
            if not is_valid:
                # Remove the temporary file
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                logger.error(f"Downloaded image is invalid: {error_message}")
                return None
                
            # Move the temporary file to the final location
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_filepath, filepath)
            
            # Verify and optimize image
            optimized_path = self._optimize_image(filepath)
            
            # Final validation after optimization
            is_valid, error_message = self.validate_image(optimized_path)
            if not is_valid:
                logger.error(f"Optimized image is invalid: {error_message}")
                if os.path.exists(optimized_path):
                    os.remove(optimized_path)
                return None
            
            from app.core.security.core.security_utils import sanitize_for_log
            logger.info(f"Downloaded and stored image: {sanitize_for_log(url)} -> {sanitize_for_log(optimized_path)}")
            return optimized_path
            
        except Exception as e:
            from app.core.security.core.security_utils import sanitize_for_log
            logger.error(f"Failed to download/store image {sanitize_for_log(url)}: {sanitize_for_log(str(e))}")
            return None
    
    def _optimize_image(self, image_path: str) -> str:
        """Optimize image for storage and processing"""
        try:
            # Handle special formats (HEIC/HEIF/AVIF) that might need conversion
            lower_path = image_path.lower()
            
            # Convert HEIC/HEIF to JPEG if detected
            if lower_path.endswith(('.heic', '.heif')):
                if not HAS_HEIF_SUPPORT:
                    logger.warning(f"HEIC/HEIF support not available. Attempting basic conversion for {image_path}")
                # Always convert HEIC/HEIF to JPEG for better compatibility
                new_path = image_path.rsplit('.', 1)[0] + '.jpg'
                with Image.open(image_path) as img:
                    # Convert to RGB (HEIC may have different color spaces)
                    img = img.convert('RGB')
                    img.save(new_path, 'JPEG', quality=85, optimize=True)
                # Remove original HEIC/HEIF file after conversion
                if os.path.exists(new_path) and os.path.exists(image_path):
                    os.remove(image_path)
                image_path = new_path
                
            # Convert AVIF to JPEG if detected
            elif lower_path.endswith('.avif'):
                if not HAS_AVIF_SUPPORT:
                    logger.warning(f"AVIF support not available. Attempting basic conversion for {image_path}")
                # Always convert AVIF to JPEG for better compatibility
                new_path = image_path.rsplit('.', 1)[0] + '.jpg'
                with Image.open(image_path) as img:
                    # Convert to RGB (AVIF may have different color spaces)
                    img = img.convert('RGB')
                    img.save(new_path, 'JPEG', quality=85, optimize=True)
                # Remove original AVIF file after conversion
                if os.path.exists(new_path) and os.path.exists(image_path):
                    os.remove(image_path)
                image_path = new_path
            
            # Standard optimization for all image types
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = (1024, 1024)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save optimized version
                if image_path.lower().endswith('.png') and img.mode == 'RGB':
                    # Convert PNG to JPEG if no transparency needed
                    new_path = image_path.rsplit('.', 1)[0] + '.jpg'
                    img.save(new_path, 'JPEG', quality=85, optimize=True)
                    if new_path != image_path and os.path.exists(image_path):
                        os.remove(image_path)
                    return new_path
                else:
                    img.save(image_path, quality=85, optimize=True)
                    return image_path
                    
        except Exception as e:
            logger.error(f"Failed to optimize image {image_path}: {e}")
            return image_path
    
    def get_image_info(self, image_path: str) -> dict:
        """Get image information"""
        try:
            with Image.open(image_path) as img:
                return {
                    'size': img.size,
                    'mode': img.mode,
                    'format': img.format,
                    'file_size': os.path.getsize(image_path)
                }
        except Exception as e:
            logger.error(f"Failed to get image info for {image_path}: {e}")
            return {}
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None