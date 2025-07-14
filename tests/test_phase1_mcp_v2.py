#!/usr/bin/env python3
"""
第一阶段测试：验证 MCP V2 服务器基础功能
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_mcp_stdio_v2 import (
    SageCommandParser, CommandType, SageSessionManager, 
    ConversationTracker, SageMCPServer, SageMode
)
from app.memory_adapter_v2 import EnhancedMemoryAdapter


class TestCommandParser:
    """测试命令解析器"""
    
    def setup_method(self):
        self.parser = SageCommandParser()
    
    def test_parse_sage_command(self):
        """测试 /SAGE 命令解析"""
        cmd_type, args = self.parser.parse("/SAGE 如何实现快速排序")
        assert cmd_type == CommandType.SAGE
        assert args["query"] == "如何实现快速排序"
    
    def test_parse_sage_mode_command(self):
        """测试 /SAGE-MODE 命令解析"""
        # 测试开启
        cmd_type, args = self.parser.parse("/SAGE-MODE on")
        assert cmd_type == CommandType.SAGE_MODE
        assert args["action"] == "on"
        
        # 测试关闭
        cmd_type, args = self.parser.parse("/SAGE-MODE off")
        assert cmd_type == CommandType.SAGE_MODE
        assert args["action"] == "off"
        
        # 测试默认
        cmd_type, args = self.parser.parse("/SAGE-MODE")
        assert cmd_type == CommandType.SAGE_MODE
        assert args["action"] == "on"
    
    def test_parse_sage_session_command(self):
        """测试 /SAGE-SESSION 命令解析"""
        cmd_type, args = self.parser.parse("/SAGE-SESSION start Python学习")
        assert cmd_type == CommandType.SAGE_SESSION
        assert args["action"] == "start"
        assert args["topic"] == "Python学习"
    
    def test_parse_sage_recall_command(self):
        """测试 /SAGE-RECALL 命令解析"""
        cmd_type, args = self.parser.parse("/SAGE-RECALL recent 10")
        assert cmd_type == CommandType.SAGE_RECALL
        assert args["type"] == "recent"
        assert args["params"] == "10"
    
    def test_parse_invalid_command(self):
        """测试无效命令"""
        cmd_type, args = self.parser.parse("这不是一个命令")
        assert cmd_type is None
        assert args == {}


class TestSessionManager:
    """测试会话管理器"""
    
    def setup_method(self):
        self.manager = SageSessionManager()
    
    def test_start_session(self):
        """测试开始会话"""
        session = self.manager.start_session("测试主题")
        assert session is not None
        assert session["topic"] == "测试主题"
        assert "id" in session
        assert self.manager.active_session == session
    
    def test_pause_resume_session(self):
        """测试暂停和恢复会话"""
        # 开始会话
        session = self.manager.start_session("测试主题")
        session_id = session["id"]
        
        # 暂停会话
        paused = self.manager.pause_session()
        assert paused["id"] == session_id
        assert self.manager.active_session is None
        
        # 恢复会话
        resumed = self.manager.resume_session()
        assert resumed["id"] == session_id
        assert self.manager.active_session == resumed
    
    def test_end_session(self):
        """测试结束会话"""
        # 开始会话
        session = self.manager.start_session("测试主题")
        session["messages"].append({"content": "测试消息"})
        
        # 结束会话
        ended = self.manager.end_session()
        assert ended is not None
        assert "summary" in ended
        assert "duration" in ended
        assert self.manager.active_session is None
        assert len(self.manager.session_history) == 1


class TestConversationTracker:
    """测试对话跟踪器"""
    
    def setup_method(self):
        self.adapter = EnhancedMemoryAdapter()
        self.tracker = ConversationTracker(self.adapter)
    
    def test_track_conversation(self):
        """测试对话跟踪"""
        # 开始跟踪
        self.tracker.start_tracking("用户的问题")
        assert self.tracker.current_conversation is not None
        assert self.tracker.current_conversation["user_input"] == "用户的问题"
        
        # 添加上下文
        self.tracker.add_context("相关的历史记忆")
        assert self.tracker.current_conversation["context_used"] == "相关的历史记忆"
        
        # 添加响应
        self.tracker.add_response("助手的回答第一部分")
        self.tracker.add_response("助手的回答第二部分")
        assert len(self.tracker.current_conversation["assistant_responses"]) == 2
        
        # 添加工具调用
        self.tracker.add_tool_call("search", {"query": "test"}, "结果")
        assert len(self.tracker.current_conversation["tool_calls"]) == 1


class TestSageMCPServerIntegration:
    """集成测试 Sage MCP 服务器"""
    
    @pytest.fixture
    async def server(self):
        """创建服务器实例"""
        server = SageMCPServer()
        yield server
    
    @pytest.mark.asyncio
    async def test_handle_sage_command(self, server):
        """测试处理 /SAGE 命令"""
        result = await server.handle_command("/SAGE 什么是Python")
        assert len(result) == 1
        assert result[0].type == "text"
        assert "当前查询" in result[0].text
        assert "什么是Python" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_sage_mode_command(self, server):
        """测试处理 /SAGE-MODE 命令"""
        # 开启智能模式
        result = await server.handle_command("/SAGE-MODE on")
        assert len(result) == 1
        assert "智能记忆模式已启用" in result[0].text
        assert server.current_mode == SageMode.SMART
        assert server.config["auto_save"] is True
        
        # 关闭智能模式
        result = await server.handle_command("/SAGE-MODE off")
        assert "智能记忆模式已关闭" in result[0].text
        assert server.current_mode == SageMode.DEFAULT
        assert server.config["auto_save"] is False
    
    @pytest.mark.asyncio
    async def test_handle_sage_session_command(self, server):
        """测试处理 /SAGE-SESSION 命令"""
        # 开始会话
        result = await server.handle_command("/SAGE-SESSION start 机器学习基础")
        assert "会话已开始" in result[0].text
        assert "机器学习基础" in result[0].text
        assert server.current_mode == SageMode.SESSION
        
        # 结束会话
        result = await server.handle_command("/SAGE-SESSION end")
        assert "会话已结束" in result[0].text
        assert server.current_mode == SageMode.DEFAULT
    
    @pytest.mark.asyncio
    async def test_handle_sage_recall_command(self, server):
        """测试处理 /SAGE-RECALL 命令"""
        # 搜索记忆
        result = await server.handle_command("/SAGE-RECALL search Python")
        assert len(result) == 1
        # 结果取决于数据库内容
    
    @pytest.mark.asyncio
    async def test_handle_sage_config_command(self, server):
        """测试处理 /SAGE-CONFIG 命令"""
        # 显示配置
        result = await server.handle_command("/SAGE-CONFIG")
        assert "当前配置" in result[0].text
        
        # 修改配置
        result = await server.handle_command("/SAGE-CONFIG rerank off")
        assert "神经网络重排序已禁用" in result[0].text
        assert server.config["neural_rerank"] is False
    
    @pytest.mark.asyncio 
    async def test_direct_action_save(self, server):
        """测试直接保存操作"""
        result = await server.handle_direct_action("save", {
            "user_prompt": "测试问题",
            "assistant_response": "测试回答",
            "metadata": {"test": True}
        })
        assert "对话已保存" in result[0].text
    
    @pytest.mark.asyncio
    async def test_direct_action_get_context(self, server):
        """测试直接获取上下文操作"""
        result = await server.handle_direct_action("get_context", {
            "query": "Python",
            "max_results": 3
        })
        assert len(result) == 1
        # 结果取决于数据库内容


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第一阶段测试：MCP V2 服务器基础功能")
    print("=" * 60)
    
    # 运行 pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()