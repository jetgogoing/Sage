#!/usr/bin/env python3
"""
端到端场景测试
模拟真实用户使用场景
"""

import sys
from pathlib import Path
import asyncio
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class E2EScenarioTester:
    """端到端场景测试"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = tempfile.mkdtemp()
        
    def cleanup(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
        
    async def scenario_learning_assistant(self):
        """场景1: 学习助手"""
        print("\n### 场景1: 学习助手 ###")
        
        try:
            from sage_session_manager_v2 import EnhancedSessionManager
            from sage_smart_prompt_system import SmartPromptGenerator
            from sage_memory_analyzer import MemoryAnalyzer, AnalysisType
            
            # 初始化组件
            session_manager = EnhancedSessionManager(data_dir=self.temp_dir)
            prompt_generator = SmartPromptGenerator()
            memory_analyzer = MemoryAnalyzer(session_manager)
            
            # 用户开始学习Python
            print("\n用户: 我想从零开始学习Python编程")
            
            # 创建学习会话
            session_id = session_manager.start_session("Python学习之旅")
            session_manager.add_message("user", "我想从零开始学习Python编程")
            
            # 生成智能提示
            prompt_result = await prompt_generator.generate_smart_prompt(
                "我想从零开始学习Python编程"
            )
            
            print(f"系统检测到: {prompt_result['context'].value} 上下文")
            print(f"用户意图: {prompt_result['intent']['primary']}")
            
            if prompt_result['learning_path']:
                print("\n推荐学习路径:")
                for step in prompt_result['learning_path']:
                    print(f"  {step['step']}. {step['topic']} ({step['duration']})")
                    
            # 模拟学习过程
            learning_topics = [
                ("Python基础语法", "变量、数据类型、控制流"),
                ("函数和模块", "函数定义、参数、模块导入"),
                ("面向对象编程", "类、继承、多态"),
                ("高级特性", "装饰器、生成器、上下文管理器")
            ]
            
            for topic, content in learning_topics:
                session_manager.add_message("user", f"请教我{topic}")
                session_manager.add_message("assistant", f"关于{topic}，{content}...")
                print(f"✓ 学习主题: {topic}")
                
            # 保存学习会话
            session_manager.save_session()
            
            # 分析学习进度
            analysis = await memory_analyzer.analyze(AnalysisType.TOPIC_CLUSTERING)
            if analysis and "clusters" in analysis:
                print(f"\n✓ 已掌握 {len(analysis['clusters'])} 个知识领域")
                
            self.test_results.append({
                "scenario": "学习助手",
                "success": True,
                "details": "成功模拟完整学习流程"
            })
            
        except Exception as e:
            self.test_results.append({
                "scenario": "学习助手",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def scenario_debugging_helper(self):
        """场景2: 调试助手"""
        print("\n### 场景2: 调试助手 ###")
        
        try:
            from sage_session_manager_v2 import EnhancedSessionManager
            from sage_smart_prompt_system import SmartPromptGenerator
            from sage_error_handler import ErrorHandler, ErrorType
            
            # 初始化组件
            session_manager = EnhancedSessionManager(data_dir=self.temp_dir)
            prompt_generator = SmartPromptGenerator()
            error_handler = ErrorHandler()
            
            # 用户遇到错误
            error_message = "TypeError: 'NoneType' object is not subscriptable"
            print(f"\n用户: 我的代码出现了错误: {error_message}")
            
            # 创建调试会话
            session_id = session_manager.start_session("调试TypeError错误")
            session_manager.add_message("user", f"我的代码出现了错误: {error_message}")
            
            # 生成调试提示
            prompt_result = await prompt_generator.generate_smart_prompt(error_message)
            
            print(f"系统检测到: {prompt_result['context'].value} 上下文")
            print("\n调试建议:")
            for prompt in prompt_result['prompts'][:3]:
                print(f"  - {prompt['text']}")
                
            # 模拟错误处理
            try:
                # 模拟触发错误
                test_dict = None
                value = test_dict['key']  # 这会触发TypeError
            except TypeError as e:
                error_info = error_handler.handle_error(e)
                print(f"\n错误类型: {error_info['type'].value}")
                print(f"是否尝试恢复: {error_info['recovery_attempted']}")
                
            # 记录调试过程
            debug_steps = [
                "检查变量是否为None",
                "添加空值检查",
                "使用默认值或异常处理",
                "验证修复是否有效"
            ]
            
            for step in debug_steps:
                session_manager.add_message("assistant", f"调试步骤: {step}")
                print(f"✓ {step}")
                
            session_manager.save_session()
            
            self.test_results.append({
                "scenario": "调试助手",
                "success": True,
                "details": "成功模拟调试流程"
            })
            
        except Exception as e:
            self.test_results.append({
                "scenario": "调试助手",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def scenario_knowledge_management(self):
        """场景3: 知识管理"""
        print("\n### 场景3: 知识管理 ###")
        
        try:
            from sage_session_manager_v2 import EnhancedSessionManager, SessionSearchType
            from sage_memory_analyzer import MemoryAnalyzer, AnalysisType
            
            # 初始化组件
            session_manager = EnhancedSessionManager(data_dir=self.temp_dir)
            memory_analyzer = MemoryAnalyzer(session_manager)
            
            # 模拟多个知识领域的对话
            knowledge_areas = [
                ("Web开发", ["Django", "Flask", "FastAPI", "前端框架"]),
                ("数据科学", ["Pandas", "NumPy", "机器学习", "数据可视化"]),
                ("系统编程", ["并发", "网络编程", "操作系统", "性能优化"]),
                ("DevOps", ["Docker", "Kubernetes", "CI/CD", "云服务"])
            ]
            
            print("\n构建知识库:")
            for area, topics in knowledge_areas:
                session_id = session_manager.start_session(f"{area}知识整理")
                
                for topic in topics:
                    session_manager.add_message("user", f"解释一下{topic}")
                    session_manager.add_message("assistant", f"{topic}是{area}中的重要概念...")
                    
                session_manager.save_session()
                print(f"✓ 整理{area}知识 ({len(topics)}个主题)")
                
            # 搜索知识
            print("\n知识检索测试:")
            
            # 关键词搜索
            results = session_manager.search_sessions(SessionSearchType.KEYWORD, "Docker")
            print(f"✓ 搜索'Docker': 找到 {len(results)} 个相关会话")
            
            # 主题搜索
            results = session_manager.search_sessions(SessionSearchType.TOPIC, "开发")
            print(f"✓ 搜索'开发'主题: 找到 {len(results)} 个相关会话")
            
            # 知识分析
            print("\n知识结构分析:")
            
            # 主题聚类
            topic_analysis = await memory_analyzer.analyze(AnalysisType.TOPIC_CLUSTERING)
            if topic_analysis and "clusters" in topic_analysis:
                print(f"✓ 识别出 {len(topic_analysis['clusters'])} 个知识集群")
                
            # 知识图谱
            knowledge_graph = await memory_analyzer.analyze(AnalysisType.KNOWLEDGE_GRAPH)
            if knowledge_graph and "nodes" in knowledge_graph:
                print(f"✓ 构建知识图谱: {len(knowledge_graph['nodes'])} 个节点")
                
            # 获取统计
            stats = session_manager.get_statistics()
            print(f"\n知识库统计:")
            print(f"  - 总会话数: {stats['total_sessions']}")
            print(f"  - 总知识条目: {stats['total_messages']}")
            print(f"  - 平均会话长度: {stats['avg_session_length']:.1f}")
            
            self.test_results.append({
                "scenario": "知识管理",
                "success": True,
                "details": "成功构建和管理知识库"
            })
            
        except Exception as e:
            self.test_results.append({
                "scenario": "知识管理",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def scenario_performance_optimization(self):
        """场景4: 性能优化"""
        print("\n### 场景4: 性能优化 ###")
        
        try:
            from sage_error_handler import (
                PerformanceMonitor,
                ResourceManager,
                OptimizationEngine,
                with_performance_monitoring
            )
            
            # 初始化组件
            monitor = PerformanceMonitor()
            resource_manager = ResourceManager()
            optimization_engine = OptimizationEngine(monitor)
            
            # 模拟高负载操作
            print("\n模拟高负载场景:")
            
            @with_performance_monitoring("heavy_operation")
            async def heavy_operation(data_size: int):
                # 模拟数据处理
                data = list(range(data_size))
                result = sum(data)
                await asyncio.sleep(0.1)  # 模拟IO操作
                return result
                
            # 执行多次操作
            for i in range(5):
                size = 10000 * (i + 1)
                result = await heavy_operation(size)
                print(f"✓ 处理 {size} 条数据")
                
                # 记录内存使用
                status = resource_manager.get_resource_status()
                monitor.record_metric("memory_usage_mb", status["memory_usage_mb"])
                
            # 获取性能报告
            perf_summary = monitor.get_performance_summary()
            print("\n性能分析:")
            
            if "heavy_operation_duration" in perf_summary["operation_stats"]:
                stats = perf_summary["operation_stats"]["heavy_operation_duration"]
                print(f"  - 平均执行时间: {stats['avg']:.3f}s")
                print(f"  - 最小/最大时间: {stats['min']:.3f}s / {stats['max']:.3f}s")
                
            # 系统资源
            sys_metrics = perf_summary["system_metrics"]
            print(f"  - CPU使用率: {sys_metrics['cpu_usage']:.1f}%")
            print(f"  - 内存使用率: {sys_metrics['memory_usage']:.1f}%")
            
            # 执行优化
            print("\n执行优化建议:")
            recommendations = optimization_engine.analyze_and_optimize()
            
            for rec in recommendations:
                status = "✓ 已应用" if rec["status"] == "applied" else "✗ 未应用"
                print(f"  {status} {rec['description']}")
                
            self.test_results.append({
                "scenario": "性能优化",
                "success": True,
                "details": "成功完成性能监控和优化"
            })
            
        except Exception as e:
            self.test_results.append({
                "scenario": "性能优化",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def scenario_collaborative_work(self):
        """场景5: 协作工作"""
        print("\n### 场景5: 协作工作 ###")
        
        try:
            from sage_session_manager_v2 import EnhancedSessionManager
            from sage_mcp_auto_save import AutoSaveManager, SmartContextInjector
            
            # 初始化组件
            session_manager = EnhancedSessionManager(data_dir=self.temp_dir)
            auto_save = AutoSaveManager(session_manager)
            context_injector = SmartContextInjector(session_manager)
            
            # 模拟团队项目讨论
            print("\n团队项目讨论:")
            
            # 第一天：项目规划
            session1 = session_manager.start_session("项目规划会议")
            planning_messages = [
                ("user", "我们需要开发一个任务管理系统"),
                ("assistant", "好的，让我们先确定核心功能需求"),
                ("user", "需要支持任务创建、分配、跟踪和报告"),
                ("assistant", "建议采用敏捷开发方法，分阶段实现")
            ]
            
            for role, content in planning_messages:
                session_manager.add_message(role, content)
                
            session_manager.save_session()
            print("✓ Day 1: 完成项目规划")
            
            # 第二天：技术选型（注入之前的上下文）
            session2 = session_manager.start_session("技术选型讨论")
            
            # 获取相关上下文
            context = await context_injector.get_relevant_context(
                "任务管理系统的技术栈选择",
                limit=3
            )
            
            if context:
                print(f"✓ 自动注入了 {len(context)} 条相关历史记录")
                
            tech_messages = [
                ("user", "基于昨天的讨论，我们用什么技术栈？"),
                ("assistant", "根据项目需求，建议使用Django + React"),
                ("user", "数据库呢？"),
                ("assistant", "PostgreSQL适合这种结构化数据")
            ]
            
            for role, content in tech_messages:
                session_manager.add_message(role, content)
                
            session_manager.save_session()
            print("✓ Day 2: 完成技术选型")
            
            # 第三天：进度回顾
            session3 = session_manager.start_session("进度回顾")
            
            # 导出之前的会议记录
            export1 = session_manager.export_session(session1, "markdown")
            export2 = session_manager.export_session(session2, "markdown")
            
            print("✓ Day 3: 导出会议记录用于回顾")
            
            # 统计协作成果
            stats = session_manager.get_statistics()
            print(f"\n协作统计:")
            print(f"  - 会议次数: {stats['total_sessions']}")
            print(f"  - 讨论条目: {stats['total_messages']}")
            print(f"  - 知识积累: {stats['total_characters']} 字符")
            
            self.test_results.append({
                "scenario": "协作工作",
                "success": True,
                "details": "成功模拟团队协作流程"
            })
            
        except Exception as e:
            self.test_results.append({
                "scenario": "协作工作",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    def print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("端到端场景测试结果")
        print("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        
        print(f"\n总场景数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        
        print("\n详细结果:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['scenario']}: {result['details']}")
            
        print("=" * 60)
        
        return passed == total


async def run_e2e_scenarios():
    """运行所有端到端场景测试"""
    print("=" * 60)
    print("Sage MCP 端到端场景测试")
    print("=" * 60)
    
    tester = E2EScenarioTester()
    
    try:
        # 运行各个场景
        await tester.scenario_learning_assistant()
        await tester.scenario_debugging_helper()
        await tester.scenario_knowledge_management()
        await tester.scenario_performance_optimization()
        await tester.scenario_collaborative_work()
        
        # 打印结果
        success = tester.print_results()
        
        return success
        
    finally:
        # 清理
        tester.cleanup()


if __name__ == "__main__":
    success = asyncio.run(run_e2e_scenarios())
    
    if success:
        print("\n✨ 所有端到端场景测试通过！")
        print("\n系统已准备好为用户提供智能记忆服务")
    else:
        print("\n❌ 部分场景测试失败")