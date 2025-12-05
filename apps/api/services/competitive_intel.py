"""Competitive Intelligence Agent Service.

Uses Claude API with citations to research competitors and generate insight cards
following the PM-focused system prompt.
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

import anthropic
import structlog
from sqlalchemy.orm import Session

from apps.api.models import (
    Competitor,
    CompetitorStatus,
    CompetitiveInsightMetadata,
    Insight,
    InsightCategory,
    ResearchSession,
)

logger = structlog.get_logger()


@dataclass
class CompetitiveInsightCard:
    """Structured competitive insight card."""

    title: str
    summary: str
    impact: str
    recommendation: str
    competitor_name: str
    competitor_moves: List[dict]

    # Severity and effort
    severity: str  # high, medium, low
    effort: str  # low, medium, high
    priority_score: int  # 0-100

    # Metrics
    evidence_count: str
    mentions_30d: str
    impacted_acv_usd: Optional[str]
    est_method: str

    # Computed scores
    severity_weight: float
    urgency_score: float
    reach_score: float
    confidence_score: float
    effort_inverse: float

    # Citations
    citations: List[dict]


class CompetitiveIntelligenceAgent:
    """Agent that researches competitors and generates PM-ready insight cards."""

    SYSTEM_PROMPT = """You are a Competitive Intelligence Agent for Product Managers.
Research competitors and turn findings into actionable insight cards that PMs can take straight to planning.

Your job:
1. Research the specified competitors within the given market scope and time window
2. Identify dated product moves (releases, AI features, data/coverage, privacy/compliance, integrations, pricing changes)
3. Synthesize insight candidates: "Competitor move → user expectations → gap/opportunity"
4. Compute metrics (evidence_count, mentions_30d, P-score formula)
5. Output structured insight cards with clear IMPACT and RECOMMENDATION sections
6. Cite every non-obvious claim with publisher, URL, published_date, and accessed_date

Severity levels:
- High: Security/compliance, parity blocker, or exec mandate
- Medium: Competitive disadvantage/CSAT drag
- Low: Nice-to-have

Effort levels:
- Low: ≤ 2 sprints
- Medium: 1-2 quarters
- High: > 2 quarters / net-new platform work

P-score formula (0-100):
P = 30*severity_weight + 25*urgency + 20*reach + 15*confidence + 10*effort_inverse
Where:
- severity_weight: High=1, Med=0.66, Low=0.33
- urgency: recent activity intensity (0-1) from mentions_30d normalized
- reach: share of personas/segments impacted (0-1)
- confidence: source quality & agreement (0-1)
- effort_inverse: Low=1, Med=0.5, High=0.2

Never guess ACV; if unknown, set null and note "not_available_web_only" in est_method.

Output Format:
Return a JSON array of insight cards, each with:
{
  "title": "...",
  "summary": "1-line summary",
  "impact": "What happens to customers/business if we don't act",
  "recommendation": "3-5 numbered steps including build/buy/partner options",
  "competitor_name": "...",
  "competitor_moves": [{"move": "...", "date": "...", "source_url": "..."}],
  "severity": "high|medium|low",
  "effort": "low|medium|high",
  "evidence_count": "X unique sources",
  "mentions_30d": "X items",
  "impacted_acv_usd": null or "$X",
  "est_method": "not_available_web_only" or how ACV was estimated,
  "severity_weight": 0.0-1.0,
  "urgency_score": 0.0-1.0,
  "reach_score": 0.0-1.0,
  "confidence_score": 0.0-1.0,
  "effort_inverse": 0.2-1.0,
  "priority_score": 0-100,
  "citations": [{"title": "...", "url": "...", "publisher": "...", "published_date": "...", "accessed_date": "..."}]
}
"""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API key."""
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    async def process_manual_input(
        self,
        db: Session,
        company_name: str,
        market_scope: str,
        target_personas: List[str],
        geo_segments: List[str],
        competitor_data: List[dict],  # PM-provided competitor data
        time_window_months: str = "12",
    ) -> ResearchSession:
        """
        Process manual competitor input from PM and format into insight cards.

        Manual Mode (Option C): PM provides competitor data, agent formats as insight cards.

        Args:
            db: Database session
            company_name: Your company name
            market_scope: e.g., "B2B sales intelligence"
            target_personas: ["SDR", "AE", "RevOps"]
            geo_segments: ["NA", "EU", "SMB", "ENT"]
            competitor_data: List of dicts with competitor info provided by PM:
                [{
                    "name": "Competitor Name",
                    "moves": [{"move": "...", "date": "...", "source_url": "..."}],
                    "description": "Context about this competitor move"
                }]
            time_window_months: How far back to look (default 12)

        Returns:
            ResearchSession with generated insights
        """
        competitor_names = [c["name"] for c in competitor_data]

        logger.info(
            "Processing manual competitive intelligence input",
            company=company_name,
            competitors=competitor_names,
            manual_mode=True,
        )

        # Create research session
        session = ResearchSession(
            id=uuid4(),
            company_name=company_name,
            market_scope=market_scope,
            target_personas=target_personas,
            geo_segments=geo_segments,
            time_window_months=time_window_months,
            competitors_researched=competitor_names,
            status="running",
        )
        db.add(session)
        db.commit()

        try:
            # Build manual mode prompt with PM-provided data
            research_prompt = self._build_manual_prompt(
                company_name=company_name,
                market_scope=market_scope,
                target_personas=target_personas,
                geo_segments=geo_segments,
                competitor_data=competitor_data,
                time_window_months=time_window_months,
            )

            # Call Claude API to format as insight cards
            logger.info("Calling Claude API to format manual input into insight cards")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": research_prompt
                    }
                ]
            )

            # Extract insight cards from response
            insight_cards = self._parse_insight_cards(response.content)

            # Create Insight records in database
            insight_ids = []
            for card in insight_cards:
                insight_id = await self._create_insight_record(db, card, session.id)
                insight_ids.append(str(insight_id))

            # Update session
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            session.insights_generated = insight_ids
            db.commit()

            logger.info(
                "Manual input processing completed successfully",
                session_id=session.id,
                insights_count=len(insight_ids),
            )

            return session

        except Exception as e:
            logger.error("Manual input processing failed", error=str(e), session_id=session.id)
            session.status = "failed"
            session.error_message = str(e)
            session.completed_at = datetime.utcnow()
            db.commit()
            raise

    async def run_research(
        self,
        db: Session,
        company_name: str,
        market_scope: str,
        target_personas: List[str],
        geo_segments: List[str],
        competitor_names: List[str],
        time_window_months: str = "12",
    ) -> ResearchSession:
        """
        Run competitive intelligence research session.

        Args:
            db: Database session
            company_name: Your company name
            market_scope: e.g., "B2B sales intelligence"
            target_personas: ["SDR", "AE", "RevOps"]
            geo_segments: ["NA", "EU", "SMB", "ENT"]
            competitor_names: List of competitors to research
            time_window_months: How far back to look (default 12)

        Returns:
            ResearchSession with generated insights
        """
        logger.info(
            "Starting competitive research",
            company=company_name,
            competitors=competitor_names,
            market_scope=market_scope,
        )

        # Create research session
        session = ResearchSession(
            id=uuid4(),
            company_name=company_name,
            market_scope=market_scope,
            target_personas=target_personas,
            geo_segments=geo_segments,
            time_window_months=time_window_months,
            competitors_researched=competitor_names,
            status="running",
        )
        db.add(session)
        db.commit()

        try:
            # Build research prompt
            research_prompt = self._build_research_prompt(
                company_name=company_name,
                market_scope=market_scope,
                target_personas=target_personas,
                geo_segments=geo_segments,
                competitor_names=competitor_names,
                time_window_months=time_window_months,
            )

            # Call Claude API for competitive research
            logger.info("Calling Claude API for competitive research")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": research_prompt
                    }
                ]
            )

            # Extract insight cards from response
            insight_cards = self._parse_insight_cards(response.content)

            # Create Insight records in database
            insight_ids = []
            for card in insight_cards:
                insight_id = await self._create_insight_record(db, card, session.id)
                insight_ids.append(str(insight_id))

            # Update session
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            session.insights_generated = insight_ids
            db.commit()

            logger.info(
                "Research completed successfully",
                session_id=session.id,
                insights_count=len(insight_ids),
            )

            return session

        except Exception as e:
            logger.error("Research failed", error=str(e), session_id=session.id)
            session.status = "failed"
            session.error_message = str(e)
            session.completed_at = datetime.utcnow()
            db.commit()
            raise

    def _build_manual_prompt(
        self,
        company_name: str,
        market_scope: str,
        target_personas: List[str],
        geo_segments: List[str],
        competitor_data: List[dict],
        time_window_months: str,
    ) -> str:
        """Build prompt for manual mode (PM provides data, agent formats)."""

        # Format competitor data for the prompt
        competitors_formatted = []
        for comp in competitor_data:
            moves_formatted = "\n    ".join([
                f"- {move.get('move', 'N/A')} (Date: {move.get('date', 'Unknown')}, Source: {move.get('source_url', 'N/A')})"
                for move in comp.get("moves", [])
            ])
            competitors_formatted.append(f"""
Competitor: {comp.get('name', 'Unknown')}
Description: {comp.get('description', 'N/A')}
Recent Moves:
    {moves_formatted}
""")

        return f"""MANUAL MODE: The PM has provided competitor data below. Your job is to:
1. Analyze the competitor moves provided
2. Synthesize insight candidates: "Competitor move → user expectations → gap/opportunity for {company_name}"
3. Compute all metrics (evidence_count, mentions_30d, P-score)
4. Format into structured PM-ready insight cards

Research Parameters:
COMPANY: {company_name}
MARKET_SCOPE: {market_scope}
PERSONAS: {', '.join(target_personas)}
GEOS_SEGMENTS: {', '.join(geo_segments)}
TIME_WINDOW: last {time_window_months} months

PM-PROVIDED COMPETITOR DATA:
{"".join(competitors_formatted)}

Instructions:
1. For each competitor move, create an insight card that explains:
   - What the competitor did
   - What this means for user expectations in the market
   - What gap/opportunity this creates for {company_name}
2. Compute P-scores using the formula (severity, urgency, reach, confidence, effort)
3. Provide clear IMPACT and RECOMMENDATION sections for each insight
4. Use the source URLs provided as citations
5. Output a JSON array of properly formatted insight cards

Focus on making these insights actionable for {company_name} PMs.
"""

    def _build_research_prompt(
        self,
        company_name: str,
        market_scope: str,
        target_personas: List[str],
        geo_segments: List[str],
        competitor_names: List[str],
        time_window_months: str,
    ) -> str:
        """Build the research prompt for Claude (Auto mode with web search)."""
        if competitor_names:
            # Competitors provided - research them
            competitor_instruction = f"""
COMPETITORS TO RESEARCH: {', '.join(competitor_names)}

1. For each competitor, research their recent product moves in the {market_scope} space
2. Look for: product launches, AI features, pricing changes, integrations, security/compliance updates
3. Focus on moves within the last {time_window_months} months (prioritize last 90 days)
"""
        else:
            # No competitors provided - identify and research them
            competitor_instruction = f"""
COMPETITOR IDENTIFICATION:

1. First, identify 3-5 top competitors for {company_name} in the {market_scope} market
2. Consider both direct competitors and adjacent players encroaching on this space
3. Then research each competitor's recent product moves (last {time_window_months} months)
4. Look for: product launches, AI features, pricing changes, integrations, security/compliance updates
"""

        return f"""AUTO RESEARCH MODE: Use your web search capabilities to research competitors and generate insights.

Research Parameters:
COMPANY: {company_name}
MARKET_SCOPE: {market_scope}
PERSONAS: {', '.join(target_personas)}
GEOS_SEGMENTS: {', '.join(geo_segments)}
TIME_WINDOW: last {time_window_months} months (highlight last 90 days)

{competitor_instruction}

Instructions:
1. Use web search to find recent, dated sources about competitor product moves
2. For each significant competitor move, create an insight card that explains:
   - What the competitor did (with specific dates)
   - What this means for user expectations in the {market_scope} market
   - What gap/opportunity this creates for {company_name}
   - Clear IMPACT on {company_name}'s business
   - Actionable RECOMMENDATION with specific steps
3. Compute P-scores using the formula (severity, urgency, reach, confidence, effort)
4. Cite every claim with publisher, URL, published_date, and accessed_date
5. Output a JSON array of properly formatted insight cards

Focus on making these insights immediately actionable for {company_name} PMs to use in roadmap planning.
Prioritize recent moves (last 90 days) and high-impact competitive threats.
"""

    def _parse_insight_cards(self, content: List) -> List[CompetitiveInsightCard]:
        """Parse Claude's response into structured insight cards."""
        insight_cards = []

        # Extract JSON from response content
        for block in content:
            if block.type == "text":
                text = block.text
                # Find JSON array in the response
                json_match = re.search(r'\[.*\]', text, re.DOTALL)
                if json_match:
                    try:
                        cards_data = json.loads(json_match.group())
                        for card_data in cards_data:
                            card = CompetitiveInsightCard(
                                title=card_data.get("title", ""),
                                summary=card_data.get("summary", ""),
                                impact=card_data.get("impact", ""),
                                recommendation=card_data.get("recommendation", ""),
                                competitor_name=card_data.get("competitor_name", ""),
                                competitor_moves=card_data.get("competitor_moves", []),
                                severity=card_data.get("severity", "medium"),
                                effort=card_data.get("effort", "medium"),
                                priority_score=card_data.get("priority_score", 50),
                                evidence_count=card_data.get("evidence_count", "0"),
                                mentions_30d=card_data.get("mentions_30d", "0"),
                                impacted_acv_usd=card_data.get("impacted_acv_usd"),
                                est_method=card_data.get("est_method", "not_available_web_only"),
                                severity_weight=card_data.get("severity_weight", 0.5),
                                urgency_score=card_data.get("urgency_score", 0.5),
                                reach_score=card_data.get("reach_score", 0.5),
                                confidence_score=card_data.get("confidence_score", 0.5),
                                effort_inverse=card_data.get("effort_inverse", 0.5),
                                citations=card_data.get("citations", []),
                            )
                            insight_cards.append(card)
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse insight cards JSON", error=str(e))

        return insight_cards

    async def _create_insight_record(
        self,
        db: Session,
        card: CompetitiveInsightCard,
        session_id: UUID,
    ) -> UUID:
        """Create Insight and CompetitiveInsightMetadata records."""
        # Create Insight record
        insight = Insight(
            id=uuid4(),
            category=InsightCategory.competitive_intel,
            theme_id=None,  # Competitive insights don't have themes
            title=card.title,
            description=card.summary,
            impact=card.impact,
            recommendation=card.recommendation,
            severity=card.severity,
            effort=card.effort,
            priority_score=card.priority_score,
            affected_customers=[],  # Competitive insights don't have direct customer links
        )
        db.add(insight)

        # Create CompetitiveInsightMetadata record
        metadata = CompetitiveInsightMetadata(
            id=uuid4(),
            insight_id=insight.id,
            competitor_name=card.competitor_name,
            competitor_moves=card.competitor_moves,
            evidence_count=card.evidence_count,
            mentions_30d=card.mentions_30d,
            impacted_acv_usd=card.impacted_acv_usd,
            est_method=card.est_method,
            severity_weight=str(card.severity_weight),
            urgency_score=str(card.urgency_score),
            reach_score=str(card.reach_score),
            confidence_score=str(card.confidence_score),
            effort_inverse=str(card.effort_inverse),
            citations=card.citations,
            research_session_id=session_id,
        )
        db.add(metadata)
        db.commit()

        logger.info(
            "Created competitive insight",
            insight_id=insight.id,
            competitor=card.competitor_name,
            priority=card.priority_score,
        )

        return insight.id
