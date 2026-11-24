"""
WSGI Entrypoint for Production Deployed Environments (Gunicorn / Railway / Vercel).
"""
import os
from app import create_app
from app.extensions import db
from app.models.user import User

env_name = os.environ.get("FLASK_ENV", "production")
app = create_app(env_name)

# Initialize database schema safely
with app.app_context():
    try:
        db.create_all()
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin = User(
                username="admin",
                email="admin@connectx.local",
                full_name="System Administrator",
                role="admin",
                avatar="default_avatar.svg",
                status_message="System Online",
            )
            admin.set_password(os.environ.get("ADMIN_PASSWORD", "Admin@123456"))
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        print(f"[WSGI Init Notice] {e}")

if __name__ == "__main__":
    from app.extensions import socketio
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host=host, port=port)
