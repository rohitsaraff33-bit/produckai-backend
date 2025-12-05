"""Ingest Jira data."""

from apps.api.scripts.seed_demo import ingest_jira_data

if __name__ == "__main__":
    count = ingest_jira_data()
    print(f"Ingested {count} Jira issues")
