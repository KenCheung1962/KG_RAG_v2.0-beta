-- Migration: Add embedding column to relationships table
-- This enables vector similarity search on relationship descriptions

-- Add embedding column
ALTER TABLE relationships 
ADD COLUMN IF NOT EXISTS embedding VECTOR(768);  -- nomic-embed-text dimension

-- Create HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_relationships_embedding 
ON relationships 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Add description column if not exists (for relationship text)
ALTER TABLE relationships 
ADD COLUMN IF NOT EXISTS description TEXT;

-- Add keywords column for quick filtering
ALTER TABLE relationships 
ADD COLUMN IF NOT EXISTS keywords TEXT;

-- Index for keyword search
CREATE INDEX IF NOT EXISTS idx_relationships_keywords 
ON relationships USING GIN(to_tsvector('english', COALESCE(keywords, '')));

COMMENT ON COLUMN relationships.embedding IS 'Vector embedding of relationship description for semantic search';
COMMENT ON COLUMN relationships.description IS 'Human-readable description of the relationship';
COMMENT ON COLUMN relationships.keywords IS 'Keywords extracted from relationship for filtering';
