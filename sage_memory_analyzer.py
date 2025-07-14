#!/usr/bin/env python3
"""
Sage 记忆分析器
提供记忆系统的深度分析功能
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict, Counter
import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """分析类型枚举"""
    TOPIC_CLUSTERING = "topic_clustering"
    TEMPORAL_PATTERNS = "temporal_patterns"
    INTERACTION_FLOW = "interaction_flow"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SENTIMENT_ANALYSIS = "sentiment_analysis"


class MemoryAnalyzer:
    """记忆分析器"""
    
    def __init__(self, memory_provider, retrieval_engine=None):
        self.memory_provider = memory_provider
        self.retrieval_engine = retrieval_engine
        self.analysis_cache = {}
        self.cache_duration = 3600  # 1小时缓存
        
    async def analyze_memory_patterns(self, 
                                    analysis_type: AnalysisType,
                                    time_range: Optional[Tuple[datetime, datetime]] = None,
                                    limit: int = 1000) -> Dict[str, Any]:
        """分析记忆模式"""
        
        # 检查缓存
        cache_key = f"{analysis_type.value}_{time_range}_{limit}"
        if cache_key in self.analysis_cache:
            cached = self.analysis_cache[cache_key]
            if (datetime.now() - cached["timestamp"]).seconds < self.cache_duration:
                return cached["result"]
                
        # 获取记忆数据
        memories = await self._fetch_memories(time_range, limit)
        
        # 执行分析
        result = None
        if analysis_type == AnalysisType.TOPIC_CLUSTERING:
            result = await self._analyze_topic_clusters(memories)
        elif analysis_type == AnalysisType.TEMPORAL_PATTERNS:
            result = self._analyze_temporal_patterns(memories)
        elif analysis_type == AnalysisType.INTERACTION_FLOW:
            result = self._analyze_interaction_flow(memories)
        elif analysis_type == AnalysisType.KNOWLEDGE_GRAPH:
            result = await self._build_knowledge_graph(memories)
        elif analysis_type == AnalysisType.SENTIMENT_ANALYSIS:
            result = self._analyze_sentiment_patterns(memories)
            
        # 缓存结果
        self.analysis_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now()
        }
        
        return result
        
    async def _fetch_memories(self, 
                            time_range: Optional[Tuple[datetime, datetime]],
                            limit: int) -> List[Dict[str, Any]]:
        """获取记忆数据"""
        # 这里模拟从记忆系统获取数据
        # 实际实现需要调用 memory_provider 的相应方法
        
        memories = []
        try:
            # 获取所有记忆（简化实现）
            results = self.memory_provider.search_memory("", n=limit)
            
            for result in results:
                memory = {
                    "content": result.content,
                    "role": result.role,
                    "timestamp": result.metadata.get("timestamp", datetime.now()),
                    "metadata": result.metadata,
                    "embedding": result.embedding if hasattr(result, "embedding") else None
                }
                
                # 时间过滤
                if time_range:
                    start_time, end_time = time_range
                    if not (start_time <= memory["timestamp"] <= end_time):
                        continue
                        
                memories.append(memory)
                
        except Exception as e:
            logger.error(f"Failed to fetch memories: {e}")
            
        return memories
        
    async def _analyze_topic_clusters(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析话题聚类"""
        
        # 提取关键词
        topic_keywords = defaultdict(list)
        keyword_frequency = Counter()
        
        for memory in memories:
            content = memory["content"].lower()
            
            # 简单的关键词提取（实际应使用NLP工具）
            words = re.findall(r'\b\w{3,}\b', content)
            
            # 过滤常见词
            stopwords = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'what', 'how'}
            keywords = [w for w in words if w not in stopwords]
            
            for keyword in keywords:
                keyword_frequency[keyword] += 1
                
        # 识别主要话题（频率最高的关键词）
        top_keywords = keyword_frequency.most_common(20)
        
        # 聚类相关记忆
        topic_clusters = defaultdict(list)
        
        for memory in memories:
            content_lower = memory["content"].lower()
            
            # 为每个记忆分配到最相关的话题
            best_topic = None
            best_score = 0
            
            for keyword, freq in top_keywords[:10]:  # 使用前10个关键词作为话题
                if keyword in content_lower:
                    score = content_lower.count(keyword) * freq
                    if score > best_score:
                        best_score = score
                        best_topic = keyword
                        
            if best_topic:
                topic_clusters[best_topic].append({
                    "content": memory["content"][:200] + "...",
                    "timestamp": memory["timestamp"],
                    "role": memory["role"]
                })
                
        # 计算话题统计
        topic_stats = {}
        for topic, cluster in topic_clusters.items():
            topic_stats[topic] = {
                "count": len(cluster),
                "first_mention": min(m["timestamp"] for m in cluster),
                "last_mention": max(m["timestamp"] for m in cluster),
                "examples": cluster[:3]  # 前3个例子
            }
            
        return {
            "total_memories": len(memories),
            "identified_topics": len(topic_clusters),
            "top_keywords": dict(top_keywords),
            "topic_clusters": topic_stats,
            "topic_evolution": self._analyze_topic_evolution(topic_clusters)
        }
        
    def _analyze_temporal_patterns(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析时间模式"""
        
        # 按时间单位分组
        hourly_distribution = defaultdict(int)
        daily_distribution = defaultdict(int)
        weekly_distribution = defaultdict(int)
        
        # 活动模式
        activity_gaps = []
        last_timestamp = None
        
        for memory in sorted(memories, key=lambda m: m["timestamp"]):
            timestamp = memory["timestamp"]
            
            # 小时分布
            hourly_distribution[timestamp.hour] += 1
            
            # 星期分布
            daily_distribution[timestamp.weekday()] += 1
            
            # 周数分布
            week_number = timestamp.isocalendar()[1]
            weekly_distribution[week_number] += 1
            
            # 计算活动间隔
            if last_timestamp:
                gap = (timestamp - last_timestamp).total_seconds()
                activity_gaps.append(gap)
            last_timestamp = timestamp
            
        # 计算活动统计
        if activity_gaps:
            avg_gap = sum(activity_gaps) / len(activity_gaps)
            max_gap = max(activity_gaps)
            min_gap = min(activity_gaps)
        else:
            avg_gap = max_gap = min_gap = 0
            
        # 识别活跃时段
        peak_hours = sorted(hourly_distribution.items(), 
                          key=lambda x: x[1], reverse=True)[:3]
        peak_days = sorted(daily_distribution.items(), 
                         key=lambda x: x[1], reverse=True)[:3]
        
        # 星期名称
        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        
        return {
            "temporal_span": {
                "start": min(m["timestamp"] for m in memories) if memories else None,
                "end": max(m["timestamp"] for m in memories) if memories else None,
                "total_days": len(set(m["timestamp"].date() for m in memories))
            },
            "activity_patterns": {
                "hourly_distribution": dict(hourly_distribution),
                "daily_distribution": {
                    day_names[k]: v for k, v in daily_distribution.items()
                },
                "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
                "peak_days": [{"day": day_names[d], "count": c} for d, c in peak_days]
            },
            "interaction_gaps": {
                "average_seconds": avg_gap,
                "max_seconds": max_gap,
                "min_seconds": min_gap,
                "total_interactions": len(memories)
            },
            "activity_trends": self._calculate_activity_trends(weekly_distribution)
        }
        
    def _analyze_interaction_flow(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析交互流程"""
        
        # 对话轮次分析
        conversation_lengths = []
        current_conversation = []
        last_timestamp = None
        conversation_gap_threshold = 1800  # 30分钟
        
        # 问答模式
        qa_patterns = []
        
        for memory in sorted(memories, key=lambda m: m["timestamp"]):
            timestamp = memory["timestamp"]
            
            # 检测对话边界
            if last_timestamp and (timestamp - last_timestamp).seconds > conversation_gap_threshold:
                if current_conversation:
                    conversation_lengths.append(len(current_conversation))
                    
                    # 分析问答模式
                    qa_pattern = self._extract_qa_pattern(current_conversation)
                    if qa_pattern:
                        qa_patterns.append(qa_pattern)
                        
                current_conversation = []
                
            current_conversation.append(memory)
            last_timestamp = timestamp
            
        # 处理最后一个对话
        if current_conversation:
            conversation_lengths.append(len(current_conversation))
            qa_pattern = self._extract_qa_pattern(current_conversation)
            if qa_pattern:
                qa_patterns.append(qa_pattern)
                
        # 统计分析
        if conversation_lengths:
            avg_length = sum(conversation_lengths) / len(conversation_lengths)
            max_length = max(conversation_lengths)
            min_length = min(conversation_lengths)
        else:
            avg_length = max_length = min_length = 0
            
        # 角色分布
        role_distribution = Counter(m["role"] for m in memories)
        
        # 交互模式
        interaction_types = self._classify_interactions(memories)
        
        return {
            "conversation_stats": {
                "total_conversations": len(conversation_lengths),
                "average_length": avg_length,
                "max_length": max_length,
                "min_length": min_length,
                "length_distribution": Counter(conversation_lengths)
            },
            "role_distribution": dict(role_distribution),
            "interaction_types": interaction_types,
            "qa_patterns": {
                "total_qa_pairs": len(qa_patterns),
                "common_question_types": self._analyze_question_types(qa_patterns),
                "response_characteristics": self._analyze_response_characteristics(qa_patterns)
            }
        }
        
    async def _build_knowledge_graph(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建知识图谱"""
        
        # 实体提取
        entities = defaultdict(set)
        entity_relations = defaultdict(list)
        
        for memory in memories:
            content = memory["content"]
            
            # 简单的实体识别（实际应使用NER）
            # 识别大写词作为潜在实体
            potential_entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
            
            for entity in potential_entities:
                entities[entity].add(memory["timestamp"])
                
            # 识别实体关系
            for i, entity1 in enumerate(potential_entities):
                for entity2 in potential_entities[i+1:]:
                    if entity1 != entity2:
                        relation = {
                            "source": entity1,
                            "target": entity2,
                            "context": content[:100],
                            "timestamp": memory["timestamp"]
                        }
                        entity_relations[f"{entity1}-{entity2}"].append(relation)
                        
        # 构建知识节点
        knowledge_nodes = []
        for entity, timestamps in entities.items():
            knowledge_nodes.append({
                "entity": entity,
                "frequency": len(timestamps),
                "first_mention": min(timestamps),
                "last_mention": max(timestamps)
            })
            
        # 构建知识边
        knowledge_edges = []
        for relation_key, relations in entity_relations.items():
            if len(relations) >= 2:  # 至少出现2次的关系
                source, target = relation_key.split("-", 1)
                knowledge_edges.append({
                    "source": source,
                    "target": target,
                    "weight": len(relations),
                    "contexts": [r["context"] for r in relations[:3]]  # 前3个上下文
                })
                
        # 识别核心概念
        core_concepts = sorted(knowledge_nodes, 
                             key=lambda n: n["frequency"], 
                             reverse=True)[:10]
        
        return {
            "graph_stats": {
                "total_nodes": len(knowledge_nodes),
                "total_edges": len(knowledge_edges),
                "avg_connections": len(knowledge_edges) * 2 / len(knowledge_nodes) if knowledge_nodes else 0
            },
            "core_concepts": core_concepts,
            "knowledge_nodes": knowledge_nodes[:50],  # 限制返回数量
            "knowledge_edges": knowledge_edges[:50],  # 限制返回数量
            "concept_evolution": self._analyze_concept_evolution(entities)
        }
        
    def _analyze_sentiment_patterns(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析情感模式（简化版）"""
        
        # 情感词典
        positive_words = {'好', '优秀', '喜欢', '成功', '完美', '很棒', '有用', '清楚', '理解'}
        negative_words = {'错误', '失败', '困难', '问题', '不懂', '复杂', '困惑', '失望'}
        
        sentiment_timeline = []
        overall_sentiment = {"positive": 0, "negative": 0, "neutral": 0}
        
        for memory in memories:
            content = memory["content"].lower()
            
            # 计算情感分数
            pos_score = sum(1 for word in positive_words if word in content)
            neg_score = sum(1 for word in negative_words if word in content)
            
            if pos_score > neg_score:
                sentiment = "positive"
                overall_sentiment["positive"] += 1
            elif neg_score > pos_score:
                sentiment = "negative"
                overall_sentiment["negative"] += 1
            else:
                sentiment = "neutral"
                overall_sentiment["neutral"] += 1
                
            sentiment_timeline.append({
                "timestamp": memory["timestamp"],
                "sentiment": sentiment,
                "score": pos_score - neg_score
            })
            
        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_timeline": sentiment_timeline[-20:],  # 最近20条
            "sentiment_trends": self._calculate_sentiment_trends(sentiment_timeline)
        }
        
    def _analyze_topic_evolution(self, topic_clusters: Dict[str, List]) -> List[Dict]:
        """分析话题演变"""
        evolution = []
        
        for topic, memories in topic_clusters.items():
            if len(memories) >= 3:  # 至少3次提及
                timeline = sorted(memories, key=lambda m: m["timestamp"])
                
                evolution.append({
                    "topic": topic,
                    "first_mention": timeline[0]["timestamp"],
                    "last_mention": timeline[-1]["timestamp"],
                    "frequency_trend": "increasing" if len(timeline[-5:]) > len(timeline[:5]) else "stable"
                })
                
        return sorted(evolution, key=lambda e: e["last_mention"], reverse=True)[:10]
        
    def _calculate_activity_trends(self, weekly_distribution: Dict[int, int]) -> Dict[str, Any]:
        """计算活动趋势"""
        if not weekly_distribution:
            return {"trend": "no_data"}
            
        weeks = sorted(weekly_distribution.keys())
        if len(weeks) < 2:
            return {"trend": "insufficient_data"}
            
        # 计算趋势
        first_half = sum(weekly_distribution[w] for w in weeks[:len(weeks)//2])
        second_half = sum(weekly_distribution[w] for w in weeks[len(weeks)//2:])
        
        if second_half > first_half * 1.2:
            trend = "increasing"
        elif second_half < first_half * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
            
        return {
            "trend": trend,
            "weekly_average": sum(weekly_distribution.values()) / len(weekly_distribution),
            "peak_week": max(weekly_distribution.items(), key=lambda x: x[1])[0]
        }
        
    def _extract_qa_pattern(self, conversation: List[Dict[str, Any]]) -> Optional[Dict]:
        """提取问答模式"""
        if len(conversation) < 2:
            return None
            
        # 查找用户问题和助手回答
        for i in range(len(conversation) - 1):
            if conversation[i]["role"] == "user" and conversation[i+1]["role"] == "assistant":
                return {
                    "question": conversation[i]["content"][:100],
                    "answer_length": len(conversation[i+1]["content"]),
                    "response_time": (conversation[i+1]["timestamp"] - conversation[i]["timestamp"]).seconds
                }
                
        return None
        
    def _classify_interactions(self, memories: List[Dict[str, Any]]) -> Dict[str, int]:
        """分类交互类型"""
        types = {
            "questions": 0,
            "explanations": 0,
            "code_related": 0,
            "troubleshooting": 0,
            "general_chat": 0
        }
        
        for memory in memories:
            content = memory["content"].lower()
            
            if "?" in content or any(q in content for q in ["什么", "如何", "为什么", "怎么"]):
                types["questions"] += 1
            if any(e in content for e in ["解释", "说明", "理解", "概念"]):
                types["explanations"] += 1
            if any(c in content for c in ["代码", "函数", "变量", "class", "def"]):
                types["code_related"] += 1
            if any(t in content for t in ["错误", "问题", "修复", "解决"]):
                types["troubleshooting"] += 1
            else:
                types["general_chat"] += 1
                
        return types
        
    def _analyze_question_types(self, qa_patterns: List[Dict]) -> Dict[str, int]:
        """分析问题类型"""
        question_types = defaultdict(int)
        
        for pattern in qa_patterns:
            question = pattern["question"].lower()
            
            if any(w in question for w in ["什么是", "what is", "define"]):
                question_types["definition"] += 1
            elif any(w in question for w in ["如何", "怎么", "how to"]):
                question_types["how_to"] += 1
            elif any(w in question for w in ["为什么", "why"]):
                question_types["explanation"] += 1
            elif any(w in question for w in ["代码", "实现", "编写"]):
                question_types["coding"] += 1
            else:
                question_types["other"] += 1
                
        return dict(question_types)
        
    def _analyze_response_characteristics(self, qa_patterns: List[Dict]) -> Dict[str, Any]:
        """分析响应特征"""
        if not qa_patterns:
            return {}
            
        answer_lengths = [p["answer_length"] for p in qa_patterns]
        response_times = [p["response_time"] for p in qa_patterns if p["response_time"] > 0]
        
        return {
            "average_answer_length": sum(answer_lengths) / len(answer_lengths),
            "max_answer_length": max(answer_lengths),
            "min_answer_length": min(answer_lengths),
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0
        }
        
    def _analyze_concept_evolution(self, entities: Dict[str, Set[datetime]]) -> List[Dict]:
        """分析概念演变"""
        evolution = []
        
        for entity, timestamps in entities.items():
            if len(timestamps) >= 3:
                sorted_times = sorted(timestamps)
                
                # 计算概念活跃度
                time_span = (sorted_times[-1] - sorted_times[0]).total_seconds()
                frequency = len(timestamps)
                activity_score = frequency / (time_span / 86400) if time_span > 0 else 0  # 每天的频率
                
                evolution.append({
                    "concept": entity,
                    "first_appearance": sorted_times[0],
                    "last_appearance": sorted_times[-1],
                    "total_mentions": frequency,
                    "activity_score": activity_score
                })
                
        return sorted(evolution, key=lambda e: e["activity_score"], reverse=True)[:20]
        
    def _calculate_sentiment_trends(self, sentiment_timeline: List[Dict]) -> Dict[str, Any]:
        """计算情感趋势"""
        if len(sentiment_timeline) < 10:
            return {"trend": "insufficient_data"}
            
        # 计算移动平均
        window_size = 5
        scores = [s["score"] for s in sentiment_timeline]
        
        moving_avg = []
        for i in range(window_size, len(scores)):
            avg = sum(scores[i-window_size:i]) / window_size
            moving_avg.append(avg)
            
        if not moving_avg:
            return {"trend": "stable"}
            
        # 判断趋势
        first_third = sum(moving_avg[:len(moving_avg)//3]) / (len(moving_avg)//3)
        last_third = sum(moving_avg[-len(moving_avg)//3:]) / (len(moving_avg)//3)
        
        if last_third > first_third + 0.5:
            trend = "improving"
        elif last_third < first_third - 0.5:
            trend = "declining"
        else:
            trend = "stable"
            
        return {
            "trend": trend,
            "current_sentiment": sentiment_timeline[-1]["sentiment"] if sentiment_timeline else "neutral",
            "sentiment_volatility": max(scores) - min(scores) if scores else 0
        }


# 测试函数
async def test_memory_analyzer():
    """测试记忆分析器"""
    print("测试记忆分析器...")
    
    # 创建模拟的记忆提供者
    class MockMemoryProvider:
        def search_memory(self, query, n=10):
            # 返回模拟数据
            class MockResult:
                def __init__(self, content, role, timestamp):
                    self.content = content
                    self.role = role
                    self.metadata = {"timestamp": timestamp}
                    self.score = 0.9
                    
            # 模拟记忆数据
            memories = [
                MockResult("什么是Python装饰器？", "user", datetime.now() - timedelta(hours=24)),
                MockResult("Python装饰器是一种设计模式...", "assistant", datetime.now() - timedelta(hours=23, minutes=59)),
                MockResult("如何使用装饰器？", "user", datetime.now() - timedelta(hours=23, minutes=58)),
                MockResult("装饰器的使用方法如下...", "assistant", datetime.now() - timedelta(hours=23, minutes=57)),
                MockResult("什么是机器学习？", "user", datetime.now() - timedelta(hours=12)),
                MockResult("机器学习是人工智能的一个分支...", "assistant", datetime.now() - timedelta(hours=11, minutes=59)),
            ]
            
            return memories[:n]
            
    # 创建分析器
    memory_provider = MockMemoryProvider()
    analyzer = MemoryAnalyzer(memory_provider)
    
    # 测试话题聚类
    print("\n1. 测试话题聚类分析...")
    topic_analysis = await analyzer.analyze_memory_patterns(AnalysisType.TOPIC_CLUSTERING)
    print(f"✓ 识别到 {topic_analysis['identified_topics']} 个话题")
    
    # 测试时间模式
    print("\n2. 测试时间模式分析...")
    temporal_analysis = await analyzer.analyze_memory_patterns(AnalysisType.TEMPORAL_PATTERNS)
    print(f"✓ 时间跨度: {temporal_analysis['temporal_span']['total_days']} 天")
    
    # 测试交互流程
    print("\n3. 测试交互流程分析...")
    interaction_analysis = await analyzer.analyze_memory_patterns(AnalysisType.INTERACTION_FLOW)
    print(f"✓ 总对话数: {interaction_analysis['conversation_stats']['total_conversations']}")
    
    # 测试知识图谱
    print("\n4. 测试知识图谱构建...")
    knowledge_graph = await analyzer.analyze_memory_patterns(AnalysisType.KNOWLEDGE_GRAPH)
    print(f"✓ 知识节点数: {knowledge_graph['graph_stats']['total_nodes']}")
    
    # 测试情感分析
    print("\n5. 测试情感模式分析...")
    sentiment_analysis = await analyzer.analyze_memory_patterns(AnalysisType.SENTIMENT_ANALYSIS)
    print(f"✓ 整体情感分布: {sentiment_analysis['overall_sentiment']}")
    
    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(test_memory_analyzer())