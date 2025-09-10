# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Asset utilities package"""

from .asset_optimizer import (
    AssetOptimizer, get_asset_optimizer, get_critical_css, 
    get_resource_hints, get_versioned_asset_url
)
from .static_asset_helpers import (
    static_url_with_cache, static_url_with_version, get_asset_size,
    get_asset_info, register_template_filters
)
from .static_cache_middleware import StaticAssetCacheMiddleware

__all__ = [
    'AssetOptimizer', 'get_asset_optimizer', 'get_critical_css', 
    'get_resource_hints', 'get_versioned_asset_url',
    'static_url_with_cache', 'static_url_with_version', 'get_asset_size',
    'get_asset_info', 'register_template_filters',
    'StaticAssetCacheMiddleware'
]