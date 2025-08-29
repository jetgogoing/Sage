#!/usr/bin/env python3
"""
Test script for Sage MCP Server

This script tests the basic functionality of the MCP server
including health checks, tool listing, and memory operations.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

# Test configuration
BASE_URL = "http://localhost:17800"
TEST_USER_PROMPT = "What is Python list comprehension?"
TEST_ASSISTANT_RESPONSE = "List comprehension is a concise way to create lists in Python. It allows you to generate a new list by applying an expression to each item in an existing iterable."

async def test_health_check():
    """Test the health check endpoint"""
    print("\n=== Testing Health Check ===")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_list_tools():
    """Test the tool listing endpoint"""
    print("\n=== Testing List Tools ===")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/tools")
            print(f"Status Code: {response.status_code}")
            data = response.json()
            print(f"Available tools: {len(data.get('tools', []))}")
            for tool in data.get('tools', []):
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_save_conversation():
    """Test saving a conversation"""
    print("\n=== Testing Save Conversation ===")
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "user_prompt": TEST_USER_PROMPT,
                "assistant_response": TEST_ASSISTANT_RESPONSE,
                "metadata": {
                    "test": True,
                    "source": "test_script"
                }
            }
            response = await client.post(
                f"{BASE_URL}/save_conversation",
                json=payload
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_get_context():
    """Test getting context"""
    print("\n=== Testing Get Context ===")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {
                "query": "Python list comprehension",
                "max_results": 3
            }
            response = await client.post(
                f"{BASE_URL}/get_context",
                json=payload
            )
            print(f"Status Code: {response.status_code}")
            data = response.json()
            print(f"Context length: {len(data.get('context', ''))} chars")
            print(f"Number of results: {data.get('num_results', 0)}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_search_memory():
    """Test searching memory"""
    print("\n=== Testing Search Memory ===")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {
                "query": "Python",
                "n": 5
            }
            response = await client.post(
                f"{BASE_URL}/search_memory",
                json=payload
            )
            print(f"Status Code: {response.status_code}")
            data = response.json()
            print(f"Total found: {data.get('total_found', 0)}")
            for i, result in enumerate(data.get('results', [])[:3]):
                print(f"\nResult {i+1}:")
                print(f"  Role: {result.get('role')}")
                print(f"  Score: {result.get('score', 0):.3f}")
                print(f"  Content: {result.get('content', '')[:100]}...")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_tool_call():
    """Test the unified tool call endpoint"""
    print("\n=== Testing Tool Call Endpoint ===")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test save_conversation via tool call
            response = await client.post(
                f"{BASE_URL}/call_tool?tool_name=save_conversation",
                json={
                    "user_prompt": "Test tool call",
                    "assistant_response": "This is a test response via tool call"
                }
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Run all tests"""
    print("Starting Sage MCP Server Tests")
    print("==============================")
    print(f"Server URL: {BASE_URL}")
    
    # Check if server is running
    print("\nChecking if server is running...")
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{BASE_URL}/health", timeout=2.0)
    except Exception:
        print("ERROR: Server is not running!")
        print("Please start the server with: python app/sage_mcp_server.py")
        return
    
    # Run tests
    tests = [
        test_health_check,
        test_list_tools,
        test_save_conversation,
        test_get_context,
        test_search_memory,
        test_tool_call
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append((test.__name__, result))
    
    # Summary
    print("\n\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n❌ {total - passed} tests failed")

if __name__ == "__main__":
    asyncio.run(main())