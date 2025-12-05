"""Jira issue content extractor."""

from datetime import datetime

from apps.api.services.ingestion.base import (
    ContentChunk,
    ContentExtractor,
    CustomerInfo,
)


class JiraExtractor(ContentExtractor):
    """
    Extract customer and feedback from Jira issues.

    Jira has structured customer information in custom fields or organization.
    Issues and comments can be chunked if very long.
    """

    def extract_customer(self, raw_content: dict) -> CustomerInfo:
        """
        Extract customer from Jira issue metadata.

        Uses organization field, custom fields, or reporter information.

        Args:
            raw_content: Dict with 'fields', 'key', etc.

        Returns:
            CustomerInfo with extracted name and confidence
        """
        self.validate_content(raw_content)

        fields = raw_content.get("fields", {})

        # Strategy 1: Check for organization/account custom field
        # Common custom field names: "Account", "Organization", "Customer"
        for field_name in ["customfield_10050", "customfield_10051"]:
            if field_name in fields and fields[field_name]:
                org_data = fields[field_name]
                # Handle both string and object formats
                if isinstance(org_data, dict):
                    customer = org_data.get("name") or org_data.get("value")
                else:
                    customer = str(org_data)

                if customer:
                    return CustomerInfo(
                        name=customer,
                        confidence=0.9,
                        extraction_method="structured_field",
                        metadata={"field": field_name}
                    )

        # Strategy 2: Extract from reporter
        reporter = fields.get("reporter", {})
        if isinstance(reporter, dict):
            reporter_email = reporter.get("emailAddress", "")
            if reporter_email and "@" in reporter_email:
                domain = reporter_email.split("@")[1].split(".")[0].title()
                return CustomerInfo(
                    name=domain,
                    confidence=0.5,
                    extraction_method="reporter_domain",
                    metadata={"email": reporter_email}
                )

        # Strategy 3: Use project name as fallback
        project = fields.get("project", {})
        if isinstance(project, dict):
            project_name = project.get("name", "Unknown")
            return CustomerInfo(
                name=project_name,
                confidence=0.4,
                extraction_method="project_name",
                metadata={"project": project_name}
            )

        # Last resort
        return CustomerInfo(
            name="Unknown",
            confidence=0.1,
            extraction_method="fallback_unknown"
        )

    def should_chunk(self, raw_content: dict) -> bool:
        """
        Jira issues are typically compact, but descriptions and comments can be long.

        Chunk if description is very long or if there are many comments.
        """
        fields = raw_content.get("fields", {})
        description = fields.get("description", "") or ""

        # Simple length-based check
        return len(str(description)) > 2000

    def chunk_content(self, raw_content: dict) -> list[ContentChunk]:
        """
        Chunk Jira issue content.

        Combines summary and description into feedback text.
        TODO: Optionally include comments as separate chunks.

        Args:
            raw_content: Dict with 'fields', 'key', etc.

        Returns:
            List of ContentChunk objects
        """
        self.validate_content(raw_content)

        fields = raw_content.get("fields", {})
        issue_key = raw_content.get("key", "unknown")

        summary = fields.get("summary", "")
        description = fields.get("description", "") or ""

        # Combine summary and description
        text = f"{summary}\n\n{description}".strip()

        return [
            ContentChunk(
                id=issue_key,
                text=text,
                metadata={
                    "issue_key": issue_key,
                    "issue_type": fields.get("issuetype", {}).get("name"),
                    "status": fields.get("status", {}).get("name"),
                    "priority": fields.get("priority", {}).get("name"),
                    "reporter": fields.get("reporter", {}).get("displayName"),
                    "assignee": fields.get("assignee", {}).get("displayName"),
                    "created_at": fields.get("created", datetime.utcnow()),
                }
            )
        ]

    def validate_content(self, raw_content: dict) -> None:
        """Validate Jira content structure."""
        super().validate_content(raw_content)

        if "fields" not in raw_content:
            raise ValueError("Jira content must have 'fields' object")

        fields = raw_content.get("fields", {})
        if not fields.get("summary"):
            raise ValueError("Jira issue must have a summary")
