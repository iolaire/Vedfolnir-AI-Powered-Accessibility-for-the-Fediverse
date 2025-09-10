# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Consolidated Database Framework for Vedfolnir.

This is the single, authoritative database framework that provides:
- MySQL database management and operations
- Redis session and caching functionality  
- Database utility functions and helpers
- Connection management and optimization
- Performance monitoring and health checks

All database-related functionality should use this consolidated framework.
No duplicate database systems should be created outside of this module.
"""

from .core.database_manager import DatabaseManager
from .components.database_helpers import (
    get_user_platform_or_404,
    get_dashboard_statistics,
    batch_update_images,
    get_user_platform_stats
)

__all__ = [
    'DatabaseManager',
    'get_user_platform_or_404',
    'get_dashboard_statistics', 
    'batch_update_images',
    'get_user_platform_stats'
]