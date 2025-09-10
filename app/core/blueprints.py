def register_blueprints(app):
    """Register all application blueprints"""
    
    # Register main blueprint (dashboard)
    from app.blueprints.main import main_bp
    app.register_blueprint(main_bp)
    
    # Register auth blueprint
    from app.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # Register GDPR blueprint
    from app.blueprints.gdpr import gdpr_bp
    app.register_blueprint(gdpr_bp)
    
    # Register platform management blueprint
    from app.blueprints.platform import platform_bp
    app.register_blueprint(platform_bp)
    
    # Register caption generation blueprint
    from app.blueprints.caption import caption_bp
    app.register_blueprint(caption_bp)
    
    # Register review blueprint
    from app.blueprints.review import review_bp
    app.register_blueprint(review_bp)
    
    # Register API blueprint
    from app.blueprints.api import api_bp
    app.register_blueprint(api_bp)
    
    # Register static/utility blueprint
    from app.blueprints.static import static_bp
    app.register_blueprint(static_bp)

    # Register admin blueprint
    from app.blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)