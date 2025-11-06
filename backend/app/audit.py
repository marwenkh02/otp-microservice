from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any
from .models import AuditLog, User
import json

class AuditLogger:
    @staticmethod
    def log_event(
        db: Session,
        user_id: int,
        action: str,
        resource: str,
        status: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an audit event"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
                status=status,
                details=details
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            print(f"Audit logging error: {e}")
            db.rollback()

    @staticmethod
    def log_login_success(db: Session, user: User, ip_address: str, user_agent: str):
        """Log successful login"""
        AuditLogger.log_event(
            db=db,
            user_id=user.id,
            action="login",
            resource="user",
            status="success",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"username": user.username}
        )

    @staticmethod
    def log_login_failure(db: Session, username: str, ip_address: str, user_agent: str, reason: str):
        """Log failed login attempt"""
        # For failed logins, we might not have a user_id
        AuditLogger.log_event(
            db=db,
            user_id=None,  # No user ID for failed logins
            action="login",
            resource="user",
            status="failure",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"username": username, "reason": reason}
        )

    @staticmethod
    def log_otp_generation(db: Session, user_id: int, config_id: int, ip_address: str, user_agent: str):
        """Log OTP generation"""
        AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action="otp_generate",
            resource="otp_config",
            status="success",
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=config_id
        )

    @staticmethod
    def log_otp_validation(db: Session, user_id: int, config_id: int, is_valid: bool, ip_address: str, user_agent: str):
        """Log OTP validation"""
        AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action="otp_validate",
            resource="otp_config",
            status="success" if is_valid else "failure",
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=config_id,
            details={"validation_result": "valid" if is_valid else "invalid"}
        )

# Global audit logger instance
audit_logger = AuditLogger()