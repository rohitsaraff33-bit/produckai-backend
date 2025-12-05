"""Customer aggregation endpoints."""

from collections import Counter
from typing import Optional

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import Customer, Feedback, Insight, InsightFeedback

logger = structlog.get_logger()
router = APIRouter()


class CustomerSummary(BaseModel):
    """Customer summary with insight count."""

    name: str
    insight_count: int
    feedback_count: int


class CustomersResponse(BaseModel):
    """List of customers."""

    customers: list[CustomerSummary]
    total_customers: int


@router.get("/customers", response_model=CustomersResponse)
async def list_customers(db: Session = Depends(get_db)):
    """
    List all customers who have contributed to insights.

    Returns:
        List of customers with their insight and feedback counts
    """
    # Get customers from the Customer table, joined to feedback and insights
    # Group by customer and count distinct insights
    customer_data = (
        db.query(
            Customer.name,
            func.count(func.distinct(InsightFeedback.insight_id)).label("insight_count"),
            func.count(func.distinct(Feedback.id)).label("feedback_count"),
        )
        .join(Feedback, Feedback.customer_id == Customer.id)
        .join(InsightFeedback, Feedback.id == InsightFeedback.feedback_id)
        .group_by(Customer.id, Customer.name)
        .order_by(func.count(func.distinct(InsightFeedback.insight_id)).desc())
        .all()
    )

    # Build response
    customers = [
        CustomerSummary(
            name=name,
            insight_count=insight_count,
            feedback_count=feedback_count,
        )
        for name, insight_count, feedback_count in customer_data
    ]

    logger.info("Listed customers", count=len(customers))

    return CustomersResponse(customers=customers, total_customers=len(customers))


@router.get("/customers/{customer_name}/insights")
async def get_customer_insights(customer_name: str, db: Session = Depends(get_db)):
    """
    Get all insights for a specific customer.

    Args:
        customer_name: Customer name
        db: Database session

    Returns:
        List of insight IDs and metadata for the customer
    """
    # Find the customer
    customer = db.query(Customer).filter(Customer.name == customer_name).first()

    if not customer:
        return {"customer": customer_name, "insights": [], "count": 0}

    # Find all feedback from this customer
    customer_feedback_ids = (
        db.query(Feedback.id).filter(Feedback.customer_id == customer.id).all()
    )

    feedback_ids = [fid[0] for fid in customer_feedback_ids]

    if not feedback_ids:
        return {"customer": customer_name, "insights": [], "count": 0}

    # Find insights linked to this customer's feedback
    insights_data = (
        db.query(
            Insight.id,
            Insight.title,
            Insight.description,
            Insight.severity,
            Insight.priority_score,
            Insight.effort,
            Insight.impact,
            Insight.recommendation,
            func.count(InsightFeedback.feedback_id).label("feedback_count"),
        )
        .join(InsightFeedback, Insight.id == InsightFeedback.insight_id)
        .filter(InsightFeedback.feedback_id.in_(feedback_ids))
        .group_by(
            Insight.id,
            Insight.title,
            Insight.description,
            Insight.severity,
            Insight.priority_score,
            Insight.effort,
            Insight.impact,
            Insight.recommendation,
        )
        .order_by(Insight.priority_score.desc())
        .all()
    )

    insights = [
        {
            "id": str(insight_id),
            "title": title,
            "description": description,
            "severity": severity,
            "priority_score": priority_score,
            "effort": effort,
            "impact": impact,
            "recommendation": recommendation,
            "feedback_count": feedback_count,
        }
        for insight_id, title, description, severity, priority_score, effort, impact, recommendation, feedback_count in insights_data
    ]

    logger.info(
        "Retrieved customer insights", customer=customer_name, count=len(insights)
    )

    return {"customer": customer_name, "insights": insights, "count": len(insights)}
