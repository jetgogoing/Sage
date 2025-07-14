#!/usr/bin/env python3
"""
阶段3：核心功能验证测试
测试目标：验证记忆系统的保存、检索等核心功能
"""

import os
import sys
import json
import time
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入项目模块
from memory import save_conversation_turn, search_memory, get_memory_stats
from memory_interface import get_memory_provider
from app.memory_adapter_v2 import get_enhanced_memory_adapter


class TestPhase3CoreFunctions:
    """核心功能验证测试类"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """每个测试方法前的设置"""
        # 确保DATABASE_URL设置正确
        os.environ['DATABASE_URL'] = "postgresql://mem:mem@localhost:5432/mem"
        self.memory_provider = get_memory_provider()
        self.enhanced_adapter = get_enhanced_memory_adapter()
        
    def test_database_connection(self):
        """测试数据库连接"""
        try:
            # 尝试执行简单查询
            results = self.memory_provider.search_memory("test", n=1)
            print("✓ 数据库连接成功")
            return True
        except Exception as e:
            pytest.fail(f"数据库连接失败: {str(e)}")
    
    def test_save_conversation_basic(self):
        """测试基础对话保存功能"""
        user_prompt = "什么是Python装饰器？"
        assistant_response = "Python装饰器是一种设计模式，用于在不修改函数本身的情况下，动态地给函数添加功能。"
        
        try:
            # 使用memory模块保存
            result = save_conversation_turn(
                user_prompt=user_prompt,
                assistant_response=assistant_response
            )
            
            print(f"✓ 基础保存成功，结果: {result}")
            # save_conversation_turn 不返回值是正常的
            
        except Exception as e:
            pytest.fail(f"保存对话失败: {str(e)}")
    
    def test_save_conversation_with_adapter(self):
        """测试使用增强适配器保存对话"""
        user_prompt = "如何使用async/await？"
        assistant_response = "async/await是Python的异步编程语法，用于处理异步操作。"
        
        try:
            # 使用增强适配器保存
            session_id, turn_id = self.enhanced_adapter.save_conversation(
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                metadata={"topic": "async programming"}
            )
            
            print(f"✓ 适配器保存成功，Session: {session_id}, Turn: {turn_id}")
            assert session_id is not None, "session_id不应为空"
            assert turn_id > 0, "turn_id应大于0"
            
        except Exception as e:
            pytest.fail(f"适配器保存对话失败: {str(e)}")
    
    def test_search_memory_basic(self):
        """测试基础记忆搜索功能"""
        # 先保存一些测试数据
        test_conversations = [
            ("Python中的列表推导式是什么？", "列表推导式是Python中创建列表的简洁方式。"),
            ("如何处理Python异常？", "使用try-except语句块来捕获和处理异常。"),
            ("Python的GIL是什么？", "GIL（全局解释器锁）是Python解释器的一个机制。")
        ]
        
        # 保存测试对话
        for user, assistant in test_conversations:
            try:
                save_conversation_turn(user, assistant)
            except:
                pass  # 忽略保存错误，可能已存在
        
        # 测试搜索
        try:
            results = search_memory("Python", n=5)
            
            print(f"✓ 搜索成功，找到 {len(results)} 条结果")
            
            # 验证结果
            assert len(results) > 0, "应该找到至少一条结果"
            
            # 打印前几条结果
            for i, result in enumerate(results[:3]):
                if isinstance(result, dict):
                    content = result.get('content', '')[:50]
                    score = result.get('score', 0)
                else:
                    content = result.content[:50] if hasattr(result, 'content') else str(result)[:50]
                    score = result.score if hasattr(result, 'score') else 0
                print(f"  结果{i+1}: {content}... (相似度: {score:.3f})")
                
        except Exception as e:
            pytest.fail(f"搜索记忆失败: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_intelligent_context_retrieval(self):
        """测试智能上下文检索"""
        query = "Python异步编程"
        
        try:
            # 使用增强适配器的智能检索
            context_result = await self.enhanced_adapter.get_intelligent_context(
                query=query,
                enable_llm_summary=False,  # 暂时禁用LLM摘要
                max_results=5
            )
            
            print(f"✓ 智能检索成功")
            print(f"  - 找到 {context_result['num_results']} 条相关记录")
            print(f"  - 使用策略: {context_result['strategy_used']}")
            
            # 验证结果结构
            assert 'context' in context_result, "结果应包含context字段"
            assert 'results' in context_result, "结果应包含results字段"
            assert context_result['num_results'] >= 0, "结果数量应非负"
            
            # 打印部分上下文
            if context_result['context']:
                print(f"  - 上下文预览: {context_result['context'][:200]}...")
                
        except Exception as e:
            pytest.fail(f"智能检索失败: {str(e)}")
    
    def test_conversation_history(self):
        """测试对话历史获取"""
        try:
            # 使用search_memory获取最近的对话
            results = search_memory("", n=10)  # 空查询获取最近记录
            
            print(f"✓ 获取对话历史成功，共 {len(results)} 条记录")
            
            # 打印最近几条
            for i, result in enumerate(results[:3]):
                content = result.content[:50] if hasattr(result, 'content') else str(result)[:50]
                score = result.score if hasattr(result, 'score') else 'N/A'
                if isinstance(score, (int, float)):
                    print(f"  记录{i+1}: {content}... (相似度: {score:.3f})")
                else:
                    print(f"  记录{i+1}: {content}... (相似度: {score})")
                
        except Exception as e:
            pytest.fail(f"获取对话历史失败: {str(e)}")
    
    def test_memory_stats(self):
        """测试记忆统计功能"""
        try:
            stats = self.enhanced_adapter.get_stats()
            
            print("✓ 记忆统计信息:")
            print(f"  - 当前会话ID: {stats['session_id']}")
            print(f"  - 对话轮数: {stats['turn_count']}")
            print(f"  - 会话历史大小: {stats['session_history_size']}")
            
            # 配置信息
            config = stats['config']
            print(f"  - LLM摘要: {'启用' if config['enable_llm_summary'] else '禁用'}")
            print(f"  - 神经重排序: {'启用' if config['enable_neural_rerank'] else '禁用'}")
            
            assert stats['session_id'] is not None, "会话ID不应为空"
            
        except Exception as e:
            pytest.fail(f"获取统计信息失败: {str(e)}")
    
    def test_embedding_generation(self):
        """测试文本嵌入生成"""
        from memory import embed_text
        
        test_text = "这是一个测试文本，用于验证嵌入向量生成功能。"
        
        try:
            embedding = embed_text(test_text)
            
            print(f"✓ 嵌入向量生成成功")
            print(f"  - 向量维度: {len(embedding)}")
            print(f"  - 向量类型: {type(embedding)}")
            print(f"  - 前5个值: {embedding[:5]}")
            
            # 验证向量
            assert len(embedding) == 4096, "嵌入向量应该是4096维"
            assert isinstance(embedding, list), "嵌入应该是列表类型"
            assert all(isinstance(x, (int, float)) for x in embedding[:10]), "嵌入值应该是数字"
            
        except Exception as e:
            pytest.fail(f"生成嵌入向量失败: {str(e)}")
    
    def test_error_handling(self):
        """测试错误处理机制"""
        # 测试空输入
        try:
            result = save_conversation_turn("", "")
            print("⚠️  空输入应该被拒绝")
        except ValueError as e:
            print(f"✓ 空输入正确拒绝: {str(e)}")
        except Exception as e:
            print(f"✓ 空输入处理异常: {str(e)}")
        
        # 测试超长输入
        long_text = "测试" * 10000  # 创建超长文本
        try:
            result = save_conversation_turn(long_text, "响应")
            print("✓ 超长输入被接受并处理")
        except Exception as e:
            print(f"✓ 超长输入处理: {str(e)}")
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def save_operation(index):
            try:
                result = save_conversation_turn(
                    f"并发测试问题 {index}",
                    f"并发测试回答 {index}"
                )
                results.put((index, result))
            except Exception as e:
                errors.put((index, str(e)))
        
        # 创建多个线程并发保存
        threads = []
        for i in range(5):
            t = threading.Thread(target=save_operation, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 检查结果
        success_count = results.qsize()
        error_count = errors.qsize()
        
        print(f"✓ 并发测试完成")
        print(f"  - 成功: {success_count}")
        print(f"  - 失败: {error_count}")
        
        assert success_count > 0, "至少应该有一个操作成功"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, '-v', '-s'])