# Sage MCP Server - Production Ready with pgvector
FROM pgvector/pgvector:pg15

# Install Python and system dependencies  
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    supervisor \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Create necessary directories and set permissions
RUN mkdir -p /app /var/log/sage /var/log/supervisor /var/run/postgresql && \
    chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql && \
    chmod 755 /var/lib/postgresql /var/run/postgresql && \
    # Create sage user for application security
    groupadd -r sage -g 1001 && \
    useradd -r -g sage -u 1001 -d /app -s /bin/bash sage && \
    chown -R sage:sage /app /var/log/sage

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY ./requirements.txt /app/
RUN python3 -m pip install --no-cache-dir --upgrade pip --break-system-packages && \
    python3 -m pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy application files
COPY ./sage_core /app/sage_core
COPY ./sage_mcp_stdio_single.py /app/

# Copy database initialization and configuration
COPY docker/init.sql /docker-entrypoint-initdb.d/
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy and prepare startup script
COPY docker/startup.sh /startup.sh
RUN chmod +x /startup.sh

# Set default environment variables
ENV PGDATA=/var/lib/postgresql/data \
    SAGE_ENV=production \
    SAGE_LOG_LEVEL=INFO \
    SAGE_LOG_DIR=/var/log/sage \
    SAGE_MAX_RESULTS=10

# Expose PostgreSQL port for external access (optional for debugging)
EXPOSE 5432

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD pg_isready -U sage -d sage_memory || exit 1

# Use supervisor to manage multiple processes
CMD ["/startup.sh"]