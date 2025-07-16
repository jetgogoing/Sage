#!/bin/bash
set -e

# Function to log messages to stderr (won't interfere with STDIO)
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Ensure log directory exists with correct permissions
mkdir -p /var/log/sage
chown -R postgres:postgres /var/log/sage

# Initialize PostgreSQL if needed
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    log "Initializing PostgreSQL database..."
    su - postgres -c "/usr/lib/postgresql/16/bin/initdb -D $PGDATA"
fi

# Start PostgreSQL
log "Starting PostgreSQL..."
su - postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D $PGDATA -l /var/log/sage/postgresql.log start"

# Wait for PostgreSQL to be ready
log "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if pg_isready -h localhost -p 5432 -U postgres >/dev/null 2>&2; then
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

# Ensure log directory exists and has correct permissions
mkdir -p /var/log/sage
touch /var/log/sage/sage_mcp_stdio.log
chown sage:sage /var/log/sage/sage_mcp_stdio.log

# Export environment variables for the application
export SAGE_DB_HOST=localhost
export SAGE_DB_PORT=5432
export SAGE_DB_NAME=sage
export SAGE_DB_USER=sage
export SAGE_DB_PASSWORD=sage

# Start the STDIO service
# All logs go to files, keeping STDIO clean for MCP protocol
log "Starting Sage MCP STDIO service..."
exec su - sage -c "cd /app && python /app/sage_mcp_stdio_single.py"