from datetime import date, datetime
from functools import wraps

from flask import abort
from flask_login import current_user

from app.security.permissions import ROLE_PERMISSIONS


def role_required(*roles):
    """Require an authenticated user with one of the given roles."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles or current_user.role not in ROLE_PERMISSIONS:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def next_code(prefix, model, field_name):
    """Generate the next zero-padded identifier for a model field."""
    highest = 0
    for record in model.query.all():
        value = getattr(record, field_name, "") or ""
        try:
            highest = max(highest, int(value.rsplit("-", 1)[-1]))
        except (TypeError, ValueError):
            continue
    return f"{prefix}-{highest + 1:04d}"


def today():
    """Return today's local date."""
    return date.today()


def parse_date(value):
    """Parse an ISO date string or return None."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def money(value):
    """Format a numeric value as Indian rupees."""
    return f"₹{value:,.2f}"
