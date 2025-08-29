#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Analyzer - 记忆分析器
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re
import json
import logging

from ..interfaces import AnalysisResult

logger = logging.getLogger(__name__)


class MemoryAnalyzer:
    """记忆分析器"""
    
    def __init__(self, memory_manager):
        """初始化分析器
        
        Args:
            memory_manager: 记忆管理器实例
        """
        self.memory_manager = memory_manager
    
    async def analyze(self, session_id: Optional[str] = None, 
                     analysis_type: str = "general") -> AnalysisResult:
        """分析记忆
        
        Args:
            session_id: 会话ID，None表示分析所有记忆
            analysis_type: 分析类型
            
        Returns:
            分析结果
        """
        # 获取要分析的记忆
        if session_id:
            memories = await self.memory_manager.storage.get_session_memories(session_id)
        else:
            # 获取所有记忆（限制数量以避免内存问题）
            memories = await self._get_all_memories(limit=1000)
        
        if not memories:
            return AnalysisResult(
                patterns=[],
                insights=["没有足够的记忆数据进行分析"],
                suggestions=["开始更多的对话以积累数据"],
                metadata={'memory_count': 0}
            )
        
        # 根据分析类型执行不同的分析
        if analysis_type == "patterns":
            return await self._analyze_patterns(memories)
        elif analysis_type == "insights":
            return await self._analyze_insights(memories)
        else:  # general
            return await self._analyze_general(memories)
    
    async def _analyze_general(self, memories: List[Dict[str, Any]]) -> AnalysisResult:
        """通用分析"""
        patterns = []
        insights = []
        suggestions = []
        
        # 基础统计
        total_memories = len(memories)
        
        # 时间分析
        if memories:
            timestamps = [datetime.fromisoformat(m['created_at']) for m in memories]
            time_span = max(timestamps) - min(timestamps)
            avg_interval = time_span / total_memories if total_memories > 1 else timedelta(0)
            
            insights.append(f"共有 {total_memories} 条记忆")
            insights.append(f"时间跨度：{time_span.days} 天")
            if total_memories > 1:
                insights.append(f"平均对话间隔：{avg_interval.total_seconds() / 3600:.1f} 小时")
        
        # 话题分析
        topics = self._extract_topics(memories)
        if topics:
            top_topics = topics.most_common(5)
            patterns.append({
                'type': 'topics',
                'data': dict(top_topics),
                'description': '最常讨论的话题'
            })
            
            topic_list = [f"{topic}({count}次)" for topic, count in top_topics]
            insights.append(f"热门话题：{', '.join(topic_list)}")
        
        # 对话长度分析
        lengths = [(len(m['user_input']), len(m['assistant_response'])) for m in memories]
        avg_user_len = sum(l[0] for l in lengths) / len(lengths)
        avg_assistant_len = sum(l[1] for l in lengths) / len(lengths)
        
        patterns.append({
            'type': 'conversation_length',
            'data': {
                'avg_user_input': avg_user_len,
                'avg_assistant_response': avg_assistant_len
            },
            'description': '平均对话长度'
        })
        
        # 活跃时段分析
        hour_distribution = self._analyze_activity_hours(memories)
        if hour_distribution:
            peak_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
            patterns.append({
                'type': 'activity_hours',
                'data': dict(hour_distribution),
                'description': '活跃时段分布'
            })
            
            peak_hours_str = [f"{h}点({c}次)" for h, c in peak_hours]
            insights.append(f"最活跃时段：{', '.join(peak_hours_str)}")
        
        # 生成建议
        if total_memories < 10:
            suggestions.append("记忆数据较少，建议多进行对话以获得更准确的分析")
        
        if avg_user_len < 20:
            suggestions.append("您的提问较为简短，可以尝试提供更多上下文信息")
        
        if topics and '技术' in dict(top_topics):
            suggestions.append("检测到技术相关话题，可以深入探讨具体的技术细节")
        
        return AnalysisResult(
            patterns=patterns,
            insights=insights,
            suggestions=suggestions,
            metadata={
                'memory_count': total_memories,
                'analysis_type': 'general',
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    async def _analyze_patterns(self, memories: List[Dict[str, Any]]) -> AnalysisResult:
        """模式分析"""
        patterns = []
        insights = []
        
        # 问题类型分析
        question_types = self._classify_questions(memories)
        if question_types:
            patterns.append({
                'type': 'question_types',
                'data': dict(question_types.most_common()),
                'description': '问题类型分布'
            })
            
            main_type = question_types.most_common(1)[0]
            insights.append(f"最常见的问题类型：{main_type[0]} ({main_type[1]}次)")
        
        # 对话模式分析
        conversation_patterns = self._analyze_conversation_patterns(memories)
        patterns.extend(conversation_patterns)
        
        # 重复话题检测
        repeated_topics = self._find_repeated_topics(memories)
        if repeated_topics:
            patterns.append({
                'type': 'repeated_topics',
                'data': repeated_topics,
                'description': '重复出现的话题'
            })
            insights.append(f"发现 {len(repeated_topics)} 个重复话题")
        
        return AnalysisResult(
            patterns=patterns,
            insights=insights,
            suggestions=["根据发现的模式，您可以尝试探索新的话题领域"],
            metadata={
                'memory_count': len(memories),
                'analysis_type': 'patterns'
            }
        )
    
    async def _analyze_insights(self, memories: List[Dict[str, Any]]) -> AnalysisResult:
        """洞察分析"""
        insights = []
        suggestions = []
        
        # 学习曲线分析
        learning_progress = self._analyze_learning_progress(memories)
        if learning_progress:
            insights.append(f"知识深度变化：{learning_progress}")
        
        # 兴趣变化分析
        interest_shift = self._analyze_interest_shift(memories)
        if interest_shift:
            insights.extend(interest_shift)
        
        # 交互质量分析
        interaction_quality = self._analyze_interaction_quality(memories)
        insights.extend(interaction_quality['insights'])
        suggestions.extend(interaction_quality['suggestions'])
        
        return AnalysisResult(
            patterns=[],
            insights=insights,
            suggestions=suggestions,
            metadata={
                'memory_count': len(memories),
                'analysis_type': 'insights'
            }
        )
    
    def _extract_topics(self, memories: List[Dict[str, Any]]) -> Counter:
        """提取话题关键词"""
        # 简单的关键词提取
        stopwords = {'的', '了', '是', '在', '我', '你', '吗', '呢', '啊', '吧', '和', '与', '或'}
        topics = Counter()
        
        for memory in memories:
            text = memory['user_input'] + ' ' + memory['assistant_response']
            # 提取中文词（简单分词）
            words = re.findall(r'[\u4e00-\u9fa5]+', text)
            # 过滤停用词和短词
            keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
            topics.update(keywords)
        
        return topics
    
    def _analyze_activity_hours(self, memories: List[Dict[str, Any]]) -> Dict[int, int]:
        """分析活跃时段"""
        hour_counts = defaultdict(int)
        
        for memory in memories:
            timestamp = datetime.fromisoformat(memory['created_at'])
            hour = timestamp.hour
            hour_counts[hour] += 1
        
        return dict(hour_counts)
    
    def _classify_questions(self, memories: List[Dict[str, Any]]) -> Counter:
        """分类问题类型"""
        question_types = Counter()
        
        patterns = {
            '如何': 'how-to',
            '什么': 'what',
            '为什么': 'why',
            '是否': 'yes-no',
            '哪': 'which',
            '多少': 'quantity',
            '代码': 'code',
            '解释': 'explanation',
            '建议': 'suggestion'
        }
        
        for memory in memories:
            user_input = memory['user_input']
            for keyword, qtype in patterns.items():
                if keyword in user_input:
                    question_types[qtype] += 1
                    break
            else:
                question_types['other'] += 1
        
        return question_types
    
    def _analyze_conversation_patterns(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析对话模式"""
        patterns = []
        
        # 分析连续对话
        if len(memories) > 1:
            consecutive_count = 0
            for i in range(1, len(memories)):
                time_diff = (datetime.fromisoformat(memories[i]['created_at']) - 
                           datetime.fromisoformat(memories[i-1]['created_at']))
                if time_diff.total_seconds() < 300:  # 5分钟内
                    consecutive_count += 1
            
            if consecutive_count > 0:
                patterns.append({
                    'type': 'consecutive_conversations',
                    'data': {'count': consecutive_count, 'percentage': consecutive_count / len(memories)},
                    'description': '连续对话模式'
                })
        
        return patterns
    
    def _find_repeated_topics(self, memories: List[Dict[str, Any]]) -> List[str]:
        """查找重复话题"""
        topic_occurrences = defaultdict(list)
        
        for i, memory in enumerate(memories):
            topics = self._extract_topics([memory])
            for topic, _ in topics.most_common(3):
                topic_occurrences[topic].append(i)
        
        # 找出在不同时间出现的话题
        repeated = []
        for topic, indices in topic_occurrences.items():
            if len(indices) > 2:  # 至少出现3次
                # 检查是否分布在不同时间
                if max(indices) - min(indices) > len(memories) * 0.3:
                    repeated.append(topic)
        
        return repeated
    
    def _analyze_learning_progress(self, memories: List[Dict[str, Any]]) -> str:
        """分析学习进展"""
        if len(memories) < 5:
            return "数据不足"
        
        # 简单的复杂度评估：基于对话长度和特定词汇
        early_complexity = sum(len(m['user_input']) for m in memories[:5]) / 5
        late_complexity = sum(len(m['user_input']) for m in memories[-5:]) / 5
        
        if late_complexity > early_complexity * 1.5:
            return "问题复杂度显著提升"
        elif late_complexity > early_complexity * 1.2:
            return "问题复杂度有所提升"
        else:
            return "问题复杂度保持稳定"
    
    def _analyze_interest_shift(self, memories: List[Dict[str, Any]]) -> List[str]:
        """分析兴趣变化"""
        if len(memories) < 10:
            return []
        
        insights = []
        
        # 将记忆分为前半部分和后半部分
        mid_point = len(memories) // 2
        early_memories = memories[:mid_point]
        late_memories = memories[mid_point:]
        
        early_topics = self._extract_topics(early_memories)
        late_topics = self._extract_topics(late_memories)
        
        # 找出新出现的话题
        early_top = set(dict(early_topics.most_common(10)).keys())
        late_top = set(dict(late_topics.most_common(10)).keys())
        
        new_topics = late_top - early_top
        if new_topics:
            insights.append(f"新增兴趣领域：{', '.join(list(new_topics)[:3])}")
        
        lost_topics = early_top - late_top
        if lost_topics:
            insights.append(f"减少关注的领域：{', '.join(list(lost_topics)[:3])}")
        
        return insights
    
    def _analyze_interaction_quality(self, memories: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """分析交互质量"""
        insights = []
        suggestions = []
        
        # 计算平均响应相关性（简化版：基于长度比例）
        response_ratios = []
        for memory in memories:
            ratio = len(memory['assistant_response']) / (len(memory['user_input']) + 1)
            response_ratios.append(ratio)
        
        avg_ratio = sum(response_ratios) / len(response_ratios)
        
        if avg_ratio > 10:
            insights.append("助手回复详细充分")
        elif avg_ratio < 2:
            insights.append("助手回复相对简洁")
            suggestions.append("可以要求更详细的解释")
        
        # 检查是否有未回答的问题（简化版）
        unanswered = 0
        for memory in memories:
            if '？' in memory['user_input'] and len(memory['assistant_response']) < 50:
                unanswered += 1
        
        if unanswered > 0:
            insights.append(f"可能有 {unanswered} 个问题未得到充分回答")
            suggestions.append("对于未充分回答的问题，可以要求进一步说明")
        
        return {
            'insights': insights,
            'suggestions': suggestions
        }
    
    async def _get_all_memories(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取所有记忆（带限制）"""
        # 这里简化处理，实际应该实现分页
        query = '''
            SELECT id, session_id, user_input, assistant_response, 
                   metadata, created_at
            FROM memories
            ORDER BY created_at DESC
            LIMIT $1
        '''
        
        results = await self.memory_manager.storage.db.fetch(query, limit)
        
        memories = []
        for row in results:
            memories.append({
                'id': str(row['id']),
                'session_id': row['session_id'],
                'user_input': row['user_input'],
                'assistant_response': row['assistant_response'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'created_at': row['created_at'].isoformat()
            })
        
        return memories