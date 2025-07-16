#!/bin/bash
set -e

# Function to log messages to stderr (won't interfere with STDIO)
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Ensure PostgreSQL directories exist
mkdir -p /var/run/postgresql /var/lib/postgresql/16/main /var/log/sage
chown -R postgres:postgres /var/run/postgresql /var/lib/postgresql /var/log/postgresql || true
chown -R sage:sage /var/log/sage || true

# Initialize PostgreSQL if needed
if [ ! -s "/var/lib/postgresql/16/main/PG_VERSION" ]; then
    log "Initializing PostgreSQL database..."
    su - postgres -c "/usr/lib/postgresql/16/bin/initdb -D /var/lib/postgresql/16/main --locale=C.UTF-8"
fi

# Start PostgreSQL in the background
log "Starting PostgreSQL..."
su - postgres -c "/usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/16/main" &
PG_PID=$!

# Wait for PostgreSQL to be ready
log "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if su - postgres -c "pg_isready -h localhost -p 5432" >/dev/null 2>&2; then
        log "PostgreSQL is ready"
        break
    fi
    sleep 1
done

# Run initialization script if database doesn't exist
if ! su - postgres -c "psql -lqt" | cut -d \| -f 1 | grep -qw sage; then
    log "Running database initialization..."
    su - postgres -c "psql -f /docker-entrypoint-initdb.d/init-db.sql"
fi

# Export environment variables for the application
export SAGE_DB_HOST=localhost
export SAGE_DB_PORT=5432
export SAGE_DB_NAME=sage
export SAGE_DB_USER=sage
export SAGE_DB_PASSWORD=sage
export SAGE_USE_HASH_VECTORIZER=true
export SAGE_LOG_DIR=/var/log/sage

# Create log file with correct permissions
touch /var/log/sage/sage_mcp_stdio.log
chown sage:sage /var/log/sage/sage_mcp_stdio.log

# Start the STDIO service as sage user
log "Starting Sage MCP STDIO service..."
exec su - sage -c "cd /app && python /app/sage_mcp_stdio_single.py"