"""Add competitive intelligence tables

Revision ID: 005_add_competitive_intelligence
Revises: 004_add_insights
Create Date: 2025-01-11 04:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '005_add_competitive_intelligence'
down_revision = '004_add_insights'
branch_labels = None
depends_on = None


def upgrade():
    # Add category column to insights table
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'insightcategory') THEN
                CREATE TYPE insightcategory AS ENUM ('customer_feedback', 'competitive_intel');
            END IF;
        END$$;
    """)

    op.execute("""
        ALTER TABLE insights
        ADD COLUMN IF NOT EXISTS category insightcategory NOT NULL DEFAULT 'customer_feedback'
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_insights_category ON insights(category)")

    # Make theme_id nullable for competitive insights
    op.execute("""
        ALTER TABLE insights
        ALTER COLUMN theme_id DROP NOT NULL
    """)

    # Create competitors table
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'competitorstatus') THEN
                CREATE TYPE competitorstatus AS ENUM ('active', 'paused', 'archived');
            END IF;
        END$$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            website_url TEXT,
            description TEXT,
            status competitorstatus NOT NULL DEFAULT 'active',
            market_scope TEXT,
            target_personas JSON,
            geo_segments JSON,
            last_researched_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_competitors_status ON competitors(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_competitors_name ON competitors(name)")

    # Create research_sessions table
    op.execute("""
        CREATE TABLE IF NOT EXISTS research_sessions (
            id UUID PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL,
            market_scope TEXT NOT NULL,
            target_personas JSON NOT NULL,
            geo_segments JSON NOT NULL,
            time_window_months VARCHAR(50) NOT NULL DEFAULT '12',
            competitors_researched JSON NOT NULL,
            insights_generated JSON,
            status VARCHAR(50) NOT NULL DEFAULT 'running',
            error_message TEXT,
            sources_consulted JSON,
            started_at TIMESTAMP NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMP
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_research_sessions_status ON research_sessions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_sessions_company ON research_sessions(company_name)")

    # Create competitive_insight_metadata table
    op.execute("""
        CREATE TABLE IF NOT EXISTS competitive_insight_metadata (
            id UUID PRIMARY KEY,
            insight_id UUID NOT NULL UNIQUE,
            competitor_name VARCHAR(255) NOT NULL,
            competitor_moves JSON,
            evidence_count VARCHAR(50),
            mentions_30d VARCHAR(50),
            impacted_acv_usd VARCHAR(100),
            est_method VARCHAR(100),
            severity_weight VARCHAR(50),
            urgency_score VARCHAR(50),
            reach_score VARCHAR(50),
            confidence_score VARCHAR(50),
            effort_inverse VARCHAR(50),
            citations JSON,
            research_session_id UUID,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_competitive_metadata_insight_id ON competitive_insight_metadata(insight_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_competitive_metadata_competitor ON competitive_insight_metadata(competitor_name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_competitive_metadata_session ON competitive_insight_metadata(research_session_id)")


def downgrade():
    op.drop_table('competitive_insight_metadata')
    op.drop_table('research_sessions')
    op.drop_table('competitors')
    op.execute("DROP TYPE IF EXISTS competitorstatus")
    op.execute("ALTER TABLE insights DROP COLUMN IF EXISTS category")
    op.execute("DROP TYPE IF EXISTS insightcategory")
    op.execute("""
        ALTER TABLE insights
        ALTER COLUMN theme_id SET NOT NULL
    """)
