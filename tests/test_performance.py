#!/usr/bin/env python3
"""
性能基准测试套件
测试Claude-Mem系统的性能指标
"""

import os
import sys
import subprocess
import time
import psutil
import statistics
import json
import tempfile
from pathlib import Path
from datetime import datetime
import asyncio
import concurrent.futures

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config_manager import get_config_manager
from memory_interface import get_memory_provider
from intelligent_retrieval import IntelligentRetrievalEngine


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics = {
            'startup_time': [],
            'retrieval_latency': [],
            'save_latency': [],
            'memory_usage': [],
            'cpu_usage': []
        }
    
    def add_metric(self, metric_name, value):
        """添加指标值"""
        if metric_name in self.metrics:
            self.metrics[metric_name].append(value)
    
    def get_summary(self):
        """获取统计摘要"""
        summary = {}
        for metric, values in self.metrics.items():
            if values:
                summary[metric] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'stdev': statistics.stdev(values) if len(values) > 1 else 0
                }
        return summary
    
    def print_report(self):
        """打印性能报告"""
        print("\n" + "=" * 60)
        print("性能测试报告")
        print("=" * 60)
        
        summary = self.get_summary()
        for metric, stats in summary.items():
            print(f"\n{metric}:")
            print(f"  最小值: {stats['min']:.3f}")
            print(f"  最大值: {stats['max']:.3f}")
            print(f"  平均值: {stats['mean']:.3f}")
            print(f"  中位数: {stats['median']:.3f}")
            print(f"  标准差: {stats['stdev']:.3f}")


class TestPerformance:
    """性能测试类"""
    
    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        cls.metrics = PerformanceMetrics()
        cls.base_dir = Path(__file__).parent.parent
        cls.process = psutil.Process()
        
        # 预热系统
        cls._warmup_system()
    
    @classmethod
    def _warmup_system(cls):
        """预热系统"""
        # 执行一次简单查询来加载模块
        subprocess.run(
            ['python', 'claude_mem_v3.py', 'test'],
            capture_output=True,
            cwd=cls.base_dir
        )
    
    def test_startup_time(self):
        """测试启动时间"""
        iterations = 5
        
        for i in range(iterations):
            start_time = time.time()
            
            result = subprocess.run(
                ['python', 'claude_mem_v3.py', '--help'],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )
            
            startup_time = (time.time() - start_time) * 1000  # 转换为毫秒
            self.metrics.add_metric('startup_time', startup_time)
            
            assert result.returncode == 0, "启动失败"
            assert startup_time < 1000, f"启动时间过长: {startup_time:.0f}ms (应 < 1000ms)"
        
        # 验证平均启动时间
        avg_startup = statistics.mean(self.metrics.metrics['startup_time'])
        assert avg_startup < 500, f"平均启动时间过长: {avg_startup:.0f}ms (应 < 500ms)"
    
    def test_retrieval_performance(self):
        """测试检索性能"""
        # 准备测试数据
        memory_provider = get_memory_provider()
        retrieval_engine = IntelligentRetrievalEngine(memory_provider)
        
        # 添加一些测试记忆
        test_memories = [
            ("Python是一种高级编程语言", {"role": "assistant", "timestamp": datetime.now().isoformat()}),
            ("机器学习是人工智能的子领域", {"role": "assistant", "timestamp": datetime.now().isoformat()}),
            ("深度学习使用神经网络", {"role": "assistant", "timestamp": datetime.now().isoformat()})
        ]
        
        for content, metadata in test_memories:
            memory_provider.add_memory(content, metadata)
        
        # 测试检索性能
        queries = ["编程语言", "人工智能", "神经网络", "数据科学", "算法"]
        
        async def test_retrieval(query):
            start_time = time.time()
            results = await retrieval_engine.intelligent_retrieve(query, max_results=3)
            latency = (time.time() - start_time) * 1000  # 毫秒
            return latency
        
        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for query in queries:
            for _ in range(3):  # 每个查询测试3次
                latency = loop.run_until_complete(test_retrieval(query))
                self.metrics.add_metric('retrieval_latency', latency)
                assert latency < 200, f"检索延迟过高: {latency:.0f}ms (应 < 200ms)"
        
        loop.close()
        
        # 验证平均检索延迟
        avg_latency = statistics.mean(self.metrics.metrics['retrieval_latency'])
        assert avg_latency < 100, f"平均检索延迟过高: {avg_latency:.0f}ms (应 < 100ms)"
    
    def test_save_performance(self):
        """测试保存性能"""
        memory_provider = get_memory_provider()
        
        test_contents = [
            "这是一条测试记忆" * 10,  # 短内容
            "这是一条较长的测试记忆内容" * 50,  # 中等内容
            "这是一条非常长的测试记忆内容，包含更多信息" * 100  # 长内容
        ]
        
        for content in test_contents:
            for _ in range(5):  # 每种内容测试5次
                start_time = time.time()
                
                memory_provider.add_memory(
                    content=content,
                    metadata={
                        'role': 'user',
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
                save_latency = (time.time() - start_time) * 1000  # 毫秒
                self.metrics.add_metric('save_latency', save_latency)
                
                assert save_latency < 100, f"保存延迟过高: {save_latency:.0f}ms (应 < 100ms)"
    
    def test_memory_usage(self):
        """测试内存使用"""
        # 获取初始内存使用
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行一系列操作
        memory_provider = get_memory_provider()
        
        # 添加大量记忆
        for i in range(100):
            memory_provider.add_memory(
                content=f"测试记忆 {i} - " + "x" * 1000,
                metadata={'role': 'user', 'timestamp': datetime.now().isoformat()}
            )
            
            if i % 10 == 0:
                current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                self.metrics.add_metric('memory_usage', memory_increase)
        
        # 验证内存使用
        max_memory_increase = max(self.metrics.metrics['memory_usage'])
        assert max_memory_increase < 200, f"内存增长过大: {max_memory_increase:.0f}MB (应 < 200MB)"
    
    def test_concurrent_performance(self):
        """测试并发性能"""
        queries = ["查询" + str(i) for i in range(10)]
        
        def run_query(query):
            start_time = time.time()
            result = subprocess.run(
                ['python', 'claude_mem_v3.py', query, '--no-memory'],
                capture_output=True,
                text=True,
                cwd=self.base_dir,
                timeout=30
            )
            latency = time.time() - start_time
            return latency, result.returncode == 0
        
        # 测试并发执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(run_query, q) for q in queries]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    latency, success = future.result(timeout=60)
                    results.append((latency, success))
                except Exception as e:
                    results.append((60, False))
            
            total_time = time.time() - start_time
        
        # 统计结果
        successful = sum(1 for _, success in results if success)
        avg_latency = statistics.mean(latency for latency, _ in results)
        
        print(f"\n并发测试结果:")
        print(f"  成功率: {successful}/{len(queries)}")
        print(f"  总耗时: {total_time:.2f}秒")
        print(f"  平均延迟: {avg_latency:.2f}秒")
        
        # 验证性能指标
        assert successful >= len(queries) * 0.5, f"并发成功率过低: {successful}/{len(queries)}"
        assert total_time < 60, f"并发执行时间过长: {total_time:.0f}秒"
    
    def test_cache_effectiveness(self):
        """测试缓存效果"""
        memory_provider = get_memory_provider()
        retrieval_engine = IntelligentRetrievalEngine(memory_provider)
        
        # 同一查询执行多次
        query = "测试缓存效果的查询"
        latencies = []
        
        async def measure_retrieval():
            start = time.time()
            await retrieval_engine.intelligent_retrieve(query, max_results=3)
            return (time.time() - start) * 1000
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 执行10次相同查询
        for i in range(10):
            latency = loop.run_until_complete(measure_retrieval())
            latencies.append(latency)
            time.sleep(0.1)  # 短暂延迟
        
        loop.close()
        
        # 分析缓存效果
        first_call_latency = latencies[0]
        cached_calls_avg = statistics.mean(latencies[1:])
        
        print(f"\n缓存效果测试:")
        print(f"  首次查询: {first_call_latency:.2f}ms")
        print(f"  缓存查询平均: {cached_calls_avg:.2f}ms")
        print(f"  性能提升: {(first_call_latency / cached_calls_avg - 1) * 100:.1f}%")
        
        # 缓存应该显著提升性能
        assert cached_calls_avg < first_call_latency * 0.8, "缓存效果不明显"
    
    @classmethod
    def teardown_class(cls):
        """测试类清理并生成报告"""
        cls.metrics.print_report()
        
        # 检查是否达到性能目标
        summary = cls.metrics.get_summary()
        
        print("\n" + "=" * 60)
        print("性能目标验证")
        print("=" * 60)
        
        targets = {
            'startup_time': ('平均启动时间', 500, 'ms'),
            'retrieval_latency': ('平均检索延迟', 100, 'ms'),
            'save_latency': ('平均保存延迟', 50, 'ms'),
            'memory_usage': ('最大内存增长', 200, 'MB')
        }
        
        all_passed = True
        for metric, (name, target, unit) in targets.items():
            if metric in summary:
                actual = summary[metric]['mean']
                passed = actual <= target
                status = "✅ 通过" if passed else "❌ 未达标"
                print(f"{name}: {actual:.1f}{unit} (目标: <{target}{unit}) {status}")
                all_passed = all_passed and passed
        
        assert all_passed, "部分性能指标未达标"


class TestResourceUsage:
    """资源使用测试"""
    
    def test_file_descriptor_leak(self):
        """测试文件描述符泄漏"""
        initial_fds = len(os.listdir(f'/proc/{os.getpid()}/fd/')) if os.path.exists(f'/proc/{os.getpid()}/fd/') else 0
        
        # 执行多次操作
        for _ in range(10):
            subprocess.run(
                ['python', 'claude_mem_v3.py', 'test', '--no-memory'],
                capture_output=True,
                cwd=Path(__file__).parent.parent
            )
        
        # 检查文件描述符
        if os.path.exists(f'/proc/{os.getpid()}/fd/'):
            final_fds = len(os.listdir(f'/proc/{os.getpid()}/fd/'))
            fd_increase = final_fds - initial_fds
            assert fd_increase < 10, f"可能存在文件描述符泄漏: 增加了{fd_increase}个"
    
    def test_thread_cleanup(self):
        """测试线程清理"""
        import threading
        initial_threads = threading.active_count()
        
        # 执行异步操作
        memory_provider = get_memory_provider()
        retrieval_engine = IntelligentRetrievalEngine(memory_provider)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for _ in range(5):
            loop.run_until_complete(
                retrieval_engine.intelligent_retrieve("test", max_results=3)
            )
        
        loop.close()
        
        # 等待线程清理
        time.sleep(1)
        
        final_threads = threading.active_count()
        thread_increase = final_threads - initial_threads
        assert thread_increase <= 2, f"可能存在线程泄漏: 增加了{thread_increase}个线程"


def run_performance_tests():
    """运行性能测试"""
    print("=" * 60)
    print("性能基准测试")
    print("=" * 60)
    
    # 运行pytest
    pytest.main([__file__, '-v', '--tb=short', '-s'])


if __name__ == '__main__':
    run_performance_tests()