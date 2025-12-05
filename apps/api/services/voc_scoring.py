"""Voice of Customer (VOC) scoring service for Jira backlog prioritization."""

import logging
from collections import defaultdict
from typing import List, Optional
from uuid import UUID

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.models import (
    Customer,
    CustomerSegment,
    Feedback,
    Insight,
    InsightFeedback,
    JiraInsightMatch,
    JiraTicket,
    VOCScore,
)
from apps.api.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)
settings = get_settings()


class VOCScoringService:
    """Service for calculating Voice of Customer scores for Jira tickets."""

    def __init__(self):
        """Initialize VOC scoring service."""
        self.embedding_service = get_embedding_service()
        logger.info("VOCScoringService initialized")

    def match_ticket_to_insights(
        self,
        db: Session,
        ticket: JiraTicket,
        similarity_threshold: float = 0.6,
        max_matches: int = 5,
    ) -> List[JiraInsightMatch]:
        """
        Match a Jira ticket to relevant insights using semantic similarity.

        Args:
            db: Database session
            ticket: Jira ticket to match
            similarity_threshold: Minimum similarity score (0-1)
            max_matches: Maximum number of matches to return

        Returns:
            List of JiraInsightMatch objects
        """
        if not ticket.embedding:
            logger.warning(f"Ticket {ticket.jira_key} has no embedding, generating one")
            ticket_text = f"{ticket.title}. {ticket.description or ''}"
            ticket.embedding = self.embedding_service.embed_text(ticket_text)
            db.flush()

        # Get all insights with embeddings (via themes)
        insights = (
            db.query(Insight)
            .filter(Insight.theme_id.isnot(None))
            .all()
        )

        if not insights:
            logger.warning("No insights found for matching")
            return []

        # Calculate similarities
        ticket_embedding = np.array(ticket.embedding)
        matches = []

        for insight in insights:
            # Get insight embedding from its title
            insight_text = f"{insight.title}. {insight.description or ''}"
            insight_embedding = np.array(self.embedding_service.embed_text(insight_text))

            # Calculate cosine similarity
            similarity = float(
                np.dot(ticket_embedding, insight_embedding)
                / (np.linalg.norm(ticket_embedding) * np.linalg.norm(insight_embedding))
            )

            if similarity >= similarity_threshold:
                # Determine confidence level
                if similarity >= 0.8:
                    confidence = "high"
                elif similarity >= 0.6:
                    confidence = "medium"
                else:
                    confidence = "low"

                matches.append({
                    "insight": insight,
                    "similarity": similarity,
                    "confidence": confidence,
                })

        # Sort by similarity and take top matches
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        matches = matches[:max_matches]

        # Create JiraInsightMatch records
        match_records = []
        for match in matches:
            # Check if match already exists
            existing = (
                db.query(JiraInsightMatch)
                .filter(
                    JiraInsightMatch.ticket_id == ticket.id,
                    JiraInsightMatch.insight_id == match["insight"].id,
                )
                .first()
            )

            if existing:
                # Update existing match
                existing.similarity_score = match["similarity"]
                existing.confidence = match["confidence"]
                match_record = existing
            else:
                # Create new match
                match_record = JiraInsightMatch(
                    ticket_id=ticket.id,
                    insight_id=match["insight"].id,
                    similarity_score=match["similarity"],
                    confidence=match["confidence"],
                )
                db.add(match_record)

            match_records.append(match_record)

        db.flush()
        logger.info(
            f"Matched ticket {ticket.jira_key} to {len(match_records)} insights "
            f"(threshold={similarity_threshold})"
        )

        return match_records

    def calculate_voc_score(
        self,
        db: Session,
        ticket: JiraTicket,
    ) -> VOCScore:
        """
        Calculate VOC score for a Jira ticket based on matched insights.

        The VOC score aggregates:
        - Number of unique customers requesting the feature
        - Total ACV of those customers
        - Customer segment distribution (ENT > MM > SMB priority)
        - Total feedback volume

        Args:
            db: Database session
            ticket: Jira ticket to score

        Returns:
            VOCScore object with calculated scores
        """
        # Get all matched insights for this ticket
        matches = (
            db.query(JiraInsightMatch)
            .filter(JiraInsightMatch.ticket_id == ticket.id)
            .all()
        )

        if not matches:
            logger.warning(f"No insight matches found for ticket {ticket.jira_key}, creating zero score")
            return self._create_zero_score(db, ticket)

        # Get all unique feedback items across matched insights
        insight_ids = [match.insight_id for match in matches]
        feedback_links = (
            db.query(InsightFeedback)
            .filter(InsightFeedback.insight_id.in_(insight_ids))
            .all()
        )

        if not feedback_links:
            logger.warning(f"No feedback found for matched insights of ticket {ticket.jira_key}")
            return self._create_zero_score(db, ticket)

        # Get unique feedback items
        feedback_ids = list(set([link.feedback_id for link in feedback_links]))
        feedback_items = (
            db.query(Feedback)
            .filter(Feedback.id.in_(feedback_ids))
            .all()
        )

        # Get unique customers
        customer_ids = list(set([f.customer_id for f in feedback_items if f.customer_id]))
        customers = (
            db.query(Customer)
            .filter(Customer.id.in_(customer_ids))
            .all()
        )

        # Calculate metrics
        customer_count = len(customers)
        total_acv = sum(c.acv for c in customers)
        feedback_volume = len(feedback_items)

        # Calculate segment breakdown
        segment_counts = defaultdict(int)
        for c in customers:
            segment_counts[c.segment] += 1

        ent_count = segment_counts[CustomerSegment.ENT]
        mm_count = segment_counts[CustomerSegment.MM]
        smb_count = segment_counts[CustomerSegment.SMB]

        # Get global maxima for normalization
        max_customer_count = db.query(func.max(VOCScore.customer_count)).scalar() or 1
        max_total_acv = db.query(func.max(VOCScore.total_acv)).scalar() or 1.0
        max_feedback_volume = db.query(func.max(VOCScore.feedback_volume)).scalar() or 1

        # If this is the first score, use current values as max
        max_customer_count = max(max_customer_count, customer_count, 1)
        max_total_acv = max(max_total_acv, total_acv, 1.0)
        max_feedback_volume = max(max_feedback_volume, feedback_volume, 1)

        # Calculate normalized component scores (0-100)
        customer_score = min(100, (customer_count / max_customer_count) * 100)
        acv_score = min(100, (total_acv / max_total_acv) * 100)
        volume_score = min(100, (feedback_volume / max_feedback_volume) * 100)

        # Calculate segment score (weighted by priority)
        # ENT customers are 3x more important, MM 2x, SMB 1x
        segment_priority_sum = (ent_count * 3) + (mm_count * 2) + (smb_count * 1)
        max_possible_segment = customer_count * 3  # If all were ENT
        segment_score = min(100, (segment_priority_sum / max(max_possible_segment, 1)) * 100) if customer_count > 0 else 0

        # Calculate final VOC score (weighted average)
        # Weights: customer_count=30%, acv=30%, segment=25%, volume=15%
        voc_score = (
            (customer_score * 0.30)
            + (acv_score * 0.30)
            + (segment_score * 0.25)
            + (volume_score * 0.15)
        )

        # Determine recommended priority
        if voc_score >= 80:
            recommended_priority = "critical"
        elif voc_score >= 60:
            recommended_priority = "high"
        elif voc_score >= 40:
            recommended_priority = "medium"
        else:
            recommended_priority = "low"

        # Upsert VOC score
        existing_score = (
            db.query(VOCScore)
            .filter(VOCScore.ticket_id == ticket.id)
            .first()
        )

        if existing_score:
            # Update existing score
            existing_score.customer_count = customer_count
            existing_score.total_acv = total_acv
            existing_score.feedback_volume = feedback_volume
            existing_score.ent_customer_count = ent_count
            existing_score.mm_customer_count = mm_count
            existing_score.smb_customer_count = smb_count
            existing_score.customer_score = customer_score
            existing_score.acv_score = acv_score
            existing_score.segment_score = segment_score
            existing_score.volume_score = volume_score
            existing_score.voc_score = voc_score
            existing_score.recommended_priority = recommended_priority
            score = existing_score
        else:
            # Create new score
            score = VOCScore(
                ticket_id=ticket.id,
                customer_count=customer_count,
                total_acv=total_acv,
                feedback_volume=feedback_volume,
                ent_customer_count=ent_count,
                mm_customer_count=mm_count,
                smb_customer_count=smb_count,
                customer_score=customer_score,
                acv_score=acv_score,
                segment_score=segment_score,
                volume_score=volume_score,
                voc_score=voc_score,
                recommended_priority=recommended_priority,
            )
            db.add(score)

        db.flush()

        logger.info(
            f"Calculated VOC score for {ticket.jira_key}: "
            f"score={voc_score:.1f}, customers={customer_count}, acv=${total_acv:.0f}, "
            f"priority={recommended_priority}"
        )

        return score

    def _create_zero_score(self, db: Session, ticket: JiraTicket) -> VOCScore:
        """Create a zero VOC score for tickets with no matches."""
        existing_score = (
            db.query(VOCScore)
            .filter(VOCScore.ticket_id == ticket.id)
            .first()
        )

        if existing_score:
            # Update to zeros
            existing_score.customer_count = 0
            existing_score.total_acv = 0.0
            existing_score.feedback_volume = 0
            existing_score.ent_customer_count = 0
            existing_score.mm_customer_count = 0
            existing_score.smb_customer_count = 0
            existing_score.customer_score = 0.0
            existing_score.acv_score = 0.0
            existing_score.segment_score = 0.0
            existing_score.volume_score = 0.0
            existing_score.voc_score = 0.0
            existing_score.recommended_priority = "low"
            score = existing_score
        else:
            score = VOCScore(
                ticket_id=ticket.id,
                customer_count=0,
                total_acv=0.0,
                feedback_volume=0,
                ent_customer_count=0,
                mm_customer_count=0,
                smb_customer_count=0,
                customer_score=0.0,
                acv_score=0.0,
                segment_score=0.0,
                volume_score=0.0,
                voc_score=0.0,
                recommended_priority="low",
            )
            db.add(score)

        db.flush()
        return score

    def process_ticket(
        self,
        db: Session,
        ticket: JiraTicket,
        similarity_threshold: float = 0.6,
    ) -> VOCScore:
        """
        Complete VOC scoring process: match ticket to insights and calculate score.

        Args:
            db: Database session
            ticket: Jira ticket to process
            similarity_threshold: Minimum similarity for insight matching

        Returns:
            VOCScore object
        """
        # Step 1: Match ticket to insights
        matches = self.match_ticket_to_insights(db, ticket, similarity_threshold)

        # Step 2: Calculate VOC score
        score = self.calculate_voc_score(db, ticket)

        return score

    def process_all_tickets(
        self,
        db: Session,
        similarity_threshold: float = 0.6,
    ) -> dict:
        """
        Process all Jira tickets for VOC scoring.

        Args:
            db: Database session
            similarity_threshold: Minimum similarity for insight matching

        Returns:
            Dictionary with processing statistics
        """
        tickets = db.query(JiraTicket).all()

        if not tickets:
            logger.warning("No Jira tickets found to process")
            return {"tickets_processed": 0, "scores_calculated": 0}

        logger.info(f"Processing {len(tickets)} Jira tickets for VOC scoring...")

        scores_calculated = 0
        for ticket in tickets:
            try:
                self.process_ticket(db, ticket, similarity_threshold)
                scores_calculated += 1
            except Exception as e:
                logger.error(f"Failed to process ticket {ticket.jira_key}: {e}", exc_info=True)

        db.commit()

        logger.info(
            f"VOC scoring complete: processed {len(tickets)} tickets, "
            f"calculated {scores_calculated} scores"
        )

        return {
            "tickets_processed": len(tickets),
            "scores_calculated": scores_calculated,
        }


# Singleton instance
_voc_scoring_service: Optional[VOCScoringService] = None


def get_voc_scoring_service() -> VOCScoringService:
    """Get or create VOC scoring service instance."""
    global _voc_scoring_service
    if _voc_scoring_service is None:
        _voc_scoring_service = VOCScoringService()
    return _voc_scoring_service
