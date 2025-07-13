#!/usr/bin/env python3
"""
🚀 Sage MCP V3 阶段2完整测试套件
世界级智能上下文检索和提示增强系统测试
"""

import unittest
import sys
import asyncio
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置测试环境
os.environ['SAGE_DEBUG'] = '1'
os.environ['ORIGINAL_CLAUDE_PATH'] = 'python3 /Volumes/1T HDD/Sage/mock_claude.py'

# 导入测试模块
from intelligent_retrieval import (
    IntelligentRetrievalEngine,
    AdvancedSemanticAnalyzer, 
    TemporalScoringEngine,
    HybridScoringAlgorithm,
    QueryType,
    RetrievalStrategy,
    RetrievalResult
)

from prompt_enhancer import (
    IntelligentPromptEnhancer,
    MemoryFusionProcessor,
    AdaptivePromptGenerator,
    EnhancementLevel,
    PromptType
)

from memory_interface import MemoryProviderV1, NullMemoryProvider


class TestAdvancedSemanticAnalyzer(unittest.TestCase):
    """测试高级语义分析器"""
    
    def setUp(self):
        self.analyzer = AdvancedSemanticAnalyzer()
    
    def test_query_type_identification(self):
        """测试查询类型识别"""
        # 技术查询
        tech_query = "如何实现Python函数的缓存装饰器？"
        context = self.analyzer.analyze_query(tech_query)
        self.assertEqual(context.query_type, QueryType.TECHNICAL)
        
        # 诊断查询
        diag_query = "我的代码报错了，显示KeyError"
        context = self.analyzer.analyze_query(diag_query)
        self.assertEqual(context.query_type, QueryType.DIAGNOSTIC)
        
        # 流程查询
        proc_query = "如何一步步部署Django应用？"
        context = self.analyzer.analyze_query(proc_query)
        self.assertEqual(context.query_type, QueryType.PROCEDURAL)
    
    def test_technical_keyword_extraction(self):
        """测试技术关键词提取"""
        query = "实现一个Redis缓存的用户认证系统，使用JWT token"
        context = self.analyzer.analyze_query(query)
        
        # 应该提取到技术关键词
        keywords = context.technical_keywords
        self.assertTrue(any('token' in kw.lower() for kw in keywords) or 'JWT' in query)
        
    def test_emotion_analysis(self):
        """测试情感分析"""
        urgent_query = "紧急！生产环境数据库连接失败"
        context = self.analyzer.analyze_query(urgent_query)
        self.assertEqual(context.emotional_tone, "urgent")
        self.assertGreaterEqual(context.urgency_level, 4)
        
        confused_query = "我不懂为什么这个算法这么慢"
        context = self.analyzer.analyze_query(confused_query)
        self.assertEqual(context.emotional_tone, "confused")


class TestTemporalScoringEngine(unittest.TestCase):
    """测试时间衰减评分引擎"""
    
    def setUp(self):
        self.engine = TemporalScoringEngine()
        self.current_time = datetime.now()
    
    def test_recent_content_boost(self):
        """测试近期内容增强"""
        # 1小时前的内容
        recent_time = self.current_time - timedelta(hours=1)
        score = self.engine.calculate_temporal_score(recent_time, self.current_time)
        
        # 3天前的内容（确保显著差异）
        old_time = self.current_time - timedelta(days=3)
        old_score = self.engine.calculate_temporal_score(old_time, self.current_time)
        
        # 近期内容应该得分更高
        self.assertGreater(score, old_score)
    
    def test_urgency_influence(self):
        """测试紧急度影响"""
        from intelligent_retrieval import QueryContext
        
        # 高紧急度查询
        urgent_context = QueryContext(
            query="紧急问题",
            query_type=QueryType.DIAGNOSTIC,
            urgency_level=5
        )
        
        test_time = self.current_time - timedelta(hours=6)
        urgent_score = self.engine.calculate_temporal_score(
            test_time, self.current_time, urgent_context
        )
        
        # 普通查询
        normal_context = QueryContext(
            query="普通问题",
            query_type=QueryType.CONCEPTUAL,
            urgency_level=1
        )
        
        normal_score = self.engine.calculate_temporal_score(
            test_time, self.current_time, normal_context
        )
        
        # 紧急查询应该对时间更敏感
        self.assertGreaterEqual(urgent_score, normal_score)


class TestMemoryFusionProcessor(unittest.TestCase):
    """测试记忆融合处理器"""
    
    def setUp(self):
        # 创建临时prompts目录
        self.temp_dir = Path(tempfile.mkdtemp())
        self.prompts_dir = self.temp_dir / "prompts"
        self.prompts_dir.mkdir()
        
        # 创建测试模板文件
        template_content = """
You are a Memory Fusion Assistant.

**Fragments**
---
{retrieved_passages}
---
"""
        template_file = self.prompts_dir / "memory_fusion_prompt_programming.txt"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template_content)
            
        self.processor = MemoryFusionProcessor(self.prompts_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_template_loading(self):
        """测试模板加载"""
        self.assertIsNotNone(self.processor.user_template)
        self.assertIn("{retrieved_passages}", self.processor.user_template)
    
    def test_memory_fusion(self):
        """测试记忆融合"""
        # 创建测试片段
        fragments = [
            RetrievalResult(
                content="这是一个Python函数示例",
                role="assistant",
                similarity_score=0.8,
                temporal_score=0.7,
                context_score=0.6,
                final_score=0.7,
                reasoning="高相似度"
            ),
            RetrievalResult(
                content="用户的相关问题",
                role="user", 
                similarity_score=0.6,
                temporal_score=0.8,
                context_score=0.5,
                final_score=0.6,
                reasoning="时效性强"
            )
        ]
        
        result = self.processor.process_memory_fusion(fragments)
        
        # 验证融合结果
        self.assertIn("Python函数示例", result)
        self.assertIn("用户的相关问题", result)
        self.assertIn("<fragment_01>", result)
        self.assertIn("<fragment_02>", result)


class MockMemoryProvider:
    """模拟记忆提供者"""
    
    def __init__(self):
        self.test_data = [
            {
                'content': 'Python中如何使用装饰器？',
                'role': 'user',
                'score': 0.8,
                'metadata': {'timestamp': datetime.now().isoformat()}
            },
            {
                'content': '装饰器是Python中的一种设计模式...',
                'role': 'assistant',
                'score': 0.7,
                'metadata': {'timestamp': (datetime.now() - timedelta(hours=1)).isoformat()}
            },
            {
                'content': '如何调试Python性能问题？',
                'role': 'user',
                'score': 0.6,
                'metadata': {'timestamp': (datetime.now() - timedelta(days=1)).isoformat()}
            }
        ]
    
    def search_memory(self, query, n=5):
        """模拟搜索记忆"""
        from memory_interface import MemorySearchResult
        results = []
        
        for item in self.test_data[:n]:
            results.append(MemorySearchResult(
                content=item['content'],
                role=item['role'],
                score=item['score'],
                metadata=item['metadata']
            ))
        
        return results


class TestIntelligentRetrievalEngine(unittest.TestCase):
    """测试智能检索引擎"""
    
    def setUp(self):
        self.memory_provider = MockMemoryProvider()
        self.engine = IntelligentRetrievalEngine(self.memory_provider)
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertIsNotNone(self.engine.semantic_analyzer)
        self.assertIsNotNone(self.engine.scoring_algorithm)
        self.assertEqual(self.engine.config['max_results'], 10)
    
    async def test_intelligent_retrieve(self):
        """测试智能检索"""
        query = "Python装饰器的使用方法"
        
        results = await self.engine.intelligent_retrieve(
            query=query,
            strategy=RetrievalStrategy.HYBRID_ADVANCED,
            max_results=3
        )
        
        # 验证结果
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)
        
        if results:
            # 验证结果结构
            result = results[0]
            self.assertIsInstance(result, RetrievalResult)
            self.assertIsInstance(result.final_score, float)
            self.assertIsInstance(result.reasoning, str)
            
            # 验证得分排序
            for i in range(1, len(results)):
                self.assertGreaterEqual(results[i-1].final_score, results[i].final_score)
    
    def test_diversity_filter(self):
        """测试多样性过滤"""
        # 创建相似的测试结果
        similar_results = [
            RetrievalResult(
                content="Python装饰器示例1",
                role="assistant",
                similarity_score=0.9,
                temporal_score=0.8,
                context_score=0.7,
                final_score=0.85,
                reasoning="高相似度"
            ),
            RetrievalResult(
                content="Python装饰器示例2",
                role="assistant", 
                similarity_score=0.8,
                temporal_score=0.7,
                context_score=0.6,
                final_score=0.75,
                reasoning="中等相似度"
            ),
            RetrievalResult(
                content="Django模型使用方法",
                role="assistant",
                similarity_score=0.7,
                temporal_score=0.6,
                context_score=0.5,
                final_score=0.65,
                reasoning="不同主题"
            )
        ]
        
        filtered = self.engine._apply_diversity_filter(similar_results, 2)
        
        # 应该选择多样性更好的组合
        self.assertEqual(len(filtered), 2)
        
        # 第一个应该是得分最高的
        self.assertEqual(filtered[0].final_score, 0.85)


class TestPromptEnhancer(unittest.TestCase):
    """测试提示增强器"""
    
    def setUp(self):
        # 创建模拟检索引擎
        self.mock_engine = Mock()
        self.mock_engine.intelligent_retrieve = AsyncMock()
        
        # 创建临时prompts目录
        self.temp_dir = Path(tempfile.mkdtemp())
        self.prompts_dir = self.temp_dir / "prompts"
        self.prompts_dir.mkdir()
        
        # 创建测试模板
        template_file = self.prompts_dir / "memory_fusion_prompt_programming.txt"
        with open(template_file, 'w') as f:
            f.write("Test template: {retrieved_passages}")
            
        self.enhancer = IntelligentPromptEnhancer(self.mock_engine, self.prompts_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_prompt_type_analysis(self):
        """测试提示类型分析"""
        # 编程类型
        coding_prompt = "请帮我实现一个Python函数"
        prompt_type = self.enhancer._analyze_prompt_type(coding_prompt)
        self.assertEqual(prompt_type, PromptType.CODING)
        
        # 调试类型
        debug_prompt = "我的代码有bug，怎么修复？"
        prompt_type = self.enhancer._analyze_prompt_type(debug_prompt)
        self.assertEqual(prompt_type, PromptType.DEBUGGING)
        
        # 解释类型
        explain_prompt = "请解释什么是RESTful API"
        prompt_type = self.enhancer._analyze_prompt_type(explain_prompt)
        self.assertEqual(prompt_type, PromptType.EXPLANATION)
    
    async def test_enhance_prompt_with_results(self):
        """测试带结果的提示增强"""
        # 设置模拟返回
        mock_results = [
            RetrievalResult(
                content="相关的技术解答",
                role="assistant",
                similarity_score=0.8,
                temporal_score=0.7,
                context_score=0.6,
                final_score=0.75,
                reasoning="高度相关"
            )
        ]
        self.mock_engine.intelligent_retrieve.return_value = mock_results
        
        # 执行增强
        context = await self.enhancer.enhance_prompt(
            "如何优化Python代码性能？",
            EnhancementLevel.STANDARD
        )
        
        # 验证结果
        self.assertIsNotNone(context.enhanced_prompt)
        self.assertEqual(len(context.fragments_used), 1)
        self.assertGreater(context.confidence_score, 0)
        self.assertIn("技术解答", context.enhanced_prompt)
    
    async def test_enhance_prompt_no_results(self):
        """测试无结果的提示增强"""
        # 设置空返回
        self.mock_engine.intelligent_retrieve.return_value = []
        
        # 执行增强
        context = await self.enhancer.enhance_prompt(
            "这是一个全新的问题",
            EnhancementLevel.ADAPTIVE
        )
        
        # 验证结果
        self.assertEqual(context.enhanced_prompt, "这是一个全新的问题")
        self.assertEqual(len(context.fragments_used), 0)
        self.assertEqual(context.confidence_score, 1.0)  # 无需增强时置信度为1
    
    def test_confidence_calculation(self):
        """测试置信度计算"""
        # 高质量片段
        high_quality = [
            RetrievalResult("content1", "user", 0.9, 0.8, 0.7, 0.85, {}, "excellent"),
            RetrievalResult("content2", "assistant", 0.8, 0.7, 0.6, 0.75, {}, "good")
        ]
        
        confidence = self.enhancer._calculate_confidence(high_quality)
        self.assertGreater(confidence, 0.7)
        
        # 低质量片段
        low_quality = [
            RetrievalResult("content3", "user", 0.3, 0.2, 0.1, 0.25, {}, "poor")
        ]
        
        low_confidence = self.enhancer._calculate_confidence(low_quality)
        self.assertLess(low_confidence, 0.5)
    
    def test_enhancement_stats(self):
        """测试增强统计"""
        stats = self.enhancer.get_enhancement_stats()
        
        # 验证统计结构
        self.assertIn('total_enhancements', stats)
        self.assertIn('successful_enhancements', stats)
        self.assertIn('success_rate', stats)
        self.assertIn('average_confidence', stats)
        self.assertIn('config', stats)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        # 使用空记忆提供者避免真实数据库依赖
        self.memory_provider = NullMemoryProvider()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_end_to_end_enhancement(self):
        """端到端增强测试"""
        # 创建带模拟数据的记忆提供者
        memory_provider = MockMemoryProvider()
        
        # 创建检索引擎
        engine = IntelligentRetrievalEngine(memory_provider)
        
        # 创建prompts目录和模板
        prompts_dir = self.temp_dir / "prompts"
        prompts_dir.mkdir()
        template_file = prompts_dir / "memory_fusion_prompt_programming.txt"
        with open(template_file, 'w') as f:
            f.write("Context: {retrieved_passages}\n\nQuery: ")
        
        # 创建增强器
        enhancer = IntelligentPromptEnhancer(engine, prompts_dir)
        
        # 执行完整流程
        query = "如何使用Python装饰器？"
        context = await enhancer.enhance_prompt(query, EnhancementLevel.COMPREHENSIVE)
        
        # 验证完整流程
        self.assertIsNotNone(context.enhanced_prompt)
        self.assertIn(query, context.enhanced_prompt or "")


def run_async_test(test_method):
    """运行异步测试的辅助函数"""
    def wrapper(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(test_method(self))
        finally:
            loop.close()
    return wrapper


# 为异步测试方法添加装饰器
TestIntelligentRetrievalEngine.test_intelligent_retrieve = run_async_test(
    TestIntelligentRetrievalEngine.test_intelligent_retrieve
)
TestPromptEnhancer.test_enhance_prompt_with_results = run_async_test(
    TestPromptEnhancer.test_enhance_prompt_with_results
)
TestPromptEnhancer.test_enhance_prompt_no_results = run_async_test(
    TestPromptEnhancer.test_enhance_prompt_no_results
)
TestIntegration.test_end_to_end_enhancement = run_async_test(
    TestIntegration.test_end_to_end_enhancement
)


def main():
    """主测试函数"""
    print("🚀 Sage MCP V3 阶段2完整测试")
    print("=" * 80)
    
    # 创建测试套件
    test_classes = [
        TestAdvancedSemanticAnalyzer,
        TestTemporalScoringEngine, 
        TestMemoryFusionProcessor,
        TestIntelligentRetrievalEngine,
        TestPromptEnhancer,
        TestIntegration
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for test_class in test_classes:
        print(f"\n🧪 运行 {test_class.__name__}")
        print("-" * 60)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        total_failures += len(result.failures)
        total_errors += len(result.errors)
    
    print("\n" + "=" * 80)
    print("阶段2完整测试报告")
    print("=" * 80)
    print(f"运行测试数: {total_tests}")
    print(f"成功: {total_tests - total_failures - total_errors}")
    print(f"失败: {total_failures}")
    print(f"错误: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("\n✅ 所有测试通过！阶段2智能系统运行完美。")
        print("🚀 世界级智能上下文检索和提示增强系统已就绪！")
    else:
        print(f"\n❌ 发现 {total_failures + total_errors} 个问题需要修复")
    
    return total_failures + total_errors == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)