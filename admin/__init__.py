# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Module

Centralized administration functionality for Vedfolnir including user management,
system health monitoring, data cleanup, and administrative oversight.
"""

from flask import Blueprint

def create_admin_blueprint(app):
    """Create and configure the admin blueprint"""
    import os
    admin_bp = Blueprint('admin', __name__, 
                        url_prefix='/admin',
                        template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    
    # Import and register route modules
    from .routes import dashboard, user_management, system_health, cleanup, monitoring
    
    dashboard.register_routes(admin_bp)
    user_management.register_routes(admin_bp)
    system_health.register_routes(admin_bp)
    cleanup.register_routes(admin_bp)
    monitoring.register_routes(admin_bp)
    
    return admin_bp