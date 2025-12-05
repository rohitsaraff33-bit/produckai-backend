"""Clustering endpoints."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.database import get_db

router = APIRouter()

# Simple file-based status tracking (can be replaced with Redis in production)
STATUS_FILE = Path("/tmp/clustering_status.json")


class ClusterResponse(BaseModel):
    """Cluster task response."""

    status: str
    message: str
    task_id: Optional[str] = None


class ClusterStatusResponse(BaseModel):
    """Cluster status response."""

    is_running: bool
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    themes_created: Optional[int] = None
    insights_created: Optional[int] = None
    error: Optional[str] = None


def get_clustering_status() -> dict:
    """Get current clustering status from file."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"is_running": False, "status": "idle"}


def set_clustering_status(status_data: dict):
    """Set clustering status to file."""
    with open(STATUS_FILE, "w") as f:
        json.dump(status_data, f)


def run_clustering_task(db_url: str):
    """Background task to run clustering."""
    try:
        # Mark as running
        set_clustering_status({
            "is_running": True,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        })

        # Run clustering
        from apps.api.scripts.run_clustering import run_clustering_pipeline

        result = run_clustering_pipeline()

        # Mark as completed
        set_clustering_status({
            "is_running": False,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "themes_created": result.get("themes_created", 0),
            "insights_created": result.get("insights_created", 0),
        })

    except Exception as e:
        # Mark as failed
        set_clustering_status({
            "is_running": False,
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e),
        })
        raise


@router.post("/run", response_model=ClusterResponse)
async def trigger_clustering(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger clustering pipeline.

    This runs as a background task and clusters all feedback into themes.

    Returns:
        Status of the clustering task
    """
    from apps.api.config import get_settings

    settings = get_settings()

    # Check if already running
    status = get_clustering_status()
    if status.get("is_running"):
        return ClusterResponse(
            status="already_running",
            message="Clustering task is already running",
        )

    # Add to background tasks
    background_tasks.add_task(run_clustering_task, settings.database_url)

    return ClusterResponse(
        status="accepted",
        message="Clustering task started in background",
    )


@router.get("/status", response_model=ClusterStatusResponse)
async def get_status():
    """
    Get current clustering pipeline status.

    Returns:
        Current status of the clustering pipeline
    """
    status = get_clustering_status()
    return ClusterStatusResponse(**status)
