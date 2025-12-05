"""Run clustering pipeline."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from uuid import uuid4

from sqlalchemy import func

from apps.api.config import get_settings
from apps.api.database import get_db_context
from apps.api.models import Customer, Feedback, FeedbackTheme, Theme, ThemeMetrics, Insight, InsightFeedback
from apps.api.services.clustering import get_clustering_service
from apps.api.services.insights import get_insight_service
from packages.shared.scoring import ScoreWeights, SegmentPriorities, calculate_theme_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


def title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two insight titles.

    Args:
        title1: First title
        title2: Second title

    Returns:
        Similarity score between 0 and 1
    """
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def deduplicate_insights(db):
    """
    Deduplicate insights with very similar titles by merging them.

    This prevents duplicate insights from being shown to users when the
    clustering algorithm creates multiple similar themes.

    Args:
        db: Database session
    """
    insights = db.query(Insight).all()

    if len(insights) < 2:
        return

    logger.info(f"Deduplicating {len(insights)} insights...")

    # Track insights to delete
    insights_to_delete = set()

    # Compare each pair of insights
    for i in range(len(insights)):
        if insights[i].id in insights_to_delete:
            continue

        for j in range(i + 1, len(insights)):
            if insights[j].id in insights_to_delete:
                continue

            # Calculate title similarity
            similarity = title_similarity(insights[i].title, insights[j].title)

            # If titles are very similar (>85% match), merge them
            if similarity > 0.85:
                insight_keep = insights[i]
                insight_delete = insights[j]

                # Prefer insight with higher priority score
                if insight_delete.priority_score > insight_keep.priority_score:
                    insight_keep, insight_delete = insight_delete, insight_keep

                logger.info(
                    f"Merging duplicate insights: '{insight_delete.title}' -> '{insight_keep.title}' "
                    f"(similarity: {similarity:.2%})"
                )

                # Move all feedback from duplicate to kept insight
                feedback_links = (
                    db.query(InsightFeedback)
                    .filter(InsightFeedback.insight_id == insight_delete.id)
                    .all()
                )

                for link in feedback_links:
                    # Check if this feedback is already linked to the kept insight
                    existing = (
                        db.query(InsightFeedback)
                        .filter(
                            InsightFeedback.insight_id == insight_keep.id,
                            InsightFeedback.feedback_id == link.feedback_id,
                        )
                        .first()
                    )

                    if not existing:
                        # Move the link to the kept insight
                        link.insight_id = insight_keep.id
                    else:
                        # Feedback already linked, just delete this link
                        db.delete(link)

                # Mark duplicate insight for deletion
                insights_to_delete.add(insight_delete.id)

    # Delete duplicate insights
    if insights_to_delete:
        for insight_id in insights_to_delete:
            insight = db.query(Insight).filter(Insight.id == insight_id).first()
            if insight:
                db.delete(insight)

        db.commit()
        logger.info(f"Deleted {len(insights_to_delete)} duplicate insights")
    else:
        logger.info("No duplicate insights found")


def run_clustering():
    """Run complete clustering pipeline."""
    with get_db_context() as db:
        # 1. Load feedback with embeddings
        feedback_items = (
            db.query(Feedback)
            .filter(Feedback.embedding.isnot(None))
            .all()
        )

        if len(feedback_items) < settings.clustering_min_feedback_count:
            logger.warning(
                f"Not enough feedback for clustering: {len(feedback_items)} < {settings.clustering_min_feedback_count}"
            )
            return

        logger.info(f"Clustering {len(feedback_items)} feedback items...")

        # 2. Prepare data
        embeddings = [f.embedding for f in feedback_items]
        texts = [f.text for f in feedback_items]

        # 3. Run clustering
        clustering_service = get_clustering_service()
        cluster_results = clustering_service.cluster_embeddings(embeddings, texts)

        logger.info(f"Found {len(cluster_results)} clusters")

        # 4. Create themes with LLM-refined labels and insights
        theme_version = int(datetime.utcnow().timestamp())
        insight_service = get_insight_service()

        for result in cluster_results:
            # Get ALL cluster feedback for insight generation (not just texts!)
            cluster_feedback = [feedback_items[idx] for idx in result.member_indices]
            cluster_texts = [f.text for f in cluster_feedback]

            # Refine label with LLM if available
            refined_label = clustering_service.refine_label_with_llm(
                result.label,
                cluster_texts[:5]
            )

            # Create theme
            theme = Theme(
                label=refined_label,
                description=result.description,
                centroid=result.centroid,
                version=theme_version,
            )
            db.add(theme)
            db.flush()

            # Link feedback to theme
            for idx, confidence in zip(result.member_indices, result.member_confidences):
                feedback = feedback_items[idx]
                ft = FeedbackTheme(
                    feedback_id=feedback.id,
                    theme_id=theme.id,
                    confidence=confidence,
                )
                db.add(ft)

            # Generate insights for this theme with ALL feedback
            try:
                generated_insights = insight_service.generate_insights_for_cluster(
                    db,  # Pass database session
                    cluster_feedback,  # Pass FULL feedback objects (not just texts!)
                    refined_label,
                )

                for gen_insight in generated_insights:
                    # Calculate priority score (0-100)
                    severity_score = {"low": 25, "medium": 50, "high": 75, "critical": 100}.get(gen_insight.severity, 50)
                    effort_score = {"low": 75, "medium": 50, "high": 25}.get(gen_insight.effort, 50)
                    priority_score = int((severity_score + effort_score) / 2)

                    # Create insight with IMMUTABLE data for data integrity
                    insight = Insight(
                        id=uuid4(),
                        theme_id=theme.id,
                        title=gen_insight.title,
                        description=gen_insight.description,
                        impact=gen_insight.impact,
                        recommendation=gen_insight.recommendation,
                        severity=gen_insight.severity,
                        effort=gen_insight.effort,
                        priority_score=priority_score,
                        # CRITICAL: Store immutable snapshots to prevent customer count mismatches
                        supporting_feedback_ids=gen_insight.supporting_feedback_ids,  # ALL feedback IDs used
                        affected_customers=gen_insight.affected_customers,  # Customer data snapshot
                        key_quotes=gen_insight.key_quotes,  # Actual quote texts
                    )
                    db.add(insight)
                    db.flush()

                    # Link ONLY the feedback that was actually used for this insight
                    # This ensures consistency: description matches linked feedback
                    supporting_feedback_id_set = set(gen_insight.supporting_feedback_ids)

                    for feedback in cluster_feedback:
                        # Only link feedback that was used for this insight
                        if str(feedback.id) in supporting_feedback_id_set:
                            # Check if this feedback is in the key quotes
                            is_key_quote = 1 if feedback.text in gen_insight.key_quotes else 0

                            # Assign relevance score: key quotes get higher score
                            relevance_score = 95 if is_key_quote else 80

                            insight_fb = InsightFeedback(
                                insight_id=insight.id,
                                feedback_id=feedback.id,
                                relevance_score=relevance_score,
                                is_key_quote=is_key_quote,
                            )
                            db.add(insight_fb)

                    logger.info(f"Linked {len(gen_insight.supporting_feedback_ids)} feedback items to insight (out of {len(cluster_feedback)} in cluster)")

                logger.info(f"Generated {len(generated_insights)} insights for theme: {refined_label}")

            except Exception as e:
                logger.error(f"Failed to generate insights for theme {refined_label}: {e}")

        db.commit()
        logger.info("Themes, insights, and links created")

        # 5. Deduplicate similar insights
        deduplicate_insights(db)

        # 6. Calculate metrics and scores
        calculate_theme_metrics(db)

        logger.info("Clustering pipeline completed!")


def calculate_theme_metrics(db):
    """Calculate metrics and ThemeScore for all themes."""
    themes = db.query(Theme).all()

    # Get global maxima for normalization
    now = datetime.utcnow()
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    max_freq_30d = 0
    max_freq_90d = 0
    max_acv_sum = 0.0

    theme_stats = {}

    for theme in themes:
        # Get feedback for this theme
        feedback_ids = (
            db.query(FeedbackTheme.feedback_id)
            .filter(FeedbackTheme.theme_id == theme.id)
            .subquery()
        )

        feedback_items = (
            db.query(Feedback)
            .filter(Feedback.id.in_(feedback_ids))
            .all()
        )

        # Calculate frequency
        accounts_30d = set()
        accounts_90d = set()

        for f in feedback_items:
            if f.created_at >= cutoff_30d:
                accounts_30d.add(f.account or "unknown")
                accounts_90d.add(f.account or "unknown")
            elif f.created_at >= cutoff_90d:
                accounts_90d.add(f.account or "unknown")

        freq_30d = len(accounts_30d)
        freq_90d = len(accounts_90d)

        # Calculate ACV
        customer_ids = set(f.customer_id for f in feedback_items if f.customer_id)
        customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
        acv_sum = sum(c.acv for c in customers)

        # Calculate sentiment (dummy for now - use VADER in production)
        sentiment = 0.0

        # Calculate segment counts
        segment_counts = defaultdict(int)
        for c in customers:
            segment_counts[c.segment.value] += 1

        # Calculate weekly counts (dummy - just use total for now)
        weekly_counts = [len(feedback_items) // 12] * 12

        theme_stats[theme.id] = {
            "freq_30d": freq_30d,
            "freq_90d": freq_90d,
            "acv_sum": acv_sum,
            "sentiment": sentiment,
            "segment_counts": dict(segment_counts),
            "weekly_counts": weekly_counts,
        }

        max_freq_30d = max(max_freq_30d, freq_30d)
        max_freq_90d = max(max_freq_90d, freq_90d)
        max_acv_sum = max(max_acv_sum, acv_sum)

    # Calculate scores
    weights = ScoreWeights(
        frequency=settings.score_weight_frequency,
        acv=settings.score_weight_acv,
        sentiment=settings.score_weight_sentiment,
        segment=settings.score_weight_segment,
        trend=settings.score_weight_trend,
        duplicate=settings.score_weight_duplicate,
    )

    seg_priorities = SegmentPriorities(
        ENT=settings.segment_priority_ent,
        MM=settings.segment_priority_mm,
        SMB=settings.segment_priority_smb,
    )

    for theme in themes:
        stats = theme_stats[theme.id]

        # Calculate ThemeScore
        components = calculate_theme_score(
            freq_30d=stats["freq_30d"],
            freq_90d=stats["freq_90d"],
            acv_sum=stats["acv_sum"],
            avg_sentiment=stats["sentiment"],
            segment_counts=stats["segment_counts"],
            weekly_counts=stats["weekly_counts"],
            similarity_to_higher=0.0,  # TODO: Calculate actual similarity
            max_freq_30d=max_freq_30d,
            max_freq_90d=max_freq_90d,
            max_acv_sum=max_acv_sum,
            weights=weights,
            segment_priorities=seg_priorities,
        )

        # Upsert metrics
        metrics = (
            db.query(ThemeMetrics)
            .filter(ThemeMetrics.theme_id == theme.id)
            .first()
        )

        if not metrics:
            metrics = ThemeMetrics(theme_id=theme.id)
            db.add(metrics)

        metrics.freq_30d = stats["freq_30d"]
        metrics.freq_90d = stats["freq_90d"]
        metrics.acv_sum = stats["acv_sum"]
        metrics.sentiment = stats["sentiment"]
        metrics.trend = components.trend_momentum
        metrics.dup_penalty = components.dup_penalty
        metrics.score = components.final_score

    db.commit()
    logger.info(f"Calculated metrics for {len(themes)} themes")


def run_clustering_pipeline():
    """
    Wrapper function to run complete clustering pipeline and return results.

    Returns:
        dict: Pipeline execution results with counts
    """
    with get_db_context() as db:
        # Clear old themes and insights
        db.query(InsightFeedback).delete()
        db.query(Insight).delete()
        db.query(ThemeMetrics).delete()
        db.query(FeedbackTheme).delete()
        db.query(Theme).delete()
        db.commit()

    # Run clustering
    run_clustering()

    # Get counts
    with get_db_context() as db:
        themes_count = db.query(Theme).count()
        insights_count = db.query(Insight).count()

    return {
        "themes_created": themes_count,
        "insights_created": insights_count,
    }


def clear_existing_themes_and_insights():
    """Clear existing themes and insights from database."""
    with get_db_context() as db:
        db.query(InsightFeedback).delete()
        db.query(Insight).delete()
        db.query(ThemeMetrics).delete()
        db.query(FeedbackTheme).delete()
        db.query(Theme).delete()
        db.commit()
        logger.info("Cleared all existing themes and insights")


if __name__ == "__main__":
    logger.info("Running clustering pipeline...")
    result = run_clustering_pipeline()
    logger.info(f"Pipeline completed: {result}")
