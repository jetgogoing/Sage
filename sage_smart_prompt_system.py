#!/usr/bin/env python3
"""
Sage 智能提示系统
提供上下文感知的智能提示和个性化建议
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """提示类型枚举"""
    CONTEXTUAL = "contextual"          # 上下文相关提示
    SUGGESTIVE = "suggestive"          # 建议性提示
    CORRECTIVE = "corrective"          # 纠正性提示
    EXPLORATORY = "exploratory"        # 探索性提示
    EDUCATIONAL = "educational"        # 教育性提示


class PromptContext(Enum):
    """提示上下文枚举"""
    CODING = "coding"                  # 编程相关
    DEBUGGING = "debugging"            # 调试相关
    LEARNING = "learning"              # 学习相关
    ANALYSIS = "analysis"              # 分析相关
    GENERAL = "general"                # 通用对话


class SmartPromptGenerator:
    """智能提示生成器"""
    
    def __init__(self, memory_analyzer=None, session_manager=None):
        self.memory_analyzer = memory_analyzer
        self.session_manager = session_manager
        self.prompt_cache = {}
        self.user_profile = UserProfileManager()
        self.context_detector = ContextDetector()
        
    async def generate_smart_prompt(self, 
                                  user_input: str,
                                  conversation_history: List[Dict[str, Any]] = None,
                                  current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成智能提示"""
        
        # 检测上下文
        detected_context = self.context_detector.detect_context(
            user_input, conversation_history
        )
        
        # 分析用户意图
        user_intent = await self._analyze_user_intent(user_input, detected_context)
        
        # 获取相关历史
        relevant_history = await self._get_relevant_history(
            user_input, detected_context
        )
        
        # 生成个性化提示
        prompts = await self._generate_prompts(
            user_input, user_intent, detected_context, relevant_history
        )
        
        # 构建响应
        return {
            "context": detected_context,
            "intent": user_intent,
            "prompts": prompts,
            "suggestions": await self._generate_suggestions(user_input, detected_context),
            "related_topics": await self._find_related_topics(user_input),
            "learning_path": await self._suggest_learning_path(user_input, detected_context)
        }
        
    async def _analyze_user_intent(self, 
                                 user_input: str, 
                                 context: PromptContext) -> Dict[str, Any]:
        """分析用户意图"""
        
        intent = {
            "primary": None,
            "confidence": 0.0,
            "keywords": [],
            "question_type": None
        }
        
        # 提取关键词
        keywords = self._extract_keywords(user_input)
        intent["keywords"] = keywords
        
        # 判断问题类型
        lower_input = user_input.lower()
        
        if any(q in lower_input for q in ["什么是", "what is", "解释", "explain"]):
            intent["question_type"] = "definition"
            intent["primary"] = "seeking_definition"
        elif any(q in lower_input for q in ["如何", "怎么", "how to", "怎样"]):
            intent["question_type"] = "how_to"
            intent["primary"] = "seeking_solution"
        elif any(q in lower_input for q in ["为什么", "why", "原因"]):
            intent["question_type"] = "explanation"
            intent["primary"] = "seeking_explanation"
        elif any(q in lower_input for q in ["错误", "error", "bug", "问题"]):
            intent["question_type"] = "troubleshooting"
            intent["primary"] = "seeking_debug_help"
        elif any(q in lower_input for q in ["比较", "对比", "区别", "vs"]):
            intent["question_type"] = "comparison"
            intent["primary"] = "seeking_comparison"
        else:
            intent["question_type"] = "general"
            intent["primary"] = "general_inquiry"
            
        # 计算置信度
        intent["confidence"] = self._calculate_intent_confidence(
            user_input, intent["primary"]
        )
        
        return intent
        
    async def _get_relevant_history(self, 
                                  user_input: str,
                                  context: PromptContext) -> List[Dict[str, Any]]:
        """获取相关历史"""
        
        if not self.memory_analyzer:
            return []
            
        # 基于上下文调整搜索策略
        search_params = self._get_search_params_for_context(context)
        
        # 搜索相关记忆
        # 这里简化实现，实际应调用 memory_analyzer
        relevant_memories = []
        
        return relevant_memories
        
    async def _generate_prompts(self,
                              user_input: str,
                              user_intent: Dict[str, Any],
                              context: PromptContext,
                              relevant_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成提示列表"""
        
        prompts = []
        
        # 根据意图生成主要提示
        if user_intent["primary"] == "seeking_definition":
            prompts.extend(self._generate_definition_prompts(user_input, context))
        elif user_intent["primary"] == "seeking_solution":
            prompts.extend(self._generate_solution_prompts(user_input, context))
        elif user_intent["primary"] == "seeking_debug_help":
            prompts.extend(self._generate_debug_prompts(user_input, context))
        elif user_intent["primary"] == "seeking_comparison":
            prompts.extend(self._generate_comparison_prompts(user_input, context))
            
        # 添加上下文相关提示
        if context == PromptContext.CODING:
            prompts.extend(self._generate_coding_prompts(user_input))
        elif context == PromptContext.LEARNING:
            prompts.extend(self._generate_learning_prompts(user_input))
            
        # 基于历史生成提示
        if relevant_history:
            prompts.extend(self._generate_history_based_prompts(relevant_history))
            
        # 排序和去重
        prompts = self._rank_and_deduplicate_prompts(prompts)
        
        return prompts[:5]  # 返回前5个最相关的提示
        
    def _generate_definition_prompts(self, user_input: str, context: PromptContext) -> List[Dict[str, Any]]:
        """生成定义类提示"""
        prompts = []
        keywords = self._extract_keywords(user_input)
        
        if keywords:
            main_keyword = keywords[0]
            prompts.append({
                "type": PromptType.CONTEXTUAL.value,
                "text": f"我来为您详细解释 {main_keyword} 的概念和原理",
                "priority": 0.9
            })
            
            prompts.append({
                "type": PromptType.SUGGESTIVE.value,
                "text": f"您想了解 {main_keyword} 的实际应用场景吗？",
                "priority": 0.7
            })
            
            if context == PromptContext.CODING:
                prompts.append({
                    "type": PromptType.EDUCATIONAL.value,
                    "text": f"需要我提供一些 {main_keyword} 的代码示例吗？",
                    "priority": 0.8
                })
                
        return prompts
        
    def _generate_solution_prompts(self, user_input: str, context: PromptContext) -> List[Dict[str, Any]]:
        """生成解决方案类提示"""
        prompts = []
        
        prompts.append({
            "type": PromptType.CONTEXTUAL.value,
            "text": "我来为您提供分步骤的解决方案",
            "priority": 0.9
        })
        
        if context == PromptContext.CODING:
            prompts.append({
                "type": PromptType.SUGGESTIVE.value,
                "text": "您需要完整的代码实现还是概念性的指导？",
                "priority": 0.8
            })
            
        prompts.append({
            "type": PromptType.EXPLORATORY.value,
            "text": "有什么特定的限制条件或要求吗？",
            "priority": 0.7
        })
        
        return prompts
        
    def _generate_debug_prompts(self, user_input: str, context: PromptContext) -> List[Dict[str, Any]]:
        """生成调试类提示"""
        prompts = []
        
        prompts.append({
            "type": PromptType.CORRECTIVE.value,
            "text": "让我帮您分析这个错误的可能原因",
            "priority": 0.95
        })
        
        prompts.append({
            "type": PromptType.SUGGESTIVE.value,
            "text": "您能提供完整的错误信息和相关代码吗？",
            "priority": 0.9
        })
        
        prompts.append({
            "type": PromptType.EXPLORATORY.value,
            "text": "这个问题是什么时候开始出现的？最近有什么改动吗？",
            "priority": 0.8
        })
        
        return prompts
        
    def _generate_comparison_prompts(self, user_input: str, context: PromptContext) -> List[Dict[str, Any]]:
        """生成比较类提示"""
        prompts = []
        
        prompts.append({
            "type": PromptType.CONTEXTUAL.value,
            "text": "我来为您详细对比这些选项的优缺点",
            "priority": 0.9
        })
        
        prompts.append({
            "type": PromptType.SUGGESTIVE.value,
            "text": "您主要关注哪些方面的比较？性能、易用性还是其他？",
            "priority": 0.8
        })
        
        return prompts
        
    def _generate_coding_prompts(self, user_input: str) -> List[Dict[str, Any]]:
        """生成编程相关提示"""
        prompts = []
        
        # 检测编程语言
        languages = self._detect_programming_languages(user_input)
        
        if languages:
            lang = languages[0]
            prompts.append({
                "type": PromptType.CONTEXTUAL.value,
                "text": f"我注意到您在使用 {lang}，需要特定版本的解决方案吗？",
                "priority": 0.7
            })
            
        return prompts
        
    def _generate_learning_prompts(self, user_input: str) -> List[Dict[str, Any]]:
        """生成学习相关提示"""
        prompts = []
        
        prompts.append({
            "type": PromptType.EDUCATIONAL.value,
            "text": "您想从基础概念开始，还是直接学习高级特性？",
            "priority": 0.8
        })
        
        prompts.append({
            "type": PromptType.SUGGESTIVE.value,
            "text": "我可以为您推荐一个循序渐进的学习路径",
            "priority": 0.7
        })
        
        return prompts
        
    def _generate_history_based_prompts(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于历史生成提示"""
        prompts = []
        
        if history:
            prompts.append({
                "type": PromptType.CONTEXTUAL.value,
                "text": "基于我们之前的讨论，您可能还想了解...",
                "priority": 0.6
            })
            
        return prompts
        
    async def _generate_suggestions(self, 
                                  user_input: str, 
                                  context: PromptContext) -> List[str]:
        """生成建议"""
        suggestions = []
        
        # 基于上下文的建议
        if context == PromptContext.CODING:
            suggestions.extend([
                "查看相关的最佳实践",
                "了解常见的陷阱和注意事项",
                "探索相关的设计模式"
            ])
        elif context == PromptContext.DEBUGGING:
            suggestions.extend([
                "使用调试工具逐步跟踪",
                "添加日志输出定位问题",
                "检查相关的单元测试"
            ])
        elif context == PromptContext.LEARNING:
            suggestions.extend([
                "通过实践项目巩固知识",
                "阅读官方文档深入理解",
                "参与社区讨论交流经验"
            ])
            
        return suggestions[:3]
        
    async def _find_related_topics(self, user_input: str) -> List[str]:
        """查找相关话题"""
        keywords = self._extract_keywords(user_input)
        related_topics = []
        
        # 简化的相关话题映射
        topic_relations = {
            "装饰器": ["闭包", "高阶函数", "元编程"],
            "异步": ["协程", "并发", "事件循环"],
            "机器学习": ["深度学习", "神经网络", "数据预处理"],
            "算法": ["数据结构", "复杂度分析", "动态规划"]
        }
        
        for keyword in keywords:
            if keyword in topic_relations:
                related_topics.extend(topic_relations[keyword])
                
        return list(set(related_topics))[:5]
        
    async def _suggest_learning_path(self, 
                                   user_input: str, 
                                   context: PromptContext) -> List[Dict[str, Any]]:
        """建议学习路径"""
        if context != PromptContext.LEARNING:
            return []
            
        keywords = self._extract_keywords(user_input)
        if not keywords:
            return []
            
        topic = keywords[0]
        
        # 简化的学习路径
        learning_paths = {
            "Python": [
                {"step": 1, "topic": "基础语法", "duration": "1周"},
                {"step": 2, "topic": "函数和模块", "duration": "1周"},
                {"step": 3, "topic": "面向对象编程", "duration": "2周"},
                {"step": 4, "topic": "高级特性", "duration": "2周"}
            ],
            "机器学习": [
                {"step": 1, "topic": "数学基础", "duration": "2周"},
                {"step": 2, "topic": "基础算法", "duration": "3周"},
                {"step": 3, "topic": "深度学习入门", "duration": "4周"},
                {"step": 4, "topic": "实践项目", "duration": "4周"}
            ]
        }
        
        # 查找匹配的学习路径
        for path_topic, path in learning_paths.items():
            if path_topic.lower() in topic.lower():
                return path
                
        return []
        
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'\b\w{2,}\b', text)
        
        # 过滤常见词
        stopwords = {'的', '是', '在', '和', '了', '有', '我', '你', '他', '她', '它',
                    'the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was', 'were'}
        
        keywords = [w for w in words if w.lower() not in stopwords and len(w) > 2]
        
        # 识别专业术语
        tech_terms = []
        for word in keywords:
            if any(char.isupper() for char in word[1:]):  # 驼峰命名
                tech_terms.append(word)
            elif word.isupper():  # 全大写缩写
                tech_terms.append(word)
                
        return tech_terms + keywords[:5]
        
    def _calculate_intent_confidence(self, user_input: str, intent: str) -> float:
        """计算意图置信度"""
        # 简化的置信度计算
        confidence = 0.5
        
        # 基于关键词匹配增加置信度
        intent_keywords = {
            "seeking_definition": ["什么是", "解释", "含义", "概念"],
            "seeking_solution": ["如何", "怎么", "方法", "步骤"],
            "seeking_debug_help": ["错误", "报错", "失败", "问题"],
            "seeking_comparison": ["比较", "对比", "区别", "优缺点"]
        }
        
        if intent in intent_keywords:
            for keyword in intent_keywords[intent]:
                if keyword in user_input:
                    confidence += 0.2
                    
        return min(confidence, 0.95)
        
    def _get_search_params_for_context(self, context: PromptContext) -> Dict[str, Any]:
        """根据上下文获取搜索参数"""
        params = {
            "limit": 10,
            "threshold": 0.7
        }
        
        if context == PromptContext.DEBUGGING:
            params["boost_recent"] = True
            params["include_errors"] = True
        elif context == PromptContext.LEARNING:
            params["boost_educational"] = True
            params["include_examples"] = True
            
        return params
        
    def _detect_programming_languages(self, text: str) -> List[str]:
        """检测编程语言"""
        languages = []
        
        language_keywords = {
            "python": ["python", "py", "pip", "django", "flask"],
            "javascript": ["javascript", "js", "node", "npm", "react"],
            "java": ["java", "spring", "maven", "gradle"],
            "cpp": ["c++", "cpp", "std::", "iostream"],
            "go": ["golang", "go", "goroutine"],
            "rust": ["rust", "cargo", "rustc"]
        }
        
        lower_text = text.lower()
        for lang, keywords in language_keywords.items():
            if any(kw in lower_text for kw in keywords):
                languages.append(lang)
                
        return languages
        
    def _rank_and_deduplicate_prompts(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """排序和去重提示"""
        # 按优先级排序
        sorted_prompts = sorted(prompts, key=lambda p: p.get("priority", 0), reverse=True)
        
        # 去重（基于文本相似度）
        unique_prompts = []
        seen_texts = set()
        
        for prompt in sorted_prompts:
            text = prompt["text"]
            if text not in seen_texts:
                unique_prompts.append(prompt)
                seen_texts.add(text)
                
        return unique_prompts


class ContextDetector:
    """上下文检测器"""
    
    def detect_context(self, 
                      user_input: str, 
                      conversation_history: List[Dict[str, Any]] = None) -> PromptContext:
        """检测当前上下文"""
        
        # 基于输入内容检测
        lower_input = user_input.lower()
        
        # 编程相关关键词
        coding_keywords = ["代码", "函数", "变量", "类", "方法", "编程", "实现",
                         "code", "function", "variable", "class", "method", "implement"]
        
        # 调试相关关键词
        debug_keywords = ["错误", "报错", "bug", "调试", "异常", "失败",
                        "error", "debug", "exception", "fail", "issue"]
        
        # 学习相关关键词
        learning_keywords = ["学习", "教程", "入门", "基础", "理解", "概念",
                           "learn", "tutorial", "beginner", "understand", "concept"]
        
        # 分析相关关键词
        analysis_keywords = ["分析", "统计", "数据", "报告", "趋势",
                           "analyze", "analysis", "statistics", "data", "report"]
        
        # 计算各上下文的匹配分数
        scores = {
            PromptContext.CODING: sum(1 for kw in coding_keywords if kw in lower_input),
            PromptContext.DEBUGGING: sum(1 for kw in debug_keywords if kw in lower_input),
            PromptContext.LEARNING: sum(1 for kw in learning_keywords if kw in lower_input),
            PromptContext.ANALYSIS: sum(1 for kw in analysis_keywords if kw in lower_input)
        }
        
        # 如果有历史对话，分析历史上下文
        if conversation_history:
            recent_context = self._analyze_conversation_context(conversation_history)
            if recent_context:
                scores[recent_context] += 2  # 历史上下文权重更高
                
        # 选择得分最高的上下文
        max_score = max(scores.values())
        if max_score > 0:
            for context, score in scores.items():
                if score == max_score:
                    return context
                    
        return PromptContext.GENERAL
        
    def _analyze_conversation_context(self, 
                                    conversation_history: List[Dict[str, Any]]) -> Optional[PromptContext]:
        """分析对话历史的上下文"""
        if not conversation_history:
            return None
            
        # 分析最近的几条消息
        recent_messages = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        
        # 统计各类上下文出现次数
        context_counts = defaultdict(int)
        
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            
            # 简化的上下文判断
            if any(kw in content for kw in ["code", "代码", "函数", "实现"]):
                context_counts[PromptContext.CODING] += 1
            elif any(kw in content for kw in ["error", "错误", "bug", "调试"]):
                context_counts[PromptContext.DEBUGGING] += 1
            elif any(kw in content for kw in ["学习", "理解", "概念", "教程"]):
                context_counts[PromptContext.LEARNING] += 1
                
        # 返回出现最多的上下文
        if context_counts:
            return max(context_counts.items(), key=lambda x: x[1])[0]
            
        return None


class UserProfileManager:
    """用户画像管理器"""
    
    def __init__(self):
        self.profiles = {}
        
    def get_user_profile(self, user_id: str = "default") -> Dict[str, Any]:
        """获取用户画像"""
        if user_id not in self.profiles:
            self.profiles[user_id] = self._create_default_profile()
            
        return self.profiles[user_id]
        
    def update_user_profile(self, user_id: str, interaction: Dict[str, Any]):
        """更新用户画像"""
        profile = self.get_user_profile(user_id)
        
        # 更新交互历史
        profile["interaction_count"] += 1
        profile["last_interaction"] = datetime.now()
        
        # 更新主题偏好
        if "keywords" in interaction:
            for keyword in interaction["keywords"]:
                profile["topic_preferences"][keyword] += 1
                
        # 更新上下文偏好
        if "context" in interaction:
            profile["context_preferences"][interaction["context"]] += 1
            
        # 更新技能水平评估
        self._update_skill_level(profile, interaction)
        
    def _create_default_profile(self) -> Dict[str, Any]:
        """创建默认用户画像"""
        return {
            "user_id": "default",
            "created_at": datetime.now(),
            "last_interaction": datetime.now(),
            "interaction_count": 0,
            "skill_level": "beginner",  # beginner, intermediate, advanced
            "topic_preferences": defaultdict(int),
            "context_preferences": defaultdict(int),
            "learning_style": "practical",  # theoretical, practical, mixed
            "response_preferences": {
                "detail_level": "medium",  # low, medium, high
                "include_examples": True,
                "include_references": False
            }
        }
        
    def _update_skill_level(self, profile: Dict[str, Any], interaction: Dict[str, Any]):
        """更新技能水平评估"""
        # 简化的技能评估逻辑
        if profile["interaction_count"] > 50:
            profile["skill_level"] = "advanced"
        elif profile["interaction_count"] > 20:
            profile["skill_level"] = "intermediate"
            
        # 基于问题复杂度调整
        if "complexity" in interaction and interaction["complexity"] == "high":
            if profile["skill_level"] == "beginner":
                profile["skill_level"] = "intermediate"


# 测试函数
async def test_smart_prompt_system():
    """测试智能提示系统"""
    print("测试智能提示系统...")
    
    # 创建提示生成器
    generator = SmartPromptGenerator()
    
    # 测试不同类型的输入
    test_cases = [
        {
            "input": "什么是Python装饰器？",
            "expected_context": PromptContext.CODING,
            "expected_intent": "seeking_definition"
        },
        {
            "input": "如何修复这个TypeError错误？",
            "expected_context": PromptContext.DEBUGGING,
            "expected_intent": "seeking_debug_help"
        },
        {
            "input": "我想学习机器学习，应该从哪里开始？",
            "expected_context": PromptContext.LEARNING,
            "expected_intent": "seeking_solution"
        },
        {
            "input": "比较一下Python和JavaScript的优缺点",
            "expected_context": PromptContext.CODING,
            "expected_intent": "seeking_comparison"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['input']}")
        
        result = await generator.generate_smart_prompt(test_case["input"])
        
        print(f"检测到的上下文: {result['context']}")
        print(f"用户意图: {result['intent']['primary']}")
        print(f"智能提示:")
        for prompt in result["prompts"][:3]:
            print(f"  - [{prompt['type']}] {prompt['text']}")
        
        if result["suggestions"]:
            print(f"建议: {result['suggestions']}")
        if result["related_topics"]:
            print(f"相关话题: {result['related_topics']}")
            
    print("\n✓ 测试完成！")


if __name__ == "__main__":
    asyncio.run(test_smart_prompt_system())