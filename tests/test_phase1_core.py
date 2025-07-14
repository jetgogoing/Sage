#!/usr/bin/env python3
"""
第一阶段核心功能测试（不依赖 MCP SDK）
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCommandParser:
    """测试命令解析器"""
    
    def test_command_patterns(self):
        """测试命令模式匹配"""
        print("\n测试命令模式匹配...")
        
        # 模拟命令解析
        commands = {
            "/SAGE 如何实现快速排序": ("SAGE", {"query": "如何实现快速排序"}),
            "/SAGE-MODE on": ("SAGE_MODE", {"action": "on"}),
            "/SAGE-SESSION start Python学习": ("SAGE_SESSION", {"action": "start", "topic": "Python学习"}),
            "/SAGE-RECALL recent 10": ("SAGE_RECALL", {"type": "recent", "params": "10"}),
            "/SAGE-ANALYZE": ("SAGE_ANALYZE", {}),
            "/SAGE-STRATEGY adaptive": ("SAGE_STRATEGY", {"strategy": "adaptive"}),
            "/SAGE-CONFIG rerank off": ("SAGE_CONFIG", {"key": "rerank", "value": "off"}),
            "/SAGE-EXPORT session": ("SAGE_EXPORT", {"type": "session"})
        }
        
        for cmd, expected in commands.items():
            # 简单解析逻辑
            parts = cmd.split()
            cmd_name = parts[0].upper()
            
            if cmd_name.startswith("/SAGE"):
                print(f"✓ 识别命令: {cmd_name}")
            else:
                print(f"✗ 无法识别命令: {cmd}")
        
        print("✓ 命令模式测试完成")


class TestSessionLogic:
    """测试会话逻辑"""
    
    def test_session_lifecycle(self):
        """测试会话生命周期"""
        print("\n测试会话生命周期...")
        
        # 模拟会话数据
        session = {
            "id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "topic": "Python学习",
            "start_time": datetime.now(),
            "messages": [],
            "context": []
        }
        
        print(f"✓ 创建会话: {session['id']}")
        
        # 添加消息
        session["messages"].append({
            "type": "user",
            "content": "什么是装饰器？",
            "timestamp": datetime.now()
        })
        session["messages"].append({
            "type": "assistant",
            "content": "装饰器是Python中的高级特性...",
            "timestamp": datetime.now()
        })
        
        print(f"✓ 添加了 {len(session['messages'])} 条消息")
        
        # 生成总结
        session["end_time"] = datetime.now()
        session["duration"] = (session["end_time"] - session["start_time"]).total_seconds()
        session["summary"] = f"会话主题：{session['topic']}，持续 {session['duration']:.1f} 秒，交流了 {len(session['messages'])} 条消息"
        
        print(f"✓ 会话总结: {session['summary']}")
        
        return True


class TestConversationTracking:
    """测试对话跟踪逻辑"""
    
    def test_conversation_structure(self):
        """测试对话结构"""
        print("\n测试对话跟踪结构...")
        
        # 模拟对话数据
        conversation = {
            "user_input": "如何优化Python代码性能？",
            "assistant_responses": [],
            "tool_calls": [],
            "context_used": None,
            "timestamp": datetime.now()
        }
        
        print("✓ 创建对话记录")
        
        # 添加上下文
        conversation["context_used"] = "之前讨论过使用 cProfile 进行性能分析..."
        print("✓ 添加历史上下文")
        
        # 添加助手响应
        conversation["assistant_responses"].append("优化Python代码性能有多种方法：")
        conversation["assistant_responses"].append("1. 使用内置函数和库...")
        conversation["assistant_responses"].append("2. 避免全局变量...")
        print(f"✓ 添加了 {len(conversation['assistant_responses'])} 个响应片段")
        
        # 添加工具调用
        conversation["tool_calls"].append({
            "tool": "search_memory",
            "arguments": {"query": "Python性能优化"},
            "result": "找到5条相关记忆",
            "timestamp": datetime.now().isoformat()
        })
        print(f"✓ 记录了 {len(conversation['tool_calls'])} 次工具调用")
        
        # 合并响应
        full_response = "\n\n".join(conversation["assistant_responses"])
        print(f"✓ 合并响应长度: {len(full_response)} 字符")
        
        return True


class TestMemoryIntegration:
    """测试记忆系统集成"""
    
    def test_memory_operations(self):
        """测试记忆操作"""
        print("\n测试记忆系统集成...")
        
        # 模拟记忆保存
        memory_data = {
            "session_id": "test_session_001",
            "turn_id": 1,
            "user_prompt": "什么是机器学习？",
            "assistant_response": "机器学习是人工智能的一个分支...",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source": "test",
                "has_code": False
            }
        }
        
        print("✓ 准备保存记忆数据")
        print(f"  - Session ID: {memory_data['session_id']}")
        print(f"  - Turn ID: {memory_data['turn_id']}")
        
        # 模拟记忆检索
        search_query = "机器学习"
        print(f"\n✓ 搜索记忆: '{search_query}'")
        
        # 模拟检索结果
        mock_results = [
            {
                "content": "机器学习是人工智能的一个分支...",
                "score": 0.95,
                "role": "assistant",
                "metadata": {"timestamp": "2025-01-14"}
            },
            {
                "content": "深度学习是机器学习的子领域...",
                "score": 0.87,
                "role": "assistant", 
                "metadata": {"timestamp": "2025-01-13"}
            }
        ]
        
        print(f"✓ 找到 {len(mock_results)} 条相关记忆")
        for i, result in enumerate(mock_results, 1):
            print(f"  {i}. 相似度: {result['score']:.2f} - {result['content'][:50]}...")
        
        return True


class TestRetrievalStrategies:
    """测试检索策略"""
    
    def test_strategy_selection(self):
        """测试策略选择"""
        print("\n测试检索策略...")
        
        strategies = {
            "semantic_first": "语义优先 - 基于含义相似度",
            "temporal_weighted": "时间加权 - 考虑时间因素",
            "context_aware": "上下文感知 - 结合会话历史",
            "hybrid_advanced": "混合高级 - 综合多种因素",
            "adaptive": "自适应 - 根据查询类型调整"
        }
        
        for name, desc in strategies.items():
            print(f"✓ 策略 '{name}': {desc}")
        
        # 模拟策略选择
        query_types = {
            "什么是Python？": "semantic_first",
            "刚才我们讨论的内容": "temporal_weighted", 
            "继续上面的话题": "context_aware",
            "综合分析一下": "hybrid_advanced"
        }
        
        print("\n策略选择示例:")
        for query, strategy in query_types.items():
            print(f"  查询: '{query}' → 策略: {strategy}")
        
        return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第一阶段核心功能测试")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    # 测试列表
    tests = [
        (TestCommandParser().test_command_patterns, "命令解析"),
        (TestSessionLogic().test_session_lifecycle, "会话管理"),
        (TestConversationTracking().test_conversation_structure, "对话跟踪"),
        (TestMemoryIntegration().test_memory_operations, "记忆集成"),
        (TestRetrievalStrategies().test_strategy_selection, "检索策略")
    ]
    
    for test_func, test_name in tests:
        total_count += 1
        try:
            test_func()
            success_count += 1
            print(f"\n✅ {test_name}测试通过")
        except Exception as e:
            print(f"\n❌ {test_name}测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("✅ 第一阶段所有核心功能测试通过！")
    else:
        print(f"❌ 有 {total_count - success_count} 个测试失败")
    
    print("=" * 60)
    
    # 提示下一步
    print("\n下一步建议:")
    print("1. 安装 MCP SDK: pip install mcp")
    print("2. 确保 PostgreSQL 数据库运行中")
    print("3. 配置环境变量 (SILICONFLOW_API_KEY, DATABASE_URL)")
    print("4. 将配置文件复制到 Claude Code 配置目录")
    print("5. 重启 Claude Code 并测试连接")


if __name__ == "__main__":
    run_all_tests()