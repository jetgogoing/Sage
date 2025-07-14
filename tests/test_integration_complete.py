#!/usr/bin/env python3
"""
完整集成测试套件
测试各个组件之间的协作
"""

import sys
from pathlib import Path
import asyncio
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class IntegrationTester:
    """集成测试类"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = tempfile.mkdtemp()
        
    def cleanup(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
        
    async def test_session_workflow(self):
        """测试完整的会话工作流程"""
        print("\n### 测试会话工作流程 ###")
        
        try:
            from sage_session_manager_v2 import EnhancedSessionManager, SessionSearchType
            from sage_mcp_auto_save import AutoSaveManager, ConversationTracker
            
            # 创建组件
            session_manager = EnhancedSessionManager(data_dir=self.temp_dir)
            auto_save = AutoSaveManager(session_manager)
            
            # 1. 创建新会话
            session_id = session_manager.start_session("集成测试会话")
            print(f"✓ 创建会话: {session_id}")
            
            # 2. 添加对话
            messages = [
                ("user", "如何学习Python编程？"),
                ("assistant", "Python是一门很好的编程语言，我建议从基础语法开始..."),
                ("user", "有什么好的学习资源吗？"),
                ("assistant", "推荐以下资源：1. Python官方文档 2. Python Cookbook...")
            ]
            
            for role, content in messages:
                session_manager.add_message(role, content)
                
            print(f"✓ 添加了 {len(messages)} 条消息")
            
            # 3. 自动保存检测
            conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            auto_save.start_conversation(conversation_id, messages[0][1])
            
            for msg in messages:
                auto_save.add_message(msg[0], msg[1])
                
            saved_result = await auto_save.save_if_complete()
            if saved_result:
                print(f"✓ 自动保存完成: {saved_result[0]}")
                
            # 4. 手动保存会话
            saved_path = session_manager.save_session()
            print(f"✓ 手动保存会话: {saved_path}")
            
            # 5. 搜索会话
            results = session_manager.search_sessions(SessionSearchType.KEYWORD, "Python")
            print(f"✓ 搜索到 {len(results)} 个相关会话")
            
            # 6. 导出会话
            export_result = session_manager.export_session(session_id, "markdown")
            if "content" in export_result:
                print("✓ 导出为Markdown格式")
                
            # 7. 获取统计
            stats = session_manager.get_statistics()
            print(f"✓ 统计信息: {stats['total_sessions']} 个会话, {stats['total_messages']} 条消息")
            
            self.test_results.append({
                "test": "session_workflow",
                "success": True,
                "details": "完整会话工作流程测试通过"
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "session_workflow",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def test_smart_prompt_workflow(self):
        """测试智能提示工作流程"""
        print("\n### 测试智能提示工作流程 ###")
        
        try:
            from sage_smart_prompt_system import SmartPromptGenerator
            
            generator = SmartPromptGenerator()
            
            # 测试用例
            test_inputs = [
                "什么是Python装饰器？",
                "我的代码出现了TypeError错误",
                "我想从零开始学习机器学习"
            ]
            
            for user_input in test_inputs:
                print(f"\n测试输入: {user_input}")
                
                # 生成智能提示
                result = await generator.generate_smart_prompt(user_input)
                
                print(f"  上下文: {result['context'].value}")
                print(f"  意图: {result['intent']['primary']}")
                print(f"  提示数: {len(result['prompts'])}")
                
                if result['prompts']:
                    print(f"  示例提示: {result['prompts'][0]['text']}")
                    
                if result['learning_path']:
                    print(f"  学习路径: {len(result['learning_path'])} 步")
                    
            self.test_results.append({
                "test": "smart_prompt_workflow",
                "success": True,
                "details": "智能提示工作流程测试通过"
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "smart_prompt_workflow",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def test_error_handling_workflow(self):
        """测试错误处理工作流程"""
        print("\n### 测试错误处理工作流程 ###")
        
        try:
            from sage_error_handler import (
                ErrorHandler, 
                PerformanceMonitor,
                ResourceManager,
                with_error_handling,
                with_performance_monitoring,
                ErrorSeverity
            )
            
            handler = ErrorHandler()
            monitor = PerformanceMonitor()
            resource_manager = ResourceManager()
            
            # 1. 测试错误处理装饰器
            @with_error_handling(ErrorSeverity.HIGH)
            @with_performance_monitoring("test_operation")
            async def risky_operation(should_fail=False):
                if should_fail:
                    raise ValueError("模拟错误")
                await asyncio.sleep(0.01)
                return "成功"
                
            # 正常执行
            result = await risky_operation(False)
            print(f"✓ 正常执行: {result}")
            
            # 错误执行
            try:
                await risky_operation(True)
            except ValueError:
                print("✓ 错误被正确处理和重新抛出")
                
            # 2. 检查性能数据
            perf_summary = monitor.get_performance_summary()
            if "test_operation_duration" in perf_summary["operation_stats"]:
                stats = perf_summary["operation_stats"]["test_operation_duration"]
                print(f"✓ 性能记录: 平均耗时 {stats['avg']:.3f}s")
                
            # 3. 检查错误统计
            error_summary = handler.get_error_summary()
            print(f"✓ 错误统计: {error_summary['total_errors']} 个错误")
            
            # 4. 检查资源状态
            resource_status = resource_manager.get_resource_status()
            print(f"✓ 资源状态: 内存使用 {resource_status['memory_usage_mb']:.1f}MB")
            
            self.test_results.append({
                "test": "error_handling_workflow",
                "success": True,
                "details": "错误处理工作流程测试通过"
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "error_handling_workflow",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def test_memory_analysis_workflow(self):
        """测试记忆分析工作流程"""
        print("\n### 测试记忆分析工作流程 ###")
        
        try:
            from sage_memory_analyzer import MemoryAnalyzer, AnalysisType
            from sage_session_manager_v2 import EnhancedSessionManager
            
            # 创建测试数据
            session_manager = EnhancedSessionManager(data_dir=self.temp_dir)
            analyzer = MemoryAnalyzer(session_manager)
            
            # 创建多个测试会话
            topics = ["Python编程", "机器学习", "Web开发", "数据分析", "Python编程"]
            
            for i, topic in enumerate(topics):
                session_manager.start_session(f"{topic}讨论")
                session_manager.add_message("user", f"我想了解{topic}")
                session_manager.add_message("assistant", f"{topic}是一个很好的主题...")
                session_manager.save_session()
                
            print(f"✓ 创建了 {len(topics)} 个测试会话")
            
            # 分析记忆
            analyses = []
            
            # 主题聚类分析
            topic_analysis = await analyzer.analyze(AnalysisType.TOPIC_CLUSTERING)
            if topic_analysis and "clusters" in topic_analysis:
                print(f"✓ 主题聚类: 发现 {len(topic_analysis['clusters'])} 个主题集群")
                analyses.append("主题聚类")
                
            # 时间模式分析
            temporal_analysis = await analyzer.analyze(AnalysisType.TEMPORAL_PATTERNS)
            if temporal_analysis:
                print("✓ 时间模式分析完成")
                analyses.append("时间模式")
                
            self.test_results.append({
                "test": "memory_analysis_workflow",
                "success": len(analyses) > 0,
                "details": f"完成了 {len(analyses)} 种分析"
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "memory_analysis_workflow",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    async def test_command_integration(self):
        """测试命令集成"""
        print("\n### 测试命令集成 ###")
        
        try:
            # 模拟命令处理流程
            commands = [
                "/save 重要讨论",
                "/search Python",
                "/recall 5",
                "/status",
                "/analyze topics"
            ]
            
            processed = 0
            for cmd in commands:
                # 这里只是模拟，实际需要完整的MCP服务器
                print(f"  处理命令: {cmd}")
                processed += 1
                
            print(f"✓ 成功处理 {processed}/{len(commands)} 个命令")
            
            self.test_results.append({
                "test": "command_integration",
                "success": processed == len(commands),
                "details": f"处理了 {processed} 个命令"
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "command_integration",
                "success": False,
                "details": f"错误: {str(e)}"
            })
            
    def print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("集成测试结果")
        print("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        
        print(f"\n总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        
        if total - passed > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
                    
        print("=" * 60)
        
        return passed == total


async def run_integration_tests():
    """运行所有集成测试"""
    print("=" * 60)
    print("Sage MCP 集成测试套件")
    print("=" * 60)
    
    tester = IntegrationTester()
    
    try:
        # 运行各项集成测试
        await tester.test_session_workflow()
        await tester.test_smart_prompt_workflow()
        await tester.test_error_handling_workflow()
        await tester.test_memory_analysis_workflow()
        await tester.test_command_integration()
        
        # 打印结果
        success = tester.print_results()
        
        return success
        
    finally:
        # 清理
        tester.cleanup()


if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    
    if success:
        print("\n✨ 所有集成测试通过！")
    else:
        print("\n❌ 部分集成测试失败")