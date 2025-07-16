-- Sage MCP Database Initialization Script

-- Create sage user and database
CREATE USER sage WITH PASSWORD 'sage';
CREATE DATABASE sage OWNER sage;

-- Connect to sage database
\c sage

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant all privileges to sage user
GRANT ALL PRIVILEGES ON DATABASE sage TO sage;
GRANT ALL ON SCHEMA public TO sage;

-- Create memories table (will be created by application, but we prepare the schema)
-- The application will handle the actual table creation with proper vector dimensions