import os

from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import Config


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    """Load a staff account for Flask-Login sessions."""
    from app.models import User

    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    """Create and configure the MediCore Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    if not app.config.get("SECRET_KEY"):
        if app.config.get("APP_ENV") == "production":
            raise RuntimeError("SECRET_KEY must be configured in production")
        app.config["SECRET_KEY"] = os.urandom(32)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."

    @app.after_request
    def apply_security_headers(response):
        """Apply baseline browser protections to every response."""
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; "
            "script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        if request.is_secure and app.config.get("APP_ENV") == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    from app import models  # noqa: F401
    from app.security.schema import ensure_security_schema
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.patients import patients_bp
    from app.routes.doctors import doctors_bp
    from app.routes.appointments import appointments_bp, appointment_api_bp
    from app.routes.billing import billing_bp
    from app.routes.prescriptions import prescriptions_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(doctors_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(appointment_api_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(prescriptions_bp)

    with app.app_context():
        ensure_security_schema()

    @app.context_processor
    def inject_branding():
        """Expose shared branding values to every template."""
        return {"APP_NAME": app.config["APP_NAME"]}

    @app.errorhandler(403)
    def forbidden(error):
        """Render the branded forbidden page."""
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def request_too_large(error):
        """Return a safe response for oversized requests."""
        if request.accept_mimetypes.best == "application/json":
            return jsonify(success=False, message="Request could not be processed."), 413
        return render_template("errors/500.html"), 413

    @app.errorhandler(404)
    def not_found(error):
        """Render the branded not-found page."""
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        """Render the branded server-error page."""
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
