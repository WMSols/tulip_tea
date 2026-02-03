"""
Tulip Tea Backend API
Main FastAPI application entry point.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from config.database import settings, engine, Base
import traceback
import os

# Import all models to register them with Base
from models import distributor, order_booker, delivery_man, zone, route, shop, credit_limit_request, daily_collection, payment, shop_visit, visit_type, order, order_item, activity_log, super_admin, warehouse, inventory, delivery_man_warehouse, product, delivery, delivery_item, subsidy, wallet, wallet_transaction

# Import routers
from routers import auth, distributor as distributor_router, order_booker, delivery_man, zone, route, shop
from routers import credit_limit_request as credit_limit_request_router, daily_collection as daily_collection_router, shop_visit as shop_visit_router, order as order_router, super_admin as super_admin_router, warehouse as warehouse_router, product as product_router, activity_log as activity_log_router, delivery as delivery_router, subsidy as subsidy_router, wallet as wallet_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup (in production, use migrations)."""
    try:
        print("🚀 Starting Tulip Tea Backend API...")
        print("📊 Creating database tables...")
        # Test connection first
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified successfully!")
        port = os.environ.get("PORT", "8000")
        print(f"🌐 Server ready at http://0.0.0.0:{port}")
    except Exception as e:
        print(f"⚠️ Warning: Error during startup: {e}")
        import traceback
        traceback.print_exc()
        print("⚠️ Server will continue, but database operations may fail.")
        print("💡 Tip: Run 'python scripts/test_db_connection.py' for detailed diagnostics.")
        # Don't raise - allow server to start even if there are issues

# CORS middleware - configured for production with environment variable
# Must be added before other middleware
frontend_url = os.environ.get("FRONTEND_URL", "")
# If FRONTEND_URL is set, use it; otherwise allow all (for development)
if frontend_url:
    allowed_origins = [frontend_url]
    allow_credentials = True
else:
    # Development mode - allow all origins
    allowed_origins = ["*"]
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Global exception handler to ensure CORS headers are always sent
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to ensure CORS headers are sent even on errors."""
    if settings.debug:
        error_detail = {
            "error": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    else:
        error_detail = {"error": "Internal server error"}
    
    # Get CORS origin from environment or use wildcard
    cors_origin = os.environ.get("FRONTEND_URL", "*")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_detail,
        headers={
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Include routers
app.include_router(auth.router)
app.include_router(distributor_router.router)
app.include_router(order_booker.router)
app.include_router(delivery_man.router)
app.include_router(zone.router)
app.include_router(route.router)
app.include_router(warehouse_router.router)
app.include_router(product_router.router)
app.include_router(shop.router)
app.include_router(credit_limit_request_router.router)
app.include_router(daily_collection_router.router)
app.include_router(shop_visit_router.router)
app.include_router(order_router.router)
app.include_router(super_admin_router.router)
app.include_router(activity_log_router.router)
app.include_router(delivery_router.router)
app.include_router(subsidy_router.router)
app.include_router(wallet_router.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Tulip Tea Backend API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/test")
async def test():
    """Simple test endpoint without database."""
    return {
        "message": "API is responding",
        "status": "ok"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies database connectivity.
    """
    try:
        # Test database connection (SQLAlchemy 2.0 syntax)
        with engine.begin() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return {
            "status": "healthy",
            "database": "connected",
            "version": settings.app_version
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/config/supabase")
async def get_supabase_config():
    """
    Get Supabase configuration for frontend.
    Returns public credentials (URL and ANON_KEY) that are safe to expose.
    """
    return {
        "supabase_url": settings.supabase_url or "",
        "supabase_anon_key": settings.supabase_anon_key or ""
    }


if __name__ == "__main__":
    import uvicorn
    # Use PORT from environment (Render provides this), default to 8000 for local dev
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

