"""Celery tasks for background processing."""

import logging

from apps.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="embed_feedback")
def embed_feedback_task(feedback_id: str):
    """
    Generate embedding for a feedback item.

    Args:
        feedback_id: Feedback UUID
    """
    from uuid import UUID

    from apps.api.database import get_db_context
    from apps.api.models import Feedback
    from apps.api.services.embeddings import get_embedding_service

    logger.info(f"Generating embedding for feedback {feedback_id}")

    with get_db_context() as db:
        feedback = db.query(Feedback).filter(Feedback.id == UUID(feedback_id)).first()

        if not feedback:
            logger.error(f"Feedback {feedback_id} not found")
            return

        # Generate embedding
        embedding_service = get_embedding_service()
        embedding = embedding_service.embed_text(feedback.text)

        # Update feedback
        feedback.embedding = embedding
        db.commit()

    logger.info(f"Embedding generated for feedback {feedback_id}")


@celery_app.task(name="cluster_feedback")
def cluster_feedback_task():
    """Run clustering pipeline on all feedback."""
    logger.info("Starting clustering task")

    from apps.api.scripts.run_clustering import run_clustering

    try:
        run_clustering()
        logger.info("Clustering completed successfully")
    except Exception as e:
        logger.error(f"Clustering failed: {e}", exc_info=True)
        raise
