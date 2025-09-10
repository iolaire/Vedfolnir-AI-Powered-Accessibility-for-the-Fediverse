# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Routes Registration"""

from . import admin_bp

# Register all admin routes with the blueprint
def register_all_routes():
    """Register all admin routes"""
    from . import dashboard
    from . import user_management
    from . import system_health
    from . import monitoring
    # from . import dashboard_monitoring  # Temporarily disabled due to import issues
    from . import cleanup
    from . import admin_api
    from . import security_audit_api
    from . import websocket_routes
    from . import admin_job_management
    from . import admin_job_api
    from . import configuration_routes
    from . import maintenance_mode
    from . import storage_management
    from . import responsiveness_api
    
    # Register route modules
    dashboard.register_routes(admin_bp)
    user_management.register_routes(admin_bp)
    system_health.register_routes(admin_bp)
    monitoring.register_routes(admin_bp)
    # dashboard_monitoring.register_dashboard_routes(admin_bp)  # Temporarily disabled
    cleanup.register_routes(admin_bp)
    admin_api.register_api_routes(admin_bp)
    # Note: security_audit_api registers itself with the app, not blueprint
    websocket_routes.register_websocket_routes(admin_bp)
    admin_job_management.register_routes(admin_bp)
    admin_job_api.register_api_routes(admin_bp)
    maintenance_mode.register_routes(admin_bp)
    storage_management.register_routes(admin_bp)
    responsiveness_api.register_routes(admin_bp)
    
    # Register configuration management routes as a sub-blueprint
    from .configuration_routes import configuration_bp
    admin_bp.register_blueprint(configuration_bp)
    
    # Register maintenance status routes as a sub-blueprint
    from .maintenance_status_routes import maintenance_status_bp
    admin_bp.register_blueprint(maintenance_status_bp)

# Auto-register routes when module is imported
try:
    register_all_routes()
    print("✅ Admin routes registered successfully")
except Exception as e:
    print(f"⚠️  Admin routes registration failed: {e}")
    # Continue without admin routes for now