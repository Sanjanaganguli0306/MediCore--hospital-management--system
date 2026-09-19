import os

from app import create_app, db


app = create_app()

with app.app_context():
    db.create_all()
    from app.models import User

    if db.session.scalar(db.select(User).limit(1)) is None:
        bootstrap_password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
        if not bootstrap_password:
            raise RuntimeError("Set BOOTSTRAP_ADMIN_PASSWORD before starting an empty database")
        admin = User(
            full_name="MediCore Administrator",
            username="admin",
            email="admin@medicore.local",
            role="admin",
        )
        admin.set_password(bootstrap_password)
        db.session.add(admin)
        db.session.commit()


if __name__ == "__main__":
    app.run(debug=os.environ.get("APP_ENV", "development") == "development")
