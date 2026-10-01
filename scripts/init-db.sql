-- =============================================================================
-- AURA — Database Initialization Script
-- Runs once when the PostgreSQL container is first created.
-- =============================================================================

-- Enable the pgvector extension for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable btree_gin for efficient composite indexes
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'AURA database initialized with extensions: vector, uuid-ossp, pg_trgm, btree_gin';
END
$$;
