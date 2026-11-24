"""
Routes Package Initialization
=============================
Exposes all modular Flask blueprints for authentication, chat, groups, REST API,
administration, analytics, and health status.
"""

from app.routes.main import main_bp
from app.routes.groups import groups_bp
from app.blueprints.auth.routes import auth_bp
from app.blueprints.chat.routes import chat_bp
from app.blueprints.api.routes import api_bp
from app.blueprints.admin.routes import admin_bp
from app.blueprints.analytics.routes import analytics_bp

__all__ = [
    "main_bp",
    "groups_bp",
    "auth_bp",
    "chat_bp",
    "api_bp",
    "admin_bp",
    "analytics_bp",
]
