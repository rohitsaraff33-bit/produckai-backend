"""Ingest Slack data."""

from apps.api.scripts.seed_demo import ingest_slack_data

if __name__ == "__main__":
    count = ingest_slack_data()
    print(f"Ingested {count} Slack messages")
