#!/usr/bin/env python3
"""Simple database initialization script.

Creates all database tables using SQLAlchemy models.
Run this from the produckai directory:
    python init_db_simple.py
"""

import sys
from pathlib import Path

# Add apps directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from apps.api.database import Base, engine
try:
    from apps.api.models import (
        Customer,
        Feedback,
        FeedbackTheme,
        Theme,
        ThemeMetrics,
        Insight,
        InsightFeedback,
        JiraInsightMatch,
        JiraTicket,
        Artifact,
        ArtifactTheme,
        OAuthToken,
    )
except ImportError as e:
    # If some models are missing, that's okay for basic setup
    from apps.api.models import Customer, Feedback, Theme, Insight
    print(f"⚠️  Warning: Some optional models couldn't be imported: {e}")

print("🔧 Initializing ProduckAI database...")
print(f"📍 Database URL: {engine.url}")

# Import all models to ensure they're registered with Base
# (already done above)

# Create all tables
try:
    print("\n📋 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

    print("\n📊 Created tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")

    print("\n🎉 Database initialization complete!")
    print("\nYou can now:")
    print("  1. Upload feedback CSV files")
    print("  2. Run clustering")
    print("  3. Generate insights")

except Exception as e:
    print(f"\n❌ Error creating tables: {e}")
    sys.exit(1)
