"""Seed database with demo data."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from apps.api.config import get_settings
from apps.api.database import get_db_context
from apps.api.models import Customer, CustomerSegment, Feedback, FeedbackSource
from apps.api.services.embeddings import get_embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


def seed_demo_customers():
    """Seed demo customers."""
    customers_data = [
        {"name": "Acme Corp", "acv": 120000, "segment": CustomerSegment.ENT},
        {"name": "TechStart Inc", "acv": 45000, "segment": CustomerSegment.MM},
        {"name": "SmallBiz LLC", "acv": 8000, "segment": CustomerSegment.SMB},
        {"name": "Enterprise Solutions", "acv": 250000, "segment": CustomerSegment.ENT},
        {"name": "MidCo Industries", "acv": 60000, "segment": CustomerSegment.MM},
    ]

    with get_db_context() as db:
        existing = db.query(Customer).count()
        if existing > 0:
            logger.info(f"Customers already seeded ({existing} found)")
            return

        for data in customers_data:
            customer = Customer(**data)
            db.add(customer)

        db.commit()
        logger.info(f"Seeded {len(customers_data)} customers")


def seed_demo_feedback():
    """Seed demo feedback from sample files."""
    with get_db_context() as db:
        existing = db.query(Feedback).count()
        if existing > 0:
            logger.info(f"Feedback already seeded ({existing} found)")
            return

        # Get customers for linking
        customers = db.query(Customer).all()
        customer_by_name = {c.name: c for c in customers}

        # Load sample Slack data
        samples_dir = Path("/app/samples") if Path("/app/samples").exists() else Path("samples")
        slack_file = samples_dir / "slack" / "demo_messages.jsonl"
        jira_file = samples_dir / "jira" / "demo_issues.json"

        feedback_items = []

        # Load Slack messages
        if slack_file.exists():
            with open(slack_file, "r") as f:
                for line in f:
                    data = json.loads(line)
                    account = data.get("account")
                    customer_id = customer_by_name[account].id if account in customer_by_name else None

                    feedback_items.append(
                        Feedback(
                            id=uuid4(),
                            source=FeedbackSource.slack,
                            source_id=data.get("ts", str(uuid4())),
                            account=account,
                            customer_id=customer_id,
                            text=data["text"],
                            created_at=datetime.fromisoformat(data["created_at"]),
                            meta={"channel": data.get("channel"), "user": data.get("user")},
                        )
                    )

        # Load Jira issues
        if jira_file.exists():
            with open(jira_file, "r") as f:
                issues = json.load(f)
                for issue in issues:
                    # Combine title and description
                    text = f"{issue['title']}. {issue.get('description', '')}"
                    account = issue.get("account")
                    customer_id = customer_by_name[account].id if account in customer_by_name else None

                    feedback_items.append(
                        Feedback(
                            id=uuid4(),
                            source=FeedbackSource.jira,
                            source_id=issue["key"],
                            account=account,
                            customer_id=customer_id,
                            text=text,
                            created_at=datetime.fromisoformat(issue["created_at"]),
                            meta={"status": issue.get("status"), "priority": issue.get("priority")},
                        )
                    )

        # Add to database
        for item in feedback_items:
            db.add(item)

        db.commit()
        logger.info(f"Seeded {len(feedback_items)} feedback items")

        # Generate embeddings
        logger.info("Generating embeddings...")
        embedding_service = get_embedding_service()

        feedback_list = db.query(Feedback).filter(Feedback.embedding.is_(None)).all()
        texts = [f.text for f in feedback_list]

        if texts:
            embeddings = embedding_service.embed_batch(texts)

            for feedback, embedding in zip(feedback_list, embeddings):
                feedback.embedding = embedding

            db.commit()
            logger.info(f"Generated embeddings for {len(feedback_list)} items")


def ingest_slack_data() -> int:
    """Ingest Slack data and return count."""
    seed_demo_feedback()
    with get_db_context() as db:
        return db.query(Feedback).filter(Feedback.source == FeedbackSource.slack).count()


def ingest_jira_data() -> int:
    """Ingest Jira data and return count."""
    seed_demo_feedback()
    with get_db_context() as db:
        return db.query(Feedback).filter(Feedback.source == FeedbackSource.jira).count()


def ingest_gdocs_data() -> int:
    """Ingest Google Docs demo data and return count."""
    from apps.api.ingestion.ingest_gdocs import ingest_gdocs_demo

    with get_db_context() as db:
        return ingest_gdocs_demo(db)


def ingest_zoom_data() -> int:
    """Ingest Zoom demo data and return count."""
    from apps.api.ingestion.ingest_zoom import ingest_zoom_demo

    with get_db_context() as db:
        return ingest_zoom_demo(db)


if __name__ == "__main__":
    logger.info("Starting demo data seed...")
    seed_demo_customers()
    seed_demo_feedback()  # Slack + Jira

    # Ingest Google Docs
    logger.info("Ingesting Google Docs demo data...")
    gdocs_count = ingest_gdocs_data()
    logger.info(f"Ingested {gdocs_count} Google Docs chunks")

    # Ingest Zoom transcripts
    logger.info("Ingesting Zoom demo data...")
    zoom_count = ingest_zoom_data()
    logger.info(f"Ingested {zoom_count} Zoom transcript chunks")

    logger.info("Demo data seed completed!")
