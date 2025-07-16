#!/bin/bash
set -e

# Function to log messages to stderr (won't interfere with STDIO)
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Ensure directories exist with correct permissions
mkdir -p /run/postgresql /var/log/sage /var/lib/postgresql/data
chown -R postgres:postgres /run/postgresql /var/lib/postgresql
chown -R sage:sage /var/log/sage

# Configure PostgreSQL
if [ ! -f /var/lib/postgresql/data/postgresql.conf ]; then
    cat > /tmp/postgresql.conf <<EOF
listen_addresses = 'localhost'
port = 5432
shared_preload_libraries = 'pgvector'
log_destination = 'stderr'
logging_collector = off
EOF
fi

# Initialize PostgreSQL if needed
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    log "Initializing PostgreSQL database..."
    su-exec postgres initdb -D "$PGDATA" --locale=C --encoding=UTF8 --auth-local=trust --auth-host=trust
    cp /tmp/postgresql.conf "$PGDATA/postgresql.conf" 2>/dev/null || true
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
    su-exec postgres psql < /docker-entrypoint-initdb.d/init-db.sql
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