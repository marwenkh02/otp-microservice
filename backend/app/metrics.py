from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from .models import User, OTPConfig, OTPEvent, AuditLog

class MetricsCollector:
    @staticmethod
    def get_system_metrics(db: Session):
        """Get comprehensive system metrics"""
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_configs = db.query(OTPConfig).count()
        active_configs = db.query(OTPConfig).filter(OTPConfig.is_active == True).count()
        
        # OTP usage metrics
        total_generations = db.query(OTPEvent).filter(OTPEvent.event_type == 'generate').count()
        total_validations = db.query(OTPEvent).filter(
            OTPEvent.event_type.in_(['validate_success', 'validate_failure'])
        ).count()
        successful_validations = db.query(OTPEvent).filter(
            OTPEvent.event_type == 'validate_success'
        ).count()
        
        # Recent activity (last 24 hours)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        recent_logins = db.query(AuditLog).filter(
            AuditLog.action == 'login',
            AuditLog.status == 'success',
            AuditLog.timestamp >= twenty_four_hours_ago
        ).count()
        
        recent_otp_generations = db.query(OTPEvent).filter(
            OTPEvent.event_type == 'generate',
            OTPEvent.timestamp >= twenty_four_hours_ago
        ).count()
        
        # User activity metrics
        active_today = db.query(AuditLog).filter(
            AuditLog.timestamp >= twenty_four_hours_ago
        ).distinct(AuditLog.user_id).count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "active_today": active_today
            },
            "configurations": {
                "total": total_configs,
                "active": active_configs,
                "by_type": {
                    "totp": db.query(OTPConfig).filter(OTPConfig.otp_type == 'totp').count(),
                    "hotp": db.query(OTPConfig).filter(OTPConfig.otp_type == 'hotp').count()
                }
            },
            "otp_usage": {
                "total_generations": total_generations,
                "total_validations": total_validations,
                "successful_validations": successful_validations,
                "success_rate": round((successful_validations / total_validations * 100), 2) if total_validations > 0 else 0
            },
            "recent_activity_24h": {
                "logins": recent_logins,
                "otp_generations": recent_otp_generations
            },
            "security": {
                "mfa_enabled_users": db.query(User).filter(User.mfa_enabled == True).count(),
                "locked_accounts": db.query(User).filter(User.account_locked_until.isnot(None)).count()
            }
        }
    
    @staticmethod
    def get_user_metrics(db: Session, user_id: int):
        """Get metrics for specific user"""
        user_configs = db.query(OTPConfig).filter(OTPConfig.user_id == user_id).count()
        active_configs = db.query(OTPConfig).filter(
            OTPConfig.user_id == user_id,
            OTPConfig.is_active == True
        ).count()
        
        # User's OTP events
        user_generations = db.query(OTPEvent).filter(
            OTPEvent.user_id == user_id,
            OTPEvent.event_type == 'generate'
        ).count()
        
        user_validations = db.query(OTPEvent).filter(
            OTPEvent.user_id == user_id,
            OTPEvent.event_type.in_(['validate_success', 'validate_failure'])
        ).count()
        
        successful_user_validations = db.query(OTPEvent).filter(
            OTPEvent.user_id == user_id,
            OTPEvent.event_type == 'validate_success'
        ).count()
        
        # Recent activity (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_generations = db.query(OTPEvent).filter(
            OTPEvent.user_id == user_id,
            OTPEvent.event_type == 'generate',
            OTPEvent.timestamp >= seven_days_ago
        ).count()
        
        recent_validations = db.query(OTPEvent).filter(
            OTPEvent.user_id == user_id,
            OTPEvent.event_type.in_(['validate_success', 'validate_failure']),
            OTPEvent.timestamp >= seven_days_ago
        ).count()
        
        return {
            "configurations": {
                "total": user_configs,
                "active": active_configs
            },
            "otp_usage": {
                "total_generations": user_generations,
                "total_validations": user_validations,
                "successful_validations": successful_user_validations,
                "success_rate": round((successful_user_validations / user_validations * 100), 2) if user_validations > 0 else 0
            },
            "recent_activity_7d": {
                "generations": recent_generations,
                "validations": recent_validations
            }
        }
    
    @staticmethod
    def get_audit_timeline(db: Session, hours: int = 24):
        """Get audit events timeline for the last N hours"""
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        events = db.query(AuditLog).filter(
            AuditLog.timestamp >= time_threshold
        ).order_by(AuditLog.timestamp.desc()).all()
        
        return [
            {
                "id": event.id,
                "user_id": event.user_id,
                "action": event.action,
                "resource": event.resource,
                "timestamp": event.timestamp.isoformat(),
                "status": event.status,
                "ip_address": event.ip_address,
                "details": event.details
            }
            for event in events
        ]

# Global metrics collector instance
metrics_collector = MetricsCollector()