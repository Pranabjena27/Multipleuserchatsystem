"""
ConnectX Application Factory
============================
Initializes extensions, registers modular blueprints, sets up structured logging,
configures error handlers, and manages application contexts.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from flask import Flask, render_template
from app.config import config_by_name, DevelopmentConfig
from app.extensions import db, login_manager, socketio, csrf, migrate


def configure_logging(app: Flask) -> None:
    """Configure structured console and rotating file logging."""
    log_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
    )

    # Console Handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Avoid duplicate handlers in reload cycles
    if not app.logger.handlers:
        app.logger.addHandler(stream_handler)

    # Rotating File Handler in instance/ folder (safe for serverless/read-only systems)
    try:
        instance_path = os.path.join(app.root_path, "..", "instance")
        os.makedirs(instance_path, exist_ok=True)
        log_file_path = os.path.join(instance_path, "connectx.log")

        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
    except (OSError, PermissionError, Exception):
        pass

    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)


def create_app(config_name: str | None = None) -> Flask:
    """
    Application Factory Pattern for ConnectX.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_class = config_by_name.get(config_name, DevelopmentConfig)

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    # Ensure required asset, instance, and upload directories exist
    os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(flask_app.config["AVATAR_FOLDER"], exist_ok=True)
    os.makedirs(flask_app.config["ATTACHMENT_FOLDER"], exist_ok=True)

    # Setup Logging
    configure_logging(flask_app)

    # Initialize extensions
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)
    csrf.init_app(flask_app)

    socketio.init_app(
        flask_app,
        cors_allowed_origins=flask_app.config.get("SOCKETIO_CORS_ALLOWED_ORIGINS", "*"),
        async_mode=flask_app.config.get("SOCKETIO_ASYNC_MODE", "threading"),
    )

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.groups import groups_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.chat import chat_bp
    from app.blueprints.api import api_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.analytics import analytics_bp

    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(groups_bp)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(chat_bp)
    flask_app.register_blueprint(api_bp)
    flask_app.register_blueprint(admin_bp)
    flask_app.register_blueprint(analytics_bp)

    # Explicitly exempt api_bp from CSRF for asynchronous JSON fetch compatibility
    csrf.exempt(api_bp)

    @flask_app.after_request
    def apply_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,OPTIONS"
        return response

    # Register SocketIO Event Handlers
    from app.sockets import events as socket_events  # noqa: F401

    @flask_app.teardown_request
    def teardown_cleanup_request(exception=None):
        """Ensure cached login user in g is cleared between requests/events."""
        from flask import g
        g.pop("_login_user", None)

    # CLI Management Commands
    @flask_app.cli.command("init-db")
    def init_db_command():
        """Initialize all database schema tables."""
        db.create_all()
        print("[ConnectX] Database tables created successfully.")

    @flask_app.cli.command("seed-db")
    def seed_db_command():
        """Seed initial database with verified test data."""
        from seed_data import seed_database
        seed_database()
        print("[ConnectX] Database seeded successfully.")

    # Global Jinja Context Processor
    @flask_app.context_processor
    def inject_global_template_vars():
        return {
            "app_name": flask_app.config.get("APP_NAME", "ConnectX"),
            "course_code": flask_app.config.get("COURSE_CODE", ""),
            "subject": flask_app.config.get("SUBJECT", ""),
            "academic_year": flask_app.config.get("ACADEMIC_YEAR", "2025-2026"),
            "now_year": datetime.now(timezone.utc).year,
        }

    # Error Handlers
    @flask_app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @flask_app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return flask_app
