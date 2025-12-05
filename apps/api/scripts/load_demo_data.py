"""Load demo data from Slack and Jira samples into the database."""

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from apps.api.config import get_settings
from apps.api.database import get_db_context
from apps.api.models import Customer, CustomerSegment, Feedback, FeedbackSource
from apps.api.services.embeddings import get_embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

# Map account names to customer segments and ACV
CUSTOMER_DATA = {
    "Acme Corp": {"segment": CustomerSegment.ENT, "acv": 140000},
    "TechStart Inc": {"segment": CustomerSegment.MM, "acv": 60000},
    "SmallBiz LLC": {"segment": CustomerSegment.SMB, "acv": 12000},
    "Enterprise Solutions": {"segment": CustomerSegment.ENT, "acv": 350000},
    "MidCo Industries": {"segment": CustomerSegment.MM, "acv": 70000},
    "Delta Inc": {"segment": CustomerSegment.MM, "acv": 50000},
    "Epsilon LLC": {"segment": CustomerSegment.ENT, "acv": 320000},
    "Zeta Systems": {"segment": CustomerSegment.SMB, "acv": 120000},
    "Eta Enterprises": {"segment": CustomerSegment.ENT, "acv": 240000},
    "Theta Group": {"segment": CustomerSegment.MM, "acv": 130000},
    "Iota Tech": {"segment": CustomerSegment.SMB, "acv": 50000},
    "Kappa Holdings": {"segment": CustomerSegment.MM, "acv": 70000},
    "Lambda Corp": {"segment": CustomerSegment.ENT, "acv": 280000},
    "Mu Ventures": {"segment": CustomerSegment.SMB, "acv": 45000},
    "Nu Solutions": {"segment": CustomerSegment.MM, "acv": 85000},
}


def get_or_create_customer(db, account_name: str):
    """Get existing customer or create new one."""
    customer = db.query(Customer).filter(Customer.name == account_name).first()

    if not customer:
        customer_info = CUSTOMER_DATA.get(account_name, {
            "segment": CustomerSegment.SMB,
            "acv": 25000
        })

        customer = Customer(
            id=uuid4(),
            name=account_name,
            segment=customer_info["segment"],
            acv=customer_info["acv"],
        )
        db.add(customer)
        db.flush()
        logger.info(f"Created customer: {account_name} ({customer_info['segment'].value}, ${customer_info['acv']})")

    return customer


def load_slack_messages():
    """Load Slack demo messages as feedback."""
    slack_file = Path(__file__).parent.parent.parent.parent / "samples" / "slack" / "demo_messages.jsonl"

    if not slack_file.exists():
        logger.warning(f"Slack demo file not found: {slack_file}")
        return 0

    with get_db_context() as db:
        # Get embedding service
        embedding_service = get_embedding_service()

        count = 0
        with open(slack_file, 'r') as f:
            for line in f:
                message = json.loads(line.strip())

                # Get or create customer
                customer = get_or_create_customer(db, message["account"])

                # Check if message already exists
                existing = db.query(Feedback).filter(
                    Feedback.source == FeedbackSource.slack,
                    Feedback.source_id == message["ts"]
                ).first()

                if existing:
                    continue

                # Generate embedding
                embedding = embedding_service.embed_text(message["text"])

                # Create feedback
                feedback = Feedback(
                    id=uuid4(),
                    source=FeedbackSource.slack,
                    source_id=message["ts"],
                    account=message["account"],
                    text=message["text"],
                    embedding=embedding,
                    created_at=datetime.fromisoformat(message["created_at"].replace('Z', '+00:00')),
                    meta={
                        "channel": message["channel"],
                        "user": message["user"],
                    },
                    customer_id=customer.id,
                )
                db.add(feedback)
                count += 1

        db.commit()
        logger.info(f"✅ Loaded {count} Slack messages")
        return count


def load_jira_issues():
    """Load Jira demo issues as feedback."""
    jira_file = Path(__file__).parent.parent.parent.parent / "samples" / "jira" / "demo_issues.json"

    if not jira_file.exists():
        logger.warning(f"Jira demo file not found: {jira_file}")
        return 0

    with get_db_context() as db:
        # Get embedding service
        embedding_service = get_embedding_service()

        with open(jira_file, 'r') as f:
            issues = json.load(f)

        count = 0
        for issue in issues:
            # Get or create customer
            customer = get_or_create_customer(db, issue["account"])

            # Check if issue already exists
            existing = db.query(Feedback).filter(
                Feedback.source == FeedbackSource.jira,
                Feedback.source_id == issue["key"]
            ).first()

            if existing:
                continue

            # Combine title and description for better context
            full_text = f"{issue['title']}. {issue['description']}"

            # Generate embedding
            embedding = embedding_service.embed_text(full_text)

            # Create feedback
            feedback = Feedback(
                id=uuid4(),
                source=FeedbackSource.jira,
                source_id=issue["key"],
                account=issue["account"],
                text=full_text,
                embedding=embedding,
                created_at=datetime.fromisoformat(issue["created_at"].replace('Z', '+00:00')),
                meta={
                    "title": issue["title"],
                    "status": issue["status"],
                    "priority": issue["priority"],
                },
                customer_id=customer.id,
            )
            db.add(feedback)
            count += 1

        db.commit()
        logger.info(f"✅ Loaded {count} Jira issues")
        return count


def main():
    """Load all demo data."""
    logger.info("Loading demo data from Slack and Jira...")

    slack_count = load_slack_messages()
    jira_count = load_jira_issues()

    total = slack_count + jira_count
    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Demo data loading complete!")
    logger.info(f"   - Slack messages: {slack_count}")
    logger.info(f"   - Jira issues: {jira_count}")
    logger.info(f"   - Total feedback: {total}")
    logger.info(f"{'='*50}")
    logger.info("\nNext steps:")
    logger.info("1. Run clustering: docker compose exec api python apps/api/scripts/run_clustering.py")
    logger.info("2. Visit http://localhost:3000 to see insights")


if __name__ == "__main__":
    main()
