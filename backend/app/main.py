"""
ActionFlow AI - Backend Main Application
FastAPI entry point

Endpoints:
    /api/v1/chat     - Chat with AI assistant
    /api/v1/flights  - Flight search & booking
    /api/v1/hotels   - Hotel search & booking
    /health          - Health check
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db, close_db
from app.core.orchestrator import shutdown as orchestrator_shutdown

# Import routers
from app.api.v1.auth_routes import router as auth_router
from app.api.v1.chat_routes import router as chat_router
from app.api.v1.flight_routes import router as flight_router
from app.api.v1.accommodation_routes import router as hotel_router
from app.api.v1.booking_routes import router as booking_router
from app.api.v1.policy_routes import router as policy_router
from app.api.v1.voice_routes import router as voice_router
from app.api.v1.whatsapp import router as whatsapp_router

from app.core.metrics import setup_metrics

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ActionFlow-Backend")


# ═══════════════════════════════════════════════════════════════════
# LIFESPAN (Startup & Shutdown)
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    
    # ─────────── STARTUP ───────────
    logger.info("🚀 Starting ActionFlow Backend...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    logger.info("✅ ActionFlow Backend started successfully")
    
    yield
    
    # ─────────── SHUTDOWN ───────────
    logger.info("🛑 Shutting down ActionFlow Backend...")
    
    # Close orchestrator (MCP client)
    try:
        await orchestrator_shutdown()
        logger.info("✅ Orchestrator shutdown complete")
    except Exception as e:
        logger.warning(f"⚠️ Orchestrator shutdown error: {e}")
    
    # Close Redis
    try:
        from app.core.redis import close_redis
        await close_redis()
    except Exception as e:
        logger.warning(f"⚠️ Redis shutdown error: {e}")

    # Close database
    try:
        await close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.warning(f"⚠️ Database close error: {e}")
    
    logger.info("👋 ActionFlow Backend stopped")


# ═══════════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ActionFlow AI",
    description="Travel Customer Support Automation - AI-powered assistant for flights, hotels, and bookings",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

setup_metrics(app)
# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da kısıtla
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
# ROUTERS
# ═══════════════════════════════════════════════════════════════════

# API v1 routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(flight_router, prefix="/api/v1")  # /api/v1/flights/...
app.include_router(hotel_router, prefix="/api/v1")   # /api/v1/hotels/...
app.include_router(booking_router, prefix="/api/v1") # /api/v1/bookings/...
app.include_router(policy_router, prefix="/api/v1")  # /api/v1/policies/...
app.include_router(voice_router, prefix="/api/v1")   # /api/v1/voice/...
app.include_router(whatsapp_router, prefix="/api/v1") # /api/v1/whatsapp/...


# ═══════════════════════════════════════════════════════════════════
# ROOT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """API root - basic info"""
    return {
        "name": "ActionFlow AI",
        "version": "1.0.0",
        "description": "Travel Customer Support Automation",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Checks:
    - API status
    - Database connection
    - MCP Server connection
    """
    from app.core.database import get_async_engine
    from app.core.orchestrator import mcp_client
    from sqlalchemy import text
    
    health = {
        "status": "healthy",
        "checks": {}
    }
    
    # Database check
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health["checks"]["database"] = "connected"
    except Exception as e:
        health["checks"]["database"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # MCP Server check
    try:
        tools = await mcp_client.list_tools()
        health["checks"]["mcp_server"] = {
            "status": "connected",
            "tools_count": len(tools)
        }
    except Exception as e:
        health["checks"]["mcp_server"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    return health


# ═══════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════

from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred"
        }
    )


# ═══════════════════════════════════════════════════════════════════
# RUN (for development)
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )