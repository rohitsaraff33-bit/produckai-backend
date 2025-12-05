"""Add insights tables

Revision ID: 004_add_insights
Revises: 003_add_oauth_tokens
Create Date: 2025-01-07 01:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '004_add_insights'
down_revision = '003_add_oauth_tokens'
branch_labels = None
depends_on = None


def upgrade():
    # Create insights table
    op.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id UUID PRIMARY KEY,
            theme_id UUID NOT NULL REFERENCES themes(id),
            title VARCHAR(500) NOT NULL,
            description TEXT,
            impact TEXT,
            recommendation TEXT,
            severity VARCHAR(50),
            effort VARCHAR(50),
            priority_score INTEGER DEFAULT 0,
            supporting_feedback_ids JSON,
            key_quotes JSON,
            affected_customers JSON,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    # Create insight_feedback association table
    op.execute("""
        CREATE TABLE IF NOT EXISTS insight_feedback (
            insight_id UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
            feedback_id UUID NOT NULL REFERENCES feedback(id) ON DELETE CASCADE,
            relevance_score INTEGER DEFAULT 100,
            is_key_quote INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            PRIMARY KEY (insight_id, feedback_id)
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_insights_theme_id ON insights(theme_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_insights_priority_score ON insights(priority_score)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_insight_feedback_insight_id ON insight_feedback(insight_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_insight_feedback_feedback_id ON insight_feedback(feedback_id)")


def downgrade():
    op.drop_table('insight_feedback')
    op.drop_table('insights')
