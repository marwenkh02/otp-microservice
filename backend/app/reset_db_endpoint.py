"""
Database Reset Endpoint
Admin-only endpoints for database management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import User, OTPConfig, OTPEvent, AuditLog, UserSession
from .auth import get_current_admin_user

router = APIRouter()

@router.post("/admin/reset-database")
async def reset_database(
    confirm: bool = Query(False, description="Must be true to confirm reset"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Reset database - drops all tables and recreates them.
    WARNING: This will delete ALL data!
    Admin only endpoint.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to reset database"
        )
    
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
        
        return {
            "message": "Database reset successfully",
            "tables_recreated": tables,
            "table_count": len(tables)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}"
        )

@router.delete("/admin/clear-all-data")
async def clear_all_data(
    confirm: bool = Query(False, description="Must be true to confirm data deletion"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Clear all data from all tables without dropping tables.
    WARNING: This will delete ALL data!
    Admin only endpoint.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to clear all data"
        )
    
    try:
        # Delete all data in reverse order of dependencies
        deleted_counts = {}
        
        deleted_counts['otp_events'] = db.query(OTPEvent).delete()
        deleted_counts['audit_logs'] = db.query(AuditLog).delete()
        deleted_counts['user_sessions'] = db.query(UserSession).delete()
        deleted_counts['otp_configs'] = db.query(OTPConfig).delete()
        deleted_counts['users'] = db.query(User).delete()
        
        db.commit()
        
        return {
            "message": "All data cleared successfully",
            "deleted_counts": deleted_counts
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear data: {str(e)}"
        )

