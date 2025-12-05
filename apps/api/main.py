"""FastAPI main application."""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.api.admin import router as admin_router
from apps.api.api.artifacts import router as artifacts_router
from apps.api.api.auth import router as auth_router
from apps.api.api.chat import router as chat_router
from apps.api.api.clustering import router as clustering_router
from apps.api.api.competitive import router as competitive_router
from apps.api.api.customers import router as customers_router
from apps.api.api.feedback import router as feedback_router
from apps.api.api.health import router as health_router
from apps.api.api.ingest import router as ingest_router
from apps.api.api.integrations import router as integrations_router
from apps.api.api.jira import router as jira_router
from apps.api.api.search import router as search_router
from apps.api.api.themes import router as themes_router
from apps.api.api.upload import router as upload_router
from apps.api.config import get_settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting ProduckAI API", version="1.0.0", demo_mode=settings.demo_mode)
    yield
    logger.info("Shutting down ProduckAI API")


# Create FastAPI app
app = FastAPI(
    title="ProduckAI API",
    description="Product Management Copilot - Feedback clustering and theme scoring",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(themes_router, prefix="/themes", tags=["Themes"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(search_router, prefix="/search", tags=["Search"])
app.include_router(clustering_router, prefix="/cluster", tags=["Clustering"])
app.include_router(ingest_router, prefix="/ingest", tags=["Ingestion"])
app.include_router(upload_router, prefix="/upload", tags=["Upload"])
app.include_router(artifacts_router, prefix="/tickets", tags=["Artifacts"])
app.include_router(integrations_router, tags=["Integrations"])
app.include_router(feedback_router, tags=["Feedback"])
app.include_router(customers_router, tags=["Customers"])
app.include_router(jira_router, tags=["Jira VOC Scoring"])
app.include_router(competitive_router, prefix="/competitive", tags=["Competitive Intelligence"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ProduckAI API",
        "version": "1.0.0",
        "demo_mode": settings.demo_mode,
        "docs": "/docs",
    }
