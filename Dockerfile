# Sage MCP Server - Production Ready
FROM python:3.10-slim

# Install PostgreSQL and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-15 \
    postgresql-contrib-15 \
    postgresql-client-15 \
    supervisor \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app /var/log/sage /var/log/supervisor /var/run/postgresql

# Set working directory
WORKDIR /app

# Copy application files
COPY ./sage_core /app/sage_core
COPY ./sage_mcp_stdio_single.py /app/
COPY ./requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy database initialization
COPY docker/init.sql /docker-entrypoint-initdb.d/

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY docker/startup.sh /startup.sh
RUN chmod +x /startup.sh

# PostgreSQL configuration
ENV PGDATA=/var/lib/postgresql/data
ENV DATABASE_URL=postgresql://sage:sage@localhost:5432/sage_memory
ENV SAGE_ENV=production
ENV SAGE_LOG_LEVEL=INFO

# Use supervisor to manage multiple processes
CMD ["/startup.sh"]