#!/usr/bin/env bash
# Test script for minimal container

set -e

echo "=== Testing Sage MCP Minimal Container ==="

# Test 1: Basic container startup
echo -e "\n[TEST 1] Container startup test..."
if timeout 10 docker run --rm sage-mcp-single:minimal echo "Container started" 2>&1 | grep -q "Starting Sage MCP"; then
    echo "✓ Container starts successfully"
else
    echo "✗ Container failed to start"
    exit 1
fi

# Test 2: PostgreSQL initialization
echo -e "\n[TEST 2] PostgreSQL initialization test..."
docker run --rm -d --name sage-test sage-mcp-single:minimal
sleep 5

if docker exec sage-test su-exec postgres pg_isready -q; then
    echo "✓ PostgreSQL is running"
else
    echo "✗ PostgreSQL failed to start"
    docker stop sage-test
    exit 1
fi

# Test 3: Database creation
echo -e "\n[TEST 3] Database creation test..."
if docker exec sage-test su-exec postgres psql -lqt | grep -q sage; then
    echo "✓ Sage database created"
else
    echo "✗ Database creation failed"
fi

# Cleanup
docker stop sage-test

echo -e "\n=== All tests completed ==="