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
from models import distributor, order_booker, delivery_man, zone, route, shop, route_shop

# Import routers
from routers import auth, distributor as distributor_router, order_booker, delivery_man, zone, route, shop

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["*"],
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
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_detail,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
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
app.include_router(shop.router)


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

