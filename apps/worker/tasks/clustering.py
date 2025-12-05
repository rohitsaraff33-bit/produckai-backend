"""Celery task for running clustering and insight generation pipeline."""

import logging
from datetime import datetime

from apps.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="run_daily_clustering_pipeline", bind=True)
def run_daily_clustering_pipeline(self):
    """
    Run the complete clustering and insight generation pipeline.

    This task:
    1. Fetches all feedback with embeddings (new + existing)
    2. Runs HDBSCAN clustering to identify themes
    3. Generates actionable insights for each theme
    4. Calculates priority scores and metrics

    Scheduled to run daily at 2 AM UTC.
    """
    try:
        logger.info("Starting daily clustering pipeline...")
        start_time = datetime.utcnow()

        # Import here to avoid circular imports
        from apps.api.database import get_db_context
        from apps.api.models import Feedback
        from apps.api.services.clustering import get_clustering_service
        from apps.api.services.insights import get_insight_service
        from apps.api.scripts.run_clustering import (
            run_clustering_pipeline,
            clear_existing_themes_and_insights,
        )

        # Check if there's enough feedback to cluster
        with get_db_context() as db:
            feedback_count = db.query(Feedback).filter(
                Feedback.embedding.isnot(None)
            ).count()

            if feedback_count < 10:
                logger.info(f"Not enough feedback to cluster ({feedback_count} items). Skipping.")
                return {
                    "status": "skipped",
                    "reason": "insufficient_data",
                    "feedback_count": feedback_count,
                    "message": "Need at least 10 feedback items to run clustering"
                }

        # Run the full clustering pipeline
        logger.info(f"Running clustering on {feedback_count} feedback items...")
        result = run_clustering_pipeline()

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Daily clustering pipeline completed successfully in {duration:.2f}s")
        logger.info(f"Generated {result.get('themes_created', 0)} themes and {result.get('insights_created', 0)} insights")

        return {
            "status": "success",
            "feedback_count": feedback_count,
            "themes_created": result.get("themes_created", 0),
            "insights_created": result.get("insights_created", 0),
            "duration_seconds": duration,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
        }

    except Exception as e:
        logger.error(f"Daily clustering pipeline failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=300, max_retries=3)  # Retry after 5 min, max 3 times


@celery_app.task(name="refresh_insights_on_demand", bind=True)
def refresh_insights_on_demand(self, clear_existing=True):
    """
    Manually trigger insight refresh (for on-demand use).

    Args:
        clear_existing: Whether to clear existing themes/insights before regenerating

    Returns:
        Dictionary with pipeline execution results
    """
    try:
        logger.info("Starting on-demand insight refresh...")
        start_time = datetime.utcnow()

        from apps.api.scripts.run_clustering import run_clustering_pipeline

        result = run_clustering_pipeline()

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"On-demand insight refresh completed in {duration:.2f}s")

        return {
            "status": "success",
            "themes_created": result.get("themes_created", 0),
            "insights_created": result.get("insights_created", 0),
            "duration_seconds": duration,
            "triggered_at": start_time.isoformat(),
        }

    except Exception as e:
        logger.error(f"On-demand insight refresh failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60, max_retries=2)
