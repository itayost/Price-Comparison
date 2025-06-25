# price_comparison_server/routes/system_routes.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
import psutil
import platform
from typing import Dict, Any

from database.connection import get_db, engine
from database.new_models import Chain, Branch, ChainProduct, BranchPrice, User, SavedCart

router = APIRouter(prefix="/api/system", tags=["system"])


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health/detailed")
def detailed_health_check(db: Session = Depends(get_db_session)):
    """Detailed system health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Database health
    try:
        # Test database connection
        db.execute(text("SELECT 1 FROM dual"))
        db_healthy = True
        
        # Get table counts
        table_counts = {
            "chains": db.query(Chain).count(),
            "branches": db.query(Branch).count(),
            "products": db.query(ChainProduct).count(),
            "prices": db.query(BranchPrice).count(),
            "users": db.query(User).count(),
            "saved_carts": db.query(SavedCart).count()
        }
        
        health_status["components"]["database"] = {
            "status": "healthy",
            "tables": table_counts
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # System resources
    health_status["components"]["system"] = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "percent": psutil.virtual_memory().percent,
            "available": f"{psutil.virtual_memory().available / (1024**3):.2f} GB"
        },
        "disk": {
            "percent": psutil.disk_usage('/').percent,
            "free": f"{psutil.disk_usage('/').free / (1024**3):.2f} GB"
        },
        "python_version": platform.python_version(),
        "platform": platform.platform()
    }
    
    return health_status


@router.get("/statistics")
def get_system_statistics(db: Session = Depends(get_db_session)):
    """Get system statistics and metrics"""
    
    stats = {}
    
    # Price statistics
    price_stats = db.query(
        func.count(BranchPrice.price_id).label('total_prices'),
        func.avg(BranchPrice.price).label('avg_price'),
        func.min(BranchPrice.price).label('min_price'),
        func.max(BranchPrice.price).label('max_price')
    ).first()
    
    stats["prices"] = {
        "total": price_stats.total_prices,
        "average": float(price_stats.avg_price) if price_stats.avg_price else 0,
        "min": float(price_stats.min_price) if price_stats.min_price else 0,
        "max": float(price_stats.max_price) if price_stats.max_price else 0
    }
    
    # Product distribution by chain
    chain_products = db.query(
        Chain.display_name,
        func.count(ChainProduct.chain_product_id).label('product_count')
    ).join(
        ChainProduct
    ).group_by(
        Chain.display_name
    ).all()
    
    stats["products_by_chain"] = {
        chain: count for chain, count in chain_products
    }
    
    # Branch distribution by city
    top_cities = db.query(
        Branch.city,
        func.count(Branch.branch_id).label('branch_count')
    ).group_by(
        Branch.city
    ).order_by(
        func.count(Branch.branch_id).desc()
    ).limit(10).all()
    
    stats["top_cities"] = [
        {"city": city, "branches": count}
        for city, count in top_cities
    ]
    
    # User activity
    recent_users = db.query(
        func.count(User.user_id).label('total_users')
    ).scalar()
    
    active_carts = db.query(
        func.count(SavedCart.cart_id).label('total_carts')
    ).scalar()
    
    stats["user_activity"] = {
        "total_users": recent_users,
        "total_saved_carts": active_carts,
        "avg_carts_per_user": active_carts / recent_users if recent_users > 0 else 0
    }
    
    # Most compared products (by saved carts)
    # This is a simplified version - in production you'd track actual comparisons
    
    return stats


@router.get("/database/info")
def get_database_info(db: Session = Depends(get_db_session)):
    """Get database connection information"""
    
    try:
        # Get Oracle version
        result = db.execute(text("SELECT * FROM v$version WHERE banner LIKE 'Oracle%'"))
        oracle_version = result.fetchone()
        
        # Get database size (simplified)
        size_result = db.execute(text("""
            SELECT 
                SUM(bytes)/1024/1024 as size_mb 
            FROM user_segments
        """))
        db_size = size_result.fetchone()
        
        return {
            "database_type": "Oracle Autonomous Database",
            "version": oracle_version[0] if oracle_version else "Unknown",
            "size_mb": float(db_size[0]) if db_size and db_size[0] else 0,
            "connection_pool": {
                "active": engine.pool.size() if hasattr(engine.pool, 'size') else "N/A",
                "overflow": engine.pool.overflow() if hasattr(engine.pool, 'overflow') else "N/A"
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "database_type": "Oracle",
            "status": "Error retrieving details"
        }


@router.get("/recent-updates")
def get_recent_updates(hours: int = 24, db: Session = Depends(get_db_session)):
    """Get recent price updates"""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    recent_updates = db.query(
        func.count(BranchPrice.price_id).label('count')
    ).filter(
        BranchPrice.last_updated >= cutoff_time
    ).scalar()
    
    # Get sample of recent updates
    recent_samples = db.query(
        ChainProduct.name,
        ChainProduct.barcode,
        BranchPrice.price,
        BranchPrice.last_updated,
        Branch.name.label('branch_name')
    ).join(
        ChainProduct
    ).join(
        Branch
    ).filter(
        BranchPrice.last_updated >= cutoff_time
    ).order_by(
        BranchPrice.last_updated.desc()
    ).limit(10).all()
    
    return {
        "hours_checked": hours,
        "total_updates": recent_updates,
        "recent_samples": [
            {
                "product": sample.name,
                "barcode": sample.barcode,
                "price": float(sample.price),
                "branch": sample.branch_name,
                "updated": sample.last_updated.isoformat()
            }
            for sample in recent_samples
        ]
    }
