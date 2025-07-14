#!/usr/bin/env python3
"""
单元测试 - 智能提示系统
测试 SmartPromptGenerator 的所有功能
"""

import sys
from pathlib import Path
import asyncio
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_smart_prompt_system import (
    SmartPromptGenerator,
    PromptType,
    PromptContext,
    ContextDetector,
    UserProfileManager
)


class TestSmartPromptSystem:
    """测试智能提示系统"""
    
    def __init__(self):
        self.test_results = []
        
    async def test_context_detection(self):
        """测试上下文检测"""
        detector = ContextDetector()
        
        test_cases = [
            {
                "input": "如何编写Python装饰器？",
                "expected": PromptContext.CODING,
                "description": "编程问题"
            },
            {
                "input": "TypeError: 'NoneType' object is not subscriptable",
                "expected": PromptContext.DEBUGGING,
                "description": "错误调试"
            },
            {
                "input": "我想学习机器学习的基础知识",
                "expected": PromptContext.LEARNING,
                "description": "学习请求"
            },
            {
                "input": "分析一下最近的用户活跃度数据",
                "expected": PromptContext.ANALYSIS,
                "description": "数据分析"
            },
            {
                "input": "你好，今天天气怎么样？",
                "expected": PromptContext.GENERAL,
                "description": "通用对话"
            },
            {
                "input": "debug这个函数的内存泄漏问题",
                "expected": PromptContext.DEBUGGING,
                "description": "调试内存问题"
            },
            {
                "input": "实现一个快速排序算法",
                "expected": PromptContext.CODING,
                "description": "算法实现"
            }
        ]
        
        all_passed = True
        for case in test_cases:
            detected = detector.detect_context(case["input"])
            success = detected == case["expected"]
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "context_detection",
                "case": case["description"],
                "success": success,
                "expected": case["expected"].value,
                "actual": detected.value
            })
            
        return all_passed
        
    async def test_intent_analysis(self):
        """测试意图分析"""
        generator = SmartPromptGenerator()
        
        test_cases = [
            {
                "input": "什么是闭包？",
                "expected_intent": "seeking_definition",
                "expected_question_type": "definition"
            },
            {
                "input": "如何优化数据库查询性能？",
                "expected_intent": "seeking_solution",
                "expected_question_type": "how_to"
            },
            {
                "input": "为什么会出现内存泄漏？",
                "expected_intent": "seeking_explanation",
                "expected_question_type": "explanation"
            },
            {
                "input": "比较React和Vue的区别",
                "expected_intent": "seeking_comparison",
                "expected_question_type": "comparison"
            },
            {
                "input": "调试一个空指针异常",
                "expected_intent": "seeking_debug_help",
                "expected_question_type": "troubleshooting"
            }
        ]
        
        all_passed = True
        for case in test_cases:
            intent = await generator._analyze_user_intent(
                case["input"], 
                PromptContext.CODING
            )
            
            intent_match = intent["primary"] == case["expected_intent"]
            question_type_match = intent["question_type"] == case["expected_question_type"]
            success = intent_match and question_type_match
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "intent_analysis",
                "case": case["input"],
                "success": success,
                "intent_result": intent
            })
            
        return all_passed
        
    async def test_keyword_extraction(self):
        """测试关键词提取"""
        generator = SmartPromptGenerator()
        
        test_cases = [
            {
                "input": "Python中的装饰器是什么？",
                "expected_keywords": ["Python", "装饰器"],
                "must_contain": ["Python", "装饰器"]
            },
            {
                "input": "使用TensorFlow实现CNN神经网络",
                "expected_keywords": ["TensorFlow", "CNN", "神经网络"],
                "must_contain": ["TensorFlow", "CNN"]
            },
            {
                "input": "JavaScript的Promise和async/await有什么区别？",
                "expected_keywords": ["JavaScript", "Promise", "async", "await"],
                "must_contain": ["JavaScript", "Promise"]
            }
        ]
        
        all_passed = True
        for case in test_cases:
            keywords = generator._extract_keywords(case["input"])
            
            # 检查必须包含的关键词
            success = all(kw in keywords for kw in case["must_contain"])
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "keyword_extraction",
                "case": case["input"],
                "success": success,
                "extracted": keywords,
                "expected": case["must_contain"]
            })
            
        return all_passed
        
    async def test_prompt_generation(self):
        """测试提示生成"""
        generator = SmartPromptGenerator()
        
        test_cases = [
            {
                "input": "Python中如何实现单例模式？",
                "min_prompts": 3,
                "should_contain_types": [PromptType.CONTEXTUAL, PromptType.SUGGESTIVE]
            },
            {
                "input": "我的程序出现了内存泄漏，如何调试？",
                "min_prompts": 3,
                "should_contain_types": [PromptType.CORRECTIVE, PromptType.SUGGESTIVE]
            },
            {
                "input": "我想从零开始学习机器学习",
                "min_prompts": 2,
                "should_contain_types": [PromptType.EDUCATIONAL]
            }
        ]
        
        all_passed = True
        for case in test_cases:
            result = await generator.generate_smart_prompt(case["input"])
            
            prompts = result["prompts"]
            prompt_types = [p["type"] for p in prompts]
            
            has_min_prompts = len(prompts) >= case["min_prompts"]
            has_required_types = any(
                pt.value in prompt_types for pt in case["should_contain_types"]
            )
            
            success = has_min_prompts and has_required_types
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "prompt_generation",
                "case": case["input"],
                "success": success,
                "prompt_count": len(prompts),
                "types": prompt_types
            })
            
        return all_passed
        
    async def test_learning_path_generation(self):
        """测试学习路径生成"""
        generator = SmartPromptGenerator()
        
        test_cases = [
            {
                "input": "我想从零开始学习Python编程",
                "should_have_path": True,
                "min_steps": 3
            },
            {
                "input": "我想学习机器学习",
                "should_have_path": True,
                "min_steps": 3
            },
            {
                "input": "如何调试代码？",
                "should_have_path": False,
                "min_steps": 0
            }
        ]
        
        all_passed = True
        for case in test_cases:
            result = await generator.generate_smart_prompt(case["input"])
            
            learning_path = result.get("learning_path", [])
            has_path = len(learning_path) > 0
            
            if case["should_have_path"]:
                success = has_path and len(learning_path) >= case["min_steps"]
            else:
                success = not has_path
                
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "learning_path_generation",
                "case": case["input"],
                "success": success,
                "path_length": len(learning_path)
            })
            
        return all_passed
        
    async def test_user_profile_management(self):
        """测试用户画像管理"""
        profile_manager = UserProfileManager()
        
        # 测试默认画像创建
        profile = profile_manager.get_user_profile("test_user")
        
        default_profile_correct = (
            profile["skill_level"] == "beginner" and
            profile["interaction_count"] == 0
        )
        
        # 测试画像更新
        for i in range(25):
            profile_manager.update_user_profile("test_user", {
                "keywords": ["Python", "机器学习"],
                "context": PromptContext.LEARNING
            })
            
        updated_profile = profile_manager.get_user_profile("test_user")
        
        profile_updated_correctly = (
            updated_profile["interaction_count"] == 25 and
            updated_profile["skill_level"] == "intermediate"  # 应该升级了
        )
        
        success = default_profile_correct and profile_updated_correctly
        
        self.test_results.append({
            "test": "user_profile_management",
            "success": success,
            "final_profile": {
                "skill_level": updated_profile["skill_level"],
                "interaction_count": updated_profile["interaction_count"]
            }
        })
        
        return success
        
    async def test_programming_language_detection(self):
        """测试编程语言检测"""
        generator = SmartPromptGenerator()
        
        test_cases = [
            {
                "input": "如何在Python中使用pandas处理数据？",
                "expected": ["python"]
            },
            {
                "input": "JavaScript中的Promise是什么？",
                "expected": ["javascript"]
            },
            {
                "input": "Java Spring Boot项目结构",
                "expected": ["java"]
            },
            {
                "input": "用C++实现一个链表",
                "expected": ["cpp"]
            },
            {
                "input": "Go语言的goroutine怎么用？",
                "expected": ["go"]
            }
        ]
        
        all_passed = True
        for case in test_cases:
            detected = generator._detect_programming_languages(case["input"])
            
            success = any(lang in detected for lang in case["expected"])
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "programming_language_detection",
                "case": case["input"],
                "success": success,
                "detected": detected,
                "expected": case["expected"]
            })
            
        return all_passed
        
    async def test_suggestions_generation(self):
        """测试建议生成"""
        generator = SmartPromptGenerator()
        
        test_cases = [
            {
                "context": PromptContext.CODING,
                "min_suggestions": 2
            },
            {
                "context": PromptContext.DEBUGGING,
                "min_suggestions": 2
            },
            {
                "context": PromptContext.LEARNING,
                "min_suggestions": 2
            }
        ]
        
        all_passed = True
        for case in test_cases:
            suggestions = await generator._generate_suggestions(
                "测试输入", 
                case["context"]
            )
            
            success = len(suggestions) >= case["min_suggestions"]
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "suggestions_generation",
                "case": f"context={case['context'].value}",
                "success": success,
                "suggestion_count": len(suggestions)
            })
            
        return all_passed
        
    async def test_related_topics_finding(self):
        """测试相关话题查找"""
        generator = SmartPromptGenerator()
        
        test_cases = [
            {
                "input": "Python装饰器的原理",
                "should_find_topics": True
            },
            {
                "input": "异步编程和协程",
                "should_find_topics": True
            },
            {
                "input": "机器学习入门",
                "should_find_topics": True
            },
            {
                "input": "随便聊聊",
                "should_find_topics": False
            }
        ]
        
        all_passed = True
        for case in test_cases:
            topics = await generator._find_related_topics(case["input"])
            
            has_topics = len(topics) > 0
            success = has_topics == case["should_find_topics"]
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "related_topics_finding",
                "case": case["input"],
                "success": success,
                "topics_found": topics
            })
            
        return all_passed
        
    async def test_conversation_context_analysis(self):
        """测试对话历史分析"""
        detector = ContextDetector()
        
        conversation_history = [
            {"role": "user", "content": "如何编写Python函数？"},
            {"role": "assistant", "content": "Python函数使用def关键字定义..."},
            {"role": "user", "content": "那装饰器呢？"},
            {"role": "assistant", "content": "装饰器是Python的高级特性..."},
            {"role": "user", "content": "给我一个例子"}
        ]
        
        context = detector._analyze_conversation_context(conversation_history)
        
        success = context == PromptContext.CODING
        
        self.test_results.append({
            "test": "conversation_context_analysis",
            "success": success,
            "detected_context": context.value if context else None
        })
        
        return success
        
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("单元测试：智能提示系统")
        print("=" * 60)
        
        # 运行各个测试
        test_methods = [
            ("上下文检测", self.test_context_detection),
            ("意图分析", self.test_intent_analysis),
            ("关键词提取", self.test_keyword_extraction),
            ("提示生成", self.test_prompt_generation),
            ("学习路径生成", self.test_learning_path_generation),
            ("用户画像管理", self.test_user_profile_management),
            ("编程语言检测", self.test_programming_language_detection),
            ("建议生成", self.test_suggestions_generation),
            ("相关话题查找", self.test_related_topics_finding),
            ("对话上下文分析", self.test_conversation_context_analysis)
        ]
        
        for test_name, test_method in test_methods:
            print(f"\n运行测试: {test_name}")
            try:
                await test_method()
                print(f"✓ {test_name} 完成")
            except Exception as e:
                print(f"✗ {test_name} 出错: {e}")
                self.test_results.append({
                    "test": test_name,
                    "success": False,
                    "error": str(e)
                })
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        
        # 显示结果
        print(f"\n总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {total_tests - passed_tests}")
        
        # 显示失败的测试
        failures = [r for r in self.test_results if not r["success"]]
        if failures:
            print("\n失败的测试:")
            for failure in failures[:5]:  # 只显示前5个失败
                print(f"  - {failure['test']}: {failure.get('case', 'N/A')}")
                if "error" in failure:
                    print(f"    错误: {failure['error']}")
        else:
            print("\n✅ 所有测试通过！")
            
        print("=" * 60)
        
        return passed_tests == total_tests


async def main():
    """主函数"""
    tester = TestSmartPromptSystem()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✨ 智能提示系统单元测试完成！")


if __name__ == "__main__":
    asyncio.run(main())