"""
Flask Extensions Module
=======================
Initializes shared extension instances to prevent circular dependencies.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
csrf = CSRFProtect()
migrate = Migrate()

# Configure login manager redirect
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access ConnectX."
login_manager.login_message_category = "info"
