#!/bin/bash
set -e

# Function to log messages to stderr (won't interfere with STDIO)
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Ensure directories exist with correct permissions
mkdir -p /run/postgresql /var/log/sage
chown postgres:postgres /run/postgresql
chown sage:sage /var/log/sage

# Initialize PostgreSQL if needed
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    log "Initializing PostgreSQL database..."
    su-exec postgres initdb -D "$PGDATA" --locale=C --encoding=UTF8
fi

# Start PostgreSQL
log "Starting PostgreSQL..."
su-exec postgres postgres -D "$PGDATA" &
PG_PID=$!

# Wait for PostgreSQL to be ready
log "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if su-exec postgres pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        log "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log "PostgreSQL failed to start"
        exit 1
    fi
    sleep 1
done

# Run initialization script if database doesn't exist
if ! su-exec postgres psql -lqt | cut -d \| -f 1 | grep -qw sage; then
    log "Running database initialization..."
    su-exec postgres psql -f /docker-entrypoint-initdb.d/init-db.sql
fi

# Create log file with correct permissions
touch /var/log/sage/sage_mcp_stdio.log
chown sage:sage /var/log/sage/sage_mcp_stdio.log

# Export environment variables
export SAGE_DB_HOST=localhost
export SAGE_DB_PORT=5432
export SAGE_DB_NAME=sage
export SAGE_DB_USER=sage
export SAGE_DB_PASSWORD=sage
export SAGE_USE_HASH_VECTORIZER=true
export SAGE_LOG_DIR=/var/log/sage

# Start the STDIO service
log "Starting Sage MCP STDIO service..."
exec su-exec sage python /app/sage_mcp_stdio_single.py