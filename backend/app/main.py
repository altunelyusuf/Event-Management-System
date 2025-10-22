"""
CelebraTech Event Management System - Main Application
Sprint 1: Infrastructure & Authentication
Sprint 2: Event Management Core
Sprint 3: Vendor Profile Foundation
Sprint 4: Booking & Quote System
Sprint 5: Payment Gateway Integration & Financial Management
Sprint 6: Review and Rating System
FastAPI application entry point
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1 import auth, events, tasks, vendors, bookings, payments, reviews


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown
    """
    # Startup
    print("🚀 Starting CelebraTech Event Management System...")
    print(f"📝 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered cultural celebration event management platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# Middleware Configuration
# -----------------------

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-2FA-Required"]
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception Handlers
# ------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    if settings.DEBUG:
        # In debug mode, show full error
        import traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "traceback": traceback.format_exc()
            }
        )
    else:
        # In production, hide error details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )


# API Routes
# ----------

# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check if the API is running"
)
async def health_check():
    """
    Health check endpoint

    Returns API status and version
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API root",
    description="Get API information"
)
async def root():
    """
    API root endpoint

    Returns basic API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# API v1 routes
# Sprint 1: Authentication
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)

# Sprint 2: Event Management
app.include_router(events.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)

# Sprint 3: Vendor Marketplace
app.include_router(vendors.router, prefix=settings.API_V1_PREFIX)

# Sprint 4: Booking & Quote System
app.include_router(bookings.router, prefix=settings.API_V1_PREFIX)

# Sprint 5: Payment Gateway & Financial Management
app.include_router(payments.router, prefix=settings.API_V1_PREFIX)

# Sprint 6: Review and Rating System
app.include_router(reviews.router, prefix=settings.API_V1_PREFIX)


# Future routers (Sprint 7+):
# app.include_router(guests.router, prefix=settings.API_V1_PREFIX)
# app.include_router(messaging.router, prefix=settings.API_V1_PREFIX)


# Development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
