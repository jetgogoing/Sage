-- Sage MCP Minimal Database Initialization (No pgvector)

-- Create sage user and database
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'sage') THEN
      CREATE USER sage WITH PASSWORD 'sage';
   END IF;
END
$do$;

-- Create database if not exists
SELECT 'CREATE DATABASE sage OWNER sage'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sage')\gexec

-- Connect to sage database
\c sage

-- Grant all privileges to sage user
GRANT ALL PRIVILEGES ON DATABASE sage TO sage;
GRANT ALL ON SCHEMA public TO sage;

-- Note: Tables will be created by the application
-- No pgvector extension needed for hash vectorization