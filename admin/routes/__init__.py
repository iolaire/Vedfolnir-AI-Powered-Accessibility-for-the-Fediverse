# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Routes Package"""

def register_all_routes(bp):
    """Register all admin routes"""
    from . import dashboard
    from . import user_management
    from . import system_health
    from . import monitoring
    from . import dashboard_monitoring
    from . import cleanup
    from . import admin_api
    from . import security_audit_api
    from . import websocket_routes
    from . import admin_job_management
    from . import admin_job_api
    from . import configuration_routes
    
    # Register route modules
    dashboard.register_routes(bp)
    user_management.register_routes(bp)
    system_health.register_routes(bp)
    monitoring.register_routes(bp)
    dashboard_monitoring.register_dashboard_routes(bp)
    cleanup.register_routes(bp)
    admin_api.register_api_routes(bp)
    # Note: security_audit_api registers itself with the app, not blueprint
    websocket_routes.register_websocket_routes(bp)
    admin_job_management.register_routes(bp)
    admin_job_api.register_api_routes(bp)
    
    # Register configuration management routes as a sub-blueprint
    from .configuration_routes import configuration_bp
    bp.register_blueprint(configuration_bp)