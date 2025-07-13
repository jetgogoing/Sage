#!/usr/bin/env python3
"""
Test Intelligent MCP Server Integration
测试智能 MCP 服务器集成
"""

import asyncio
import pytest
import pytest_asyncio
import httpx
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test server URL
SERVER_URL = "http://localhost:17800"


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    response = await client.get(f"{SERVER_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    logger.info(f"Health check: {data}")


@pytest.mark.asyncio
async def test_save_conversation_with_metadata(client):
    """Test saving conversation with enhanced metadata"""
    request_data = {
        "user_prompt": "如何使用 Python 实现快速排序算法？",
        "assistant_response": "快速排序是一种高效的分治排序算法。以下是 Python 实现：\n\n```python\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)\n```",
        "metadata": {
            "topic": "algorithms",
            "language": "python",
            "difficulty": "intermediate"
        }
    }
    
    response = await client.post(f"{SERVER_URL}/save_conversation", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] is not None
    assert data["turn_id"] is not None
    logger.info(f"Saved conversation: Session {data['session_id']}, Turn {data['turn_id']}")


@pytest.mark.asyncio
async def test_intelligent_context_without_llm(client):
    """Test getting context without LLM summary"""
    request_data = {
        "query": "Python 排序算法",
        "max_results": 5,
        "enable_llm_summary": False
    }
    
    response = await client.post(f"{SERVER_URL}/get_context", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "context" in data
    assert data["strategy_used"] == "intelligent_retrieval"
    assert data["llm_summary_used"] is False
    assert "query_analysis" in data
    
    logger.info(f"Context without LLM: {len(data['context'])} chars")
    logger.info(f"Query analysis: {data['query_analysis']}")


@pytest.mark.asyncio
async def test_intelligent_context_with_llm(client):
    """Test getting context with LLM summary"""
    request_data = {
        "query": "解释一下之前讨论的排序算法",
        "max_results": 10,
        "enable_llm_summary": True
    }
    
    response = await client.post(f"{SERVER_URL}/get_context", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "context" in data
    assert data["strategy_used"] == "intelligent_retrieval"
    # Note: llm_summary_used might be True or False depending on whether summarize_context is called
    
    logger.info(f"Context with LLM option: {len(data['context'])} chars")
    logger.info(f"LLM summary used: {data['llm_summary_used']}")


@pytest.mark.asyncio
async def test_diagnostic_query_type(client):
    """Test diagnostic query type detection"""
    # First save a conversation about an error
    error_data = {
        "user_prompt": "我遇到了 KeyError: 'config' 错误，请帮我解决",
        "assistant_response": "KeyError 通常表示尝试访问字典中不存在的键。检查 'config' 键是否存在。",
        "metadata": {"error_type": "KeyError"}
    }
    
    await client.post(f"{SERVER_URL}/save_conversation", json=error_data)
    
    # Now query for diagnostic help
    request_data = {
        "query": "KeyError 错误怎么解决",
        "max_results": 5,
        "enable_llm_summary": False
    }
    
    response = await client.post(f"{SERVER_URL}/get_context", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    query_analysis = data.get("query_analysis", {})
    
    logger.info(f"Diagnostic query detected type: {query_analysis.get('detected_type')}")
    # Should detect as diagnostic type
    assert query_analysis.get("detected_type") == "diagnostic"


@pytest.mark.asyncio
async def test_conversational_continuity(client):
    """Test conversational continuity tracking"""
    # Save multiple turns in a conversation
    conversations = [
        {
            "user_prompt": "什么是机器学习？",
            "assistant_response": "机器学习是人工智能的一个分支，让计算机从数据中学习模式。"
        },
        {
            "user_prompt": "能举个例子吗？",
            "assistant_response": "比如垃圾邮件过滤器，通过学习邮件特征来识别垃圾邮件。"
        },
        {
            "user_prompt": "那深度学习呢？",
            "assistant_response": "深度学习是机器学习的子集，使用多层神经网络。"
        }
    ]
    
    for conv in conversations:
        await client.post(f"{SERVER_URL}/save_conversation", json=conv)
        await asyncio.sleep(0.5)  # Small delay between saves
    
    # Query with conversational context
    request_data = {
        "query": "继续解释一下它们的区别",
        "max_results": 10,
        "enable_llm_summary": False
    }
    
    response = await client.post(f"{SERVER_URL}/get_context", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["num_results"] > 0
    
    query_analysis = data.get("query_analysis", {})
    logger.info(f"Conversational query type: {query_analysis.get('detected_type')}")
    logger.info(f"Session continuity: {query_analysis.get('session_continuity')}")


@pytest.mark.asyncio
async def test_code_detection(client):
    """Test code detection in conversations"""
    code_conv = {
        "user_prompt": "如何在 JavaScript 中实现防抖函数？",
        "assistant_response": """防抖函数用于限制函数调用频率。实现如下：

```javascript
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}
```

使用示例：
```javascript
const debouncedSearch = debounce(searchAPI, 300);
input.addEventListener('input', debouncedSearch);
```""",
        "metadata": {"contains_code": True}
    }
    
    response = await client.post(f"{SERVER_URL}/save_conversation", json=code_conv)
    assert response.status_code == 200
    
    # Query for the code
    context_response = await client.post(f"{SERVER_URL}/get_context", json={
        "query": "JavaScript 防抖实现",
        "max_results": 5
    })
    
    assert context_response.status_code == 200
    data = context_response.json()
    
    # Check if code-related content is retrieved
    assert data["num_results"] > 0
    assert any("debounce" in str(result.get("content", "")) for result in data["results"])


@pytest.mark.asyncio
async def test_search_with_scoring_details(client):
    """Test search memory with detailed scoring information"""
    response = await client.post(f"{SERVER_URL}/search_memory", json={
        "query": "排序算法 Python",
        "n": 3
    })
    
    assert response.status_code == 200
    data = response.json()
    
    logger.info(f"Found {data['total_found']} results")
    
    for i, result in enumerate(data["results"]):
        logger.info(f"Result {i+1}: Score={result.get('score', 0):.3f}, Role={result['role']}")
        # Log first 100 chars of content
        logger.info(f"  Content: {result['content'][:100]}...")


@pytest.mark.asyncio
async def test_performance_comparison(client):
    """Compare performance with and without LLM summary"""
    query = "解释 Python 的装饰器模式"
    
    # Test without LLM
    start_time = datetime.now()
    response1 = await client.post(f"{SERVER_URL}/get_context", json={
        "query": query,
        "enable_llm_summary": False,
        "max_results": 10
    })
    time_without_llm = (datetime.now() - start_time).total_seconds()
    
    # Test with LLM
    start_time = datetime.now()
    response2 = await client.post(f"{SERVER_URL}/get_context", json={
        "query": query,
        "enable_llm_summary": True,
        "max_results": 10
    })
    time_with_llm = (datetime.now() - start_time).total_seconds()
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    logger.info(f"Performance comparison:")
    logger.info(f"  Without LLM: {time_without_llm:.2f}s")
    logger.info(f"  With LLM: {time_with_llm:.2f}s")
    logger.info(f"  Difference: {time_with_llm - time_without_llm:.2f}s")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_health_check(httpx.AsyncClient(timeout=30.0)))
    print("\nRun with pytest for complete test suite:")
    print("pytest -v tests/test_intelligent_mcp.py")