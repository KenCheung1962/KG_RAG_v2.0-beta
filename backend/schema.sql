-- KG_RAG PostgreSQL Schema with pgvector
-- Version: 1.0.0

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Entities Table (knowledge graph nodes)
-- ============================================
CREATE TABLE IF NOT EXISTS entities (
    id              SERIAL PRIMARY KEY,
    entity_id       VARCHAR(255) UNIQUE NOT NULL,
    entity_type     VARCHAR(100) NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    properties      JSONB DEFAULT '{}',
    embedding       VECTOR(768),  -- nomic-embed-text dimension
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for vector similarity search on entities
CREATE INDEX IF NOT EXISTS idx_entities_embedding 
ON entities 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index for entity type queries
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

-- Index for entity_id lookups
CREATE INDEX IF NOT EXISTS idx_entities_entity_id ON entities(entity_id);

-- ============================================
-- Relationships Table (knowledge graph edges)
-- ============================================
CREATE TABLE IF NOT EXISTS relationships (
    id              SERIAL PRIMARY KEY,
    relationship_id VARCHAR(255) UNIQUE NOT NULL,
    source_id       VARCHAR(255) NOT NULL,
    target_id       VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(100) NOT NULL,
    properties      JSONB DEFAULT '{}',
    weight          FLOAT DEFAULT 1.0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for relationship lookups by source
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);

-- Index for relationship lookups by target
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id);

-- Index for relationship type queries
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);

-- Composite index for traversal queries
CREATE INDEX IF NOT EXISTS idx_relationships_source_target 
ON relationships(source_id, target_id);

-- ============================================
-- Chunks Table (text chunks for RAG)
-- ============================================
CREATE TABLE IF NOT EXISTS chunks (
    id              SERIAL PRIMARY KEY,
    chunk_id        VARCHAR(255) UNIQUE NOT NULL,
    entity_id       VARCHAR(255) REFERENCES entities(entity_id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    source          VARCHAR(255),
    chunk_index     INTEGER DEFAULT 0,
    embedding       VECTOR(768),  -- nomic-embed-text dimension
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for vector similarity search on chunks
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
ON chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index for chunk lookups by entity
CREATE INDEX IF NOT EXISTS idx_chunks_entity_id ON chunks(entity_id);

-- Index for source queries
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);

-- ============================================
-- Full-text search indexes (optional enhancement)
-- ============================================
ALTER TABLE entities ADD COLUMN IF NOT EXISTS name_tsv tsvector 
    GENERATED ALWAYS AS (to_tsvector('english', name)) STORED;

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS content_tsv tsvector 
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS idx_entities_name_fts ON entities USING GIN(name_tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_content_fts ON chunks USING GIN(content_tsv);

-- ============================================
-- Function: Similarity search with hybrid scoring
-- ============================================
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_limit INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id VARCHAR(255),
    content TEXT,
    source TEXT,
    similarity FLOAT
) LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.chunk_id,
        c.content,
        c.source,
        (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE c.embedding <=> query_embedding < (1 - match_threshold)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_limit;
END;
$$;

-- ============================================
-- Function: Auto-update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_entities_updated_at 
    BEFORE UPDATE ON entities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Comments for documentation
-- ============================================
COMMENT ON TABLE entities IS 'Knowledge graph entities with vector embeddings';
COMMENT ON TABLE relationships IS 'Knowledge graph relationships/edges between entities';
COMMENT ON TABLE chunks IS 'Text chunks for RAG retrieval with vector embeddings';
COMMENT ON INDEX idx_entities_embedding IS 'HNSW index for entity similarity search';
COMMENT ON INDEX idx_chunks_embedding IS 'HNSW index for chunk similarity search';
