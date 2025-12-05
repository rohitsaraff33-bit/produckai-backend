"""Insight generation service using LLM."""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

from apps.api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def sanitize_title(title: str, customer_names: List[str]) -> str:
    """
    Remove customer/company names from insight titles.

    This ensures titles are generic and don't expose customer information.

    Args:
        title: The insight title to sanitize
        customer_names: List of customer names to remove

    Returns:
        Sanitized title without customer names
    """
    sanitized = title
    for customer_name in customer_names:
        if not customer_name:
            continue
        # Remove exact matches (case-insensitive)
        pattern = re.compile(re.escape(customer_name), re.IGNORECASE)
        sanitized = pattern.sub("", sanitized)

    # Clean up any resulting double spaces, leading/trailing spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    # Remove any leftover artifacts like ", ", " - ", etc.
    sanitized = re.sub(r'^[,\-\s]+|[,\-\s]+$', '', sanitized)

    return sanitized


@dataclass
class GeneratedInsight:
    """Generated insight from feedback cluster."""

    title: str
    description: str
    impact: str
    recommendation: str
    severity: str  # low, medium, high, critical
    effort: str  # low, medium, high
    key_quote_indices: List[int]  # Indices of most representative feedback

    # Immutable data for data integrity
    supporting_feedback_ids: List[str]  # UUIDs of ALL feedback used for this insight
    affected_customers: List[dict]  # Full customer data: [{id, name, segment, acv}, ...]
    key_quotes: List[str]  # Actual text of key quotes (immutable)


class InsightGenerationService:
    """Service for generating actionable insights from feedback clusters."""

    def __init__(self):
        """Initialize insight generation service."""
        self.has_openai = bool(settings.openai_api_key)
        if self.has_openai:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.openai_api_key)
                logger.info("InsightGenerationService initialized with OpenAI")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")
                self.has_openai = False

        if not self.has_openai:
            logger.info("InsightGenerationService initialized without OpenAI (fallback mode)")

    def generate_insights_for_cluster(
        self,
        db,  # Database session to fetch customer data
        feedback_items: List,  # Full feedback objects with customer relationships
        theme_label: str,
    ) -> List[GeneratedInsight]:
        """
        Generate actionable insights from a cluster of feedback.

        Args:
            db: Database session for querying customer data
            feedback_items: List of Feedback objects (with customer relationships loaded)
            theme_label: The theme label from clustering

        Returns:
            List of GeneratedInsight objects with immutable customer/feedback data
        """
        if len(feedback_items) < 3:
            # Too few items for meaningful insights
            return self._generate_simple_insight(db, feedback_items, theme_label)

        if self.has_openai:
            return self._generate_insights_with_llm(db, feedback_items, theme_label)
        else:
            return self._generate_simple_insight(db, feedback_items, theme_label)

    def _generate_insights_with_llm(
        self,
        db,
        feedback_items: List,
        theme_label: str,
    ) -> List[GeneratedInsight]:
        """Generate insights using OpenAI LLM with ALL feedback considered."""
        try:
            from apps.api.models import Customer

            # CRITICAL: Count ALL unique customers from ALL feedback
            unique_customer_ids = set(f.customer_id for f in feedback_items if f.customer_id)
            num_customers = len(unique_customer_ids)

            # Fetch full customer data from database (immutable snapshot)
            customers_data = []
            if unique_customer_ids:
                customers = db.query(Customer).filter(Customer.id.in_(unique_customer_ids)).all()
                customers_data = [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "segment": c.segment.value,
                        "acv": float(c.acv),
                    }
                    for c in customers
                ]

            # Store ALL supporting feedback IDs (immutable)
            supporting_feedback_ids = [str(f.id) for f in feedback_items]

            # Create customer ID to letter mapping for LLM prompt
            customer_id_to_letter = {
                str(cid): chr(65 + i) for i, cid in enumerate(unique_customer_ids)
            }

            # Intelligently sample feedback for LLM (max 20 items to fit token limits)
            # Strategy: Ensure we include diverse customers while staying under token limit
            sampled_feedback = []
            customers_included = set()

            # First pass: Include at least one feedback from each unique customer
            for f in feedback_items:
                if f.customer_id and f.customer_id not in customers_included:
                    sampled_feedback.append(f)
                    customers_included.add(f.customer_id)
                    if len(sampled_feedback) >= 20:
                        break

            # Second pass: Fill remaining slots with additional feedback
            if len(sampled_feedback) < 20:
                for f in feedback_items:
                    if f not in sampled_feedback:
                        sampled_feedback.append(f)
                        if len(sampled_feedback) >= 20:
                            break

            # Prepare feedback summary with customer anonymization
            feedback_summary = "\n".join(
                f"{i+1}. [Customer {customer_id_to_letter.get(str(f.customer_id), '?')}] {f.text[:200]}"
                for i, f in enumerate(sampled_feedback)
            )

            # Format affected customers count
            affected = f"{num_customers} customer(s)" if num_customers > 0 else "Multiple users"

            logger.info(f"Generating insight with LLM: {num_customers} customers, {len(feedback_items)} feedback items, {len(sampled_feedback)} sampled for LLM")

            prompt = f"""You are a product manager analyzing customer feedback. Given this cluster of feedback:

Theme: {theme_label}
Affected: {affected}

Feedback:
{feedback_summary}

Generate 1 actionable insight that synthesizes this feedback. Provide:

1. **Title**: A clear, business-focused statement (MAX 6 words, under 45 characters)
   CRITICAL: DO NOT include any customer names, company names, or person names in the title.
   The title must be generic and applicable to any customer facing this issue.
   Good examples: "SSO/SAML blocks enterprise deals", "Export performance affects workflows"
   Bad examples:
   - "SSO/SAML integration is blocking enterprise deals" (too long!)
   - "Acme Corp needs SSO integration" (contains customer name!)
   - "John's team needs better export" (contains person name!)

2. **Description**: What is the core issue or opportunity? Be specific about what users are experiencing.
   Example: "Enterprise customers report they cannot deploy our product without SSO/SAML support. Security teams are blocking adoption due to password-based authentication requirements."

3. **Impact**: Why does this matter? What's at stake? Include business metrics if possible.
   Example: "This is blocking $250K in enterprise ARR. 3 large deals are on hold pending SSO implementation. Security compliance is non-negotiable for enterprise customers."

4. **Recommendation**: Provide 2-3 specific, actionable next steps. Be concrete.
   Example: "1) Schedule technical discovery with engineering to scope SAML 2.0 integration with Okta/Azure AD. 2) Prioritize as Q1 roadmap item given revenue impact. 3) Set up customer advisory board with blocked accounts to validate requirements."

   DO NOT use generic recommendations like "Prioritize investigation" or "Schedule a team discussion".
   BE SPECIFIC about what to investigate, who to talk to, what to build, or what decision to make.

5. **Severity**: low, medium, high, or critical (based on customer impact and business risk)

6. **Effort**: low, medium, or high (realistic engineering estimate)

7. **Key Quotes**: Which feedback items (by number, max 3) best represent this insight?

Format your response as JSON:
{{
  "insights": [
    {{
      "title": "...",
      "description": "...",
      "impact": "...",
      "recommendation": "...",
      "severity": "medium|high|critical",
      "effort": "low|medium|high",
      "key_quotes": [1, 5, 7]
    }}
  ]
}}"""

            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a senior product manager with expertise in synthesizing customer feedback into actionable insights."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000,
            )

            import json
            result = json.loads(response.choices[0].message.content)

            insights = []

            for insight_data in result.get("insights", []):
                # Convert 1-based indices to 0-based (indices refer to sampled feedback)
                key_quote_indices = [idx - 1 for idx in insight_data.get("key_quotes", [1])]
                # Validate indices against sampled feedback
                key_quote_indices = [idx for idx in key_quote_indices if 0 <= idx < len(sampled_feedback)]
                if not key_quote_indices:
                    key_quote_indices = [0]  # Default to first item

                # Extract actual quote texts for immutability
                key_quotes = [sampled_feedback[idx].text for idx in key_quote_indices]

                # Use title directly (customer IDs are UUIDs, won't appear in titles)
                title = insight_data.get("title", "Untitled Insight")

                insights.append(GeneratedInsight(
                    title=title,
                    description=insight_data.get("description", ""),
                    impact=insight_data.get("impact", ""),
                    recommendation=insight_data.get("recommendation", ""),
                    severity=insight_data.get("severity", "medium"),
                    effort=insight_data.get("effort", "medium"),
                    key_quote_indices=key_quote_indices,
                    # IMMUTABLE DATA for data integrity
                    supporting_feedback_ids=supporting_feedback_ids,  # ALL feedback IDs
                    affected_customers=customers_data,  # Full customer data
                    key_quotes=key_quotes,  # Actual quote texts
                ))

            logger.info(f"Generated {len(insights)} insights with LLM: {num_customers} customers, {len(feedback_items)} feedback items")
            return insights

        except Exception as e:
            logger.error(f"Failed to generate insights with LLM: {e}", exc_info=True)
            return self._generate_simple_insight(db, feedback_items, theme_label)

    def _generate_simple_insight(
        self,
        db,
        feedback_items: List,
        theme_label: str,
    ) -> List[GeneratedInsight]:
        """Generate context-aware insight without LLM (fallback) with ALL feedback considered."""
        from apps.api.models import Customer

        # CRITICAL: Count ALL unique customers from ALL feedback
        unique_customer_ids = set(f.customer_id for f in feedback_items if f.customer_id)
        affected = len(unique_customer_ids) if unique_customer_ids else 1

        # Fetch full customer data from database (immutable snapshot)
        customers_data = []
        if unique_customer_ids:
            customers = db.query(Customer).filter(Customer.id.in_(unique_customer_ids)).all()
            customers_data = [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "segment": c.segment.value,
                    "acv": float(c.acv),
                }
                for c in customers
            ]

        # Store ALL supporting feedback IDs (immutable)
        supporting_feedback_ids = [str(f.id) for f in feedback_items]

        # For display purposes, use generic labels since we only have IDs
        customer_list = f"{affected} customer(s)"

        logger.info(f"Generating fallback insight: {affected} customers, {len(feedback_items)} feedback items")

        # Determine severity based on frequency and enterprise impact
        enterprise_keywords = ['enterprise', 'security', 'compliance', 'sso', 'saml']
        has_enterprise_impact = any(kw in theme_label.lower() for kw in enterprise_keywords)

        if (affected >= 5 or len(feedback_items) >= 10) or has_enterprise_impact:
            severity = "high"
        elif affected >= 3 or len(feedback_items) >= 5:
            severity = "medium"
        else:
            severity = "low"

        # Analyze theme for context-specific content
        theme_lower = theme_label.lower()

        # Strip numeric prefixes and clean up theme label
        import re
        clean_theme = re.sub(r'^\d+\s+', '', theme_label)  # Remove leading numbers
        clean_theme = clean_theme.replace(", ", " & ").replace("  ", " ")

        # Generate context-specific, actionable title and description
        if 'sso' in theme_lower or 'saml' in theme_lower or 'auth' in theme_lower:
            title = "Enterprise SSO/SAML integration blocking deals"
            description = f"Enterprise customers across {affected} accounts are blocked from deploying due to lack of SSO/SAML authentication. Security teams require enterprise SSO for compliance, making this a deployment blocker rather than a feature request."
        elif 'export' in theme_lower or 'excel' in theme_lower or 'csv' in theme_lower:
            title = "Data export functionality needs enhancement"
            description = f"{affected} customer(s) report workflow friction with data export functionality. Users need to extract data into Excel/CSV for analysis, reporting, and integration with other tools. Current export capabilities are insufficient for their daily workflows."
        elif 'mobile' in theme_lower or 'responsive' in theme_lower:
            title = "Mobile responsiveness limiting field team usage"
            description = f"{affected} customer(s) report usability issues on mobile devices. The application is not optimized for mobile/tablet usage, affecting field workers and remote teams who rely on mobile access."
        elif 'search' in theme_lower or 'filter' in theme_lower:
            title = "Search and filter functionality inadequate"
            description = f"{affected} customer(s) struggle to find information efficiently. Search and filtering functionality is inadequate, forcing users to manually browse through data, impacting productivity."
        elif 'dashboard' in theme_lower or 'performance' in theme_lower or 'loading' in theme_lower:
            title = "Dashboard performance impacting user engagement"
            description = f"{affected} customer(s) experience performance issues with dashboard loading times. Slow page loads and sluggish interactions are frustrating daily users and reducing platform engagement."
        elif 'webhook' in theme_lower or 'api' in theme_lower or 'integration' in theme_lower:
            title = "Build webhook and API integration capabilities"
            description = f"{affected} customer(s) require integration capabilities to connect with their existing tech stack. Lack of webhook/API functionality prevents automation and forces manual workflows."
        elif 'dark mode' in theme_lower or 'theme' in theme_lower:
            title = "Add dark mode theme for reduced eye strain"
            description = f"{affected} customer(s) have requested dark mode for reduced eye strain. This is particularly important for users who spend extended hours in the application daily."
        else:
            # Fallback: use cleaned theme label as title with better shortening logic
            if len(clean_theme) <= 60:
                title = clean_theme
            else:
                # Try to shorten by removing redundant phrases
                short_theme = clean_theme.replace(" requires immediate attention", "")
                short_theme = short_theme.replace(" is a frequently requested feature", " frequently requested")
                short_theme = short_theme.replace(" needs improvement", "")
                short_theme = short_theme.replace(" affecting daily", "")

                if len(short_theme) <= 60:
                    title = short_theme
                else:
                    # Last resort: truncate intelligently at word boundary
                    title = clean_theme[:57].rsplit(' ', 1)[0] + "..."

            description = f"{affected} customer(s) have provided feedback on {clean_theme.lower()}. This pattern suggests a consistent user need that should be evaluated for product roadmap inclusion."

        # Generate context-specific impact
        if 'sso' in theme_lower or 'saml' in theme_lower:
            impact = f"Blocking enterprise sales. Affects {customer_list}. Security compliance is non-negotiable for enterprise buyers. Each delayed deal represents significant ARR loss."
        elif 'export' in theme_lower:
            impact = f"Daily workflow friction for {customer_list}. Export is a frequently used feature; limitations here compound user frustration and may drive churn."
        elif 'mobile' in theme_lower or 'responsive' in theme_lower:
            impact = f"Excluding mobile users from effective product usage. Affects field teams and remote workers at {customer_list}. Growing mobile usage makes this increasingly critical."
        elif 'dashboard' in theme_lower or 'performance' in theme_lower:
            impact = f"Performance issues create daily friction for {customer_list}. Slow experiences reduce engagement and may push users toward alternative solutions."
        elif 'api' in theme_lower or 'integration' in theme_lower or 'webhook' in theme_lower:
            impact = f"Limits enterprise adoption at {customer_list}. Integration capabilities are table-stakes for mid-market and enterprise customers who need to connect their tech stack."
        else:
            impact = f"Affects {affected} customer(s) including {customer_list}. Addressing this issue could improve user satisfaction and reduce friction in their workflows."

        # Generate context-specific, actionable recommendations
        if 'sso' in theme_lower or 'saml' in theme_lower or 'auth' in theme_lower:
            recommendation = "1) Conduct technical scoping for SAML 2.0 integration with major IdPs (Okta, Azure AD, Google Workspace). 2) Evaluate build vs buy (e.g., Auth0, WorkOS) to accelerate delivery. 3) Prioritize on Q1 roadmap given enterprise pipeline impact. 4) Set up design partnership with 2-3 blocked accounts to validate requirements."
            effort = "medium"
        elif 'export' in theme_lower or 'excel' in theme_lower or 'csv' in theme_lower:
            recommendation = "1) Interview affected users to understand specific export use cases and formats needed. 2) Prioritize bulk export functionality and format options (Excel, CSV, PDF). 3) Consider adding scheduled exports for recurring reporting needs. 4) Implement export progress indicators for large datasets."
            effort = "medium"
        elif 'mobile' in theme_lower or 'responsive' in theme_lower:
            recommendation = "1) Conduct mobile usability audit to identify critical UI breakpoints. 2) Prioritize responsive design for most-used features (viewing, light editing). 3) Consider Progressive Web App (PWA) approach vs native apps. 4) Test with actual mobile users from affected accounts."
            effort = "high"
        elif 'search' in theme_lower or 'filter' in theme_lower:
            recommendation = "1) Analyze search analytics to understand user search patterns and failure cases. 2) Implement fuzzy matching and better tokenization. 3) Add advanced filters for common use cases. 4) Consider full-text search engine (e.g., Elasticsearch) if current approach is insufficient."
            effort = "medium"
        elif 'dashboard' in theme_lower or 'performance' in theme_lower or 'loading' in theme_lower:
            recommendation = "1) Profile dashboard queries and identify slow database queries. 2) Implement caching for expensive computations. 3) Add skeleton loaders and progressive loading for better perceived performance. 4) Consider pagination or virtualization for large datasets."
            effort = "medium"
        elif 'webhook' in theme_lower or 'api' in theme_lower or 'integration' in theme_lower:
            recommendation = "1) Survey affected customers to understand integration needs and target systems. 2) Design webhook event schema and API endpoints for common workflows. 3) Build self-service webhook configuration UI. 4) Create integration guides for popular tools (Zapier, Slack, etc.)."
            effort = "medium"
        elif 'dark mode' in theme_lower or 'theme' in theme_lower:
            recommendation = "1) Audit design system for dark mode compatibility. 2) Implement theme toggle with user preference persistence. 3) Ensure WCAG contrast standards in both modes. 4) Consider auto-switching based on system preferences."
            effort = "low"
        else:
            recommendation = f"1) Conduct user interviews with {customer_list} to understand root cause and specific pain points. 2) Review all {len(feedback_items)} feedback items to identify common patterns. 3) Draft technical requirements and effort estimate. 4) Present findings to product team for roadmap prioritization."
            effort = "medium"

        # Select key quotes by finding feedback that matches title keywords
        # Extract meaningful keywords from title (remove common words)
        import re
        common_words = {'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
                        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                        'needs', 'need', 'require', 'requires', 'required', 'attention', 'improvement',
                        'enhancement', 'better', 'improved', 'new', 'add', 'added', 'adding'}

        title_words = re.findall(r'\b\w+\b', title.lower())
        title_keywords = [w for w in title_words if w not in common_words and len(w) > 2]

        # Score each feedback item by keyword matches
        feedback_scores = []
        for idx, f in enumerate(feedback_items):
            text_lower = f.text.lower()
            matches = sum(1 for kw in title_keywords if kw in text_lower)
            feedback_scores.append((idx, matches))

        # Sort by number of matches (descending)
        feedback_scores.sort(key=lambda x: x[1], reverse=True)

        # Select top 3 items with at least 1 keyword match
        key_quote_indices = [idx for idx, score in feedback_scores if score > 0][:3]

        # Fallback: if no matches found, just take first 3
        if not key_quote_indices:
            key_quote_indices = list(range(min(3, len(feedback_items))))

        # Extract actual quote texts for immutability
        key_quotes = [feedback_items[idx].text for idx in key_quote_indices]

        # Use title directly (customer IDs are UUIDs, won't appear in titles)
        insight = GeneratedInsight(
            title=title,
            description=description,
            impact=impact,
            recommendation=recommendation,
            severity=severity,
            effort=effort,
            key_quote_indices=key_quote_indices,
            # IMMUTABLE DATA for data integrity
            supporting_feedback_ids=supporting_feedback_ids,  # ALL feedback IDs
            affected_customers=customers_data,  # Full customer data
            key_quotes=key_quotes,  # Actual quote texts
        )

        logger.info(f"Generated fallback insight: {affected} customers, {len(feedback_items)} feedback items")
        return [insight]


# Global instance
_insight_service: Optional[InsightGenerationService] = None


def get_insight_service() -> InsightGenerationService:
    """Get or create the global insight generation service instance."""
    global _insight_service
    if _insight_service is None:
        _insight_service = InsightGenerationService()
    return _insight_service
