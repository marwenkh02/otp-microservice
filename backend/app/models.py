from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # MFA and security fields
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    department = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    access_level = Column(Integer, default=0)
    session_timeout = Column(Integer, default=30)
    must_change_password = Column(Boolean, default=True)
    
    # Relationships
    otp_configs = relationship("OTPConfig", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    otp_events = relationship("OTPEvent", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    ip_address = Column(String)
    user_agent = Column(String)
    is_revoked = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="sessions")

class OTPConfig(Base):
    __tablename__ = "otp_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    otp_type = Column(String, nullable=False)  # 'totp' or 'hotp'
    algorithm = Column(String, default='sha1')  # 'sha1', 'sha256', 'sha512'
    digits = Column(Integer, default=6)
    interval = Column(Integer, default=30)  # For TOTP
    counter = Column(BigInteger, default=0)  # For HOTP
    issuer = Column(String, nullable=False)
    secret_key = Column(String, nullable=False)  # This will now store encrypted secrets
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="otp_configs")
    events = relationship("OTPEvent", back_populates="config", cascade="all, delete-orphan")

class OTPEvent(Base):
    __tablename__ = "otp_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    config_id = Column(Integer, ForeignKey("otp_configs.id"))
    event_type = Column(String, nullable=False)  # 'generate', 'validate_success', 'validate_failure'
    otp_code = Column(String, nullable=True)
    is_success = Column(Boolean, default=True)
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="otp_events")
    config = relationship("OTPConfig", back_populates="events")

# NEW: Audit Logging Table
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)  # 'login', 'otp_generate', 'config_create', 'user_create'
    resource = Column(String, nullable=False)  # 'user', 'otp_config', 'system'
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)  # 'success', 'failure'
    details = Column(JSON)  # Additional context as JSON
    
    user = relationship("User", back_populates="audit_logs")