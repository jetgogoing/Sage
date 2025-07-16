#!/usr/bin/env bash
# Sage MCP Single Container Launch Script
# For Unix/Linux/macOS

# Default image name
IMAGE_NAME="${SAGE_IMAGE:-sage-mcp-single:latest}"

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

# Run the container
# -i: Keep STDIN open (required for MCP STDIO)
# --rm: Remove container after exit
# Optional: Add -v for data persistence
exec docker run --rm -i \
    --name sage-mcp-stdio \
    $SAGE_DOCKER_OPTS \
    "$IMAGE_NAME"