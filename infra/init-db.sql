-- Initialize Postgres database with pgvector extension
-- This runs automatically on first startup via docker-entrypoint-initdb.d

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE produckai TO produckai;

-- Set default search path
ALTER DATABASE produckai SET search_path TO public;
