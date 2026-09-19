from sqlalchemy import inspect, text

from app import db


def ensure_security_schema():
    """Apply the small security schema delta for the existing SQLite deployment."""
    db.create_all()
    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("user")}
    additions = {
        "failed_login_count": "INTEGER NOT NULL DEFAULT 0",
        "locked_until": "DATETIME",
        "last_login_at": "DATETIME",
    }
    for name, definition in additions.items():
        if name not in columns:
            db.session.execute(text(f"ALTER TABLE user ADD COLUMN {name} {definition}"))
    db.session.commit()
