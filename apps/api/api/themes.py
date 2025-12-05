"""Insight endpoints (formerly themes)."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, or_, and_
from sqlalchemy.orm import Session, joinedload

from apps.api.database import get_db
from apps.api.models import Customer, Feedback, FeedbackTheme, Insight, InsightFeedback, Theme, ThemeMetrics

router = APIRouter()


class CustomerInfo(BaseModel):
    """Customer information for an insight."""

    id: str
    name: str
    segment: str
    acv: float

    class Config:
        from_attributes = True


class InsightListResponse(BaseModel):
    """Insight list item (top-level)."""

    id: str
    theme_id: Optional[str] = None  # Parent theme ID for linking insights to themes
    title: str
    description: Optional[str]
    impact: Optional[str]
    recommendation: Optional[str]
    severity: str
    effort: str
    priority_score: int
    created_at: str
    updated_at: str
    metrics: Optional[dict]
    feedback_count: int
    customers: List[CustomerInfo]  # List of customers who contributed
    total_acv: float  # Total ACV across all customers

    class Config:
        from_attributes = True


class InsightDetailResponse(BaseModel):
    """Detailed insight with supporting feedback."""

    id: str
    theme_id: Optional[str] = None  # Parent theme ID for linking insights to themes
    title: str
    description: Optional[str]
    impact: Optional[str]
    recommendation: Optional[str]
    severity: str
    effort: str
    priority_score: int
    created_at: str
    updated_at: str
    metrics: Optional[dict]
    feedback_count: int
    customers: List[CustomerInfo]  # List of customers who contributed
    total_acv: float  # Total ACV across all customers
    key_quotes: List[dict]  # Highlighted feedback
    supporting_feedback: List[dict]  # All supporting feedback

    class Config:
        from_attributes = True


class FilterCountsResponse(BaseModel):
    """Quick filter counts."""

    enterprise_blockers: int
    high_priority: int
    trending: int

    class Config:
        from_attributes = True


@router.get("", response_model=List[InsightListResponse])
async def list_insights(
    sort_by: str = Query("priority", enum=["priority", "score", "trend", "created_at"]),
    filter: Optional[str] = Query(None, enum=["enterprise_blockers", "high_priority", "trending"]),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    # Phase 1 Filters
    priority_min: Optional[int] = Query(None, ge=0, le=100, description="Minimum priority score"),
    priority_max: Optional[int] = Query(None, ge=0, le=100, description="Maximum priority score"),
    severity: Optional[List[str]] = Query(None, description="Filter by severity (critical, high, medium, low)"),
    segments: Optional[List[str]] = Query(None, description="Filter by customer segments (ENT, MM, SMB)"),
    effort: Optional[List[str]] = Query(None, description="Filter by effort (low, medium, high)"),
    db: Session = Depends(get_db),
):
    """
    List insights with optional sorting, filtering, and pagination.

    Args:
        sort_by: Sort field (priority, score, trend, created_at)
        filter: Quick filter category (enterprise_blockers, high_priority, trending)
        limit: Maximum number of results
        offset: Pagination offset
        priority_min: Minimum priority score (0-100)
        priority_max: Maximum priority score (0-100)
        severity: Filter by severity levels
        segments: Filter by customer segments
        effort: Filter by effort levels
        db: Database session

    Returns:
        List of insights

    Quick Filter Criteria:
        - enterprise_blockers: severity='critical' OR (severity='high' AND acv_sum >= 50000)
        - high_priority: priority_score >= 70 OR severity IN ('high', 'critical')
        - trending: trend > 0 AND freq_30d >= 3
    """
    # Query insights and join to theme for metrics
    query = db.query(Insight).join(Insight.theme).join(Theme.metrics, isouter=True)

    # Apply quick filter (backward compatibility)
    if filter == "enterprise_blockers":
        # Critical severity OR high severity with high ACV
        query = query.filter(
            (Insight.severity == "critical")
            | ((Insight.severity == "high") & (ThemeMetrics.acv_sum >= 50000))
        )
    elif filter == "high_priority":
        # High priority score OR high/critical severity
        query = query.filter(
            (Insight.priority_score >= 70) | (Insight.severity.in_(["high", "critical"]))
        )
    elif filter == "trending":
        # Positive trend with minimum activity
        query = query.filter((ThemeMetrics.trend > 0) & (ThemeMetrics.freq_30d >= 3))

    # Apply Phase 1 filters
    if priority_min is not None:
        query = query.filter(Insight.priority_score >= priority_min)
    if priority_max is not None:
        query = query.filter(Insight.priority_score <= priority_max)
    if severity:
        query = query.filter(Insight.severity.in_(severity))
    if effort:
        query = query.filter(Insight.effort.in_(effort))

    # Filter by customer segments (requires checking if any linked customer has the segment)
    if segments:
        # Subquery to get insight IDs that have customers in the specified segments
        segment_insight_ids = (
            db.query(InsightFeedback.insight_id.distinct())
            .join(Feedback, Feedback.id == InsightFeedback.feedback_id)
            .join(Customer, Customer.id == Feedback.customer_id)
            .filter(Customer.segment.in_(segments))
            .subquery()
        )
        query = query.filter(Insight.id.in_(segment_insight_ids))

    # Apply sorting
    if sort_by == "priority":
        query = query.order_by(desc(Insight.priority_score))
    elif sort_by == "score":
        query = query.order_by(desc(ThemeMetrics.score))
    elif sort_by == "trend":
        query = query.order_by(desc(ThemeMetrics.trend))
    else:
        query = query.order_by(desc(Insight.created_at))

    insights = query.offset(offset).limit(limit).all()

    # Format response
    results = []
    for insight in insights:
        # Count feedback linked to this insight
        feedback_count = (
            db.query(func.count(InsightFeedback.feedback_id))
            .filter(InsightFeedback.insight_id == insight.id)
            .scalar()
        )

        # Get customers from IMMUTABLE affected_customers field (data integrity)
        # This ensures customer counts match what LLM saw during insight generation
        if insight.affected_customers:
            # Use immutable customer data stored at insight generation time
            customers_list = [
                CustomerInfo(
                    id=c["id"],
                    name=c["name"],
                    segment=c["segment"],
                    acv=c["acv"],
                )
                for c in insight.affected_customers
            ]
            total_acv = sum(c["acv"] for c in insight.affected_customers)
        else:
            # Fallback for insights created before immutable fields (backward compatibility)
            customer_ids_subq = (
                db.query(Customer.id.distinct())
                .join(Feedback, Feedback.customer_id == Customer.id)
                .join(InsightFeedback, InsightFeedback.feedback_id == Feedback.id)
                .filter(InsightFeedback.insight_id == insight.id)
                .subquery()
            )

            customers_data = (
                db.query(Customer)
                .filter(Customer.id.in_(customer_ids_subq))
                .all()
            )

            customers_list = [
                CustomerInfo(
                    id=str(c.id),
                    name=c.name,
                    segment=c.segment.value,
                    acv=c.acv or 0.0,
                )
                for c in customers_data
            ]
            total_acv = sum(c.acv or 0.0 for c in customers_data)

        # Get theme metrics
        metrics_dict = None
        if insight.theme.metrics:
            metrics_dict = {
                "freq_30d": insight.theme.metrics.freq_30d,
                "freq_90d": insight.theme.metrics.freq_90d,
                "acv_sum": insight.theme.metrics.acv_sum,
                "sentiment": insight.theme.metrics.sentiment,
                "trend": insight.theme.metrics.trend,
                "score": insight.theme.metrics.score,
            }

        results.append(
            InsightListResponse(
                id=str(insight.id),
                theme_id=str(insight.theme_id) if insight.theme_id else None,
                title=insight.title,
                description=insight.description,
                impact=insight.impact,
                recommendation=insight.recommendation,
                severity=insight.severity or "medium",
                effort=insight.effort or "medium",
                priority_score=insight.priority_score,
                created_at=insight.created_at.isoformat(),
                updated_at=insight.updated_at.isoformat(),
                metrics=metrics_dict,
                feedback_count=feedback_count,
                customers=customers_list,
                total_acv=total_acv,
            )
        )

    return results


@router.get("/filter-counts", response_model=FilterCountsResponse)
async def get_filter_counts(db: Session = Depends(get_db)):
    """
    Get counts for each quick filter category.

    Returns:
        Counts for enterprise_blockers, high_priority, and trending filters
    """
    # Base query
    base_query = db.query(Insight).join(Insight.theme).join(Theme.metrics, isouter=True)

    # Count enterprise blockers
    enterprise_blockers_count = (
        base_query.filter(
            or_(
                Insight.severity == "critical",
                and_(Insight.severity == "high", ThemeMetrics.acv_sum >= 50000),
            )
        )
        .count()
    )

    # Count high priority
    high_priority_count = (
        base_query.filter(
            or_(Insight.priority_score >= 70, Insight.severity.in_(["high", "critical"]))
        )
        .count()
    )

    # Count trending
    trending_count = (
        base_query.filter(and_(ThemeMetrics.trend > 0, ThemeMetrics.freq_30d >= 3))
        .count()
    )

    return FilterCountsResponse(
        enterprise_blockers=enterprise_blockers_count,
        high_priority=high_priority_count,
        trending=trending_count,
    )


@router.get("/{insight_id}", response_model=InsightDetailResponse)
async def get_insight(insight_id: UUID, db: Session = Depends(get_db)):
    """
    Get detailed insight information with supporting feedback.

    Args:
        insight_id: Insight UUID
        db: Database session

    Returns:
        Detailed insight information with key quotes and supporting feedback
    """
    insight = (
        db.query(Insight)
        .filter(Insight.id == insight_id)
        .options(joinedload(Insight.theme).joinedload(Theme.metrics))
        .first()
    )

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Get key quotes (is_key_quote=1)
    key_quotes_data = (
        db.query(Feedback, InsightFeedback.relevance_score)
        .join(InsightFeedback, Feedback.id == InsightFeedback.feedback_id)
        .filter(InsightFeedback.insight_id == insight.id, InsightFeedback.is_key_quote == 1)
        .order_by(desc(InsightFeedback.relevance_score))
        .all()
    )

    key_quotes = [
        {
            "id": str(f.id),
            "text": f.text,
            "source": f.source.value,
            "source_id": f.source_id,
            "account": f.account,
            "created_at": f.created_at.isoformat(),
            "confidence": score,
            "meta": f.meta,
            "doc_url": f.doc_url,
            "speaker": f.speaker,
            "started_at": f.started_at.isoformat() if f.started_at else None,
            "ended_at": f.ended_at.isoformat() if f.ended_at else None,
        }
        for f, score in key_quotes_data
    ]

    # Get supporting feedback (is_key_quote=0)
    supporting_data = (
        db.query(Feedback, InsightFeedback.relevance_score)
        .join(InsightFeedback, Feedback.id == InsightFeedback.feedback_id)
        .filter(InsightFeedback.insight_id == insight.id, InsightFeedback.is_key_quote == 0)
        .order_by(desc(InsightFeedback.relevance_score))
        .limit(20)  # Limit supporting feedback
        .all()
    )

    supporting_feedback = [
        {
            "id": str(f.id),
            "text": f.text,
            "source": f.source.value,
            "source_id": f.source_id,
            "account": f.account,
            "created_at": f.created_at.isoformat(),
            "confidence": score,
            "meta": f.meta,
            "doc_url": f.doc_url,
            "speaker": f.speaker,
            "started_at": f.started_at.isoformat() if f.started_at else None,
            "ended_at": f.ended_at.isoformat() if f.ended_at else None,
        }
        for f, score in supporting_data
    ]

    # Count total feedback
    feedback_count = (
        db.query(func.count(InsightFeedback.feedback_id))
        .filter(InsightFeedback.insight_id == insight.id)
        .scalar()
    )

    # Get customers from IMMUTABLE affected_customers field (data integrity)
    # This ensures customer counts match what LLM saw during insight generation
    if insight.affected_customers:
        # Use immutable customer data stored at insight generation time
        customers_list = [
            CustomerInfo(
                id=c["id"],
                name=c["name"],
                segment=c["segment"],
                acv=c["acv"],
            )
            for c in insight.affected_customers
        ]
        total_acv = sum(c["acv"] for c in insight.affected_customers)
    else:
        # Fallback for insights created before immutable fields (backward compatibility)
        customer_ids_subq = (
            db.query(Customer.id.distinct())
            .join(Feedback, Feedback.customer_id == Customer.id)
            .join(InsightFeedback, InsightFeedback.feedback_id == Feedback.id)
            .filter(InsightFeedback.insight_id == insight.id)
            .subquery()
        )

        customers_data = (
            db.query(Customer)
            .filter(Customer.id.in_(customer_ids_subq))
            .all()
        )

        customers_list = [
            CustomerInfo(
                id=str(c.id),
                name=c.name,
                segment=c.segment.value,
                acv=c.acv or 0.0,
            )
            for c in customers_data
        ]
        total_acv = sum(c.acv or 0.0 for c in customers_data)

    # Get theme metrics
    metrics_dict = None
    if insight.theme.metrics:
        metrics_dict = {
            "freq_30d": insight.theme.metrics.freq_30d,
            "freq_90d": insight.theme.metrics.freq_90d,
            "acv_sum": insight.theme.metrics.acv_sum,
            "sentiment": insight.theme.metrics.sentiment,
            "trend": insight.theme.metrics.trend,
            "dup_penalty": insight.theme.metrics.dup_penalty,
            "score": insight.theme.metrics.score,
        }

    return InsightDetailResponse(
        id=str(insight.id),
        theme_id=str(insight.theme_id) if insight.theme_id else None,
        title=insight.title,
        description=insight.description,
        impact=insight.impact,
        recommendation=insight.recommendation,
        severity=insight.severity or "medium",
        effort=insight.effort or "medium",
        priority_score=insight.priority_score,
        created_at=insight.created_at.isoformat(),
        updated_at=insight.updated_at.isoformat(),
        metrics=metrics_dict,
        feedback_count=feedback_count,
        customers=customers_list,
        total_acv=total_acv,
        key_quotes=key_quotes,
        supporting_feedback=supporting_feedback,
    )


@router.get("/{insight_id}/generate-prd")
async def generate_prd(insight_id: UUID, db: Session = Depends(get_db)):
    """
    Generate a comprehensive PRD (Product Requirements Document) for an insight.

    Auto-generates 13 sections from existing data:
    1. Problem & Goal
    2. Who
    3. Voice of Customer
    4. Hypothesis
    5. Use cases
    6. Solution
    7. Scope
    8. Acceptance criteria
    9. Success metrics
    10. Experiment plan
    11. GTM
    12. Dependencies & risks
    13. Open questions

    Args:
        insight_id: Insight UUID
        db: Database session

    Returns:
        Markdown-formatted PRD with evidence-backed content
    """
    # Get insight with all related data
    insight = (
        db.query(Insight)
        .filter(Insight.id == insight_id)
        .options(joinedload(Insight.theme).joinedload(Theme.metrics))
        .first()
    )

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Get customers from IMMUTABLE affected_customers field (data integrity)
    # This ensures customer counts match what LLM saw during insight generation
    if insight.affected_customers:
        # Use immutable customer data - convert dict to object-like for compatibility
        from types import SimpleNamespace
        customers_data = [SimpleNamespace(**c) for c in insight.affected_customers]
    else:
        # Fallback for insights created before immutable fields (backward compatibility)
        customer_ids_subq = (
            db.query(Customer.id.distinct())
            .join(Feedback, Feedback.customer_id == Customer.id)
            .join(InsightFeedback, InsightFeedback.feedback_id == Feedback.id)
            .filter(InsightFeedback.insight_id == insight.id)
            .subquery()
        )

        customers_data = (
            db.query(Customer)
            .filter(Customer.id.in_(customer_ids_subq))
            .all()
        )

    # Get key quotes
    key_quotes_data = (
        db.query(Feedback, InsightFeedback.relevance_score)
        .join(InsightFeedback, Feedback.id == InsightFeedback.feedback_id)
        .filter(InsightFeedback.insight_id == insight.id, InsightFeedback.is_key_quote == 1)
        .order_by(desc(InsightFeedback.relevance_score))
        .all()
    )

    # Get metrics
    metrics = insight.theme.metrics if insight.theme.metrics else None

    # Calculate key metrics
    total_customers = len(customers_data)
    total_acv = sum(c.acv or 0.0 for c in customers_data)
    freq_30d = metrics.freq_30d if metrics else 0

    # Format ACV with proper US currency format
    def format_acv(amount: float) -> str:
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}k"
        else:
            return f"${amount:.0f}"

    total_acv_formatted = format_acv(total_acv)

    # Group customers by segment
    segment_groups = {"ENT": [], "MM": [], "SMB": []}
    for c in customers_data:
        segment_groups[c.segment.value].append(c)

    # Calculate segment breakdown
    segment_breakdown = []
    for segment in ["ENT", "MM", "SMB"]:
        customers = segment_groups[segment]
        if customers:
            count = len(customers)
            acv = sum(c.acv or 0.0 for c in customers)
            segment_breakdown.append(f"{count} {segment} ({format_acv(acv)})")

    segment_mix = ", ".join(segment_breakdown) if segment_breakdown else "No segment data"

    # Top 3 priority accounts
    top_accounts = sorted(customers_data, key=lambda x: x.acv or 0, reverse=True)[:3]
    top_accounts_list = []
    for i, c in enumerate(top_accounts, 1):
        top_accounts_list.append(f"{i}. {c.name} ({c.segment.value}, {format_acv(c.acv or 0.0)})")

    # Format key quotes for VoC section
    voc_quotes = []
    for f, score in key_quotes_data[:3]:  # Top 3 quotes
        customer = db.query(Customer).filter(Customer.id == f.customer_id).first()
        customer_name = customer.name if customer else "Unknown"
        customer_segment = customer.segment.value if customer else "Unknown"
        customer_acv_fmt = format_acv(customer.acv) if customer and customer.acv else "$0"
        date = f.created_at.strftime("%b %d")

        voc_quotes.append(f'"{f.text}" — {customer_name}, {customer_segment} {customer_acv_fmt}, {date}')

    # Derive hypothesis from severity and effort
    severity_map = {
        "critical": "Resolving this will significantly reduce churn risk and unlock expansion opportunities",
        "high": "Addressing this will improve customer satisfaction and product-market fit",
        "medium": "Implementing this will enhance user experience and competitive positioning",
        "low": "This improvement will optimize workflows and increase product value"
    }
    hypothesis_text = severity_map.get(insight.severity or "medium", severity_map["medium"])

    # Generate use cases based on customer segments
    use_cases = []
    if segment_groups["ENT"]:
        use_cases.append(f"Enterprise teams ({len(segment_groups['ENT'])} accounts) need this to maintain compliance and scale operations")
    if segment_groups["MM"]:
        use_cases.append(f"Mid-market companies ({len(segment_groups['MM'])} accounts) need this to improve team productivity")
    if segment_groups["SMB"]:
        use_cases.append(f"SMB users ({len(segment_groups['SMB'])} accounts) need this to reduce manual work")

    if not use_cases:
        use_cases.append("Users across all segments need this capability to achieve their goals efficiently")

    # Success metrics based on severity
    success_metrics = []
    if insight.severity in ["critical", "high"]:
        success_metrics.extend([
            f"NPS improvement from affected {total_customers} accounts",
            "Reduction in support tickets related to this issue",
            f"Retention rate improvement for {total_acv_formatted} ACV at risk"
        ])
    else:
        success_metrics.extend([
            "Adoption rate among target customer segments",
            "Time saved per user workflow",
            "Feature satisfaction score (CSAT)"
        ])

    # GTM considerations based on ACV and segment
    gtm_approach = []
    if total_acv >= 500_000:
        gtm_approach.append("White-glove rollout to top 3 enterprise accounts with dedicated CSM support")
    if segment_groups["ENT"]:
        gtm_approach.append("Enterprise early access program with executive briefings")
    gtm_approach.append("Product marketing asset creation (blog post, demo video, changelog)")
    gtm_approach.append("Customer enablement via in-app tooltips and documentation")

    # Effort to timeline mapping
    effort_to_timeline = {
        "low": "1-2 weeks",
        "medium": "3-4 weeks",
        "high": "6-8 weeks"
    }
    timeline_estimate = effort_to_timeline.get(insight.effort or "medium", "3-4 weeks")

    # Effort to beta duration mapping
    effort_to_beta = {
        "low": "1 week",
        "medium": "2 weeks",
        "high": "3 weeks"
    }
    beta_duration = effort_to_beta.get(insight.effort or "medium", "2 weeks")

    # Affected segments for acceptance criteria
    affected_segments = ", ".join([seg for seg in ["ENT", "MM", "SMB"] if segment_groups[seg]])

    # Build comprehensive PRD
    prd_markdown = f"""# {insight.title}

*Generated: {datetime.utcnow().strftime("%b %d, %Y")}* | *Priority: {insight.priority_score}/100* | *Severity: {(insight.severity or 'medium').upper()}*

**TL;DR**: {total_customers} customers ({total_acv_formatted} ACV) reported {freq_30d}× in 30d. {segment_mix}.

---

## Problem & Goal

{insight.description or "Customer feedback indicates a critical gap in our current product that creates friction in workflows and impacts satisfaction."}

**Goal**: {insight.impact or "Deliver capability that resolves customer pain points and improves product-market fit"}

---

## Who

- **Total impact**: {total_customers} customers, {total_acv_formatted} ACV
- **Segment mix**: {segment_mix}
- **Frequency**: {freq_30d} mentions in last 30 days
- **Top accounts**: {", ".join([c.name for c in top_accounts[:3]])}

**Priority accounts**:
{chr(10).join(top_accounts_list) if top_accounts_list else "No priority accounts identified"}

---

## Voice of Customer

**Theme**: {insight.theme.label if insight.theme else "User feedback"}

{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(voc_quotes)]) if voc_quotes else "No key quotes available"}

[View full evidence →](http://localhost:3000/insights/{insight_id})

---

## Hypothesis

{hypothesis_text}. Expected impact: improved retention for {total_acv_formatted} ACV, reduced churn risk, and increased expansion opportunities.

---

## Use cases

{chr(10).join([f"{i+1}. {uc}" for i, uc in enumerate(use_cases)])}

---

## Solution

**Recommended approach**: {insight.recommendation or "Conduct discovery with top 3 affected customers to validate requirements, then design MVP solution with eng team"}

**Effort estimate**: {(insight.effort or 'medium').upper()} - Estimated {timeline_estimate}

---

## Scope

**MVP** (Must-have):
- Core functionality addressing primary pain point from customer feedback
- Integration with existing workflows
- Basic success metrics tracking

**Next** (Should-have):
- Advanced configuration options requested by enterprise accounts
- Enhanced reporting and analytics
- Mobile/API support if mentioned in feedback

**Not in scope**:
- Features not validated by customer evidence
- Capabilities requiring separate architectural decisions
- Items with <3 customer requests

---

## Acceptance criteria

- [ ] Resolves specific pain points mentioned in top 3 customer quotes
- [ ] Tested with at least 1 account from each affected segment ({affected_segments})
- [ ] Performance meets SLA requirements (sub-second response time)
- [ ] Documentation and help resources published
- [ ] Success metrics instrumentation deployed

---

## Success metrics

**Primary**:
{chr(10).join([f"- {m}" for m in success_metrics])}

**Secondary**:
- Feature adoption rate week-over-week
- Customer satisfaction feedback from beta users

---

## Experiment plan

1. **Beta phase** ({beta_duration}): Deploy to 3-5 friendly accounts, gather feedback
2. **Iterate**: Address critical issues found in beta
3. **GA rollout**: Phased release to all affected customers with monitoring

---

## GTM

{chr(10).join([f"- {g}" for g in gtm_approach])}

---

## Dependencies & risks

**Dependencies**:
- Engineering capacity: {(insight.effort or 'medium').upper()} effort estimate
- Design review if UI changes required
- QA test coverage for affected workflows

**Risks**:
- Scope creep if additional requirements emerge during beta
- Technical complexity may extend timeline
- Adoption risk if change management not handled properly

**Mitigation**: Maintain tight scope control, over-communicate with stakeholders, run thorough beta program

---

## Open questions

- What is the exact technical approach? (Requires eng discovery)
- Are there any compliance/security considerations?
- Do we need data migration for existing customer data?
- What is the competitive landscape for this capability?

---

*Auto-generated from ProductAI insights. Data sources: {len(key_quotes_data)} key quotes, {freq_30d} feedback items, {total_customers} customer accounts.*
"""

    return {"prd_markdown": prd_markdown, "insight_id": str(insight_id)}


@router.get("/{insight_id}/generate-ai-prompt")
async def generate_ai_prototype_prompt(
    insight_id: UUID,
    prototype_type: str = Query(default="mvp", enum=["ui_component", "feature_flow", "mvp", "technical_poc"]),
    db: Session = Depends(get_db)
):
    """
    Generate structured AI prototype prompt from insight data.

    Args:
        insight_id: Insight UUID
        prototype_type: Type of prototype to generate
        db: Database session

    Returns:
        Structured prompt for AI prototyping tools with tool recommendation
    """
    # Get insight with all related data
    insight = (
        db.query(Insight)
        .filter(Insight.id == insight_id)
        .options(joinedload(Insight.theme).joinedload(Theme.metrics))
        .first()
    )

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Get customers from IMMUTABLE affected_customers field (data integrity)
    # This ensures customer counts match what LLM saw during insight generation
    if insight.affected_customers:
        # Use immutable customer data - convert dict to object-like for compatibility
        from types import SimpleNamespace
        customers_data = [SimpleNamespace(**c) for c in insight.affected_customers]
    else:
        # Fallback for insights created before immutable fields (backward compatibility)
        customer_ids_subq = (
            db.query(Customer.id.distinct())
            .join(Feedback, Feedback.customer_id == Customer.id)
            .join(InsightFeedback, InsightFeedback.feedback_id == Feedback.id)
            .filter(InsightFeedback.insight_id == insight.id)
            .subquery()
        )

        customers_data = (
            db.query(Customer)
            .filter(Customer.id.in_(customer_ids_subq))
            .all()
        )

    # Get key quotes
    key_quotes_data = (
        db.query(Feedback, InsightFeedback.relevance_score)
        .join(InsightFeedback, Feedback.id == InsightFeedback.feedback_id)
        .filter(InsightFeedback.insight_id == insight.id, InsightFeedback.is_key_quote == 1)
        .order_by(desc(InsightFeedback.relevance_score))
        .limit(3)
        .all()
    )

    # Calculate metrics
    total_customers = len(customers_data)
    total_acv = sum(c.acv or 0.0 for c in customers_data)

    def format_acv(amount: float) -> str:
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}k"
        else:
            return f"${amount:.0f}"

    total_acv_formatted = format_acv(total_acv)

    # Group by segment
    segment_groups = {"ENT": [], "MM": [], "SMB": []}
    for c in customers_data:
        segment_groups[c.segment.value].append(c)

    # Format customer evidence
    customer_evidence = []
    for f, score in key_quotes_data:
        customer = db.query(Customer).filter(Customer.id == f.customer_id).first()
        if customer:
            customer_evidence.append(
                f'"{f.text}" — {customer.name}, {customer.segment.value} {format_acv(customer.acv or 0)}'
            )

    # Extract potential integrations from feedback
    all_feedback = [f.text.lower() for f, _ in key_quotes_data]
    integrations = []
    integration_keywords = {
        "salesforce", "hubspot", "marketo", "slack", "teams", "microsoft teams",
        "google", "zoom", "jira", "confluence", "notion", "linear"
    }
    for keyword in integration_keywords:
        if any(keyword in feedback for feedback in all_feedback):
            integrations.append(keyword.title())

    # Recommend tool based on insight characteristics
    def recommend_tool():
        if prototype_type == "ui_component":
            return "v0", "Best for UI components and design system elements"
        elif prototype_type == "technical_poc":
            return "Bolt", "Best for quick technical proof-of-concept"
        elif total_acv >= 500_000 or any(segment_groups["ENT"]):
            return "Lovable", "High-value feature for Enterprise accounts requires production-quality MVP"
        elif insight.severity in ["critical", "high"]:
            return "Lovable", "High-severity feature requires full-stack MVP with backend"
        else:
            return "Bolt", "Best for quick functional demo and validation"

    recommended_tool, recommendation_reason = recommend_tool()

    # Generate prototype type description
    prototype_descriptions = {
        "ui_component": "a UI component prototype (layout, navigation, form elements)",
        "feature_flow": "a feature flow prototype (multi-step workflow)",
        "mvp": "a functional MVP (end-to-end feature with backend)",
        "technical_poc": "a technical proof-of-concept (validate feasibility)"
    }

    # Effort to timeline mapping
    effort_timeline = {
        "low": "1-2 weeks",
        "medium": "3-4 weeks",
        "high": "6-8 weeks"
    }
    timeline_str = effort_timeline.get(insight.effort or "medium", "3-4 weeks")

    # Target users string
    target_users_list = [f'{len(segment_groups[seg])} {seg}' for seg in ["ENT", "MM", "SMB"] if segment_groups[seg]]
    target_users_str = ", ".join(target_users_list)

    # Target segments string
    target_segments_str = ", ".join([seg for seg in ["ENT", "MM", "SMB"] if segment_groups[seg]])

    # Top customer names for testing
    top_customer_names = ", ".join([c.name for c in sorted(customers_data, key=lambda x: x.acv or 0, reverse=True)[:3]])

    # Build structured prompt
    prototype_prompt = f"""# Build: {insight.title}

## Context
Create {prototype_descriptions[prototype_type]} based on validated customer feedback from {total_customers} account{"s" if total_customers != 1 else ""} ({total_acv_formatted} ACV).

## User Problem
{insight.description or "Customer feedback indicates a critical gap that needs to be addressed."}

## Customer Evidence
{chr(10).join(customer_evidence) if customer_evidence else "Multiple customers have reported this issue"}

## Requirements
- Severity: {(insight.severity or "medium").upper()} priority
- Estimated effort: {(insight.effort or "medium").upper()} ({timeline_str})
- Target segments: {target_segments_str}
- Must be production-ready: {"Yes - Enterprise customers" if segment_groups["ENT"] else "Start simple, iterate"}

## Design Constraints
- Target users: {target_users_str}
- {f"Must integrate with: {', '.join(integrations)}" if integrations else "Consider integration points mentioned in feedback"}
- {"Focus on compliance and security (Enterprise users)" if segment_groups["ENT"] else "Focus on ease of use and quick setup"}

## Success Criteria
- Solves the core problem described in customer evidence
- {"Handles enterprise-scale requirements (SSO, permissions, audit logs)" if segment_groups["ENT"] else "Quick to set up and use"}
- Can be validated with {min(3, total_customers)} customer{"s" if min(3, total_customers) != 1 else ""}

## Recommended Approach
{insight.recommendation or "Start with user interviews to validate requirements, then design and build MVP iteratively"}

---

**Next Steps:**
1. Review the customer evidence and requirements above
2. Design 2-3 UI variations for the main workflow
3. Implement core functionality based on highest-priority requirements
4. Prepare for customer testing with {top_customer_names}
"""

    return {
        "prompt": prototype_prompt,
        "recommended_tool": recommended_tool,
        "recommendation_reason": recommendation_reason,
        "insight_id": str(insight_id),
        "metadata": {
            "total_customers": total_customers,
            "total_acv": total_acv_formatted,
            "severity": insight.severity or "medium",
            "effort": insight.effort or "medium",
            "has_enterprise_customers": len(segment_groups["ENT"]) > 0,
            "integrations": integrations
        }
    }
