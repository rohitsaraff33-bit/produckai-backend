"""Initial schema with all tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("acv", sa.Float(), nullable=False),
        sa.Column("segment", sa.Enum("SMB", "MM", "ENT", name="customersegment"), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_customers_name"), "customers", ["name"], unique=True)

    # Create feedback table
    op.create_table(
        "feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.Enum("SLACK", "JIRA", "LINEAR", "UPLOAD", name="feedbacksource"), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("account", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_created_at"), "feedback", ["created_at"], unique=False)
    op.create_index(op.f("ix_feedback_source"), "feedback", ["source"], unique=False)

    # Create themes table
    op.create_table(
        "themes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("centroid", Vector(384), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_themes_updated_at"), "themes", ["updated_at"], unique=False)

    # Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Enum("TICKET", "PRD", "ROADMAP", name="artifactkind"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_artifacts_external_id"), "artifacts", ["external_id"], unique=True)
    op.create_index(op.f("ix_artifacts_kind"), "artifacts", ["kind"], unique=False)

    # Create feedback_theme junction table
    op.create_table(
        "feedback_theme",
        sa.Column("feedback_id", sa.UUID(), nullable=False),
        sa.Column("theme_id", sa.UUID(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedback.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("feedback_id", "theme_id"),
    )

    # Create artifact_theme junction table
    op.create_table(
        "artifact_theme",
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("theme_id", sa.UUID(), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id", "theme_id"),
    )

    # Create theme_metrics table
    op.create_table(
        "theme_metrics",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("theme_id", sa.UUID(), nullable=False),
        sa.Column("freq_30d", sa.Integer(), nullable=False),
        sa.Column("freq_90d", sa.Integer(), nullable=False),
        sa.Column("acv_sum", sa.Float(), nullable=False),
        sa.Column("sentiment", sa.Float(), nullable=False),
        sa.Column("trend", sa.Float(), nullable=False),
        sa.Column("dup_penalty", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("theme_id"),
    )
    op.create_index(op.f("ix_theme_metrics_score"), "theme_metrics", ["score"], unique=False)

    # Create vector indexes for similarity search (using ivfflat)
    # Note: These require data to be present, so we'll create them after initial data load
    # For now, we'll add them as raw SQL to avoid Alembic issues
    op.execute("CREATE INDEX IF NOT EXISTS idx_feedback_embedding ON feedback USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_themes_centroid ON themes USING ivfflat (centroid vector_cosine_ops) WITH (lists = 50)")

    # Create full-text search index on feedback text
    op.execute("CREATE INDEX IF NOT EXISTS idx_feedback_text_fts ON feedback USING gin(to_tsvector('english', text))")


def downgrade() -> None:
    op.drop_index("idx_feedback_text_fts", table_name="feedback")
    op.drop_index("idx_themes_centroid", table_name="themes")
    op.drop_index("idx_feedback_embedding", table_name="feedback")
    op.drop_index(op.f("ix_theme_metrics_score"), table_name="theme_metrics")
    op.drop_table("theme_metrics")
    op.drop_table("artifact_theme")
    op.drop_table("feedback_theme")
    op.drop_index(op.f("ix_artifacts_kind"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_external_id"), table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index(op.f("ix_themes_updated_at"), table_name="themes")
    op.drop_table("themes")
    op.drop_index(op.f("ix_feedback_source"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_created_at"), table_name="feedback")
    op.drop_table("feedback")
    op.drop_index(op.f("ix_customers_name"), table_name="customers")
    op.drop_table("customers")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS artifactkind")
    op.execute("DROP TYPE IF EXISTS customersegment")
    op.execute("DROP TYPE IF EXISTS feedbacksource")
