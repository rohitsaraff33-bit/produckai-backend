"""Add Google Docs and Zoom support

Revision ID: 002_add_gdocs_zoom
Revises: 001_initial
Create Date: 2025-01-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_gdocs_zoom'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add new enum values to feedbacksource
    op.execute("ALTER TYPE feedbacksource ADD VALUE IF NOT EXISTS 'gdoc'")
    op.execute("ALTER TYPE feedbacksource ADD VALUE IF NOT EXISTS 'zoom'")

    # Add new columns to feedback table
    op.add_column('feedback', sa.Column('doc_url', sa.Text(), nullable=True))
    op.add_column('feedback', sa.Column('speaker', sa.Text(), nullable=True))
    op.add_column('feedback', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('feedback', sa.Column('ended_at', sa.DateTime(), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column('feedback', 'ended_at')
    op.drop_column('feedback', 'started_at')
    op.drop_column('feedback', 'speaker')
    op.drop_column('feedback', 'doc_url')

    # Note: Cannot remove enum values in PostgreSQL without recreating the entire enum type
    # This would require complex migration with table data preservation
    # For downgrade, we leave the enum values in place but they won't be used
