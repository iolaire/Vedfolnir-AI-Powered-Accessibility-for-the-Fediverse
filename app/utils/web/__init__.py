# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Web utilities package"""

from .decorators import require_platform_context, get_platform_context_or_redirect
from .request_helpers import (
    extract_form_data, get_form_int, get_form_float, get_form_bool,
    validate_request_origin, sanitize_user_input, validate_url_parameter, get_client_ip
)
from .response_helpers import success_response, error_response, validation_error_response
from .error_responses import (
    ErrorCodes, create_error_response, validation_error, configuration_error,
    internal_error, handle_security_error
)

__all__ = [
    'require_platform_context', 'get_platform_context_or_redirect',
    'extract_form_data', 'get_form_int', 'get_form_float', 'get_form_bool',
    'validate_request_origin', 'sanitize_user_input', 'validate_url_parameter', 'get_client_ip',
    'success_response', 'error_response', 'validation_error_response',
    'ErrorCodes', 'create_error_response', 'validation_error', 'configuration_error',
    'internal_error', 'handle_security_error'
]