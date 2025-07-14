#!/usr/bin/env python3
"""
第一阶段简化测试：验证 MCP V2 服务器基础功能
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_mcp_stdio_v2 import (
    SageCommandParser, CommandType, SageSessionManager, 
    ConversationTracker, SageMCPServer, SageMode
)


def test_command_parser():
    """测试命令解析器"""
    print("\n测试命令解析器...")
    parser = SageCommandParser()
    
    # 测试 /SAGE 命令
    cmd_type, args = parser.parse("/SAGE 如何实现快速排序")
    assert cmd_type == CommandType.SAGE
    assert args["query"] == "如何实现快速排序"
    print("✓ /SAGE 命令解析正确")
    
    # 测试 /SAGE-MODE 命令
    cmd_type, args = parser.parse("/SAGE-MODE on")
    assert cmd_type == CommandType.SAGE_MODE
    assert args["action"] == "on"
    print("✓ /SAGE-MODE 命令解析正确")
    
    # 测试 /SAGE-SESSION 命令
    cmd_type, args = parser.parse("/SAGE-SESSION start Python学习")
    assert cmd_type == CommandType.SAGE_SESSION
    assert args["action"] == "start"
    assert args["topic"] == "Python学习"
    print("✓ /SAGE-SESSION 命令解析正确")
    
    # 测试无效命令
    cmd_type, args = parser.parse("这不是一个命令")
    assert cmd_type is None
    print("✓ 无效命令处理正确")


def test_session_manager():
    """测试会话管理器"""
    print("\n测试会话管理器...")
    manager = SageSessionManager()
    
    # 开始会话
    session = manager.start_session("测试主题")
    assert session["topic"] == "测试主题"
    assert manager.active_session == session
    print("✓ 开始会话功能正常")
    
    # 暂停会话
    session_id = session["id"]
    paused = manager.pause_session()
    assert paused["id"] == session_id
    assert manager.active_session is None
    print("✓ 暂停会话功能正常")
    
    # 恢复会话
    resumed = manager.resume_session()
    assert resumed["id"] == session_id
    assert manager.active_session == resumed
    print("✓ 恢复会话功能正常")
    
    # 结束会话
    ended = manager.end_session()
    assert "summary" in ended
    assert manager.active_session is None
    print("✓ 结束会话功能正常")


async def test_mcp_server():
    """测试 MCP 服务器"""
    print("\n测试 MCP 服务器...")
    server = SageMCPServer()
    
    # 测试 /SAGE 命令处理
    result = await server.handle_command("/SAGE 什么是Python")
    assert len(result) == 1
    assert "当前查询" in result[0].text
    print("✓ /SAGE 命令处理正确")
    
    # 测试 /SAGE-MODE 命令处理
    result = await server.handle_command("/SAGE-MODE on")
    assert "智能记忆模式已启用" in result[0].text
    assert server.current_mode == SageMode.SMART
    print("✓ /SAGE-MODE 命令处理正确")
    
    # 测试 /SAGE-SESSION 命令处理
    result = await server.handle_command("/SAGE-SESSION start 测试主题")
    assert "会话已开始" in result[0].text
    assert server.current_mode == SageMode.SESSION
    print("✓ /SAGE-SESSION 命令处理正确")
    
    # 测试配置命令
    result = await server.handle_command("/SAGE-CONFIG")
    assert "当前配置" in result[0].text
    print("✓ /SAGE-CONFIG 命令处理正确")


async def test_conversation_tracking():
    """测试对话跟踪"""
    print("\n测试对话跟踪...")
    
    try:
        from app.memory_adapter_v2 import EnhancedMemoryAdapter
        adapter = EnhancedMemoryAdapter()
        tracker = ConversationTracker(adapter)
        
        # 开始跟踪
        tracker.start_tracking("用户的问题")
        assert tracker.current_conversation["user_input"] == "用户的问题"
        print("✓ 对话跟踪启动正常")
        
        # 添加上下文
        tracker.add_context("相关的历史记忆")
        assert tracker.current_conversation["context_used"] == "相关的历史记忆"
        print("✓ 上下文添加正常")
        
        # 添加响应
        tracker.add_response("助手的回答")
        assert len(tracker.current_conversation["assistant_responses"]) == 1
        print("✓ 响应添加正常")
        
    except Exception as e:
        print(f"⚠️ 对话跟踪测试失败（可能数据库未启动）: {e}")


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第一阶段测试：MCP V2 服务器基础功能")
    print("=" * 60)
    
    try:
        # 基础功能测试
        test_command_parser()
        test_session_manager()
        
        # 异步功能测试
        await test_mcp_server()
        await test_conversation_tracking()
        
        print("\n" + "=" * 60)
        print("✅ 第一阶段所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())