#!/usr/bin/env python3
"""
Enhanced Memory Adapter with Intelligent Retrieval
使用智能检索引擎的增强版记忆适配器
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import uuid
import json

# Import existing memory components
from memory_interface import get_memory_provider, MemorySearchResult
from memory import summarize_context
from intelligent_retrieval import (
    IntelligentRetrievalEngine,
    RetrievalStrategy,
    QueryType,
    RetrievalResult
)

logger = logging.getLogger(__name__)


class EnhancedMemoryAdapter:
    """
    增强版记忆适配器，集成智能检索系统
    
    Features:
    - 使用 IntelligentRetrievalEngine 进行智能检索
    - 支持查询意图分类和多维度评分
    - 可选的 LLM 摘要生成
    - 智能格式化和对话分割符号处理
    """
    
    def __init__(self):
        """初始化增强版适配器"""
        self.memory_provider = get_memory_provider()
        self.intelligent_engine = IntelligentRetrievalEngine(self.memory_provider)
        
        # Session management
        self.current_session_id = str(uuid.uuid4())
        self.current_turn_id = 0
        self.session_history = []
        
        # Configuration
        self.config = {
            'enable_llm_summary': True,  # 是否启用 LLM 摘要
            'retrieval_count': 10,       # 检索数量
            'max_context_tokens': 2000,  # 最大上下文 token 数
            'summary_max_words': 200,    # 摘要最大字数
            'handle_zen_splits': True,   # 处理 ZEN MCP 分割符号
            'enable_neural_rerank': True, # 启用神经网络重排序
        }
        
        logger.info("Enhanced Memory Adapter initialized with Intelligent Retrieval")
    
    def save_conversation(
        self,
        user_prompt: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, int]:
        """
        保存对话到记忆系统
        
        Returns:
            Tuple of (session_id, turn_id)
        """
        try:
            # Increment turn ID for this conversation
            self.current_turn_id += 1
            
            # Prepare enhanced metadata
            enhanced_metadata = {
                'session_id': self.current_session_id,
                'turn_id': self.current_turn_id,
                'timestamp': datetime.now().isoformat(),
                'source': 'mcp_server',
                'has_code': self._contains_code(user_prompt + assistant_response),
                'query_length': len(user_prompt),
                'response_length': len(assistant_response),
            }
            
            # Merge with provided metadata
            if metadata:
                enhanced_metadata.update(metadata)
            
            # Save both parts of conversation
            self.memory_provider.save_conversation(
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                metadata=enhanced_metadata
            )
            
            # Update session history for context awareness
            self.session_history.append({
                'turn_id': self.current_turn_id,
                'user_prompt': user_prompt[:200],  # Store preview
                'timestamp': enhanced_metadata['timestamp'],
                'keywords': self._extract_keywords(user_prompt)
            })
            
            # Keep only recent history (last 10 turns)
            if len(self.session_history) > 10:
                self.session_history = self.session_history[-10:]
            
            logger.info(f"Saved conversation - Session: {self.current_session_id}, Turn: {self.current_turn_id}")
            return self.current_session_id, self.current_turn_id
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise
    
    async def get_intelligent_context(
        self,
        query: str,
        enable_llm_summary: Optional[bool] = None,
        max_results: Optional[int] = None,
        enable_neural_rerank: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        使用智能检索引擎获取相关上下文
        
        Args:
            query: 查询字符串
            enable_llm_summary: 是否启用 LLM 摘要（覆盖默认配置）
            max_results: 最大结果数（覆盖默认配置）
            
        Returns:
            包含上下文和元数据的字典
        """
        try:
            # Override configuration if specified
            use_llm = enable_llm_summary if enable_llm_summary is not None else self.config['enable_llm_summary']
            retrieval_count = max_results if max_results is not None else self.config['retrieval_count']
            use_neural = enable_neural_rerank if enable_neural_rerank is not None else self.config['enable_neural_rerank']
            
            logger.info(f"Getting intelligent context - LLM: {use_llm}, Count: {retrieval_count}, Neural: {use_neural}")
            
            # Use intelligent retrieval engine
            retrieval_results = await self.intelligent_engine.intelligent_retrieve(
                query=query,
                strategy=RetrievalStrategy.HYBRID_ADVANCED,
                session_history=self.session_history,
                max_results=retrieval_count,
                enable_neural_rerank=use_neural
            )
            
            # Format results based on configuration
            if use_llm and retrieval_results:
                # Convert RetrievalResult to format expected by summarize_context
                conversations = []
                for result in retrieval_results:
                    conversations.append({
                        'role': result.role,
                        'content': result.content,
                        'metadata': result.metadata
                    })
                
                # Use existing LLM summarization
                context = summarize_context(conversations, query)
                logger.info(f"Generated LLM summary: {len(context)} chars")
            else:
                # Use intelligent formatting without LLM
                context = self._intelligent_format_context(retrieval_results, query)
                logger.info(f"Generated formatted context: {len(context)} chars")
            
            # Prepare detailed results
            results_detail = []
            for result in retrieval_results:
                results_detail.append({
                    'content': result.content,
                    'role': result.role,
                    'final_score': result.final_score,
                    'similarity_score': result.similarity_score,
                    'reasoning': result.reasoning,
                    'metadata': result.metadata
                })
            
            return {
                'context': context,
                'num_results': len(retrieval_results),
                'results': results_detail,
                'strategy_used': 'intelligent_retrieval',
                'llm_summary_used': use_llm,
                'neural_rerank_used': use_neural,
                'query_analysis': {
                    'detected_type': self._get_query_type_info(query),
                    'session_continuity': len(self.session_history) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get intelligent context: {e}")
            # Fallback to basic search
            return await self._fallback_basic_search(query, retrieval_count)
    
    def _intelligent_format_context(
        self,
        results: List[RetrievalResult],
        query: str
    ) -> str:
        """
        智能格式化上下文，不使用 LLM
        
        Features:
        - 根据得分和推理排序
        - 处理 ZEN MCP 分割符号
        - 智能截断和省略
        - 保持对话连贯性
        """
        if not results:
            return ""
        
        context_parts = []
        total_tokens = 0
        max_tokens = self.config['max_context_tokens']
        
        # Group by conversation turns if possible
        grouped_results = self._group_by_conversation(results)
        
        for group in grouped_results:
            if total_tokens >= max_tokens:
                break
                
            # Format group with smart truncation
            formatted = self._format_conversation_group(group, max_tokens - total_tokens)
            if formatted:
                context_parts.append(formatted)
                # Rough token estimation (1 token ≈ 4 chars)
                total_tokens += len(formatted) // 4
        
        # Handle ZEN MCP splitting symbols
        if self.config['handle_zen_splits']:
            context = self._handle_zen_splits("\n\n---\n\n".join(context_parts))
        else:
            context = "\n\n---\n\n".join(context_parts)
        
        # Add header with metadata
        header = f"# 相关历史上下文 (共 {len(results)} 条记录)\n\n"
        
        return header + context
    
    def _group_by_conversation(self, results: List[RetrievalResult]) -> List[List[RetrievalResult]]:
        """按对话轮次分组结果"""
        groups = []
        current_group = []
        
        for result in results:
            # Check if this belongs to the same conversation turn
            if current_group and self._is_same_turn(current_group[-1], result):
                current_group.append(result)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [result]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _is_same_turn(self, result1: RetrievalResult, result2: RetrievalResult) -> bool:
        """判断两个结果是否属于同一对话轮次"""
        meta1 = result1.metadata or {}
        meta2 = result2.metadata or {}
        
        # Check session and turn IDs
        if meta1.get('session_id') == meta2.get('session_id'):
            turn1 = meta1.get('turn_id', -1)
            turn2 = meta2.get('turn_id', -2)
            return abs(turn1 - turn2) <= 1
        
        return False
    
    def _format_conversation_group(
        self,
        group: List[RetrievalResult],
        max_chars: int
    ) -> str:
        """格式化对话组"""
        parts = []
        total_chars = 0
        
        for result in group:
            # Determine role label
            role_label = "👤 用户" if result.role == "user" else "🤖 助手"
            
            # Calculate available space
            available = max_chars - total_chars - len(role_label) - 10
            if available <= 0:
                break
            
            # Smart truncation
            content = self._smart_truncate(result.content, available)
            
            # Add reasoning as comment if high score
            if result.final_score > 0.8:
                part = f"{role_label}: {content}\n<!-- {result.reasoning} -->"
            else:
                part = f"{role_label}: {content}"
            
            parts.append(part)
            total_chars += len(part)
        
        return "\n".join(parts) if parts else ""
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """智能截断文本，保持完整性"""
        if len(text) <= max_length:
            return text
        
        # Try to cut at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('。')
        last_question = truncated.rfind('？')
        last_exclaim = truncated.rfind('！')
        
        cut_point = max(last_period, last_question, last_exclaim)
        
        if cut_point > max_length * 0.7:  # If we found a good cut point
            return truncated[:cut_point + 1] + "..."
        else:
            return truncated[:max_length - 3] + "..."
    
    def _handle_zen_splits(self, context: str) -> str:
        """处理 ZEN MCP 的分割符号"""
        # Common ZEN MCP splitting patterns
        zen_patterns = [
            ('==========', '\n---\n'),
            ('##########', '\n---\n'),
            ('\\*\\*\\*\\*\\*', '\n---\n'),
            ('----------', '\n---\n'),
        ]
        
        result = context
        for pattern, replacement in zen_patterns:
            result = result.replace(pattern, replacement)
        
        # Remove excessive newlines
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()
    
    def _contains_code(self, text: str) -> bool:
        """检测文本是否包含代码"""
        code_indicators = [
            '```', 'def ', 'class ', 'import ', 'function',
            'const ', 'let ', 'var ', '<?php', '<script'
        ]
        return any(indicator in text for indicator in code_indicators)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简单实现）"""
        # This is a simple implementation
        # Could be enhanced with proper NLP
        import re
        
        # Remove common words
        stop_words = {'的', '是', '在', '和', '了', '有', '我', '你', '他', '她', 'the', 'is', 'at', 'on', 'in', 'a', 'an'}
        
        # Extract words
        words = re.findall(r'\w+', text.lower())
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # Return top 5 most common
        from collections import Counter
        word_counts = Counter(keywords)
        return [word for word, count in word_counts.most_common(5)]
    
    def _get_query_type_info(self, query: str) -> str:
        """获取查询类型信息"""
        # Use the semantic analyzer from intelligent retrieval
        analyzer = self.intelligent_engine.semantic_analyzer
        query_context = analyzer.analyze_query(query)
        return query_context.query_type.value
    
    async def _fallback_basic_search(
        self,
        query: str,
        max_results: int
    ) -> Dict[str, Any]:
        """降级到基础搜索"""
        logger.warning("Falling back to basic search")
        
        results = self.memory_provider.search_memory(query, n=max_results)
        
        context_parts = []
        results_detail = []
        
        for result in results:
            role_label = "用户" if result.role == "user" else "助手"
            context_parts.append(f"[{role_label}]: {result.content[:200]}...")
            
            results_detail.append({
                'content': result.content,
                'role': result.role,
                'score': result.score,
                'metadata': result.metadata
            })
        
        return {
            'context': "\n\n".join(context_parts),
            'num_results': len(results),
            'results': results_detail,
            'strategy_used': 'basic_search',
            'llm_summary_used': False,
            'query_analysis': {'fallback': True}
        }
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        logger.info(f"Configuration updated: {config}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'session_id': self.current_session_id,
            'turn_count': self.current_turn_id,
            'session_history_size': len(self.session_history),
            'config': self.config.copy(),
            'retrieval_stats': self.intelligent_engine.get_retrieval_stats()
        }


# Singleton instance
_enhanced_adapter_instance = None


def get_enhanced_memory_adapter() -> EnhancedMemoryAdapter:
    """获取增强版记忆适配器的单例实例"""
    global _enhanced_adapter_instance
    if _enhanced_adapter_instance is None:
        _enhanced_adapter_instance = EnhancedMemoryAdapter()
    return _enhanced_adapter_instance