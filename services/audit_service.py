import logging
from typing import Dict, Any, List, Optional
from database.repository import repo

logger = logging.getLogger("smart_grocery.audit")

class AuditService:
    @staticmethod
    def record_event(
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Records a compliance and workflow audit event in the database.
        """
        logger.info(f"[AUDIT] {event_type} on {entity_type} {entity_id} by {actor}: {details}")
        repo.log_audit(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details
        )

    @staticmethod
    def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
        return repo.get_audit_logs(limit=limit)

audit_service = AuditService()
