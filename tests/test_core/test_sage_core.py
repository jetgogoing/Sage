"""
Test Sage Core Service - 核心服务测试
"""
import pytest
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sage_core import SageCore, MemoryContent, SearchOptions


@pytest.fixture
async def sage_core():
    """创建测试用的 SageCore 实例"""
    core = SageCore()
    
    # 使用测试配置
    test_config = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "sage_test",
            "user": "sage",
            "password": "sage123"
        },
        "embedding": {
            "model": "Qwen/Qwen3-Embedding-8B",
            "device": "cpu"
        }
    }
    
    await core.initialize(test_config)
    yield core
    await core.cleanup()


@pytest.mark.asyncio
async def test_initialize():
    """测试初始化"""
    core = SageCore()
    
    config = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "sage_test",
            "user": "sage",
            "password": "sage123"
        }
    }
    
    await core.initialize(config)
    assert core._initialized is True
    
    # 测试重复初始化
    await core.initialize(config)  # 应该不会出错
    
    await core.cleanup()


@pytest.mark.asyncio
async def test_save_and_search_memory(sage_core):
    """测试保存和搜索记忆"""
    # 保存记忆
    content = MemoryContent(
        user_input="什么是人工智能？",
        assistant_response="人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
        metadata={"topic": "AI"}
    )
    
    memory_id = await sage_core.save_memory(content)
    assert memory_id is not None
    assert isinstance(memory_id, str)
    
    # 搜索记忆
    options = SearchOptions(limit=5, strategy="semantic")
    results = await sage_core.search_memory("人工智能", options)
    
    assert len(results) > 0
    assert results[0]['user_input'] == "什么是人工智能？"


@pytest.mark.asyncio
async def test_get_context(sage_core):
    """测试获取上下文"""
    # 先保存一些记忆
    memories = [
        MemoryContent(
            user_input="Python是什么？",
            assistant_response="Python是一种高级编程语言。"
        ),
        MemoryContent(
            user_input="如何学习Python？",
            assistant_response="可以通过在线教程、书籍和实践项目来学习Python。"
        )
    ]
    
    for content in memories:
        await sage_core.save_memory(content)
    
    # 获取上下文
    context = await sage_core.get_context("Python编程", max_results=5)
    
    assert isinstance(context, str)
    assert "Python" in context


@pytest.mark.asyncio
async def test_session_management(sage_core):
    """测试会话管理"""
    # 创建新会话
    session_info = await sage_core.manage_session("create")
    assert session_info.session_id is not None
    assert session_info.memory_count == 0
    
    new_session_id = session_info.session_id
    
    # 保存一些记忆
    content = MemoryContent(
        user_input="测试会话",
        assistant_response="这是测试会话的内容"
    )
    await sage_core.save_memory(content)
    
    # 获取会话信息
    session_info = await sage_core.manage_session("info", new_session_id)
    assert session_info.memory_count == 1
    
    # 列出所有会话
    session_info = await sage_core.manage_session("list")
    assert 'all_sessions' in session_info.metadata


@pytest.mark.asyncio
async def test_memory_analysis(sage_core):
    """测试记忆分析"""
    # 保存一些测试数据
    test_memories = [
        ("什么是机器学习？", "机器学习是人工智能的一个子领域。"),
        ("深度学习和机器学习的区别？", "深度学习是机器学习的一个分支。"),
        ("如何开始学习AI？", "可以从基础的Python编程开始。"),
    ]
    
    for user_input, assistant_response in test_memories:
        content = MemoryContent(
            user_input=user_input,
            assistant_response=assistant_response
        )
        await sage_core.save_memory(content)
    
    # 执行分析
    analysis_result = await sage_core.analyze_memory(analysis_type="general")
    
    assert len(analysis_result.insights) > 0
    assert analysis_result.metadata['memory_count'] >= 3


@pytest.mark.asyncio
async def test_generate_prompt(sage_core):
    """测试生成提示"""
    prompt = await sage_core.generate_prompt("测试上下文", style="question")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    
    prompt = await sage_core.generate_prompt("测试上下文", style="suggestion")
    assert isinstance(prompt, str)


@pytest.mark.asyncio
async def test_export_session(sage_core):
    """测试导出会话"""
    # 创建会话并保存数据
    session_info = await sage_core.manage_session("create")
    session_id = session_info.session_id
    
    content = MemoryContent(
        user_input="导出测试",
        assistant_response="这是导出测试的内容"
    )
    await sage_core.save_memory(content)
    
    # 导出为 JSON
    json_data = await sage_core.export_session(session_id, format="json")
    assert isinstance(json_data, bytes)
    
    # 导出为 Markdown
    md_data = await sage_core.export_session(session_id, format="markdown")
    assert isinstance(md_data, bytes)
    assert b"导出测试" in md_data


@pytest.mark.asyncio
async def test_get_status(sage_core):
    """测试获取状态"""
    status = await sage_core.get_status()
    
    assert status['initialized'] is True
    assert status['service'] == 'sage_core'
    assert 'components' in status
    assert status['components']['memory_manager'] is True


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    core = SageCore()
    
    # 未初始化时调用方法应该抛出错误
    with pytest.raises(RuntimeError):
        await core.save_memory(MemoryContent(
            user_input="test",
            assistant_response="test"
        ))
    
    # 无效的会话操作
    await core.initialize({})
    with pytest.raises(ValueError):
        await core.manage_session("invalid_action")
    
    await core.cleanup()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])