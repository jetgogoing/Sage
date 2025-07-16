#!/usr/bin/env bash
# Build script for Optimized Sage MCP Single Container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running"
    exit 1
fi

# Build configuration
IMAGE_NAME="${1:-sage-mcp-single:optimized}"
BUILD_CONTEXT="."

print_status "Building Optimized Sage MCP Single Container"
print_info "Target image: $IMAGE_NAME"
print_info "Expected size: <1GB"

# Ensure sage_mcp_stdio_single.py exists
if [ ! -f sage_mcp_stdio_single.py ]; then
    print_warning "sage_mcp_stdio_single.py not found, copying from v3"
    cp sage_mcp_stdio_v3.py sage_mcp_stdio_single.py
fi

# Show what's being excluded
print_info "Files excluded by .dockerignore:"
if [ -f .dockerignore ]; then
    echo "$(grep -v '^#' .dockerignore | grep -v '^$' | head -10)"
    EXCLUDED_COUNT=$(grep -v '^#' .dockerignore | grep -v '^$' | wc -l)
    if [ $EXCLUDED_COUNT -gt 10 ]; then
        echo "... and $((EXCLUDED_COUNT - 10)) more patterns"
    fi
fi

# Build the Docker image
print_status "Starting multi-stage build..."
DOCKER_BUILDKIT=1 docker build \
    -f Dockerfile.single.optimized \
    -t "$IMAGE_NAME" \
    --progress=plain \
    "$BUILD_CONTEXT"

if [ $? -eq 0 ]; then
    print_status "Build completed successfully!"
    
    # Show image details
    IMAGE_SIZE=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "$IMAGE_NAME" | awk '{print $2}')
    IMAGE_ID=$(docker images --format "{{.ID}}" "$IMAGE_NAME" | head -1)
    
    print_info "Image name: $IMAGE_NAME"
    print_info "Image ID: $IMAGE_ID"
    print_info "Image size: $IMAGE_SIZE"
    
    # Size check
    SIZE_MB=$(docker images --format "{{.Size}}" "$IMAGE_NAME" | head -1 | sed 's/GB/*1024/;s/MB//;s/kB/\/1024/' | bc 2>/dev/null || echo "0")
    if [ -n "$SIZE_MB" ] && [ "$SIZE_MB" -lt 1024 ]; then
        print_status "✓ Size goal achieved: ${IMAGE_SIZE} < 1GB"
    else
        print_warning "Image size ${IMAGE_SIZE} may be larger than target"
    fi
    
    echo ""
    print_status "Next steps:"
    echo "1. Test the container:"
    echo "   docker run --rm -i $IMAGE_NAME"
    echo ""
    echo "2. Update run script to use optimized image:"
    echo "   export SAGE_IMAGE=$IMAGE_NAME"
    echo "   ./run_sage_single.sh"
    echo ""
    echo "3. Register with Claude Code:"
    echo "   claude mcp add sage ./run_sage_single.sh"
else
    print_error "Build failed!"
    exit 1
fi