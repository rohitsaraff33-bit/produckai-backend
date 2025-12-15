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
    """Seed demo feedback from sample files (Slack + Jira)."""
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
        logger.info(f"Seeded {len(feedback_items)} feedback items (Slack + Jira)")

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


def seed_gdocs_demo_data():
    """Load Google Docs demo data from JSON file."""
    samples_dir = Path("/app/samples") if Path("/app/samples").exists() else Path("samples")
    gdocs_file = samples_dir / "gdocs" / "demo_documents.json"

    if not gdocs_file.exists():
        logger.warning(f"Google Docs demo file not found: {gdocs_file}")
        return 0

    with get_db_context() as db:
        # Get customers for linking
        customers = db.query(Customer).all()
        customer_by_name = {c.name: c for c in customers}

        # Check if already loaded
        existing_gdocs = db.query(Feedback).filter(Feedback.source == FeedbackSource.gdoc).count()
        if existing_gdocs > 0:
            logger.info(f"Google Docs demo data already loaded ({existing_gdocs} found)")
            return existing_gdocs

        # Load documents
        with open(gdocs_file, "r") as f:
            documents = json.load(f)

        feedback_items = []
        for doc in documents:
            account = doc.get("account")
            customer_id = customer_by_name[account].id if account in customer_by_name else None

            # Create feedback item
            feedback_items.append(
                Feedback(
                    id=uuid4(),
                    source=FeedbackSource.gdoc,
                    source_id=doc["document_id"],
                    account=account,
                    customer_id=customer_id,
                    text=f"{doc['title']}\n\n{doc['text']}",
                    created_at=datetime.fromisoformat(doc["created_at"]),
                    meta={
                        "document_id": doc["document_id"],
                        "title": doc["title"],
                        "owner": doc.get("owner"),
                    },
                )
            )

        # Add to database
        for item in feedback_items:
            db.add(item)

        db.commit()
        logger.info(f"Loaded {len(feedback_items)} Google Docs demo items")

        # Generate embeddings
        logger.info("Generating embeddings for Google Docs...")
        embedding_service = get_embedding_service()

        texts = [f.text for f in feedback_items]
        embeddings = embedding_service.embed_batch(texts)

        for feedback, embedding in zip(feedback_items, embeddings):
            feedback.embedding = embedding

        db.commit()
        logger.info(f"Generated embeddings for {len(feedback_items)} Google Docs items")

        return len(feedback_items)


def seed_zoom_demo_data():
    """Load Zoom demo data from JSON file."""
    samples_dir = Path("/app/samples") if Path("/app/samples").exists() else Path("samples")
    zoom_file = samples_dir / "zoom" / "demo_transcripts.json"

    if not zoom_file.exists():
        logger.warning(f"Zoom demo file not found: {zoom_file}")
        return 0

    with get_db_context() as db:
        # Get customers for linking
        customers = db.query(Customer).all()
        customer_by_name = {c.name: c for c in customers}

        # Check if already loaded
        existing_zoom = db.query(Feedback).filter(Feedback.source == FeedbackSource.zoom).count()
        if existing_zoom > 0:
            logger.info(f"Zoom demo data already loaded ({existing_zoom} found)")
            return existing_zoom

        # Load transcripts
        with open(zoom_file, "r") as f:
            meetings = json.load(f)

        feedback_items = []
        for meeting in meetings:
            account = meeting.get("account")
            customer_id = customer_by_name[account].id if account in customer_by_name else None

            # Create feedback item
            feedback_items.append(
                Feedback(
                    id=uuid4(),
                    source=FeedbackSource.zoom,
                    source_id=meeting["meeting_id"],
                    account=account,
                    customer_id=customer_id,
                    text=f"{meeting['title']}\n\nTranscript:\n{meeting['transcript']}",
                    created_at=datetime.fromisoformat(meeting["created_at"]),
                    meta={
                        "meeting_id": meeting["meeting_id"],
                        "title": meeting["title"],
                        "participants": meeting.get("participants", []),
                        "duration_minutes": meeting.get("duration_minutes"),
                    },
                )
            )

        # Add to database
        for item in feedback_items:
            db.add(item)

        db.commit()
        logger.info(f"Loaded {len(feedback_items)} Zoom demo items")

        # Generate embeddings
        logger.info("Generating embeddings for Zoom transcripts...")
        embedding_service = get_embedding_service()

        texts = [f.text for f in feedback_items]
        embeddings = embedding_service.embed_batch(texts)

        for feedback, embedding in zip(feedback_items, embeddings):
            feedback.embedding = embedding

        db.commit()
        logger.info(f"Generated embeddings for {len(feedback_items)} Zoom items")

        return len(feedback_items)


if __name__ == "__main__":
    logger.info("🌱 Starting demo data seed...")

    # Seed customers first
    seed_demo_customers()

    # Seed Slack + Jira feedback
    seed_demo_feedback()

    # Seed Google Docs
    try:
        logger.info("📄 Loading Google Docs demo data...")
        gdocs_count = seed_gdocs_demo_data()
        logger.info(f"✅ Loaded {gdocs_count} Google Docs items")
    except Exception as e:
        logger.error(f"❌ Failed to load Google Docs demo data: {e}")

    # Seed Zoom transcripts
    try:
        logger.info("🎥 Loading Zoom demo data...")
        zoom_count = seed_zoom_demo_data()
        logger.info(f"✅ Loaded {zoom_count} Zoom items")
    except Exception as e:
        logger.error(f"❌ Failed to load Zoom demo data: {e}")

    # Final summary
    with get_db_context() as db:
        total_feedback = db.query(Feedback).count()
        total_customers = db.query(Customer).count()

    logger.info("=" * 60)
    logger.info("✅ Demo data seed completed!")
    logger.info(f"📊 Total customers: {total_customers}")
    logger.info(f"📊 Total feedback items: {total_feedback}")
    logger.info("=" * 60)
    logger.info("🎯 Next step: Run 'make cluster' to generate insights!")
