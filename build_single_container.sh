#!/usr/bin/env bash
# Build script for Sage MCP Single Container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Set build variables
IMAGE_NAME="${1:-sage-mcp-single:latest}"
BUILD_CONTEXT="."

print_status "Building Sage MCP Single Container image: $IMAGE_NAME"

# Copy the modified stdio file
print_status "Preparing build context..."
if [ -f sage_mcp_stdio_single.py ]; then
    print_status "Using existing sage_mcp_stdio_single.py"
else
    print_warning "sage_mcp_stdio_single.py not found, copying from v3"
    cp sage_mcp_stdio_v3.py sage_mcp_stdio_single.py
fi

# Build the Docker image
print_status "Building Docker image..."
docker build \
    -f Dockerfile.single.minimal \
    -t "$IMAGE_NAME" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    "$BUILD_CONTEXT"

if [ $? -eq 0 ]; then
    print_status "Build completed successfully!"
    print_status "Image name: $IMAGE_NAME"
    
    # Show image size
    IMAGE_SIZE=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "$IMAGE_NAME" | awk '{print $2}')
    print_status "Image size: $IMAGE_SIZE"
    
    echo ""
    print_status "To test the container locally:"
    echo "  ./run_sage_single.sh"
    echo ""
    print_status "To register with Claude Code:"
    echo "  claude mcp add sage ./run_sage_single.sh"
else
    print_error "Build failed!"
    exit 1
fi