#!/bin/bash
set -e

# Simple logging to stderr
log() {
    >&2 echo "[$(date '+%H:%M:%S')] $1"
}

# Fix permissions
chown -R postgres:postgres /var/lib/postgresql /run/postgresql 2>/dev/null || true
chown -R sage:sage /var/log/sage 2>/dev/null || true

# Initialize PostgreSQL if needed
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    log "Initializing PostgreSQL..."
    su-exec postgres initdb -D "$PGDATA" --auth-local=trust --auth-host=trust
    
    # Simple config
    cat >> "$PGDATA/postgresql.conf" <<EOF
listen_addresses = 'localhost'
logging_collector = off
log_destination = 'stderr'
EOF
fi

# Start PostgreSQL
log "Starting PostgreSQL..."
su-exec postgres postgres -D "$PGDATA" &
PGPID=$!

# Wait for PostgreSQL with exponential backoff
log "Waiting for PostgreSQL..."
MAX_ATTEMPTS=30
attempt=0
wait_time=1

while [ $attempt -lt $MAX_ATTEMPTS ]; do
    if su-exec postgres pg_isready -q -h localhost -p 5432; then
        log "PostgreSQL is ready"
        break
    fi
    
    attempt=$((attempt + 1))
    if [ $attempt -eq $MAX_ATTEMPTS ]; then
        log "ERROR: PostgreSQL failed to start after $MAX_ATTEMPTS attempts"
        kill $PGPID 2>/dev/null || true
        exit 1
    fi
    
    log "PostgreSQL not ready, attempt $attempt/$MAX_ATTEMPTS, waiting ${wait_time}s..."
    sleep $wait_time
    
    # Exponential backoff with max 5s
    if [ $wait_time -lt 5 ]; then
        wait_time=$((wait_time * 2))
    fi
done

# Initialize database
if ! su-exec postgres psql -lqt | grep -q sage; then
    log "Creating database..."
    su-exec postgres createuser -s sage 2>/dev/null || true
    su-exec postgres createdb -O sage sage 2>/dev/null || true
fi

# Prepare log file
touch /var/log/sage/sage_mcp_stdio.log
chown sage:sage /var/log/sage/sage_mcp_stdio.log

# Start Sage MCP
log "Starting Sage MCP..."
exec su-exec sage python /app/sage_mcp_stdio_single.py