#!/usr/bin/env bash
# Sage MCP Single Container Launch Script
# For Unix/Linux/macOS
set -e

# Default image name
IMAGE_NAME="${SAGE_IMAGE:-sage-mcp-single:minimal}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH" >&2
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running" >&2
    exit 1
fi

# Create volume for data persistence if it doesn't exist
docker volume create sage-mcp-data 2>/dev/null || true

# Run the container with data persistence
# -i: Keep STDIN open (required for MCP STDIO)
# --rm: Remove container after exit (data persists in volume)
# -v: Mount volume for PostgreSQL data persistence
exec docker run --rm -i \
    --name sage-mcp-stdio \
    -v sage-mcp-data:/var/lib/postgresql/data \
    $SAGE_DOCKER_OPTS \
    "$IMAGE_NAME"