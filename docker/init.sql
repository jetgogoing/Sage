-- Sage MCP Database Initialization Script
-- Creates tables for memory storage with pgvector support

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create memories table with vector storage
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255),
    user_input TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    embedding vector(4096),  -- Store 4096-dimensional vectors
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
-- Note: For 4096 dimensions, we skip the vector index as ivfflat has a 2000 dimension limit
-- HNSW index would work but requires more setup. Sequential scan will be used for now.

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active DESC);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create a default session
INSERT INTO sessions (id, name, metadata) 
VALUES ('default', 'Default Session', '{"description": "Default session for MCP"}')
ON CONFLICT (id) DO NOTHING;

-- Grant permissions to sage user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sage;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sage;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO sage;