"""PM Copilot Agent - AI assistant for product managers."""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from apps.api.config import get_settings
from apps.api.models import Insight, Theme, ThemeMetrics, Feedback, InsightFeedback

logger = logging.getLogger(__name__)
settings = get_settings()


class PMCopilotAgent:
    """AI agent that helps PMs make data-driven decisions."""

    def __init__(self):
        """Initialize PM Copilot agent."""
        self.has_openai = bool(settings.openai_api_key)
        if self.has_openai:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.openai_api_key)
                logger.info("PMCopilotAgent initialized with OpenAI")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")
                self.has_openai = False

        if not self.has_openai:
            logger.info("PMCopilotAgent initialized without OpenAI (fallback mode)")

    def chat(
        self,
        user_message: str,
        db: Session,
        selected_insight_id: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """
        Process user message and generate AI response.

        Args:
            user_message: The user's question
            db: Database session
            selected_insight_id: Optional ID of currently selected insight
            conversation_history: Previous messages for context

        Returns:
            AI-generated response
        """
        # Gather context from database
        context = self._gather_context(db, selected_insight_id)

        if self.has_openai:
            return self._generate_llm_response(
                user_message, context, conversation_history
            )
        else:
            return self._generate_fallback_response(user_message, context)

    def _gather_context(
        self, db: Session, selected_insight_id: Optional[str] = None
    ) -> dict:
        """Gather relevant data from database to provide context to AI."""
        context = {}

        # Get all insights with metrics, sorted by priority
        insights_query = (
            db.query(Insight)
            .join(Insight.theme)
            .join(Theme.metrics, isouter=True)
            .order_by(desc(Insight.priority_score))
            .limit(20)
        )
        insights = insights_query.all()

        # Structure insights data
        context["insights"] = []
        for insight in insights:
            insight_data = {
                "id": str(insight.id),
                "title": insight.title,
                "description": insight.description,
                "severity": insight.severity,
                "effort": insight.effort,
                "priority_score": insight.priority_score,
            }

            if insight.theme.metrics:
                insight_data["metrics"] = {
                    "freq_30d": insight.theme.metrics.freq_30d,
                    "freq_90d": insight.theme.metrics.freq_90d,
                    "acv_sum": insight.theme.metrics.acv_sum,
                    "trend": insight.theme.metrics.trend,
                    "score": insight.theme.metrics.score,
                }

            # Count feedback
            feedback_count = (
                db.query(func.count(InsightFeedback.feedback_id))
                .filter(InsightFeedback.insight_id == insight.id)
                .scalar()
            )
            insight_data["feedback_count"] = feedback_count

            context["insights"].append(insight_data)

        # If specific insight is selected, get detailed info
        if selected_insight_id:
            selected_insight = (
                db.query(Insight)
                .filter(Insight.id == selected_insight_id)
                .first()
            )
            if selected_insight:
                context["selected_insight"] = {
                    "id": str(selected_insight.id),
                    "title": selected_insight.title,
                    "description": selected_insight.description,
                    "impact": selected_insight.impact,
                    "recommendation": selected_insight.recommendation,
                    "severity": selected_insight.severity,
                    "effort": selected_insight.effort,
                    "priority_score": selected_insight.priority_score,
                }

                # Get customer accounts affected
                feedback_items = (
                    db.query(Feedback)
                    .join(InsightFeedback)
                    .filter(InsightFeedback.insight_id == selected_insight_id)
                    .all()
                )
                affected_customers = list(
                    set([f.account for f in feedback_items if f.account])
                )
                context["selected_insight"]["affected_customers"] = affected_customers

        # Summary statistics
        context["summary"] = {
            "total_insights": len(context["insights"]),
            "critical_count": sum(
                1 for i in context["insights"] if i["severity"] == "critical"
            ),
            "high_count": sum(
                1 for i in context["insights"] if i["severity"] == "high"
            ),
            "quick_wins": sum(
                1
                for i in context["insights"]
                if i["severity"] in ["high", "critical"] and i["effort"] == "low"
            ),
        }

        return context

    def _generate_llm_response(
        self,
        user_message: str,
        context: dict,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """Generate response using OpenAI."""
        try:
            # Build system prompt with context
            system_prompt = self._build_system_prompt(context)

            # Build messages
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history if available
            if conversation_history:
                messages.extend(conversation_history[-4:])  # Last 4 messages

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Generate response
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            return self._generate_fallback_response(user_message, context)

    def _build_system_prompt(self, context: dict) -> str:
        """Build system prompt with insights data."""
        insights_summary = []
        for insight in context["insights"][:10]:  # Top 10 insights
            metrics_str = ""
            if "metrics" in insight:
                m = insight["metrics"]
                metrics_str = f" | {m['freq_30d']} mentions (30d) | ${m['acv_sum']/1000:.0f}k ACV | Trend: {'+' if m['trend'] > 0 else '='}"

            insights_summary.append(
                f"- [{insight['severity'].upper()}] [{insight['effort'].upper()} effort] P{insight['priority_score']}: {insight['title']}{metrics_str}"
            )

        insights_text = "\n".join(insights_summary)

        prompt = f"""You are an AI PM copilot helping a product manager make data-driven decisions.

You have access to {context['summary']['total_insights']} product insights from customer feedback analysis:
- {context['summary']['critical_count']} CRITICAL severity
- {context['summary']['high_count']} HIGH severity
- {context['summary']['quick_wins']} quick wins (high severity + low effort)

Top insights by priority:
{insights_text}

When answering questions:
1. Be specific and actionable - reference actual insights by title
2. Prioritize based on severity, effort, ACV impact, and trends
3. Identify quick wins when relevant
4. Consider customer impact and revenue implications
5. Provide clear recommendations, not just analysis
6. Keep responses concise (2-4 paragraphs)

Your role is to help PMs:
- Plan quarterly priorities
- Identify top customer pain points
- Find quick wins
- Assess revenue impact
- Make data-driven roadmap decisions
"""

        # Add selected insight context if available
        if "selected_insight" in context:
            si = context["selected_insight"]
            customers_str = ", ".join(si["affected_customers"][:3])
            prompt += f"""

CURRENTLY SELECTED INSIGHT:
Title: {si['title']}
Severity: {si['severity']} | Effort: {si['effort']} | Priority: P{si['priority_score']}
Description: {si['description']}
Impact: {si['impact']}
Affected customers: {customers_str}

When the user asks about "this insight" or similar, they're referring to this selected insight.
"""

        return prompt

    def _generate_fallback_response(
        self, user_message: str, context: dict
    ) -> str:
        """Generate response without LLM (rule-based)."""
        message_lower = user_message.lower()

        # Quick wins query
        if "quick win" in message_lower or "low effort" in message_lower:
            quick_wins = [
                i
                for i in context["insights"]
                if i["severity"] in ["high", "critical"] and i["effort"] == "low"
            ]
            if quick_wins:
                response = f"I found {len(quick_wins)} quick wins (high severity + low effort):\n\n"
                for qw in quick_wins[:3]:
                    response += f"• {qw['title']} [{qw['severity'].upper()} severity, LOW effort, P{qw['priority_score']}]\n"
                return response
            else:
                return "No quick wins found. Consider reviewing medium effort items with high severity."

        # Quarterly focus query
        if "quarter" in message_lower or "focus" in message_lower:
            top_3 = context["insights"][:3]
            response = "Based on priority scores and customer impact, I recommend focusing on:\n\n"
            for idx, insight in enumerate(top_3, 1):
                metrics_str = ""
                if "metrics" in insight:
                    metrics_str = f" ({insight['metrics']['freq_30d']} mentions, ${insight['metrics']['acv_sum']/1000:.0f}k ACV)"
                response += f"{idx}. {insight['title']} [P{insight['priority_score']}]{metrics_str}\n"
            return response

        # Top complaints query
        if "complaint" in message_lower or "pain" in message_lower:
            top_issues = [
                i for i in context["insights"][:5] if i["severity"] in ["high", "critical"]
            ]
            response = f"Top {len(top_issues)} customer pain points:\n\n"
            for issue in top_issues:
                response += f"• {issue['title']} [{issue['severity'].upper()}, {issue['feedback_count']} reports]\n"
            return response

        # Enterprise blockers
        if "enterprise" in message_lower or "blocker" in message_lower:
            blockers = [
                i
                for i in context["insights"]
                if "enterprise" in i["title"].lower()
                or "sso" in i["title"].lower()
                or "saml" in i["title"].lower()
                or i["severity"] == "critical"
            ]
            if blockers:
                response = f"Found {len(blockers)} enterprise blockers:\n\n"
                for blocker in blockers[:3]:
                    response += f"• {blocker['title']} [P{blocker['priority_score']}]\n"
                return response

        # Selected insight query
        if "selected_insight" in context and (
            "this" in message_lower or "selected" in message_lower
        ):
            si = context["selected_insight"]
            return f"The selected insight '{si['title']}' has {si['severity']} severity and {si['effort']} effort. It affects customers: {', '.join(si['affected_customers'][:3])}."

        # Default response
        return f"I have analyzed {context['summary']['total_insights']} insights. You can ask me about:\n- Quarterly priorities\n- Top customer complaints\n- Quick wins\n- Enterprise blockers\n- Specific insights\n\nWhat would you like to know?"


# Global instance
_pm_agent: Optional[PMCopilotAgent] = None


def get_pm_agent() -> PMCopilotAgent:
    """Get or create the global PM agent instance."""
    global _pm_agent
    if _pm_agent is None:
        _pm_agent = PMCopilotAgent()
    return _pm_agent
