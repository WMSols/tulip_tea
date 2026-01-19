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

# Import all models to register them with Base
from models import distributor, order_booker, delivery_man, zone, route, shop, route_shop, credit_limit_request, daily_collection, payment, shop_visit, visit_type, order, order_item, activity_log, super_admin, delivery_man_route, warehouse, inventory, delivery_man_warehouse, product, delivery, delivery_item

# Import routers
from routers import auth, distributor as distributor_router, order_booker, delivery_man, zone, route, shop
from routers import credit_limit_request as credit_limit_request_router, daily_collection as daily_collection_router, shop_visit as shop_visit_router, order as order_router, super_admin as super_admin_router, warehouse as warehouse_router, product as product_router, activity_log as activity_log_router, delivery as delivery_router

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
        print(f"🌐 Server ready at http://0.0.0.0:8000")
    except Exception as e:
        print(f"⚠️ Warning: Error during startup: {e}")
        import traceback
        traceback.print_exc()
        print("⚠️ Server will continue, but database operations may fail.")
        # Don't raise - allow server to start even if there are issues

# CORS middleware (allow all origins for development)
# Must be added before other middleware
# Note: allow_origins=["*"] doesn't work with null origin (file://)
# So we need to use a custom function or allow all
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",  # Allow all origins including null/file://
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Custom middleware to ensure CORS headers on all responses (including errors)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CORSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure CORS headers are always present, even on errors."""
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin") or request.headers.get("Origin") or "*"
        cors_headers = {
            "Access-Control-Allow-Origin": origin if origin != "null" else "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Allow-Credentials": "false",
        }
        
        try:
            response = await call_next(request)
            # Add CORS headers to response if not already present
            for key, value in cors_headers.items():
                if key not in response.headers:
                    response.headers[key] = value
            return response
        except Exception as exc:
            # If an exception occurs, create a response with CORS headers
            import traceback
            error_detail = {
                "error": str(exc),
                "type": type(exc).__name__,
            }
            if settings.debug:
                error_detail["traceback"] = traceback.format_exc()
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_detail,
                headers=cors_headers
            )

# Add CORS enforcement middleware AFTER CORS middleware
app.add_middleware(CORSEnforcementMiddleware)


# Import SQLAlchemy exceptions
from sqlalchemy.exc import OperationalError, SQLAlchemyError
try:
    import psycopg2
except ImportError:
    psycopg2 = None

# Global exception handler to ensure CORS headers are always sent
@app.exception_handler(OperationalError)
async def database_error_handler(request: Request, exc: OperationalError):
    """Handle database connection errors with CORS headers."""
    origin = request.headers.get("origin") or request.headers.get("Origin") or "*"
    
    print(f"❌ [DB] Database OperationalError: {str(exc)}")
    
    error_detail = {
        "error": "Database connection error",
        "detail": "Please ensure Supabase local is running. Start it with: supabase start",
        "type": "OperationalError"
    }
    
    if settings.debug:
        error_detail["debug"] = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_detail,
        headers={
            "Access-Control-Allow-Origin": origin if origin != "null" else "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Allow-Credentials": "false",
        }
    )

# Handle psycopg2 errors if available
if psycopg2:
    @app.exception_handler(psycopg2.OperationalError)
    async def psycopg2_error_handler(request: Request, exc: psycopg2.OperationalError):
        """Handle psycopg2 database connection errors with CORS headers."""
        origin = request.headers.get("origin") or request.headers.get("Origin") or "*"
        
        print(f"❌ [DB] psycopg2 OperationalError: {str(exc)}")
        
        error_detail = {
            "error": "Database connection error",
            "detail": "Please ensure Supabase local is running. Start it with: supabase start",
            "type": "psycopg2.OperationalError"
        }
        
        if settings.debug:
            error_detail["debug"] = str(exc)
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_detail,
            headers={
                "Access-Control-Allow-Origin": origin if origin != "null" else "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Allow-Credentials": "false",
            }
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to ensure CORS headers are sent even on errors."""
    # Get origin from request to echo it back (required for null origin)
    origin = request.headers.get("origin") or request.headers.get("Origin") or "*"
    
    # Skip if it's an HTTPException (already handled)
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        # Add CORS headers to existing HTTPException
        if not exc.headers:
            exc.headers = {}
        exc.headers["Access-Control-Allow-Origin"] = origin if origin != "null" else "*"
        exc.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        exc.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        raise exc
    
    if settings.debug:
        error_detail = {
            "error": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    else:
        error_detail = {"error": "Internal server error"}
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_detail,
        headers={
            "Access-Control-Allow-Origin": origin if origin != "null" else "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Allow-Credentials": "false",
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


@app.options("/{full_path:path}")
async def options_handler(full_path: str, request: Request):
    """
    Handle OPTIONS requests for CORS preflight.
    This ensures CORS works even when opening HTML files directly (file://).
    """
    origin = request.headers.get("origin") or request.headers.get("Origin") or "*"
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": origin if origin != "null" else "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Allow-Credentials": "false",
            "Access-Control-Max-Age": "3600",
        }
    )


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

