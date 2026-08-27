"""Audit trail helper.

NFR-B and FR-D5 require a traceable record of who touched sensitive data.
Only identifiers and action names are written; clinical content is never
copied into the audit table (Coding Standard 3.6).
"""

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    summary: str | None = None,
) -> AuditLog:
    """Append an entry to the audit trail.

    Args:
        db: The active database session.
        actor_id: The user performing the action, or ``None`` for system actions.
        action: A short verb such as ``"record.view"`` or ``"certificate.approve"``.
        entity_type: The affected entity, for example ``"medical_record"``.
        entity_id: The affected row identifier when one exists.
        summary: A short non clinical description of the action.

    Returns:
        AuditLog: The pending audit row. The caller commits with the surrounding
        unit of work so that the audit entry and the change share one transaction.
    """
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
    )
    db.add(entry)
    return entry
