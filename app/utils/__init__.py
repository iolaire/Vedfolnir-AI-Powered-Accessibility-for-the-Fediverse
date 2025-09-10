# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Application utilities package"""

# Import from existing subdirectories
from . import helpers
from . import initialization
from . import logging
from . import migration
from . import processing
from . import templates
from . import version

# Import from new consolidated subdirectories
from . import web
from . import assets
from . import session
from . import forms
from . import landing

# Import commonly used utilities for backward compatibility
from .helpers.utils import async_retry, RetryConfig, get_retry_stats_summary, get_retry_stats_detailed
from .web.decorators import require_platform_context, get_platform_context_or_redirect
from .web.error_responses import ErrorCodes, create_error_response, validation_error, configuration_error, internal_error
from .web.response_helpers import success_response, error_response, validation_error_response
from .assets.static_asset_helpers import register_template_filters
from .session.session_detection import has_previous_session, detect_previous_session

__all__ = [
    # Submodules
    'helpers', 'initialization', 'logging', 'migration', 'processing', 'templates', 'version',
    'web', 'assets', 'session', 'forms', 'landing',
    
    # Common utilities
    'async_retry', 'RetryConfig', 'get_retry_stats_summary', 'get_retry_stats_detailed',
    'require_platform_context', 'get_platform_context_or_redirect',
    'ErrorCodes', 'create_error_response', 'validation_error', 'configuration_error', 'internal_error',
    'success_response', 'error_response', 'validation_error_response',
    'register_template_filters',
    'has_previous_session', 'detect_previous_session'
]