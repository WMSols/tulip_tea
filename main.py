"""
Tulip Tea Backend API
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from config.database import settings, engine, Base

# Import all models to register them with Base
from models import distributor, order_booker, delivery_man

# Import routers
from routers import auth, distributor as distributor_router, order_booker, delivery_man

# Create database tables (in production, use migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(distributor_router.router)
app.include_router(order_booker.router)
app.include_router(delivery_man.router)


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

