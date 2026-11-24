"""
ConnectX Application Entrypoint
===============================
Starts the Flask-SocketIO real-time server with automatic database initialization.
"""

import os
from app import create_app
from app.extensions import db, socketio
from app.models.user import User

# Create application instance using environment configuration
env_name = os.environ.get("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    with app.app_context():
        # Ensure database tables exist
        db.create_all()

        # Seed initial admin user if database is empty
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            print("[ConnectX] Initializing default administrator account...")
            admin = User(
                username="admin",
                email="admin@connectx.local",
                full_name="System Administrator",
                role="admin",
                bio="ConnectX Platform Administrator & Academic Proctor",
                avatar="default_avatar.svg",
                status_message="System Online",
            )
            admin.set_password("Admin@123456")
            db.session.add(admin)
            db.session.commit()
            print("[ConnectX] Default admin created: username='admin', password='Admin@123456'")

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))

    print("\n" + "=" * 60)
    print(" CONNECTX – REAL-TIME MULTI-USER CHAT SYSTEM")
    print(f" Server running at: http://{host}:{port}")
    print(" Admin credentials: admin / Admin@123456")
    print("=" * 60 + "\n")

    socketio.run(
        app,
        host=host,
        port=port,
        debug=(env_name == "development"),
        allow_unsafe_werkzeug=True,
    )
