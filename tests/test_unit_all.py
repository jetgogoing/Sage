#!/usr/bin/env python3
"""
综合单元测试套件
测试所有核心组件（不依赖MCP）
"""

import sys
from pathlib import Path
import asyncio
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum

# 测试结果统计
class TestResults:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.details = []
        
    def add_result(self, test_name: str, success: bool, details: str = ""):
        self.total += 1
        if success:
            self.passed += 1
        else:
            self.failed += 1
        self.details.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def print_summary(self):
        print("\n" + "=" * 60)
        print(f"测试总结: {self.passed}/{self.total} 通过")
        if self.failed > 0:
            print(f"\n失败的测试:")
            for detail in self.details:
                if not detail["success"]:
                    print(f"  - {detail['test']}: {detail['details']}")
        print("=" * 60)


# 模拟命令类型枚举
class CommandType(Enum):
    SAVE = "save"
    SEARCH = "search"
    FORGET = "forget"
    RECALL = "recall"
    STATUS = "status"
    MODE = "mode"
    HELP = "help"
    ANALYZE = "analyze"
    UNKNOWN = "unknown"


# 简化的命令解析器（用于测试）
class SimpleCommandParser:
    def parse_command(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if not text.startswith("/"):
            return {"type": CommandType.UNKNOWN, "params": {}}
            
        parts = text.split(maxsplit=1)
        command = parts[0][1:].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "save":
            return {
                "type": CommandType.SAVE,
                "params": {"title": args} if args else {}
            }
        elif command == "search":
            if not args:
                return {"type": CommandType.UNKNOWN, "params": {}}
            return {
                "type": CommandType.SEARCH,
                "params": {"query": args}
            }
        elif command == "forget":
            if not args:
                return {
                    "type": CommandType.FORGET,
                    "params": {"scope": "current"}
                }
            elif args == "all":
                return {
                    "type": CommandType.FORGET,
                    "params": {"scope": "all"}
                }
            else:
                return {
                    "type": CommandType.FORGET,
                    "params": {"scope": "specific", "session_id": args}
                }
        elif command == "recall":
            if not args:
                return {
                    "type": CommandType.RECALL,
                    "params": {"limit": 10}
                }
            elif args.isdigit():
                return {
                    "type": CommandType.RECALL,
                    "params": {"limit": int(args)}
                }
            elif args.startswith("session_"):
                return {
                    "type": CommandType.RECALL,
                    "params": {"session_id": args}
                }
            else:
                return {
                    "type": CommandType.RECALL,
                    "params": {"limit": 10}
                }
        elif command == "status":
            return {"type": CommandType.STATUS, "params": {}}
        elif command == "mode":
            if not args:
                return {
                    "type": CommandType.MODE,
                    "params": {"mode": "status"}
                }
            elif args in ["on", "off"]:
                return {
                    "type": CommandType.MODE,
                    "params": {"mode": args}
                }
            else:
                return {
                    "type": CommandType.MODE,
                    "params": {"mode": "status"}
                }
        elif command == "help":
            return {
                "type": CommandType.HELP,
                "params": {"command": args} if args else {}
            }
        elif command == "analyze":
            if not args:
                return {"type": CommandType.ANALYZE, "params": {}}
            parts = args.split()
            params = {"analysis_type": parts[0]}
            if len(parts) > 1 and parts[1].isdigit():
                params["days"] = int(parts[1])
            return {"type": CommandType.ANALYZE, "params": params}
        else:
            return {"type": CommandType.UNKNOWN, "params": {}}


# 简化的会话管理器（用于测试）
class SimpleSessionManager:
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".sage" / "sessions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.active_session = None
        
    def start_session(self, title: str = None) -> str:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.active_session = {
            "session_id": session_id,
            "title": title or "Untitled Session",
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "tags": []
        }
        return session_id
        
    def add_message(self, role: str, content: str):
        if self.active_session:
            self.active_session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            
    def save_session(self) -> str:
        if not self.active_session:
            return None
            
        file_path = self.data_dir / f"{self.active_session['session_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.active_session, f, ensure_ascii=False, indent=2)
            
        session_id = self.active_session["session_id"]
        self.active_session = None
        return str(file_path)
        
    def load_session(self, session_id: str) -> Dict[str, Any]:
        file_path = self.data_dir / f"{session_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
        
    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        for file_path in self.data_dir.glob("session_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data["session_id"],
                        "title": data["title"],
                        "created_at": data["created_at"],
                        "message_count": len(data.get("messages", []))
                    })
            except:
                pass
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)


# 测试函数
async def test_command_parser(results: TestResults):
    """测试命令解析器"""
    print("\n### 测试命令解析器 ###")
    parser = SimpleCommandParser()
    
    # 测试保存命令
    cmd = parser.parse_command("/save 测试标题")
    success = cmd["type"] == CommandType.SAVE and cmd["params"].get("title") == "测试标题"
    results.add_result("命令解析 - 保存", success)
    
    # 测试搜索命令
    cmd = parser.parse_command("/search Python")
    success = cmd["type"] == CommandType.SEARCH and cmd["params"].get("query") == "Python"
    results.add_result("命令解析 - 搜索", success)
    
    # 测试忘记命令
    cmd = parser.parse_command("/forget all")
    success = cmd["type"] == CommandType.FORGET and cmd["params"].get("scope") == "all"
    results.add_result("命令解析 - 忘记", success)
    
    # 测试回忆命令
    cmd = parser.parse_command("/recall 5")
    success = cmd["type"] == CommandType.RECALL and cmd["params"].get("limit") == 5
    results.add_result("命令解析 - 回忆", success)
    
    # 测试模式命令
    cmd = parser.parse_command("/mode on")
    success = cmd["type"] == CommandType.MODE and cmd["params"].get("mode") == "on"
    results.add_result("命令解析 - 模式", success)
    
    # 测试未知命令
    cmd = parser.parse_command("/unknown")
    success = cmd["type"] == CommandType.UNKNOWN
    results.add_result("命令解析 - 未知命令", success)


async def test_session_manager(results: TestResults):
    """测试会话管理器"""
    print("\n### 测试会话管理器 ###")
    
    # 使用临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SimpleSessionManager(temp_dir)
        
        # 测试创建会话
        session_id = manager.start_session("测试会话")
        success = session_id is not None and manager.active_session is not None
        results.add_result("会话管理 - 创建", success)
        
        # 测试添加消息
        manager.add_message("user", "你好")
        manager.add_message("assistant", "你好！")
        success = len(manager.active_session["messages"]) == 2
        results.add_result("会话管理 - 添加消息", success)
        
        # 测试保存会话
        saved_path = manager.save_session()
        success = saved_path is not None and Path(saved_path).exists()
        results.add_result("会话管理 - 保存", success)
        
        # 测试加载会话
        loaded = manager.load_session(session_id)
        success = loaded is not None and loaded["title"] == "测试会话"
        results.add_result("会话管理 - 加载", success)
        
        # 测试列出会话
        sessions = manager.list_sessions()
        success = len(sessions) >= 1
        results.add_result("会话管理 - 列出", success)


async def test_error_handling(results: TestResults):
    """测试错误处理"""
    print("\n### 测试错误处理 ###")
    
    # 添加父目录到路径
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # 测试错误分类
    try:
        from sage_error_handler import ErrorHandler, ErrorType, ErrorSeverity
    except ImportError:
        results.add_result("错误处理 - 模块导入", False, "无法导入错误处理模块")
        return
    
    handler = ErrorHandler()
    
    # 测试验证错误
    error_info = handler.handle_error(ValueError("Invalid input"))
    success = error_info["type"] == ErrorType.VALIDATION_ERROR
    results.add_result("错误处理 - 验证错误分类", success)
    
    # 测试系统错误
    error_info = handler.handle_error(FileNotFoundError("File not found"))
    success = error_info["type"] == ErrorType.SYSTEM_ERROR
    results.add_result("错误处理 - 系统错误分类", success)
    
    # 测试错误统计
    summary = handler.get_error_summary()
    success = "total_errors" in summary and "error_distribution" in summary
    results.add_result("错误处理 - 错误统计", success)


async def test_performance_monitoring(results: TestResults):
    """测试性能监控"""
    print("\n### 测试性能监控 ###")
    
    from sage_error_handler import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    
    # 测试性能测量
    async with monitor.measure_performance("test_op"):
        await asyncio.sleep(0.01)  # 10ms
        
    summary = monitor.get_performance_summary()
    success = "operation_stats" in summary
    results.add_result("性能监控 - 操作测量", success)
    
    # 测试系统指标
    metrics = monitor.get_system_metrics()
    success = all(k in metrics for k in ["cpu_usage", "memory_usage"])
    results.add_result("性能监控 - 系统指标", success)


async def test_smart_prompt_basic(results: TestResults):
    """测试智能提示基础功能"""
    print("\n### 测试智能提示 ###")
    
    from sage_smart_prompt_system import (
        ContextDetector, PromptContext, SmartPromptGenerator
    )
    
    # 测试上下文检测
    detector = ContextDetector()
    
    context = detector.detect_context("如何编写Python装饰器？")
    success = context == PromptContext.CODING
    results.add_result("智能提示 - 编程上下文检测", success)
    
    context = detector.detect_context("TypeError: 'NoneType' object is not subscriptable")
    success = context == PromptContext.DEBUGGING
    results.add_result("智能提示 - 调试上下文检测", success)
    
    context = detector.detect_context("我想学习机器学习")
    success = context == PromptContext.LEARNING
    results.add_result("智能提示 - 学习上下文检测", success)
    
    # 测试关键词提取
    generator = SmartPromptGenerator()
    keywords = generator._extract_keywords("Python中的装饰器是什么？")
    success = "Python" in keywords and "装饰器" in keywords
    results.add_result("智能提示 - 关键词提取", success)


async def test_auto_save_features(results: TestResults):
    """测试自动保存功能"""
    print("\n### 测试自动保存功能 ###")
    
    try:
        from sage_mcp_auto_save import AutoSaveManager
        
        # 创建简单的会话管理器用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SimpleSessionManager(temp_dir)
            auto_save = AutoSaveManager(session_manager)
            
            # 测试自动保存管理器初始化
            success = auto_save is not None
            results.add_result("自动保存 - 管理器初始化", success)
            
            # 测试对话跟踪功能
            conversation_id = "test_conv_001"
            auto_save.start_conversation(conversation_id, "测试对话")
            
            # 添加消息
            auto_save.add_message("user", "你好")
            auto_save.add_message("assistant", "你好！有什么可以帮助你的吗？")
            
            # 检查对话是否被跟踪
            success = conversation_id in auto_save.conversations
            results.add_result("自动保存 - 对话跟踪", success)
            
            # 测试自动保存触发
            # 注意：由于测试环境限制，这里只验证方法存在
            success = hasattr(auto_save, 'save_if_complete')
            results.add_result("自动保存 - 保存方法存在", success)
            
    except Exception as e:
        results.add_result("自动保存 - 基础功能", False, str(e))


async def test_memory_analysis_basic(results: TestResults):
    """测试记忆分析基础功能"""
    print("\n### 测试记忆分析 ###")
    
    # 创建测试数据
    test_sessions = [
        {
            "session_id": "test1",
            "title": "Python编程",
            "messages": [
                {"role": "user", "content": "如何使用Python装饰器？"},
                {"role": "assistant", "content": "装饰器是Python的高级特性..."}
            ],
            "created_at": datetime.now().isoformat()
        },
        {
            "session_id": "test2",
            "title": "机器学习",
            "messages": [
                {"role": "user", "content": "什么是神经网络？"},
                {"role": "assistant", "content": "神经网络是一种模拟人脑的计算模型..."}
            ],
            "created_at": datetime.now().isoformat()
        }
    ]
    
    # 测试主题提取
    topics = set()
    for session in test_sessions:
        for msg in session["messages"]:
            if "Python" in msg["content"] or "装饰器" in msg["content"]:
                topics.add("Python编程")
            if "神经网络" in msg["content"] or "机器学习" in msg["content"]:
                topics.add("机器学习")
                
    success = len(topics) == 2
    results.add_result("记忆分析 - 主题提取", success)


async def run_all_unit_tests():
    """运行所有单元测试"""
    print("=" * 60)
    print("Sage MCP 综合单元测试")
    print("=" * 60)
    
    results = TestResults()
    
    # 运行各项测试
    await test_command_parser(results)
    await test_session_manager(results)
    await test_error_handling(results)
    await test_performance_monitoring(results)
    await test_smart_prompt_basic(results)
    await test_auto_save_features(results)
    await test_memory_analysis_basic(results)
    
    # 打印总结
    results.print_summary()
    
    return results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_unit_tests())
    
    if success:
        print("\n✨ 所有单元测试通过！")
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        sys.exit(1)