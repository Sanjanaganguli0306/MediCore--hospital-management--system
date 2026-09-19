from functools import wraps

from flask import abort
from flask_login import current_user, login_required


ROLES = {"admin", "doctor", "nurse", "receptionist", "accountant", "billing_staff", "patient"}

ROLE_PERMISSIONS = {
    "admin": {"users.manage", "roles.manage", "security.view", "patients.read", "patients.write", "clinical.write", "billing.write", "appointments.write", "prescriptions.read", "prescriptions.write"},
    "doctor": {"patients.read", "clinical.write", "appointments.write", "prescriptions.read", "prescriptions.write"},
    "nurse": {"patients.read", "clinical.write", "appointments.read", "prescriptions.read"},
    "receptionist": {"patients.read", "patients.write", "appointments.write"},
    "accountant": {"billing.write"},
    "billing_staff": {"billing.write"},
    "patient": {"self.read"},
}


def has_permission(permission):
    """Return whether the current user has a named permission."""
    return current_user.is_authenticated and permission in ROLE_PERMISSIONS.get(current_user.role, set())


def permission_required(permission):
    """Protect a view with authentication and a centralized permission."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not has_permission(permission):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def can_access_patient(patient):
    """Apply object-level patient access for assigned clinicians."""
    if not current_user.is_authenticated:
        return False
    if current_user.role in {"admin", "receptionist"}:
        return True
    if current_user.role == "doctor":
        return any(appointment.doctor.user_id == current_user.id for appointment in patient.appointments)
    if current_user.role == "nurse":
        return any(appointment.doctor.user_id == current_user.id for appointment in patient.appointments)
    return False
