#!/usr/bin/env python3
"""
第三阶段高级功能测试
测试增强的会话管理和记忆分析功能
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import components
from sage_session_manager_v2 import (
    EnhancedSessionManager,
    SessionStatus,
    SessionSearchType
)
from sage_memory_analyzer import (
    MemoryAnalyzer,
    AnalysisType
)


class TestEnhancedSessionManager:
    """测试增强版会话管理器"""
    
    def test_session_lifecycle(self):
        """测试会话生命周期"""
        print("\n测试增强会话生命周期...")
        
        manager = EnhancedSessionManager()
        
        # 创建会话
        session1 = manager.create_session("Python异步编程", {"level": "advanced"})
        print(f"✓ 创建会话: {session1['id']}")
        
        # 添加消息和上下文
        manager.add_message("user", "什么是async/await？")
        manager.add_message("assistant", "async/await是Python中的异步编程语法...")
        manager.add_context_injection("之前讨论过协程的概念", "async/await")
        
        # 添加工具调用
        manager.add_message("assistant", "让我搜索一些例子...", {
            "tool_calls": [{"tool": "search_memory", "arguments": {"query": "async"}}]
        })
        
        # 验证统计
        stats = session1["statistics"]
        assert stats["message_count"] == 3
        assert stats["user_message_count"] == 1
        assert stats["assistant_message_count"] == 2
        assert stats["tool_call_count"] == 1
        assert stats["context_injections"] == 1
        
        print("✓ 消息和统计正确更新")
        
        # 暂停会话
        paused = manager.pause_session()
        assert paused["status"] == SessionStatus.PAUSED.value
        print("✓ 会话已暂停")
        
        # 创建第二个会话
        session2 = manager.create_session("数据结构与算法")
        manager.add_message("user", "解释一下二叉树")
        
        # 恢复第一个会话
        resumed = manager.resume_session(session1["id"])
        assert resumed["id"] == session1["id"]
        assert manager.active_session["id"] == session1["id"]
        print("✓ 会话已恢复")
        
        # 完成会话
        completed = manager.complete_session()
        assert completed["status"] == SessionStatus.COMPLETED.value
        assert completed["summary"] is not None
        print("✓ 会话已完成，生成摘要")
        
        return True
    
    def test_session_search(self):
        """测试会话搜索功能"""
        print("\n测试会话搜索功能...")
        
        manager = EnhancedSessionManager()
        
        # 创建多个测试会话
        topics = [
            "Python装饰器详解",
            "机器学习入门",
            "Python性能优化",
            "深度学习框架比较"
        ]
        
        for topic in topics:
            session = manager.create_session(topic)
            manager.add_message("user", f"请介绍{topic}")
            manager.add_message("assistant", f"关于{topic}的内容...")
            manager.complete_session()
            
        # 按主题搜索
        results = manager.search_sessions(SessionSearchType.BY_TOPIC, "Python")
        assert len(results) == 2  # Python装饰器、Python性能优化
        print(f"✓ 主题搜索: 找到 {len(results)} 个Python相关会话")
        
        # 按关键词搜索
        results = manager.search_sessions(SessionSearchType.BY_KEYWORD, "学习")
        assert len(results) >= 2  # 机器学习、深度学习
        print(f"✓ 关键词搜索: 找到 {len(results)} 个包含'学习'的会话")
        
        # 按状态搜索
        results = manager.search_sessions(SessionSearchType.BY_STATUS, "completed")
        assert len(results) == 4
        print(f"✓ 状态搜索: 找到 {len(results)} 个已完成会话")
        
        return True
    
    def test_session_analytics(self):
        """测试会话分析功能"""
        print("\n测试会话分析功能...")
        
        manager = EnhancedSessionManager()
        
        # 创建测试数据
        session = manager.create_session("测试会话")
        for i in range(5):
            manager.add_message("user", f"问题 {i+1}")
            manager.add_message("assistant", f"回答 {i+1}")
        manager.complete_session()
        
        # 获取分析
        analytics = manager.get_session_analytics()
        
        assert analytics["total_sessions"] == 1
        assert analytics["total_messages"] == 10
        assert analytics["average_messages_per_session"] == 10
        
        print(f"✓ 基础统计: {analytics['total_sessions']} 个会话, {analytics['total_messages']} 条消息")
        print(f"✓ 状态分布: {analytics['status_distribution']}")
        
        # 话题分析
        if analytics.get("top_topics"):
            print(f"✓ 热门话题: {analytics['top_topics'][:3]}")
            
        return True
    
    def test_session_export(self):
        """测试会话导出功能"""
        print("\n测试会话导出功能...")
        
        manager = EnhancedSessionManager()
        
        # 创建会话
        session = manager.create_session("导出测试会话")
        manager.add_message("user", "这是一个测试问题")
        manager.add_message("assistant", "这是一个测试回答", {
            "tool_calls": [{"tool": "test_tool", "arguments": {"param": "value"}}]
        })
        manager.complete_session()
        
        # JSON导出
        json_export = manager.export_session(session["id"], "json")
        assert len(json_export) > 0
        assert "session" in json_export
        print(f"✓ JSON导出: {len(json_export)} 字符")
        
        # Markdown导出
        md_export = manager.export_session(session["id"], "markdown")
        assert len(md_export) > 0
        assert "# 会话记录" in md_export
        assert "## 对话内容" in md_export
        print(f"✓ Markdown导出: {len(md_export)} 字符")
        
        return True


class TestMemoryAnalyzer:
    """测试记忆分析器"""
    
    def __init__(self):
        # 创建模拟的记忆提供者
        self.memory_provider = self._create_mock_provider()
        self.analyzer = MemoryAnalyzer(self.memory_provider)
    
    def _create_mock_provider(self):
        """创建模拟记忆提供者"""
        class MockProvider:
            def search_memory(self, query, n=10):
                # 生成模拟记忆数据
                memories = []
                
                # 模拟不同时间的记忆
                base_time = datetime.now()
                topics = [
                    ("Python", "装饰器", "函数"),
                    ("机器学习", "神经网络", "深度学习"),
                    ("数据结构", "算法", "复杂度"),
                    ("Web开发", "API", "REST")
                ]
                
                for i in range(n):
                    topic_group = topics[i % len(topics)]
                    content = f"关于{topic_group[i % 3]}的讨论..."
                    
                    class MockResult:
                        def __init__(self, content, role, timestamp):
                            self.content = content
                            self.role = role if role else ("user" if i % 2 == 0 else "assistant")
                            self.metadata = {"timestamp": timestamp}
                            self.score = 0.9 - (i * 0.05)
                            
                    timestamp = base_time - timedelta(hours=i*2)
                    memories.append(MockResult(content, None, timestamp))
                    
                return memories[:n]
                
            def get_memory_stats(self):
                return {
                    "total": 100,
                    "with_embeddings": 80,
                    "sessions": 20
                }
                
        return MockProvider()
    
    async def test_topic_clustering(self):
        """测试话题聚类分析"""
        print("\n测试话题聚类分析...")
        
        result = await self.analyzer.analyze_memory_patterns(
            AnalysisType.TOPIC_CLUSTERING,
            limit=50
        )
        
        assert result["total_memories"] > 0
        assert result["identified_topics"] > 0
        assert "top_keywords" in result
        
        print(f"✓ 分析了 {result['total_memories']} 条记忆")
        print(f"✓ 识别到 {result['identified_topics']} 个话题")
        
        # 显示热门关键词
        if result.get("top_keywords"):
            keywords = list(result["top_keywords"].items())[:5]
            print(f"✓ 热门关键词: {keywords}")
            
        return True
    
    async def test_temporal_patterns(self):
        """测试时间模式分析"""
        print("\n测试时间模式分析...")
        
        result = await self.analyzer.analyze_memory_patterns(
            AnalysisType.TEMPORAL_PATTERNS,
            limit=50
        )
        
        assert "temporal_span" in result
        assert "activity_patterns" in result
        assert "interaction_gaps" in result
        
        span = result["temporal_span"]
        print(f"✓ 时间跨度: {span.get('total_days', 0)} 天")
        
        patterns = result["activity_patterns"]
        if patterns.get("peak_hours"):
            print(f"✓ 活跃时段: {patterns['peak_hours'][:3]}")
            
        gaps = result["interaction_gaps"]
        print(f"✓ 平均交互间隔: {gaps.get('average_seconds', 0) / 60:.1f} 分钟")
        
        return True
    
    async def test_interaction_flow(self):
        """测试交互流程分析"""
        print("\n测试交互流程分析...")
        
        result = await self.analyzer.analyze_memory_patterns(
            AnalysisType.INTERACTION_FLOW,
            limit=50
        )
        
        assert "conversation_stats" in result
        assert "role_distribution" in result
        assert "interaction_types" in result
        
        conv_stats = result["conversation_stats"]
        print(f"✓ 总对话数: {conv_stats.get('total_conversations', 0)}")
        print(f"✓ 平均对话长度: {conv_stats.get('average_length', 0):.1f}")
        
        role_dist = result["role_distribution"]
        print(f"✓ 角色分布: {role_dist}")
        
        return True
    
    async def test_knowledge_graph(self):
        """测试知识图谱构建"""
        print("\n测试知识图谱构建...")
        
        result = await self.analyzer.analyze_memory_patterns(
            AnalysisType.KNOWLEDGE_GRAPH,
            limit=50
        )
        
        assert "graph_stats" in result
        assert "core_concepts" in result
        assert "knowledge_nodes" in result
        
        stats = result["graph_stats"]
        print(f"✓ 知识图谱: {stats['total_nodes']} 个节点, {stats['total_edges']} 条边")
        
        if result.get("core_concepts"):
            concepts = result["core_concepts"][:3]
            print(f"✓ 核心概念: {[c['entity'] for c in concepts]}")
            
        return True


class TestIntegration:
    """测试集成功能"""
    
    async def test_session_with_memory_analysis(self):
        """测试会话与记忆分析的集成"""
        print("\n测试会话与记忆分析集成...")
        
        # 创建管理器
        session_manager = EnhancedSessionManager()
        memory_analyzer = TestMemoryAnalyzer().analyzer
        
        # 创建会话并添加内容
        session = session_manager.create_session("集成测试会话")
        
        # 模拟对话
        messages = [
            ("user", "解释Python的装饰器"),
            ("assistant", "装饰器是Python的高级特性..."),
            ("user", "能给个例子吗？"),
            ("assistant", "当然，这是一个简单的装饰器例子...")
        ]
        
        for role, content in messages:
            session_manager.add_message(role, content)
            
        # 完成会话
        session_manager.complete_session()
        
        # 执行记忆分析
        topic_analysis = await memory_analyzer.analyze_memory_patterns(
            AnalysisType.TOPIC_CLUSTERING
        )
        
        print("✓ 会话创建并完成")
        print(f"✓ 记忆分析识别到 {topic_analysis['identified_topics']} 个话题")
        
        # 导出会话
        export = session_manager.export_session(session["id"], "markdown")
        print(f"✓ 会话导出成功 ({len(export)} 字符)")
        
        return True


async def run_all_phase3_tests():
    """运行第三阶段所有测试"""
    print("=" * 60)
    print("第三阶段高级功能测试")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    # 测试列表
    test_cases = [
        # 会话管理测试
        (TestEnhancedSessionManager().test_session_lifecycle, "增强会话生命周期"),
        (TestEnhancedSessionManager().test_session_search, "会话搜索功能"),
        (TestEnhancedSessionManager().test_session_analytics, "会话分析功能"),
        (TestEnhancedSessionManager().test_session_export, "会话导出功能"),
        
        # 记忆分析测试
        (TestMemoryAnalyzer().test_topic_clustering, "话题聚类分析"),
        (TestMemoryAnalyzer().test_temporal_patterns, "时间模式分析"),
        (TestMemoryAnalyzer().test_interaction_flow, "交互流程分析"),
        (TestMemoryAnalyzer().test_knowledge_graph, "知识图谱构建"),
        
        # 集成测试
        (TestIntegration().test_session_with_memory_analysis, "会话与记忆分析集成")
    ]
    
    for test_func, test_name in test_cases:
        total_count += 1
        try:
            # 运行测试
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                success_count += 1
                print(f"\n✅ {test_name}测试通过")
            else:
                print(f"\n❌ {test_name}测试失败")
        except Exception as e:
            print(f"\n❌ {test_name}测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("✅ 第三阶段所有测试通过！")
        print("\n核心功能验证:")
        print("• 增强会话管理 ✓")
        print("• 会话搜索导出 ✓")
        print("• 记忆深度分析 ✓")
        print("• 知识图谱构建 ✓")
        print("• 系统集成测试 ✓")
    else:
        print(f"❌ 有 {total_count - success_count} 个测试失败")
    
    print("=" * 60)
    
    return success_count == total_count


if __name__ == "__main__":
    # 运行异步测试
    success = asyncio.run(run_all_phase3_tests())
    
    if success:
        print("\n✨ 第三阶段功能开发完成！")
        print("可以进入第四阶段：实现智能提示系统")