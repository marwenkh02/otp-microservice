from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import os
from jose import JWTError, jwt
import pyotp
from typing import List
import time
import secrets
import hashlib
import threading
from collections import defaultdict

from .database import SessionLocal, engine, get_db
from .models import User, Base, OTPConfig, OTPEvent, AuditLog
from .schemas import (
    UserCreate, UserResponse, Token, LoginRequest, 
    MFAEnableRequest, MFAResponse, PasswordChangeRequest,
    OTPConfigCreate, OTPConfigResponse, OTPGenerateRequest,
    OTPGenerateResponse, OTPValidateRequest, OTPValidateResponse,
    OTPStatsResponse
)
from .auth import (
    get_password_hash, authenticate_user, 
    create_access_token, create_refresh_token,
    get_current_user, get_current_admin_user, verify_password,
    verify_totp_code, generate_mfa_secret, generate_mfa_uri,
    create_user_session, ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY, ALGORITHM, get_digest_algorithm
)
from .security import security_manager
from .audit import audit_logger
from .metrics import metrics_collector
from .reset_db_endpoint import router as reset_router

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OTP Generator Microservice", 
    version="2.1.0",
    description="Highly available OTP generator with enhanced security and monitoring"
)

# Enhanced CORS configuration
# Get CORS origins from environment variable or use defaults
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Enhanced in-memory rate limiting storage with cleanup
class RateLimiter:
    def __init__(self):
        self.attempts = defaultdict(list)
        self.lock = threading.Lock()
        self.cleanup_interval = 300  # Clean every 5 minutes
        self.last_cleanup = datetime.utcnow()
    
    def is_rate_limited(self, key: str, max_requests: int = 10, window: int = 60) -> bool:
        """Enhanced rate limiting with automatic cleanup"""
        with self.lock:
            current_time = datetime.utcnow()
            
            # Cleanup old entries periodically
            if (current_time - self.last_cleanup).total_seconds() > self.cleanup_interval:
                self._cleanup_old_entries()
                self.last_cleanup = current_time
            
            # Remove old attempts outside the window
            window_start = current_time - timedelta(seconds=window)
            self.attempts[key] = [t for t in self.attempts[key] if t > window_start]
            
            # Check if rate limited
            if len(self.attempts[key]) >= max_requests:
                return True
            
            # Add current attempt
            self.attempts[key].append(current_time)
            return False
    
    def _cleanup_old_entries(self):
        """Clean up old rate limiting entries"""
        current_time = datetime.utcnow()
        one_hour_ago = current_time - timedelta(hours=1)
        
        keys_to_delete = []
        for key, attempts in self.attempts.items():
            # Remove attempts older than 1 hour
            self.attempts[key] = [t for t in attempts if t > one_hour_ago]
            if not self.attempts[key]:
                keys_to_delete.append(key)
        
        # Remove empty keys
        for key in keys_to_delete:
            del self.attempts[key]

# Global rate limiter instance
rate_limiter = RateLimiter()

# Create database tables
Base.metadata.create_all(bind=engine)

# Include reset database router (admin endpoints)
from .reset_db_endpoint import router as reset_router
app.include_router(reset_router)

@app.get("/")
async def root():
    return {
        "message": "OTP Generator Microservice API v2.1", 
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "features": ["encryption", "audit_logging", "metrics", "rate_limiting"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.1.0"
    }

# Enhanced User Management with Audit Logging
@app.post("/users/", response_model=UserResponse)
def create_user(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Rate limiting for user registration
    if rate_limiter.is_rate_limited(f"registration_{request.client.host}", max_requests=3, window=3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )
    
    hashed = get_password_hash(user_data.password)
    user = User(
        username=user_data.username, 
        email=user_data.email, 
        hashed_password=hashed,
        department=user_data.department,
        job_title=user_data.job_title
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Audit logging
    audit_logger.log_user_creation(
        db=db,
        user_id=user.id,
        username=user.username,
        email=user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    logger.info(f"Created new user: {user.username}")
    return user

@app.get("/users/", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    users = db.query(User).all()
    return users

@app.get("/users/me/", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/token", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: LoginRequest, 
    db: Session = Depends(get_db)
):
    # Enhanced rate limiting
    if rate_limiter.is_rate_limited(f"login_{form_data.username}", max_requests=5, window=300):
        audit_logger.log_login_failure(
            db=db,
            username=form_data.username,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            reason="rate_limit_exceeded"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    try:
        user = authenticate_user(db, form_data.username, form_data.password, request)
        
        # Check if MFA is required
        if user.mfa_enabled:
            if not form_data.mfa_code:
                return {
                    "access_token": "",
                    "refresh_token": "",
                    "mfa_required": True
                }
            
            if not verify_totp_code(user.mfa_secret, form_data.mfa_code):
                audit_logger.log_login_failure(
                    db=db,
                    username=form_data.username,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    reason="invalid_mfa_code"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": user.username})
        
        # Create session
        session_token = create_user_session(
            db, user.id, user, request, access_token_expires
        )
        
        # Audit logging
        audit_logger.log_login_success(
            db=db,
            user=user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        logger.info(f"User logged in: {user.username}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "mfa_required": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.log_login_failure(
            db=db,
            username=form_data.username,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            reason=str(e)
        )
        raise

# Enhanced OTP Configuration with Encryption
@app.post("/otp/configs/", response_model=OTPConfigResponse)
def create_otp_config(
    config_data: OTPConfigCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new OTP configuration with enhanced security"""
    # Rate limiting for config creation
    if rate_limiter.is_rate_limited(f"config_create_{current_user.id}", max_requests=10, window=3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many configuration creations. Please try again later."
        )
    
    # Check for duplicate names
    existing_config = db.query(OTPConfig).filter(
        OTPConfig.user_id == current_user.id,
        OTPConfig.name == config_data.name
    ).first()
    
    if existing_config:
        raise HTTPException(
            status_code=400,
            detail="Configuration with this name already exists"
        )
    
    # Generate secure secret key
    secret_key = pyotp.random_base32()
    
    # Encrypt the secret before storing
    encrypted_secret = security_manager.encrypt_secret(secret_key)
    
    otp_config = OTPConfig(
        user_id=current_user.id,
        name=config_data.name,
        otp_type=config_data.otp_type.value,
        algorithm=config_data.algorithm.value,
        digits=config_data.digits,
        interval=config_data.interval,
        counter=config_data.counter,
        issuer=config_data.issuer,
        secret_key=encrypted_secret,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(otp_config)
    db.commit()
    db.refresh(otp_config)
    
    # Audit logging
    audit_logger.log_config_creation(
        db=db,
        user_id=current_user.id,
        config_id=otp_config.id,
        config_name=config_data.name,
        config_type=config_data.otp_type.value,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    logger.info(f"Created OTP config '{config_data.name}' for user {current_user.username}")
    
    return otp_config

@app.get("/otp/configs/", response_model=list[OTPConfigResponse])
def get_otp_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all OTP configurations for current user"""
    configs = db.query(OTPConfig).filter(OTPConfig.user_id == current_user.id).all()
    return configs

@app.get("/otp/configs/{config_id}", response_model=OTPConfigResponse)
def get_otp_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific OTP configuration"""
    config = db.query(OTPConfig).filter(
        OTPConfig.id == config_id,
        OTPConfig.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="OTP configuration not found")
    
    return config

@app.delete("/otp/configs/{config_id}")
def delete_otp_config(
    config_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete OTP configuration"""
    config = db.query(OTPConfig).filter(
        OTPConfig.id == config_id,
        OTPConfig.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="OTP configuration not found")
    
    config_name = config.name
    db.delete(config)
    db.commit()
    
    # Audit logging
    audit_logger.log_config_deletion(
        db=db,
        user_id=current_user.id,
        config_id=config_id,
        config_name=config_name,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    logger.info(f"Deleted OTP config '{config_name}' for user {current_user.username}")
    
    return {"message": "OTP configuration deleted successfully"}

# Enhanced OTP Generation with Security
@app.post("/otp/generate", response_model=OTPGenerateResponse)
def generate_otp(
    request: Request,
    gen_data: OTPGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate OTP code with enhanced security"""
    # Rate limiting per user
    if rate_limiter.is_rate_limited(f"generate_{current_user.id}", max_requests=30, window=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        logger.info(f"Generating OTP for config_id: {gen_data.config_id}, user: {current_user.username}")
        
        config = db.query(OTPConfig).filter(
            OTPConfig.id == gen_data.config_id,
            OTPConfig.user_id == current_user.id,
            OTPConfig.is_active == True
        ).first()
        
        if not config:
            logger.warning(f"OTP config not found: {gen_data.config_id} for user {current_user.username}")
            raise HTTPException(status_code=404, detail="OTP configuration not found or inactive")
        
        # Decrypt the secret key
        try:
            decrypted_secret = security_manager.decrypt_secret(config.secret_key)
        except Exception as e:
            logger.error(f"Failed to decrypt secret for config {config.id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Security error: failed to decrypt OTP secret")
        
        logger.info(f"Found config: {config.name}, type: {config.otp_type}")
        
        # Generate OTP based on type
        remaining_seconds = None
        next_counter = None
        current_time = datetime.utcnow()
        
        if config.otp_type == 'totp':
            logger.info("Generating TOTP...")
            digest = get_digest_algorithm(config.algorithm)
            
            totp = pyotp.TOTP(
                decrypted_secret,
                digits=config.digits,
                interval=config.interval,
                digest=digest
            )
            otp_code = totp.now()
            
            current_timestamp = time.time()
            remaining_seconds = int(config.interval - (current_timestamp % config.interval))
            
            logger.info(f"Generated TOTP for config {config.name}, remaining: {remaining_seconds}s")
            
        else:  # HOTP
            logger.info("Generating HOTP...")
            digest = get_digest_algorithm(config.algorithm)
            
            hotp = pyotp.HOTP(
                decrypted_secret,
                digits=config.digits,
                digest=digest
            )
            otp_code = hotp.at(config.counter)
            next_counter = config.counter + 1 if gen_data.counter_increment else None
            
            if gen_data.counter_increment:
                config.counter += 1
                config.updated_at = current_time
                db.commit()
                logger.info(f"Generated HOTP for config {config.name}, counter: {config.counter}")
        
        # Log generation event
        event = OTPEvent(
            user_id=current_user.id,
            config_id=config.id,
            event_type='generate',
            otp_code=otp_code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(event)
        db.commit()
        
        # Audit logging
        audit_logger.log_otp_generation(
            db=db,
            user_id=current_user.id,
            config_id=config.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return OTPGenerateResponse(
            otp_code=otp_code,
            config_id=config.id,
            remaining_seconds=remaining_seconds,
            next_counter=next_counter,
            generated_at=current_time
        )
        
    except Exception as e:
        logger.error(f"Error generating OTP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Enhanced OTP Validation with Security
@app.post("/otp/validate", response_model=OTPValidateResponse)
def validate_otp(
    request: Request,
    validate_data: OTPValidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate OTP code with enhanced security"""
    # Rate limiting for validation attempts
    if rate_limiter.is_rate_limited(f"validate_{current_user.id}", max_requests=20, window=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many validation attempts. Please try again later."
        )
    
    try:
        logger.info(f"Validating OTP for config_id: {validate_data.config_id}, code: {validate_data.otp_code}")
        
        config = db.query(OTPConfig).filter(
            OTPConfig.id == validate_data.config_id,
            OTPConfig.user_id == current_user.id,
            OTPConfig.is_active == True
        ).first()
        
        if not config:
            logger.warning(f"OTP config not found for validation: {validate_data.config_id}")
            raise HTTPException(status_code=404, detail="OTP configuration not found or inactive")
        
        # Decrypt the secret key
        try:
            decrypted_secret = security_manager.decrypt_secret(config.secret_key)
        except Exception as e:
            logger.error(f"Failed to decrypt secret for config {config.id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Security error: failed to decrypt OTP secret")
        
        is_valid = False
        message = ""
        current_time = datetime.utcnow()
        
        if config.otp_type == 'totp':
            logger.info("Validating TOTP...")
            digest = get_digest_algorithm(config.algorithm)
            
            totp = pyotp.TOTP(
                decrypted_secret,
                digits=config.digits,
                interval=config.interval,
                digest=digest
            )
            
            is_valid = totp.verify(validate_data.otp_code, valid_window=1)
            message = "TOTP validation successful" if is_valid else "Invalid TOTP code"
            logger.info(f"TOTP validation result: {is_valid}")
            
        else:  # HOTP
            logger.info("Validating HOTP...")
            digest = get_digest_algorithm(config.algorithm)
            
            hotp = pyotp.HOTP(
                decrypted_secret,
                digits=config.digits,
                digest=digest
            )
            
            counter = validate_data.counter if validate_data.counter is not None else config.counter
            is_valid = hotp.verify(validate_data.otp_code, counter)
            message = "HOTP validation successful" if is_valid else "Invalid HOTP code or counter"
            logger.info(f"HOTP validation result: {is_valid}, counter: {counter}")
            
            if is_valid and validate_data.counter is None:
                config.counter += 1
                config.updated_at = current_time
                db.commit()
        
        # Log validation event
        event = OTPEvent(
            user_id=current_user.id,
            config_id=config.id,
            event_type='validate_success' if is_valid else 'validate_failure',
            otp_code=validate_data.otp_code,
            is_success=is_valid,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(event)
        db.commit()
        
        # Audit logging
        audit_logger.log_otp_validation(
            db=db,
            user_id=current_user.id,
            config_id=config.id,
            is_valid=is_valid,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return OTPValidateResponse(
            is_valid=is_valid,
            config_id=config.id,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error validating OTP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# NEW: Enhanced System Metrics Endpoints
@app.get("/system/metrics")
def get_system_metrics(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive system metrics (admin only)"""
    return metrics_collector.get_system_metrics(db)

@app.get("/user/metrics")
def get_user_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user-specific metrics"""
    return metrics_collector.get_user_metrics(db, current_user.id)

# NEW: Audit Logs Endpoints
@app.get("/audit/logs")
def get_audit_logs(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get audit logs (admin only)"""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat(),
            "status": log.status,
            "details": log.details
        }
        for log in logs
    ]

@app.get("/audit/timeline")
def get_audit_timeline(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    hours: int = 24
):
    """Get audit timeline (admin only)"""
    return metrics_collector.get_audit_timeline(db, hours)

# New endpoint: Bulk OTP operations
@app.post("/otp/bulk/generate")
def bulk_generate_otp(
    config_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate OTPs for multiple configurations at once"""
    results = []
    
    for config_id in config_ids:
        try:
            # Use existing generate logic
            gen_request = OTPGenerateRequest(
                config_id=config_id,
                counter_increment=False
            )
            
            # Create a mock request for the internal call
            class MockRequest:
                client = None
                headers = {}
            
            otp_result = generate_otp(MockRequest(), gen_request, current_user, db)
            results.append({
                "config_id": config_id,
                "success": True,
                "otp_code": otp_result.otp_code,
                "remaining_seconds": otp_result.remaining_seconds
            })
            
        except Exception as e:
            results.append({
                "config_id": config_id,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}

# Enhanced stats endpoint
@app.get("/otp/stats", response_model=OTPStatsResponse)
def get_otp_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get OTP usage statistics"""
    total_configs = db.query(OTPConfig).filter(OTPConfig.user_id == current_user.id).count()
    active_configs = db.query(OTPConfig).filter(
        OTPConfig.user_id == current_user.id,
        OTPConfig.is_active == True
    ).count()
    
    total_generations = db.query(OTPEvent).filter(
        OTPEvent.user_id == current_user.id,
        OTPEvent.event_type == 'generate'
    ).count()
    
    total_validations = db.query(OTPEvent).filter(
        OTPEvent.user_id == current_user.id,
        OTPEvent.event_type.in_(['validate_success', 'validate_failure'])
    ).count()
    
    successful_validations = db.query(OTPEvent).filter(
        OTPEvent.user_id == current_user.id,
        OTPEvent.event_type == 'validate_success'
    ).count()
    
    return OTPStatsResponse(
        total_configs=total_configs,
        active_configs=active_configs,
        total_generations=total_generations,
        total_validations=total_validations,
        successful_validations=successful_validations
    )

# Enhanced stats endpoint with time-based analytics
@app.get("/otp/stats/enhanced", response_model=dict)
def get_enhanced_otp_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enhanced OTP usage statistics with time-based analytics"""
    # Basic stats
    basic_stats = get_otp_stats(current_user, db)
    
    # Time-based analytics (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    recent_generations = db.query(OTPEvent).filter(
        OTPEvent.user_id == current_user.id,
        OTPEvent.event_type == 'generate',
        OTPEvent.timestamp >= seven_days_ago
    ).count()
    
    recent_validations = db.query(OTPEvent).filter(
        OTPEvent.user_id == current_user.id,
        OTPEvent.event_type.in_(['validate_success', 'validate_failure']),
        OTPEvent.timestamp >= seven_days_ago
    ).count()
    
    successful_recent_validations = db.query(OTPEvent).filter(
        OTPEvent.user_id == current_user.id,
        OTPEvent.event_type == 'validate_success',
        OTPEvent.timestamp >= seven_days_ago
    ).count()
    
    return {
        **basic_stats.dict(),
        "recent_generations": recent_generations,
        "recent_validations": recent_validations,
        "recent_success_rate": (
            successful_recent_validations / recent_validations * 100 
            if recent_validations > 0 else 0
        ),
        "analysis_period": "7 days"
    }

# Recent OTP Events Endpoint
@app.get("/otp/events/recent", response_model=List[dict])
def get_recent_otp_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100)
):
    """Get recent OTP events for the current user"""
    events = db.query(OTPEvent).filter(
        OTPEvent.user_id == current_user.id
    ).order_by(OTPEvent.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "otp_code": event.otp_code,
            "timestamp": event.timestamp,
            "is_success": event.is_success,
            "config": {
                "name": event.config.name
            }
        }
        for event in events
    ]

# Enhanced MFA Endpoints with Audit Logging
@app.post("/users/me/mfa/enable", response_model=MFAResponse)
def enable_mfa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled"
        )
    
    # Generate new MFA secret
    mfa_secret = generate_mfa_secret()
    current_user.mfa_secret = mfa_secret
    db.commit()
    
    # Generate MFA URI for QR code
    mfa_uri = generate_mfa_uri(current_user.username, mfa_secret)
    
    logger.info(f"MFA setup initiated for user: {current_user.username}")
    
    return {"mfa_uri": mfa_uri, "mfa_secret": mfa_secret}

@app.post("/users/me/mfa/verify")
def verify_mfa(
    mfa_data: MFAEnableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA secret not generated"
        )
    
    if verify_totp_code(current_user.mfa_secret, mfa_data.mfa_code):
        current_user.mfa_enabled = True
        db.commit()
        
        # Audit logging
        audit_logger.log_mfa_enabled(
            db=db,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        logger.info(f"MFA enabled for user: {current_user.username}")
        
        return {"message": "MFA enabled successfully"}
    else:
        logger.warning(f"Failed MFA verification for user: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )

@app.post("/users/me/mfa/disable")
def disable_mfa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled"
        )
    
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()
    
    # Audit logging
    audit_logger.log_mfa_disabled(
        db=db,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    logger.info(f"MFA disabled for user: {current_user.username}")
    
    return {"message": "MFA disabled successfully"}

@app.post("/users/me/change-password")
def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Set new password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.must_change_password = False
    db.commit()
    
    # Audit logging
    audit_logger.log_password_change(
        db=db,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    logger.info(f"Password changed for user: {current_user.username}")
    
    return {"message": "Password changed successfully"}