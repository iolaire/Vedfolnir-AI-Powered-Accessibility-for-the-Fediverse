# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Landing page utilities package"""

from .landing_page_fallback import (
    LandingPageError, AuthenticationFailureError, TemplateRenderingError, SessionDetectionError,
    log_authentication_failure, create_fallback_landing_html, handle_template_rendering_error,
    handle_session_detection_error, handle_authentication_error, ensure_system_stability,
    test_error_scenarios
)

__all__ = [
    'LandingPageError', 'AuthenticationFailureError', 'TemplateRenderingError', 'SessionDetectionError',
    'log_authentication_failure', 'create_fallback_landing_html', 'handle_template_rendering_error',
    'handle_session_detection_error', 'handle_authentication_error', 'ensure_system_stability',
    'test_error_scenarios'
]