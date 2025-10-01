from .routes import main_bp
from .health_routes import health_bp

# Register health routes with main blueprint
main_bp.register_blueprint(health_bp)

__all__ = ['main_bp']
