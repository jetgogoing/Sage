#!/usr/bin/env python3
"""
Sage MCP 智能上下文检索引擎 V2.0
🚀 世界级检索算法实现，支持多维度相似度计算、时间衰减、语义理解和动态权重调整
"""

import math
import asyncio
import hashlib
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import re
from collections import defaultdict, Counter

logger = logging.getLogger('SageIntelligentRetrieval')

# Import Qwen Reranker if available
try:
    from reranker_qwen import HybridReranker, RerankingMode
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logger.warning("Qwen Reranker not available, using standard retrieval only")


class QueryType(Enum):
    """查询类型枚举"""
    TECHNICAL = "technical"      # 技术查询（代码、调试、实现）
    CONCEPTUAL = "conceptual"    # 概念查询（解释、原理、理论）
    PROCEDURAL = "procedural"    # 流程查询（如何做、步骤、方法）
    DIAGNOSTIC = "diagnostic"    # 诊断查询（错误、问题、故障排除）
    CREATIVE = "creative"        # 创意查询（设计、创新、方案）
    CONVERSATIONAL = "conversational"  # 对话延续（基于上下文）


class RetrievalStrategy(Enum):
    """检索策略枚举"""
    SEMANTIC_FIRST = "semantic_first"      # 语义优先
    TEMPORAL_WEIGHTED = "temporal_weighted"  # 时间加权
    CONTEXT_AWARE = "context_aware"        # 上下文感知
    HYBRID_ADVANCED = "hybrid_advanced"    # 混合高级策略
    ADAPTIVE = "adaptive"                  # 自适应策略


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    role: str
    similarity_score: float
    temporal_score: float
    context_score: float
    final_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""  # 选择原因


@dataclass
class QueryContext:
    """查询上下文"""
    query: str
    query_type: QueryType
    session_history: List[Dict[str, Any]] = field(default_factory=list)
    user_intent: Optional[str] = None
    technical_keywords: List[str] = field(default_factory=list)
    emotional_tone: str = "neutral"
    urgency_level: int = 1  # 1-5级紧急程度


class AdvancedSemanticAnalyzer:
    """高级语义分析器"""
    
    def __init__(self):
        # 技术关键词库（可扩展）
        self.technical_patterns = {
            'programming': ['函数', 'function', 'class', '类', '方法', 'method', '变量', 'variable', 
                          'API', 'algorithm', '算法', 'bug', 'debug', '调试', 'error', '错误'],
            'database': ['数据库', 'database', 'SQL', 'query', '查询', 'table', '表', 'index', '索引'],
            'system': ['系统', 'system', '架构', 'architecture', '性能', 'performance', '优化', 'optimization'],
            'network': ['网络', 'network', 'HTTP', 'API', '接口', 'interface', '协议', 'protocol'],
            'data': ['数据', 'data', '分析', 'analysis', '统计', 'statistics', '模型', 'model']
        }
        
        # 情感词典
        self.emotion_patterns = {
            'urgent': ['紧急', 'urgent', '急', '立即', 'immediately', '马上', 'ASAP'],
            'confused': ['不懂', 'confused', '困惑', '不理解', "don't understand", '搞不清楚'],
            'frustrated': ['烦躁', 'frustrated', '头疼', '麻烦', 'trouble', '问题'],
            'curious': ['好奇', 'curious', '想知道', 'wonder', '了解', '学习', 'learn']
        }
        
        # 意图模式
        self.intent_patterns = {
            'implementation': ['如何实现', 'how to implement', '怎么做', '实现方法', '代码示例'],
            'explanation': ['是什么', 'what is', '解释', 'explain', '原理', 'principle'],
            'troubleshooting': ['不工作', 'not working', '错误', 'error', '失败', 'failed', '问题'],
            'comparison': ['比较', 'compare', '区别', 'difference', '选择', 'choose', 'vs'],
            'optimization': ['优化', 'optimize', '改进', 'improve', '提升', 'enhance', '性能']
        }
    
    def analyze_query(self, query: str) -> QueryContext:
        """深度分析查询意图和上下文"""
        query_lower = query.lower()
        
        # 1. 识别查询类型
        query_type = self._identify_query_type(query_lower)
        
        # 2. 提取技术关键词
        tech_keywords = self._extract_technical_keywords(query)
        
        # 3. 分析情感基调
        emotion = self._analyze_emotion(query_lower)
        
        # 4. 推断用户意图
        intent = self._infer_intent(query_lower)
        
        # 5. 评估紧急程度
        urgency = self._assess_urgency(query_lower, emotion)
        
        return QueryContext(
            query=query,
            query_type=query_type,
            technical_keywords=tech_keywords,
            emotional_tone=emotion,
            user_intent=intent,
            urgency_level=urgency
        )
    
    def _identify_query_type(self, query_lower: str) -> QueryType:
        """识别查询类型"""
        # 诊断查询模式（优先级最高）
        diagnostic_patterns = ['错误', 'error', 'bug', '不工作', '失败', '问题', '报错', 'keyerror', 'exception']
        if any(pattern in query_lower for pattern in diagnostic_patterns):
            return QueryType.DIAGNOSTIC
            
        # 技术查询模式
        tech_patterns = ['代码', 'code', '函数', 'function', 'class', '实现', 'implement', '开发']
        if any(pattern in query_lower for pattern in tech_patterns):
            return QueryType.TECHNICAL
            
        # 流程查询模式
        proc_patterns = ['如何', 'how to', '步骤', 'step', '方法', 'method', '一步步']
        if any(pattern in query_lower for pattern in proc_patterns):
            return QueryType.PROCEDURAL
            
        # 概念查询模式
        concept_patterns = ['是什么', 'what is', '解释', 'explain', '原理', 'principle']
        if any(pattern in query_lower for pattern in concept_patterns):
            return QueryType.CONCEPTUAL
            
        # 对话延续模式
        conv_patterns = ['继续', 'continue', '然后', 'then', '接下来']
        if any(pattern in query_lower for pattern in conv_patterns):
            return QueryType.CONVERSATIONAL
            
        return QueryType.CONCEPTUAL  # 默认
    
    def _extract_technical_keywords(self, query: str) -> List[str]:
        """提取技术关键词"""
        keywords = []
        query_lower = query.lower()
        
        for category, patterns in self.technical_patterns.items():
            for pattern in patterns:
                if pattern.lower() in query_lower:
                    keywords.append(pattern)
                    
        # 提取代码标识符（驼峰命名、下划线等）
        code_patterns = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*[A-Z][a-zA-Z0-9_]*\b', query)  # 驼峰
        code_patterns += re.findall(r'\b[a-z_]+_[a-z_]+\b', query)  # 下划线
        keywords.extend(code_patterns)
        
        return list(set(keywords))
    
    def _analyze_emotion(self, query_lower: str) -> str:
        """分析情感基调"""
        for emotion, patterns in self.emotion_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return emotion
        return "neutral"
    
    def _infer_intent(self, query_lower: str) -> str:
        """推断用户意图"""
        for intent, patterns in self.intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return intent
        return "general"
    
    def _assess_urgency(self, query_lower: str, emotion: str) -> int:
        """评估紧急程度"""
        urgency = 1
        
        # 基于情感调整
        if emotion == "urgent":
            urgency = 5
        elif emotion == "frustrated":
            urgency = 4
        elif emotion == "confused":
            urgency = 3
            
        # 基于关键词调整
        urgent_keywords = ['紧急', 'urgent', '立即', 'critical', '严重', 'severe']
        if any(kw in query_lower for kw in urgent_keywords):
            urgency = max(urgency, 4)
            
        return min(urgency, 5)


class TemporalScoringEngine:
    """时间衰减评分引擎"""
    
    def __init__(self):
        self.decay_params = {
            'exponential_base': 0.95,    # 指数衰减基数
            'linear_factor': 0.1,        # 线性衰减因子
            'recency_boost': 2.0,        # 近期增强因子
            'session_bonus': 1.5,        # 会话内奖励
            'peak_hours': 24 * 7,        # 峰值时间（小时）
        }
    
    def calculate_temporal_score(
        self,
        timestamp: datetime,
        current_time: Optional[datetime] = None,
        query_context: Optional[QueryContext] = None
    ) -> float:
        """计算时间相关性得分"""
        if current_time is None:
            current_time = datetime.now()
            
        hours_diff = (current_time - timestamp).total_seconds() / 3600
        
        # 1. 基础指数衰减
        base_score = self.decay_params['exponential_base'] ** (hours_diff / 24)
        
        # 2. 近期增强（24小时内）
        if hours_diff <= 24:
            base_score *= self.decay_params['recency_boost']
            
        # 3. 会话内奖励（1小时内）
        if hours_diff <= 1:
            base_score *= self.decay_params['session_bonus']
        
        # 4. 确保有明显的时间差异
        if hours_diff <= 1:
            base_score = max(base_score, 0.9)
        elif hours_diff <= 24:
            base_score = max(base_score, 0.7)
            
        # 4. 根据查询紧急程度调整
        if query_context and query_context.urgency_level >= 4:
            # 紧急查询更重视近期内容
            base_score *= (1 + (5 - query_context.urgency_level) * 0.2)
            
        return min(base_score, 1.0)
    
    def calculate_session_relevance(
        self,
        content_metadata: Dict[str, Any],
        session_history: List[Dict[str, Any]]
    ) -> float:
        """计算会话相关性"""
        if not session_history:
            return 0.0
            
        session_score = 0.0
        content_session = content_metadata.get('session_id', '')
        
        # 检查是否在同一会话中
        for history_item in session_history:
            if history_item.get('session_id') == content_session:
                session_score += 0.3
                
        # 检查主题连续性
        content_keywords = set(content_metadata.get('keywords', []))
        for history_item in session_history:
            history_keywords = set(history_item.get('keywords', []))
            overlap = len(content_keywords & history_keywords)
            if overlap > 0:
                session_score += overlap * 0.1
                
        return min(session_score, 1.0)


class HybridScoringAlgorithm:
    """混合评分算法引擎"""
    
    def __init__(self):
        self.semantic_analyzer = AdvancedSemanticAnalyzer()
        self.temporal_engine = TemporalScoringEngine()
        
        # 动态权重配置（可根据查询类型调整）
        self.weight_profiles = {
            QueryType.TECHNICAL: {
                'semantic': 0.5,
                'temporal': 0.2,
                'context': 0.2,
                'keyword': 0.1
            },
            QueryType.DIAGNOSTIC: {
                'semantic': 0.4,
                'temporal': 0.3,
                'context': 0.2,
                'keyword': 0.1
            },
            QueryType.CONVERSATIONAL: {
                'semantic': 0.3,
                'temporal': 0.4,
                'context': 0.3,
                'keyword': 0.0
            },
            QueryType.CONCEPTUAL: {
                'semantic': 0.6,
                'temporal': 0.1,
                'context': 0.2,
                'keyword': 0.1
            },
            QueryType.PROCEDURAL: {
                'semantic': 0.5,
                'temporal': 0.2,
                'context': 0.2,
                'keyword': 0.1
            }
        }
    
    def calculate_comprehensive_score(
        self,
        content: Dict[str, Any],
        query_context: QueryContext,
        base_similarity: float
    ) -> Tuple[float, str]:
        """计算综合得分"""
        
        # 1. 语义得分（基础相似度）
        semantic_score = base_similarity
        
        # 2. 时间得分
        timestamp = content.get('timestamp')
        if timestamp:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            temporal_score = self.temporal_engine.calculate_temporal_score(
                timestamp, query_context=query_context
            )
        else:
            temporal_score = 0.5  # 默认中等时间得分
            
        # 3. 上下文得分
        context_score = self._calculate_context_score(content, query_context)
        
        # 4. 关键词匹配得分
        keyword_score = self._calculate_keyword_score(content, query_context)
        
        # 5. 获取权重配置
        weights = self.weight_profiles.get(query_context.query_type, 
                                         self.weight_profiles[QueryType.CONCEPTUAL])
        
        # 6. 计算最终得分
        final_score = (
            semantic_score * weights['semantic'] +
            temporal_score * weights['temporal'] +
            context_score * weights['context'] +
            keyword_score * weights['keyword']
        )
        
        # 7. 生成推理说明
        reasoning = self._generate_reasoning(
            semantic_score, temporal_score, context_score, keyword_score, weights
        )
        
        return final_score, reasoning
    
    def _calculate_context_score(self, content: Dict[str, Any], query_context: QueryContext) -> float:
        """计算上下文相关性得分"""
        context_score = 0.0
        
        # 1. 会话连续性
        if query_context.session_history:
            session_score = self.temporal_engine.calculate_session_relevance(
                content.get('metadata', {}), query_context.session_history
            )
            context_score += session_score * 0.4
            
        # 2. 角色一致性（用户问题 vs 助手回答）
        content_role = content.get('role', '')
        if query_context.query_type == QueryType.CONVERSATIONAL:
            if content_role == 'assistant':  # 对话延续更需要助手的回答
                context_score += 0.3
        elif content_role == 'user':  # 其他查询更关注相似问题
            context_score += 0.2
            
        # 3. 技术领域匹配
        content_keywords = content.get('metadata', {}).get('keywords', [])
        query_keywords = query_context.technical_keywords
        if content_keywords and query_keywords:
            keyword_overlap = len(set(content_keywords) & set(query_keywords))
            context_score += (keyword_overlap / max(len(query_keywords), 1)) * 0.3
            
        return min(context_score, 1.0)
    
    def _calculate_keyword_score(self, content: Dict[str, Any], query_context: QueryContext) -> float:
        """计算关键词匹配得分"""
        if not query_context.technical_keywords:
            return 0.0
            
        content_text = content.get('content', '').lower()
        keyword_matches = 0
        
        for keyword in query_context.technical_keywords:
            if keyword.lower() in content_text:
                keyword_matches += 1
                
        return keyword_matches / len(query_context.technical_keywords)
    
    def _generate_reasoning(
        self,
        semantic: float,
        temporal: float,
        context: float,
        keyword: float,
        weights: Dict[str, float]
    ) -> str:
        """生成得分推理说明"""
        components = []
        
        if semantic > 0.7:
            components.append(f"高语义相似度({semantic:.2f})")
        elif semantic > 0.5:
            components.append(f"中等语义相似度({semantic:.2f})")
            
        if temporal > 0.8:
            components.append("时效性强")
        elif temporal > 0.5:
            components.append("时效性中等")
            
        if context > 0.6:
            components.append("上下文相关")
            
        if keyword > 0.5:
            components.append("关键词匹配")
            
        return " + ".join(components) if components else "基础匹配"


class IntelligentRetrievalEngine:
    """智能检索引擎主类"""
    
    def __init__(self, memory_provider):
        self.memory_provider = memory_provider
        self.semantic_analyzer = AdvancedSemanticAnalyzer()
        self.scoring_algorithm = HybridScoringAlgorithm()
        
        # 初始化混合重排序器（如果可用）
        self.hybrid_reranker = None
        if RERANKER_AVAILABLE:
            try:
                self.hybrid_reranker = HybridReranker()
                logger.info("Hybrid reranker initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize hybrid reranker: {e}")
        
        # 检索配置
        self.config = {
            'max_results': 10,
            'min_similarity_threshold': 0.3,
            'diversity_factor': 0.7,  # 结果多样性因子
            'quality_threshold': 0.5,  # 质量阈值
            'enable_neural_rerank': True,  # 启用神经网络重排序
            'rerank_batch_size': 20,  # 重排序批大小
        }
        
        # 缓存机制
        self.query_cache = {}
        self.cache_expiry = timedelta(minutes=30)
        
    async def intelligent_retrieve(
        self,
        query: str,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID_ADVANCED,
        session_history: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 5,
        enable_neural_rerank: Optional[bool] = None
    ) -> List[RetrievalResult]:
        """智能检索主方法"""
        
        # 1. 查询分析
        query_context = self.semantic_analyzer.analyze_query(query)
        if session_history:
            query_context.session_history = session_history
            
        logger.info(f"查询分析: 类型={query_context.query_type.value}, "
                   f"意图={query_context.user_intent}, 紧急度={query_context.urgency_level}")
        
        # 2. 检查缓存
        use_neural = enable_neural_rerank if enable_neural_rerank is not None else self.config['enable_neural_rerank']
        cache_key = self._generate_cache_key(query, strategy, max_results, use_neural)
        if cache_key in self.query_cache:
            cached_result, timestamp = self.query_cache[cache_key]
            if datetime.now() - timestamp < self.cache_expiry:
                logger.info("使用缓存结果")
                return cached_result
                
        # 3. 基础检索（获取更多结果用于重排序）
        retrieval_count = max_results * 3 if use_neural and self.hybrid_reranker else max_results * 2
        base_results = await self._perform_base_retrieval(query, retrieval_count)
        
        # 4. 智能重排序
        enhanced_results = await self._intelligent_rerank(base_results, query_context)
        
        # 5. 神经网络重排序（如果启用）
        if use_neural and self.hybrid_reranker and len(enhanced_results) > 3:
            enhanced_results = await self._apply_neural_rerank(
                query, enhanced_results, query_context
            )
        
        # 6. 多样性优化
        final_results = self._apply_diversity_filter(enhanced_results, max_results)
        
        # 7. 缓存结果
        self.query_cache[cache_key] = (final_results, datetime.now())
        
        logger.info(f"智能检索完成: 返回{len(final_results)}个结果 (神经重排序: {use_neural})")
        return final_results
    
    async def _perform_base_retrieval(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """执行基础检索"""
        try:
            # 使用记忆提供者的搜索功能
            search_results = self.memory_provider.search_memory(query, n=max_results)
            
            results = []
            for result in search_results:
                results.append({
                    'content': result.content,
                    'role': result.role,
                    'similarity_score': result.score,
                    'metadata': result.metadata
                })
            
            return results
            
        except Exception as e:
            logger.error(f"基础检索失败: {e}")
            return []
    
    async def _intelligent_rerank(
        self,
        base_results: List[Dict[str, Any]],
        query_context: QueryContext
    ) -> List[RetrievalResult]:
        """智能重排序"""
        enhanced_results = []
        
        for result in base_results:
            # 计算综合得分
            final_score, reasoning = self.scoring_algorithm.calculate_comprehensive_score(
                result, query_context, result['similarity_score']
            )
            
            # 创建增强结果
            enhanced_result = RetrievalResult(
                content=result['content'],
                role=result['role'],
                similarity_score=result['similarity_score'],
                temporal_score=0.0,  # 将在综合得分中体现
                context_score=0.0,   # 将在综合得分中体现
                final_score=final_score,
                metadata=result.get('metadata', {}),
                reasoning=reasoning
            )
            
            enhanced_results.append(enhanced_result)
        
        # 按最终得分排序
        enhanced_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return enhanced_results
    
    def _apply_diversity_filter(
        self,
        results: List[RetrievalResult],
        max_results: int
    ) -> List[RetrievalResult]:
        """应用多样性过滤"""
        if len(results) <= max_results:
            return results
            
        # 选择算法：贪心选择，平衡得分和多样性
        selected = []
        remaining = results.copy()
        
        # 1. 选择得分最高的
        if remaining:
            selected.append(remaining.pop(0))
            
        # 2. 平衡选择剩余的
        while len(selected) < max_results and remaining:
            best_candidate = None
            best_diversity_score = -1
            
            for i, candidate in enumerate(remaining):
                # 计算与已选择结果的多样性
                diversity = self._calculate_diversity(candidate, selected)
                combined_score = (
                    candidate.final_score * (1 - self.config['diversity_factor']) +
                    diversity * self.config['diversity_factor']
                )
                
                if combined_score > best_diversity_score:
                    best_diversity_score = combined_score
                    best_candidate = i
                    
            if best_candidate is not None:
                selected.append(remaining.pop(best_candidate))
            else:
                break
                
        return selected
    
    def _calculate_diversity(
        self,
        candidate: RetrievalResult,
        selected: List[RetrievalResult]
    ) -> float:
        """计算候选结果与已选结果的多样性"""
        if not selected:
            return 1.0
            
        similarities = []
        candidate_content = candidate.content.lower()
        
        for selected_result in selected:
            selected_content = selected_result.content.lower()
            
            # 简单的词汇重叠度计算
            candidate_words = set(candidate_content.split())
            selected_words = set(selected_content.split())
            
            if not candidate_words or not selected_words:
                similarities.append(0.0)
                continue
                
            overlap = len(candidate_words & selected_words)
            union = len(candidate_words | selected_words)
            similarity = overlap / union if union > 0 else 0.0
            similarities.append(similarity)
            
        # 返回平均相似度的补数（多样性）
        avg_similarity = statistics.mean(similarities) if similarities else 0.0
        return 1.0 - avg_similarity
    
    async def _apply_neural_rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        query_context: QueryContext
    ) -> List[RetrievalResult]:
        """应用神经网络重排序"""
        try:
            # 转换为重排序器期望的格式
            rerank_input = []
            for result in results:
                rerank_input.append({
                    'content': result.content,
                    'role': result.role,
                    'final_score': result.final_score,
                    'metadata': result.metadata
                })
            
            # 执行混合重排序
            reranked = await self.hybrid_reranker.hybrid_rerank(
                query=query,
                retrieval_results=rerank_input,
                query_type=query_context.query_type.value,
                enable_neural=True
            )
            
            # 转换回 RetrievalResult 格式
            reranked_results = []
            for item in reranked:
                # 找到对应的原始结果
                for original in results:
                    if (original.content == item['content'] and 
                        original.role == item['role']):
                        # 更新得分和推理
                        original.final_score = item.get('rerank_score', original.final_score)
                        original.reasoning += f" + 神经重排序({item.get('rerank_score', 0):.3f})"
                        reranked_results.append(original)
                        break
            
            return reranked_results if reranked_results else results
            
        except Exception as e:
            logger.error(f"Neural reranking failed: {e}")
            return results
    
    def _generate_cache_key(self, query: str, strategy: RetrievalStrategy, max_results: int, use_neural: bool = False) -> str:
        """生成缓存键"""
        content = f"{query}_{strategy.value}_{max_results}_{use_neural}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """获取检索统计信息"""
        stats = {
            'cache_size': len(self.query_cache),
            'cache_hit_rate': 0.0,  # TODO: 实现缓存命中率统计
            'config': self.config.copy(),
            'reranker_available': RERANKER_AVAILABLE,
            'reranker_enabled': self.config.get('enable_neural_rerank', False)
        }
        
        if self.hybrid_reranker:
            stats['fusion_configs'] = self.hybrid_reranker.fusion_configs
            
        return stats
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        logger.info(f"IntelligentRetrievalEngine config updated: {config}")


# 工厂函数
def create_intelligent_retrieval_engine(memory_provider) -> IntelligentRetrievalEngine:
    """创建智能检索引擎实例"""
    return IntelligentRetrievalEngine(memory_provider)