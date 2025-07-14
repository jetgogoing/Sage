-- PostgreSQL pgvector extension initialization
-- This script runs when the database is first created

-- Create the vector extension for storing embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify the extension is installed
SELECT * FROM pg_extension WHERE extname = 'vector';