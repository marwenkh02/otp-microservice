from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class OTPType(str, Enum):
    TOTP = "totp"
    HOTP = "hotp"

class OTPAlgorithm(str, Enum):
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=12)
    department: Optional[str] = None
    job_title: Optional[str] = None

    @validator('password')
    def validate_password_complexity(cls, v):
        errors = []
        if len(v) < 12:
            errors.append("Password must be at least 12 characters long")
        if not any(c.isupper() for c in v):
            errors.append("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("Password must contain at least one digit")
        special_chars = "!@#$%^&*(),.?:{}|<>"
        if not any(c in special_chars for c in v):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValueError("; ".join(errors))
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    mfa_enabled: bool
    last_login: Optional[datetime]
    department: Optional[str]
    job_title: Optional[str]
    access_level: int
    must_change_password: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    mfa_required: bool = False

class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None

class MFAEnableRequest(BaseModel):
    mfa_code: str

class MFAResponse(BaseModel):
    mfa_uri: str
    mfa_secret: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)

    @validator('new_password')
    def validate_password_complexity(cls, v):
        errors = []
        if len(v) < 12:
            errors.append("Password must be at least 12 characters long")
        if not any(c.isupper() for c in v):
            errors.append("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("Password must contain at least one digit")
        special_chars = "!@#$%^&*(),.?:{}|<>"
        if not any(c in special_chars for c in v):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValueError("; ".join(errors))
        return v

class OTPConfigCreate(BaseModel):
    name: str = Field(..., description="Name for this OTP configuration")
    otp_type: OTPType = Field(..., description="TOTP or HOTP")
    algorithm: OTPAlgorithm = Field(default=OTPAlgorithm.SHA1)
    digits: int = Field(default=6, ge=6, le=8)
    interval: int = Field(default=30, ge=10, le=300, description="Time interval in seconds for TOTP")
    counter: int = Field(default=0, ge=0, description="Initial counter for HOTP")
    issuer: str = Field(..., description="Issuer name (e.g., your company)")

class OTPConfigResponse(BaseModel):
    id: int
    user_id: int
    name: str
    otp_type: OTPType
    algorithm: OTPAlgorithm
    digits: int
    interval: int
    counter: int
    issuer: str
    secret_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OTPGenerateRequest(BaseModel):
    config_id: int
    counter_increment: bool = Field(default=False, description="Increment HOTP counter after generation")

class OTPGenerateResponse(BaseModel):
    otp_code: str
    config_id: int
    remaining_seconds: Optional[int] = None
    next_counter: Optional[int] = None
    generated_at: datetime

    class Config:
        from_attributes = True

class OTPValidateRequest(BaseModel):
    config_id: int
    otp_code: str
    counter: Optional[int] = None

class OTPValidateResponse(BaseModel):
    is_valid: bool
    config_id: int
    message: str

class OTPStatsResponse(BaseModel):
    total_configs: int
    active_configs: int
    total_generations: int
    total_validations: int
    successful_validations: int

# NEW: Audit Log Response
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource: str
    resource_id: Optional[int]
    ip_address: Optional[str]
    timestamp: datetime
    status: str
    details: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

# NEW: System Metrics Response
class SystemMetricsResponse(BaseModel):
    users: Dict[str, int]
    configurations: Dict[str, Any]
    otp_usage: Dict[str, Any]
    recent_activity_24h: Dict[str, int]
    security: Dict[str, int]