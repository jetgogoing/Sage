#!/bin/bash
# Entrypoint script for Sage MCP Single Container
set -e

# Function to wait for PostgreSQL with exponential backoff
wait_for_postgres() {
    local MAX_ATTEMPTS=30
    local attempt=1
    local wait_time=1
    
    echo "[INIT] Waiting for PostgreSQL to start..."
    
    while [ $attempt -le $MAX_ATTEMPTS ]; do
        if su - postgres -c "pg_isready -q"; then
            echo "[INIT] PostgreSQL is ready"
            return 0
        fi
        
        echo "[INIT] Attempt $attempt/$MAX_ATTEMPTS: PostgreSQL not ready, waiting ${wait_time}s..."
        sleep $wait_time
        
        # Exponential backoff with max wait of 30s
        wait_time=$((wait_time * 2))
        if [ $wait_time -gt 30 ]; then
            wait_time=30
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo "[ERROR] PostgreSQL failed to start after $MAX_ATTEMPTS attempts"
    return 1
}

# Initialize PostgreSQL if not already initialized
if [ ! -d "$PGDATA" ] || [ -z "$(ls -A "$PGDATA")" ]; then
    echo "[INIT] Initializing PostgreSQL database..."
    mkdir -p "$PGDATA"
    chown -R postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
    
    # Initialize database
    su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D $PGDATA"
    
    # Configure PostgreSQL for local connections
    echo "host    all             all             127.0.0.1/32            trust" >> "$PGDATA/pg_hba.conf"
    echo "local   all             all                                     trust" >> "$PGDATA/pg_hba.conf"
    echo "listen_addresses = 'localhost'" >> "$PGDATA/postgresql.conf"
fi

# Start PostgreSQL
echo "[INIT] Starting PostgreSQL..."
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D $PGDATA -l /var/log/postgresql/postgresql.log start"

# Wait for PostgreSQL to be ready
wait_for_postgres

# Create database and user if they don't exist
echo "[INIT] Setting up Sage database..."
su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname = 'sage_memory'\" | grep -q 1 || createdb sage_memory"
su - postgres -c "psql -tc \"SELECT 1 FROM pg_user WHERE usename = 'sage'\" | grep -q 1 || createuser sage"
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE sage_memory TO sage;\""

# Skip pgvector installation - using hash vectorization with JSONB instead
echo "[INIT] Using hash-based vectorization (no pgvector needed)..."

# Run initialization SQL if exists
if [ -f /docker-entrypoint-initdb.d/init.sql ]; then
    echo "[INIT] Running initialization SQL..."
    su - postgres -c "psql -d sage_memory -f /docker-entrypoint-initdb.d/init.sql"
fi

# Set environment variables for the application
export DATABASE_URL="postgresql://sage:sage@localhost:5432/sage_memory"
export SAGE_ENV="production"
export SAGE_LOG_LEVEL="INFO"

# Start the STDIO service
# All logs go to files, keeping STDIO clean for MCP protocol
echo "[INIT] Starting Sage MCP STDIO service..."
exec python -u /app/sage_mcp_stdio_single.py