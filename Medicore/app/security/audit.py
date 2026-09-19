from flask import has_request_context, request
from flask_login import current_user

from app import db
from app.models import AuditEvent


def record_event(action, *, resource_type=None, resource_id=None, success=True, context=None, commit=True):
    """Record minimal security context without copying clinical data into logs."""
    event = AuditEvent(
        user_id=current_user.id if current_user.is_authenticated else None,
        user_role=current_user.role if current_user.is_authenticated else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=request.remote_addr if has_request_context() else None,
        user_agent=(request.user_agent.string[:512] if has_request_context() else None),
        success=success,
        context=context[:500] if context else None,
    )
    db.session.add(event)
    if commit:
        db.session.commit()
    return event
