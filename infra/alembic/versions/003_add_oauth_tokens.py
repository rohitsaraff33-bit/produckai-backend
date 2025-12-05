"""Add OAuth tokens table

Revision ID: 003_add_oauth_tokens
Revises: 002_add_gdocs_zoom
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '003_add_oauth_tokens'
down_revision = '002_add_gdocs_zoom'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types with error handling
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'oauthprovider') THEN
                CREATE TYPE oauthprovider AS ENUM ('google', 'zoom');
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tokenstatus') THEN
                CREATE TYPE tokenstatus AS ENUM ('active', 'revoked', 'expired');
            END IF;
        END $$;
    """)

    # Create oauth_tokens table using raw SQL
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id UUID PRIMARY KEY,
            user_id UUID,
            provider oauthprovider NOT NULL,
            account_email VARCHAR(255),
            scopes TEXT NOT NULL,
            access_token_enc TEXT NOT NULL,
            refresh_token_enc TEXT,
            expires_at TIMESTAMP NOT NULL,
            status tokenstatus NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes with IF NOT EXISTS
    op.execute("CREATE INDEX IF NOT EXISTS ix_oauth_tokens_provider ON oauth_tokens(provider)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_oauth_tokens_expires_at ON oauth_tokens(expires_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_oauth_tokens_status ON oauth_tokens(status)")


def downgrade():
    op.drop_index('ix_oauth_tokens_status', 'oauth_tokens')
    op.drop_index('ix_oauth_tokens_expires_at', 'oauth_tokens')
    op.drop_index('ix_oauth_tokens_provider', 'oauth_tokens')
    op.drop_table('oauth_tokens')
    op.execute('DROP TYPE tokenstatus')
    op.execute('DROP TYPE oauthprovider')
