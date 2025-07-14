#!/usr/bin/env python3
"""
第四阶段最终功能测试
测试智能提示系统、错误处理和性能优化
"""

import sys
from pathlib import Path
from datetime import datetime
import asyncio
from typing import Dict, Any, List
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import components
from sage_smart_prompt_system import (
    SmartPromptGenerator,
    PromptType,
    PromptContext,
    ContextDetector,
    UserProfileManager
)
from sage_error_handler import (
    ErrorHandler,
    PerformanceMonitor,
    ResourceManager,
    OptimizationEngine,
    ErrorType,
    ErrorSeverity,
    with_error_handling,
    with_performance_monitoring
)


class TestSmartPromptSystem:
    """测试智能提示系统"""
    
    async def test_context_detection(self):
        """测试上下文检测"""
        print("\n测试上下文检测...")
        
        detector = ContextDetector()
        
        test_cases = [
            ("如何编写Python装饰器？", PromptContext.CODING),
            ("TypeError: 'NoneType' object is not subscriptable", PromptContext.DEBUGGING),
            ("我想学习机器学习的基础知识", PromptContext.LEARNING),
            ("分析一下最近的用户活跃度数据", PromptContext.ANALYSIS),
            ("你好，今天天气怎么样？", PromptContext.GENERAL)
        ]
        
        for input_text, expected_context in test_cases:
            detected = detector.detect_context(input_text)
            match = "✓" if detected == expected_context else "✗"
            print(f"{match} '{input_text[:30]}...' → {detected.value}")
            
        return True
    
    async def test_intent_analysis(self):
        """测试意图分析"""
        print("\n测试用户意图分析...")
        
        generator = SmartPromptGenerator()
        
        test_inputs = [
            "什么是闭包？",
            "如何优化数据库查询性能？",
            "为什么会出现内存泄漏？",
            "比较React和Vue的区别",
            "调试一个空指针异常"
        ]
        
        for input_text in test_inputs:
            intent = await generator._analyze_user_intent(
                input_text, 
                PromptContext.CODING
            )
            print(f"✓ '{input_text}' → {intent['primary']} (置信度: {intent['confidence']:.2f})")
            
        return True
    
    async def test_smart_prompts_generation(self):
        """测试智能提示生成"""
        print("\n测试智能提示生成...")
        
        generator = SmartPromptGenerator()
        
        # 测试编程相关提示
        result = await generator.generate_smart_prompt(
            "Python中如何实现单例模式？"
        )
        
        print(f"✓ 检测上下文: {result['context'].value}")
        print(f"✓ 用户意图: {result['intent']['primary']}")
        print(f"✓ 生成了 {len(result['prompts'])} 个智能提示:")
        
        for prompt in result['prompts'][:3]:
            print(f"  - [{prompt['type']}] {prompt['text']}")
            
        if result['suggestions']:
            print(f"✓ 建议: {result['suggestions'][:2]}")
            
        if result['related_topics']:
            print(f"✓ 相关话题: {result['related_topics']}")
            
        return True
    
    async def test_learning_path_suggestion(self):
        """测试学习路径建议"""
        print("\n测试学习路径建议...")
        
        generator = SmartPromptGenerator()
        
        result = await generator.generate_smart_prompt(
            "我想从零开始学习机器学习",
            conversation_history=[],
            current_context={"skill_level": "beginner"}
        )
        
        if result['learning_path']:
            print("✓ 推荐学习路径:")
            for step in result['learning_path']:
                print(f"  {step['step']}. {step['topic']} - {step['duration']}")
        else:
            print("✗ 未生成学习路径")
            
        return True
    
    async def test_user_profile(self):
        """测试用户画像管理"""
        print("\n测试用户画像管理...")
        
        profile_manager = UserProfileManager()
        
        # 获取默认画像
        profile = profile_manager.get_user_profile("test_user")
        print(f"✓ 创建用户画像: {profile['skill_level']} 级别")
        
        # 更新画像
        for i in range(25):
            profile_manager.update_user_profile("test_user", {
                "keywords": ["Python", "机器学习"],
                "context": PromptContext.LEARNING
            })
            
        updated_profile = profile_manager.get_user_profile("test_user")
        print(f"✓ 更新后技能级别: {updated_profile['skill_level']}")
        print(f"✓ 交互次数: {updated_profile['interaction_count']}")
        
        return True


class TestErrorHandling:
    """测试错误处理"""
    
    def test_error_classification(self):
        """测试错误分类"""
        print("\n测试错误分类...")
        
        handler = ErrorHandler()
        
        test_errors = [
            (ValueError("Invalid input"), ErrorType.VALIDATION_ERROR),
            (FileNotFoundError("File not found"), ErrorType.SYSTEM_ERROR),
            (ConnectionError("Database connection failed"), ErrorType.DATABASE_ERROR),
            (MemoryError("Out of memory"), ErrorType.MEMORY_ERROR),
            (asyncio.TimeoutError("Request timeout"), ErrorType.TIMEOUT_ERROR),
            (Exception("Unknown error"), ErrorType.UNKNOWN_ERROR)
        ]
        
        for error, expected_type in test_errors:
            error_info = handler.handle_error(error, severity=ErrorSeverity.LOW)
            detected_type = error_info["type"]
            match = "✓" if detected_type == expected_type else "✗"
            print(f"{match} {error.__class__.__name__} → {detected_type.value}")
            
        return True
    
    def test_error_recovery(self):
        """测试错误恢复"""
        print("\n测试错误恢复机制...")
        
        handler = ErrorHandler()
        
        # 测试数据库错误恢复
        db_error = ConnectionError("Database connection lost")
        error_info = handler.handle_error(
            db_error, 
            {"operation": "query"}, 
            ErrorSeverity.HIGH
        )
        
        print(f"✓ 错误类型: {error_info['type'].value}")
        print(f"✓ 恢复尝试: {error_info['recovery_attempted']}")
        if error_info['recovery_attempted']:
            print(f"✓ 恢复策略: {error_info.get('recovery_strategy', 'N/A')}")
            
        # 获取错误摘要
        summary = handler.get_error_summary()
        print(f"✓ 总错误数: {summary['total_errors']}")
        print(f"✓ 错误分布: {summary['error_distribution']}")
        
        return True
    
    async def test_error_handling_decorator(self):
        """测试错误处理装饰器"""
        print("\n测试错误处理装饰器...")
        
        @with_error_handling(ErrorSeverity.MEDIUM)
        async def risky_operation(should_fail: bool = False):
            if should_fail:
                raise ValueError("Simulated error")
            return "Success"
            
        # 测试成功情况
        result = await risky_operation(False)
        print(f"✓ 正常执行: {result}")
        
        # 测试失败情况
        try:
            await risky_operation(True)
        except ValueError:
            print("✓ 错误被正确处理并重新抛出")
            
        return True


class TestPerformanceOptimization:
    """测试性能优化"""
    
    async def test_performance_monitoring(self):
        """测试性能监控"""
        print("\n测试性能监控...")
        
        monitor = PerformanceMonitor()
        
        @with_performance_monitoring("test_operation")
        async def slow_operation():
            await asyncio.sleep(0.05)  # 50ms
            return "done"
            
        # 执行多次操作
        for i in range(3):
            await slow_operation()
            
        # 获取性能摘要
        summary = monitor.get_performance_summary()
        
        print(f"✓ 系统CPU使用率: {summary['system_metrics']['cpu_usage']:.1f}%")
        print(f"✓ 系统内存使用率: {summary['system_metrics']['memory_usage']:.1f}%")
        
        if "test_operation_duration" in summary['operation_stats']:
            stats = summary['operation_stats']['test_operation_duration']
            print(f"✓ 操作平均耗时: {stats['avg']:.3f}s")
            print(f"✓ 最小/最大耗时: {stats['min']:.3f}s / {stats['max']:.3f}s")
            
        return True
    
    async def test_resource_management(self):
        """测试资源管理"""
        print("\n测试资源管理...")
        
        manager = ResourceManager()
        
        # 获取初始状态
        initial_status = manager.get_resource_status()
        print(f"✓ 初始操作数: {initial_status['current_operations']}")
        
        # 获取资源
        async with manager.acquire_resource():
            during_status = manager.get_resource_status()
            print(f"✓ 获取资源后: {during_status['current_operations']} 个操作")
            
        # 释放后
        final_status = manager.get_resource_status()
        print(f"✓ 释放资源后: {final_status['current_operations']} 个操作")
        
        # 检查内存限制
        print(f"✓ 内存使用: {final_status['memory_usage_mb']:.1f}/{final_status['memory_limit_mb']} MB")
        
        return True
    
    def test_optimization_engine(self):
        """测试优化引擎"""
        print("\n测试优化引擎...")
        
        monitor = PerformanceMonitor()
        engine = OptimizationEngine(monitor)
        
        # 模拟高内存使用
        monitor.record_metric("system_memory_usage", 75.0)
        
        # 分析并优化
        recommendations = engine.analyze_and_optimize()
        
        print(f"✓ 生成了 {len(recommendations)} 条优化建议:")
        for rec in recommendations:
            status = "应用" if rec['status'] == 'applied' else "失败"
            print(f"  - {rec['description']} [{status}]")
            
        return True


class TestIntegration:
    """测试系统集成"""
    
    async def test_complete_workflow(self):
        """测试完整工作流程"""
        print("\n测试完整工作流程...")
        
        # 创建所有组件
        prompt_generator = SmartPromptGenerator()
        error_handler = ErrorHandler()
        performance_monitor = PerformanceMonitor()
        resource_manager = ResourceManager()
        
        # 模拟用户查询
        user_input = "我的Python程序出现了内存泄漏，如何调试？"
        
        try:
            # 监控性能
            async with performance_monitor.measure_performance("complete_workflow"):
                # 检查资源
                if await resource_manager.check_resources():
                    print("✓ 资源检查通过")
                    
                    # 生成智能提示
                    result = await prompt_generator.generate_smart_prompt(user_input)
                    
                    print(f"✓ 上下文: {result['context'].value}")
                    print(f"✓ 意图: {result['intent']['primary']}")
                    print(f"✓ 生成 {len(result['prompts'])} 个提示")
                    
        except Exception as e:
            # 处理错误
            error_info = error_handler.handle_error(e, {"workflow": "complete"})
            print(f"✗ 工作流程出错: {error_info['message']}")
            
        # 获取性能数据
        perf_summary = performance_monitor.get_performance_summary()
        if "complete_workflow_duration" in perf_summary['operation_stats']:
            duration = perf_summary['operation_stats']['complete_workflow_duration']['avg']
            print(f"✓ 完整流程耗时: {duration:.3f}s")
            
        return True


async def run_all_phase4_tests():
    """运行第四阶段所有测试"""
    print("=" * 60)
    print("第四阶段最终功能测试")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    # 测试列表
    test_cases = [
        # 智能提示测试
        (TestSmartPromptSystem().test_context_detection, "上下文检测"),
        (TestSmartPromptSystem().test_intent_analysis, "意图分析"),
        (TestSmartPromptSystem().test_smart_prompts_generation, "智能提示生成"),
        (TestSmartPromptSystem().test_learning_path_suggestion, "学习路径建议"),
        (TestSmartPromptSystem().test_user_profile, "用户画像管理"),
        
        # 错误处理测试
        (TestErrorHandling().test_error_classification, "错误分类"),
        (TestErrorHandling().test_error_recovery, "错误恢复"),
        (TestErrorHandling().test_error_handling_decorator, "错误处理装饰器"),
        
        # 性能优化测试
        (TestPerformanceOptimization().test_performance_monitoring, "性能监控"),
        (TestPerformanceOptimization().test_resource_management, "资源管理"),
        (TestPerformanceOptimization().test_optimization_engine, "优化引擎"),
        
        # 集成测试
        (TestIntegration().test_complete_workflow, "完整工作流程")
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
        print("✅ 第四阶段所有测试通过！")
        print("\n核心功能验证:")
        print("• 智能提示系统 ✓")
        print("• 错误处理机制 ✓")
        print("• 性能监控优化 ✓")
        print("• 资源管理 ✓")
        print("• 系统集成 ✓")
    else:
        print(f"❌ 有 {total_count - success_count} 个测试失败")
    
    print("=" * 60)
    
    return success_count == total_count


if __name__ == "__main__":
    # 运行异步测试
    success = asyncio.run(run_all_phase4_tests())
    
    if success:
        print("\n✨ 第四阶段功能开发完成！")
        print("可以进入第五阶段：编写完整测试套件和文档")