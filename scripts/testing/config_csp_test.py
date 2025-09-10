# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration for CSP compliance testing
"""

import os
from config import Config


class CSPTestConfig(Config):
    """Configuration with strict CSP enabled for testing"""
    
    # Enable strict CSP testing
    CSP_STRICT_MODE = True
    CSP_REPORT_ONLY = os.environ.get('CSP_REPORT_ONLY', 'false').lower() == 'true'
    
    # Security settings
    SECURITY_CSP_ENABLED = True
    SECURITY_HEADERS_ENABLED = True
    
    # Testing settings
    TESTING = True
    WTF_CSRF_ENABLED = True
    
    @staticmethod
    def init_app(app):
        """Initialize app with CSP testing configuration"""
        Config.init_app(app)
        
        # Enable CSP testing middleware
        from app.core.security.config.strict_csp_config import CSPTestingMiddleware
        
        csp_middleware = CSPTestingMiddleware(
            app=app,
            strict_mode=CSPTestConfig.CSP_STRICT_MODE,
            report_only=CSPTestConfig.CSP_REPORT_ONLY
        )
        
        # Store middleware reference for testing
        app.csp_testing_middleware = csp_middleware
