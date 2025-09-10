# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""ActivityPub service module."""

# Export main classes for easier importing
from .components.activitypub_client import ActivityPubClient
from .components.activitypub_platforms import (
    ActivityPubPlatform, 
    PixelfedPlatform, 
    MastodonPlatform, 
    PleromaPlatform,
    PlatformAdapterFactory, 
    PlatformAdapterError,
    get_platform_adapter,
    detect_platform_type
)
# Note: PostingService not imported here to avoid circular imports with DatabaseManager
# Import directly: from app.services.activitypub.posts.service import PostingService

__all__ = [
    'ActivityPubClient',
    'ActivityPubPlatform',
    'PixelfedPlatform',
    'MastodonPlatform',
    'PleromaPlatform',
    'PlatformAdapterFactory',
    'PlatformAdapterError',
    'get_platform_adapter',
    'detect_platform_type',
    # 'PostingService'  # Excluded to avoid circular imports
]