#!/usr/bin/env bash
# Sage MCP Single Container Launch Script - Persistent Mode
# For Unix/Linux/macOS
set -e

# Default image name
IMAGE_NAME="${SAGE_IMAGE:-sage-mcp-single:minimal}"
CONTAINER_NAME="sage-mcp"

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

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "Container ${CONTAINER_NAME} is already running"
        # Attach to the running container's STDIO
        exec docker attach ${CONTAINER_NAME}
    else
        echo "Starting existing container ${CONTAINER_NAME}..."
        exec docker start -ai ${CONTAINER_NAME}
    fi
else
    echo "Creating and starting new container ${CONTAINER_NAME}..."
    # Run the container with data persistence
    # -i: Keep STDIN open (required for MCP STDIO)
    # --name: Give container a persistent name
    # -v: Mount volume for PostgreSQL data persistence
    exec docker run -i \
        --name ${CONTAINER_NAME} \
        -v sage-mcp-data:/var/lib/postgresql/data \
        $SAGE_DOCKER_OPTS \
        "$IMAGE_NAME"
fi