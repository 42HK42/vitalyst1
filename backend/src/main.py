"""Main application module for the Vitalyst Knowledge Graph backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api.routes import router as api_router
from src.utils.config import Settings

# Load settings
settings = Settings()

# Create FastAPI application
app = FastAPI(
    title="Vitalyst Knowledge Graph API",
    description="API for managing and querying the Vitalyst Knowledge Graph",
    version="1.0.0-alpha",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 