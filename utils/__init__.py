# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
DEPRECATED: Root utils package - Use app.utils instead

This module provides backward compatibility imports for the old utils structure.
All utilities have been moved to app.utils with proper organization.

New import paths:
- utils.decorators -> app.utils.web.decorators
- utils.request_helpers -> app.utils.web.request_helpers
- utils.response_helpers -> app.utils.web.response_helpers
- utils.error_responses -> app.utils.web.error_responses
- utils.asset_optimizer -> app.utils.assets.asset_optimizer
- utils.static_asset_helpers -> app.utils.assets.static_asset_helpers
- utils.static_cache_middleware -> app.utils.assets.static_cache_middleware
- utils.template_cache -> app.utils.templates.template_cache
- utils.session_detection -> app.utils.session.session_detection
- utils.form_helpers -> app.utils.forms.form_helpers
- utils.landing_page_fallback -> app.utils.landing.landing_page_fallback
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The root 'utils' package is deprecated. Use 'app.utils' instead. "
    "See app.utils documentation for new import paths.",
    DeprecationWarning,
    stacklevel=2
)

# Backward compatibility imports - redirect to new locations
try:
    # Import from new consolidated app.utils structure
    from app.utils.helpers.utils import async_retry, RetryConfig, get_retry_stats_summary, get_retry_stats_detailed
    
    # Web utilities
    from app.utils.web.decorators import require_platform_context, get_platform_context_or_redirect
    from app.utils.web.request_helpers import (
        extract_form_data, get_form_int, get_form_float, get_form_bool,
        validate_request_origin, sanitize_user_input, validate_url_parameter, get_client_ip
    )
    from app.utils.web.response_helpers import success_response, error_response, validation_error_response
    from app.utils.web.error_responses import (
        ErrorCodes, create_error_response, validation_error, configuration_error,
        internal_error, handle_security_error
    )
    
    # Asset utilities
    from app.utils.assets.asset_optimizer import (
        AssetOptimizer, get_asset_optimizer, get_critical_css, 
        get_resource_hints, get_versioned_asset_url
    )
    from app.utils.assets.static_asset_helpers import (
        static_url_with_cache, static_url_with_version, get_asset_size,
        get_asset_info, register_template_filters
    )
    from app.utils.assets.static_cache_middleware import StaticAssetCacheMiddleware
    
    # Template utilities
    from app.utils.templates.template_cache import (
        TemplateCacheManager, get_template_cache_manager, cached_render_template,
        cache_template, invalidate_template_cache, clear_template_cache, get_template_cache_stats
    )
    
    # Session utilities
    from app.utils.session.session_detection import (
        SessionDetectionResult, has_previous_session, detect_previous_session,
        clear_session_indicators, get_session_detection_summary
    )
    
    # Form utilities
    from app.utils.forms.form_helpers import (
        populate_form_from_dict, create_settings_form_with_data,
        validate_and_extract_form_data, CAPTION_SETTINGS_DEFAULTS
    )
    
    # Landing page utilities
    from app.utils.landing.landing_page_fallback import (
        LandingPageError, AuthenticationFailureError, TemplateRenderingError, SessionDetectionError,
        log_authentication_failure, create_fallback_landing_html, handle_template_rendering_error,
        handle_session_detection_error, handle_authentication_error, ensure_system_stability,
        test_error_scenarios
    )
    
    __all__ = [
        # Core utilities
        'async_retry', 'RetryConfig', 'get_retry_stats_summary', 'get_retry_stats_detailed',
        
        # Web utilities
        'require_platform_context', 'get_platform_context_or_redirect',
        'extract_form_data', 'get_form_int', 'get_form_float', 'get_form_bool',
        'validate_request_origin', 'sanitize_user_input', 'validate_url_parameter', 'get_client_ip',
        'success_response', 'error_response', 'validation_error_response',
        'ErrorCodes', 'create_error_response', 'validation_error', 'configuration_error',
        'internal_error', 'handle_security_error',
        
        # Asset utilities
        'AssetOptimizer', 'get_asset_optimizer', 'get_critical_css', 
        'get_resource_hints', 'get_versioned_asset_url',
        'static_url_with_cache', 'static_url_with_version', 'get_asset_size',
        'get_asset_info', 'register_template_filters',
        'StaticAssetCacheMiddleware',
        
        # Template utilities
        'TemplateCacheManager', 'get_template_cache_manager', 'cached_render_template',
        'cache_template', 'invalidate_template_cache', 'clear_template_cache', 'get_template_cache_stats',
        
        # Session utilities
        'SessionDetectionResult', 'has_previous_session', 'detect_previous_session',
        'clear_session_indicators', 'get_session_detection_summary',
        
        # Form utilities
        'populate_form_from_dict', 'create_settings_form_with_data',
        'validate_and_extract_form_data', 'CAPTION_SETTINGS_DEFAULTS',
        
        # Landing page utilities
        'LandingPageError', 'AuthenticationFailureError', 'TemplateRenderingError', 'SessionDetectionError',
        'log_authentication_failure', 'create_fallback_landing_html', 'handle_template_rendering_error',
        'handle_session_detection_error', 'handle_authentication_error', 'ensure_system_stability',
        'test_error_scenarios'
    ]
    
except ImportError as e:
    # Fallback if new structure is not available
    warnings.warn(
        f"Failed to import from new app.utils structure: {e}. "
        "Using fallback implementations.",
        ImportWarning,
        stacklevel=2
    )
    
    # Minimal fallback implementations
    def async_retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class RetryConfig:
        def __init__(self, *args, **kwargs):
            pass
    
    def get_retry_stats_summary():
        return {}
    
    def get_retry_stats_detailed():
        return {}
    
    __all__ = ['async_retry', 'RetryConfig', 'get_retry_stats_summary', 'get_retry_stats_detailed']
