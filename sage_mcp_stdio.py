#!/usr/bin/env python3
"""
Sage MCP Server - stdio wrapper
This wraps the HTTP MCP server to work with stdio transport
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/sage_mcp_stdio.log')]
)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = "http://localhost:17800/mcp"

async def send_request(method: str, params: Dict[str, Any] = None, id: str = None):
    """Send request to HTTP MCP server"""
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
    }
    if id is not None:
        request["id"] = id
    
    async with aiohttp.ClientSession() as session:
        async with session.post(MCP_SERVER_URL, json=request) as response:
            return await response.json()

async def handle_stdio():
    """Handle stdio MCP protocol"""
    logger.info("Sage MCP stdio wrapper started")
    
    # Read from stdin and write to stdout
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    
    while True:
        try:
            # Read line from stdin
            line = await reader.readline()
            if not line:
                break
                
            line = line.decode('utf-8').strip()
            if not line:
                continue
                
            logger.info(f"Received: {line}")
            
            # Parse JSON-RPC request
            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                continue
            
            # Convert numeric ID to string for compatibility
            request_id = request.get("id")
            if request_id is not None and isinstance(request_id, int):
                request["id"] = str(request_id)
            
            # Forward to HTTP server
            response = await send_request(
                method=request.get("method"),
                params=request.get("params"),
                id=request.get("id")
            )
            
            # Send response to stdout
            response_line = json.dumps(response)
            logger.info(f"Sending: {response_line}")
            print(response_line, flush=True)
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            if "id" in locals() and "request" in locals():
                error_response["id"] = request.get("id")
            print(json.dumps(error_response), flush=True)

def main():
    """Main entry point"""
    # Ensure HTTP server is running
    import subprocess
    import time
    
    # Check if server is running
    try:
        import requests
        response = requests.get("http://localhost:17800/health", timeout=2)
        if response.status_code != 200:
            logger.warning("MCP HTTP server not healthy, starting it...")
            subprocess.Popen([sys.executable, "app/sage_mcp_server.py"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            time.sleep(5)
    except:
        logger.info("Starting MCP HTTP server...")
        subprocess.Popen([sys.executable, "app/sage_mcp_server.py"], 
                       stdout=subprocess.DEVNULL, 
                       stderr=subprocess.DEVNULL)
        time.sleep(5)
    
    # Run stdio handler
    asyncio.run(handle_stdio())

if __name__ == "__main__":
    main()