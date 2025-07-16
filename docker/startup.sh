#!/bin/bash
set -e

echo "[STARTUP] Sage MCP Server starting..."

# Initialize PostgreSQL if needed
if [ ! -d "$PGDATA" ] || [ -z "$(ls -A "$PGDATA")" ]; then
    echo "[STARTUP] Initializing PostgreSQL..."
    mkdir -p "$PGDATA"
    chown -R postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
    
    # Initialize database
    su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D $PGDATA"
    
    # Configure PostgreSQL
    echo "host    all             all             127.0.0.1/32            trust" >> "$PGDATA/pg_hba.conf"
    echo "local   all             all                                     trust" >> "$PGDATA/pg_hba.conf"
    echo "listen_addresses = 'localhost'" >> "$PGDATA/postgresql.conf"
fi

# Start supervisor (which manages PostgreSQL)
echo "[STARTUP] Starting Supervisor..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf &
SUPERVISOR_PID=$!

# Wait for PostgreSQL to be ready
echo "[STARTUP] Waiting for PostgreSQL..."
MAX_ATTEMPTS=30
attempt=1
while [ $attempt -le $MAX_ATTEMPTS ]; do
    if su - postgres -c "pg_isready -q"; then
        echo "[STARTUP] PostgreSQL is ready"
        break
    fi
    echo "[STARTUP] Attempt $attempt/$MAX_ATTEMPTS: PostgreSQL not ready, waiting..."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $MAX_ATTEMPTS ]; then
    echo "[STARTUP] ERROR: PostgreSQL failed to start"
    exit 1
fi

# Create database and user
echo "[STARTUP] Setting up database..."
su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname = 'sage_memory'\" | grep -q 1 || createdb sage_memory"
su - postgres -c "psql -tc \"SELECT 1 FROM pg_user WHERE usename = 'sage'\" | grep -q 1 || createuser sage"
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE sage_memory TO sage;\""

# Run initialization SQL
if [ -f /docker-entrypoint-initdb.d/init.sql ]; then
    echo "[STARTUP] Running initialization SQL..."
    su - postgres -c "psql -d sage_memory -f /docker-entrypoint-initdb.d/init.sql"
fi

# Start MCP service via supervisor
echo "[STARTUP] Starting MCP STDIO service..."
supervisorctl start sage-mcp

# Keep container running and forward MCP stdio
echo "[STARTUP] MCP service started, forwarding STDIO..."
exec tail -f /dev/null