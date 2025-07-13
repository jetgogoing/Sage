#!/usr/bin/env python3
"""
Sage MCP 提示增强引擎 V2.0
🎯 世界级提示工程，融合记忆、上下文和智能模板系统
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging

from intelligent_retrieval import (
    IntelligentRetrievalEngine, 
    QueryType, 
    RetrievalStrategy,
    RetrievalResult
)

logger = logging.getLogger('SagePromptEnhancer')


class EnhancementLevel(Enum):
    """增强级别"""
    MINIMAL = "minimal"        # 最小增强
    STANDARD = "standard"      # 标准增强
    COMPREHENSIVE = "comprehensive"  # 全面增强
    ADAPTIVE = "adaptive"      # 自适应增强


class PromptType(Enum):
    """提示类型"""
    CODING = "coding"          # 编程相关
    DEBUGGING = "debugging"    # 调试相关
    EXPLANATION = "explanation"  # 解释说明
    ANALYSIS = "analysis"      # 分析类
    CREATIVE = "creative"      # 创意类
    GENERAL = "general"        # 通用类


@dataclass
class EnhancementContext:
    """增强上下文"""
    original_prompt: str
    enhanced_prompt: str
    fragments_used: List[RetrievalResult]
    enhancement_reasoning: str
    metadata: Dict[str, Any]
    confidence_score: float = 0.0


class MemoryFusionProcessor:
    """记忆融合处理器 - 基于用户模板"""
    
    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self.template_cache = {}
        self._load_templates()
        
    def _load_templates(self):
        """加载用户提示模板"""
        try:
            template_file = self.prompts_dir / "memory_fusion_prompt_programming.txt"
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    self.user_template = f.read()
                logger.info(f"已加载用户模板: {template_file}")
            else:
                logger.warning(f"用户模板文件不存在: {template_file}")
                self.user_template = None
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            self.user_template = None
    
    def process_memory_fusion(
        self,
        fragments: List[RetrievalResult],
        max_tokens: int = 3000
    ) -> str:
        """使用用户模板处理记忆融合"""
        if not self.user_template:
            return self._fallback_fusion(fragments, max_tokens)
            
        # 构建检索片段文本
        retrieved_passages = []
        for i, fragment in enumerate(fragments, 1):
            role_label = "用户" if fragment.role == "user" else "助手"
            passage = f"<fragment_{i:02d}>\n[{role_label}] {fragment.content}\n</fragment_{i:02d}>"
            retrieved_passages.append(passage)
            
        passages_text = "\n\n".join(retrieved_passages)
        
        # 替换模板中的占位符
        enhanced_template = self.user_template.replace(
            "{retrieved_passages}", 
            passages_text
        )
        
        # 截断以满足token限制
        if len(enhanced_template) > max_tokens * 4:  # 粗略估算
            enhanced_template = enhanced_template[:max_tokens * 4] + "\n...\n"
            
        return enhanced_template
    
    def _fallback_fusion(self, fragments: List[RetrievalResult], max_tokens: int) -> str:
        """备用融合方法"""
        if not fragments:
            return ""
            
        parts = ["## 相关记忆片段"]
        token_count = 0
        
        for i, fragment in enumerate(fragments, 1):
            role = "用户" if fragment.role == "user" else "助手"
            content = fragment.content
            
            # 估算token并截断
            estimated_tokens = len(content) // 4
            if token_count + estimated_tokens > max_tokens:
                remaining_tokens = max_tokens - token_count
                if remaining_tokens > 50:
                    content = content[:remaining_tokens * 4] + "..."
                else:
                    break
                    
            parts.append(f"\n### 片段 {i} ({role})")
            parts.append(content)
            parts.append(f"*相关性: {fragment.final_score:.2f} | {fragment.reasoning}*")
            
            token_count += estimated_tokens
            
        return "\n".join(parts)


class AdaptivePromptGenerator:
    """自适应提示生成器"""
    
    def __init__(self):
        # 提示模式库
        self.prompt_patterns = {
            PromptType.CODING: {
                'prefix': "作为资深软件工程师，基于以下技术背景：",
                'context_label': "## 相关技术背景",
                'task_label': "## 当前开发任务",
                'suffix': "请提供具体、可执行的代码解决方案，包含必要的注释和错误处理。"
            },
            PromptType.DEBUGGING: {
                'prefix': "作为调试专家，参考以下问题解决历史：",
                'context_label': "## 类似问题解决记录",
                'task_label': "## 当前调试任务",
                'suffix': "请分析问题根因，提供系统性的调试方案和预防措施。"
            },
            PromptType.EXPLANATION: {
                'prefix': "基于以下相关知识背景：",
                'context_label': "## 相关概念和背景",
                'task_label': "## 需要解释的问题",
                'suffix': "请提供清晰、结构化的解释，使用恰当的示例和类比。"
            },
            PromptType.ANALYSIS: {
                'prefix': "作为分析师，结合以下参考信息：",
                'context_label': "## 相关分析案例",
                'task_label': "## 当前分析目标",
                'suffix': "请进行深入分析，提供数据支撑的结论和建议。"
            }
        }
        
    def generate_adaptive_prompt(
        self,
        original_prompt: str,
        context_content: str,
        prompt_type: PromptType,
        enhancement_level: EnhancementLevel
    ) -> str:
        """生成自适应提示"""
        
        if enhancement_level == EnhancementLevel.MINIMAL:
            return f"{context_content}\n\n{original_prompt}"
            
        pattern = self.prompt_patterns.get(prompt_type, self.prompt_patterns[PromptType.CODING])
        
        parts = []
        
        # 添加前缀
        if enhancement_level in [EnhancementLevel.COMPREHENSIVE, EnhancementLevel.ADAPTIVE]:
            parts.append(pattern['prefix'])
            
        # 添加上下文
        if context_content.strip():
            parts.append(f"\n{pattern['context_label']}")
            parts.append(context_content)
            
        # 添加任务
        parts.append(f"\n{pattern['task_label']}")
        parts.append(original_prompt)
        
        # 添加后缀指导
        if enhancement_level == EnhancementLevel.COMPREHENSIVE:
            parts.append(f"\n{pattern['suffix']}")
            
        return "\n".join(parts)


class IntelligentPromptEnhancer:
    """智能提示增强器 - 主控制器"""
    
    def __init__(self, retrieval_engine: IntelligentRetrievalEngine, prompts_dir: Path):
        self.retrieval_engine = retrieval_engine
        self.memory_fusion = MemoryFusionProcessor(prompts_dir)
        self.adaptive_generator = AdaptivePromptGenerator()
        
        # 增强配置
        self.config = {
            'default_enhancement_level': EnhancementLevel.ADAPTIVE,
            'max_context_tokens': 2000,
            'min_relevance_threshold': 0.3,
            'diversity_boost': True,
            'confidence_threshold': 0.6
        }
        
        # 统计信息
        self.stats = {
            'total_enhancements': 0,
            'successful_enhancements': 0,
            'average_confidence': 0.0
        }
    
    async def enhance_prompt(
        self,
        original_prompt: str,
        enhancement_level: Optional[EnhancementLevel] = None,
        session_history: Optional[List[Dict[str, Any]]] = None,
        force_enhancement: bool = False
    ) -> EnhancementContext:
        """智能增强提示"""
        
        self.stats['total_enhancements'] += 1
        
        # 1. 确定增强级别
        if enhancement_level is None:
            enhancement_level = self.config['default_enhancement_level']
            
        # 2. 分析原始提示
        prompt_type = self._analyze_prompt_type(original_prompt)
        
        # 3. 智能检索相关上下文
        relevant_fragments = await self._retrieve_relevant_context(
            original_prompt, session_history
        )
        
        # 4. 评估是否需要增强
        if not force_enhancement and not self._should_enhance(relevant_fragments):
            return EnhancementContext(
                original_prompt=original_prompt,
                enhanced_prompt=original_prompt,
                fragments_used=[],
                enhancement_reasoning="无需增强 - 未找到相关上下文",
                metadata={'enhancement_level': enhancement_level.value},
                confidence_score=1.0
            )
        
        # 5. 执行记忆融合
        context_content = self.memory_fusion.process_memory_fusion(
            relevant_fragments, 
            self.config['max_context_tokens']
        )
        
        # 6. 生成增强提示
        enhanced_prompt = self._generate_enhanced_prompt(
            original_prompt, context_content, prompt_type, enhancement_level
        )
        
        # 7. 计算置信度
        confidence = self._calculate_confidence(relevant_fragments)
        
        # 8. 生成推理说明
        reasoning = self._generate_enhancement_reasoning(
            relevant_fragments, prompt_type, enhancement_level
        )
        
        # 9. 更新统计
        if confidence >= self.config['confidence_threshold']:
            self.stats['successful_enhancements'] += 1
            
        self._update_confidence_stats(confidence)
        
        return EnhancementContext(
            original_prompt=original_prompt,
            enhanced_prompt=enhanced_prompt,
            fragments_used=relevant_fragments,
            enhancement_reasoning=reasoning,
            metadata={
                'enhancement_level': enhancement_level.value,
                'prompt_type': prompt_type.value,
                'fragments_count': len(relevant_fragments),
                'context_tokens': len(context_content) // 4
            },
            confidence_score=confidence
        )
    
    def _analyze_prompt_type(self, prompt: str) -> PromptType:
        """分析提示类型"""
        prompt_lower = prompt.lower()
        
        # 编程关键词
        coding_keywords = ['代码', 'code', '函数', 'function', '实现', 'implement', 
                          'class', '类', '方法', 'method', 'algorithm', '算法']
        
        # 调试关键词
        debug_keywords = ['调试', 'debug', '错误', 'error', 'bug', '修复', 'fix', 
                         '问题', 'issue', '不工作', 'not working']
        
        # 解释关键词
        explain_keywords = ['解释', 'explain', '是什么', 'what is', '原理', 'principle',
                           '如何', 'how', '为什么', 'why']
        
        # 分析关键词
        analysis_keywords = ['分析', 'analyze', '评估', 'evaluate', '比较', 'compare',
                           '优化', 'optimize', '性能', 'performance']
        
        if any(kw in prompt_lower for kw in debug_keywords):
            return PromptType.DEBUGGING
        elif any(kw in prompt_lower for kw in coding_keywords):
            return PromptType.CODING
        elif any(kw in prompt_lower for kw in analysis_keywords):
            return PromptType.ANALYSIS
        elif any(kw in prompt_lower for kw in explain_keywords):
            return PromptType.EXPLANATION
        else:
            return PromptType.GENERAL
    
    async def _retrieve_relevant_context(
        self,
        prompt: str,
        session_history: Optional[List[Dict[str, Any]]]
    ) -> List[RetrievalResult]:
        """检索相关上下文"""
        try:
            results = await self.retrieval_engine.intelligent_retrieve(
                query=prompt,
                strategy=RetrievalStrategy.HYBRID_ADVANCED,
                session_history=session_history,
                max_results=5
            )
            
            # 过滤低相关性结果
            filtered_results = [
                r for r in results 
                if r.final_score >= self.config['min_relevance_threshold']
            ]
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"检索上下文失败: {e}")
            return []
    
    def _should_enhance(self, fragments: List[RetrievalResult]) -> bool:
        """判断是否应该增强"""
        if not fragments:
            return False
            
        # 检查是否有高质量片段
        high_quality_count = sum(
            1 for f in fragments 
            if f.final_score >= self.config['confidence_threshold']
        )
        
        return high_quality_count > 0
    
    def _generate_enhanced_prompt(
        self,
        original_prompt: str,
        context_content: str,
        prompt_type: PromptType,
        enhancement_level: EnhancementLevel
    ) -> str:
        """生成增强提示"""
        
        if enhancement_level == EnhancementLevel.MINIMAL and context_content:
            return f"{context_content}\n\n---\n\n{original_prompt}"
        
        return self.adaptive_generator.generate_adaptive_prompt(
            original_prompt, context_content, prompt_type, enhancement_level
        )
    
    def _calculate_confidence(self, fragments: List[RetrievalResult]) -> float:
        """计算增强置信度"""
        if not fragments:
            return 0.0
            
        # 基于片段质量计算置信度
        scores = [f.final_score for f in fragments]
        
        # 使用加权平均，权重递减
        weights = [1.0 / (i + 1) for i in range(len(scores))]
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        weight_sum = sum(weights)
        
        base_confidence = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        # 考虑片段数量的影响
        quantity_factor = min(len(fragments) / 2.0, 1.0)  # 2个片段为最佳
        
        # 如果有高质量片段，提升置信度
        high_quality_count = sum(1 for score in scores if score >= 0.7)
        if high_quality_count > 0:
            base_confidence = min(base_confidence * 1.2, 1.0)
        
        return base_confidence * quantity_factor
    
    def _generate_enhancement_reasoning(
        self,
        fragments: List[RetrievalResult],
        prompt_type: PromptType,
        enhancement_level: EnhancementLevel
    ) -> str:
        """生成增强推理说明"""
        if not fragments:
            return "无相关记忆片段"
            
        parts = []
        parts.append(f"类型: {prompt_type.value}")
        parts.append(f"级别: {enhancement_level.value}")
        parts.append(f"片段数: {len(fragments)}")
        
        # 添加片段质量描述
        high_quality = sum(1 for f in fragments if f.final_score >= 0.7)
        medium_quality = sum(1 for f in fragments if 0.4 <= f.final_score < 0.7)
        
        if high_quality > 0:
            parts.append(f"高质量片段: {high_quality}")
        if medium_quality > 0:
            parts.append(f"中等质量片段: {medium_quality}")
            
        return " | ".join(parts)
    
    def _update_confidence_stats(self, confidence: float):
        """更新置信度统计"""
        total = self.stats['total_enhancements']
        current_avg = self.stats['average_confidence']
        
        # 增量更新平均值
        self.stats['average_confidence'] = (
            (current_avg * (total - 1) + confidence) / total
        )
    
    def get_enhancement_stats(self) -> Dict[str, Any]:
        """获取增强统计信息"""
        total = self.stats['total_enhancements']
        successful = self.stats['successful_enhancements']
        
        return {
            'total_enhancements': total,
            'successful_enhancements': successful,
            'success_rate': successful / total if total > 0 else 0.0,
            'average_confidence': self.stats['average_confidence'],
            'config': self.config.copy()
        }
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"配置已更新: {key} = {value}")


# 工厂函数
def create_prompt_enhancer(retrieval_engine: IntelligentRetrievalEngine, prompts_dir: Path) -> IntelligentPromptEnhancer:
    """创建提示增强器实例"""
    return IntelligentPromptEnhancer(retrieval_engine, prompts_dir)