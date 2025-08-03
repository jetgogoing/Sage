#!/usr/bin/env python3
"""
Test script for MCP STDIO protocol
"""
import json
import subprocess
import sys
import time

def send_request(proc, request):
    """Send a request to the MCP server"""
    request_str = json.dumps(request)
    print(f"Sending: {request_str}", file=sys.stderr)
    proc.stdin.write(request_str + '\n')
    proc.stdin.flush()

def read_response(proc):
    """Read a response from the MCP server"""
    response = proc.stdout.readline()
    if response:
        print(f"Received: {response.strip()}", file=sys.stderr)
        return json.loads(response)
    return None

def test_mcp_protocol():
    """Test the MCP STDIO protocol"""
    # Start the container
    print("Starting container...", file=sys.stderr)
    proc = subprocess.Popen(
        ['docker', 'run', '--rm', '-i', 'sage-mcp-single:lite'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Wait for container to be ready
    time.sleep(5)
    
    try:
        # Test 1: Initialize
        print("\n=== Test 1: Initialize ===", file=sys.stderr)
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        })
        
        response = read_response(proc)
        if response and 'result' in response:
            print("✓ Initialize successful", file=sys.stderr)
        else:
            print("✗ Initialize failed", file=sys.stderr)
        
        # Test 2: List tools
        print("\n=== Test 2: List tools ===", file=sys.stderr)
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        })
        
        response = read_response(proc)
        if response and 'result' in response and 'tools' in response['result']:
            tools = response['result']['tools']
            print(f"✓ Found {len(tools)} tools", file=sys.stderr)
            for tool in tools:
                print(f"  - {tool['name']}", file=sys.stderr)
        else:
            print("✗ List tools failed", file=sys.stderr)
        
        # Test 3: Call a tool
        print("\n=== Test 3: Call tool (get_status) ===", file=sys.stderr)
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_status",
                "arguments": {}
            },
            "id": 3
        })
        
        response = read_response(proc)
        if response and 'result' in response:
            print("✓ Tool call successful", file=sys.stderr)
        else:
            print("✗ Tool call failed", file=sys.stderr)
        
    finally:
        # Clean up
        proc.terminate()
        proc.wait()
        print("\nTest completed", file=sys.stderr)

if __name__ == "__main__":
    test_mcp_protocol()