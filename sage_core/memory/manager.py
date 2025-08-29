#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Manager - 记忆管理器
"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging

from ..interfaces import MemoryContent, SearchOptions
from ..database import DatabaseConnection
from ..database.transaction import TransactionManager
from .storage import MemoryStorage
from .vectorizer import TextVectorizer
from ..resilience import retry, circuit_breaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 整合存储和向量化"""
    
    def __init__(self, db_connection: DatabaseConnection, 
                 vectorizer: TextVectorizer,
                 transaction_manager: Optional[TransactionManager] = None):
        """初始化记忆管理器
        
        Args:
            db_connection: 数据库连接
            vectorizer: 向量化器
            transaction_manager: 事务管理器（可选）
        """
        self.storage = MemoryStorage(db_connection, transaction_manager)
        self.vectorizer = vectorizer
        self.transaction_manager = transaction_manager
        self.current_session_id: Optional[str] = None
    
    async def initialize(self) -> None:
        """初始化管理器"""
        await self.storage.connect()
        await self.vectorizer.initialize()
        
        # 创建默认会话
        self.current_session_id = str(uuid.uuid4())
        logger.info(f"记忆管理器初始化完成，会话ID：{self.current_session_id}")
    
    async def save(self, content: MemoryContent) -> str:
        """保存记忆 - 支持事务
        
        Args:
            content: 记忆内容
            
        Returns:
            记忆ID
        """
        # 如果有事务管理器，使用事务保存
        if self.transaction_manager:
            return await self._save_with_transaction(content)
        else:
            return await self._save_without_transaction(content)
    
    async def _save_with_transaction(self, content: MemoryContent) -> str:
        """在事务中保存记忆"""
        async with self.transaction_manager.transaction() as conn:
            try:
                # 合并用户输入和助手回复进行向量化
                combined_text = f"{content.user_input}\n{content.assistant_response}"
                embedding = await self._vectorize_with_protection(combined_text)
                
                # 使用当前会话ID（如果内容中没有指定）
                session_id = content.session_id or self.current_session_id
                
                # 保存到存储 - 传递事务连接和Agent字段
                memory_id = await self.storage.save(
                    user_input=content.user_input,
                    assistant_response=content.assistant_response,
                    embedding=embedding,
                    metadata=content.metadata,
                    session_id=session_id,
                    is_agent_report=content.is_agent_report,  # 添加
                    agent_metadata=content.agent_metadata,    # 添加
                    _transaction_conn=conn
                )
                
                logger.info(f"记忆已保存（事务中）：{memory_id}")
                return memory_id
                
            except Exception as e:
                logger.error(f"保存记忆失败（事务将回滚）：{e}")
                raise
    
    @retry(max_attempts=3, initial_delay=0.5)
    @circuit_breaker("memory_save", failure_threshold=5, recovery_timeout=60)
    async def _save_without_transaction(self, content: MemoryContent) -> str:
        """使用显式事务保存记忆 - 确保原子性"""
        try:
            # 如果有事务管理器，使用事务保存
            if self.transaction_manager:
                async with self.transaction_manager.transaction() as conn:
                    # 合并用户输入和助手回复进行向量化
                    combined_text = f"{content.user_input}\n{content.assistant_response}"
                    embedding = await self._vectorize_with_protection(combined_text)
                    
                    # 使用当前会话ID（如果内容中没有指定）
                    session_id = content.session_id or self.current_session_id
                    
                    # 调试：打印MemoryContent内容
                    logger.info(f"[DEBUG] MemoryManager._save_without_transaction - 事务模式")
                    logger.info(f"  - content.is_agent_report: {content.is_agent_report}")
                    logger.info(f"  - content.agent_metadata: {content.agent_metadata}")
                    
                    # 在同一事务中保存 - 传递Agent字段
                    memory_id = await self.storage.save(
                        user_input=content.user_input,
                        assistant_response=content.assistant_response,
                        embedding=embedding,
                        metadata=content.metadata,
                        session_id=session_id,
                        is_agent_report=content.is_agent_report,
                        agent_metadata=content.agent_metadata,
                        _transaction_conn=conn
                    )
                    
                    logger.info(f"记忆已原子保存：{memory_id}")
                    return memory_id
            else:
                # 降级到无事务模式
                combined_text = f"{content.user_input}\n{content.assistant_response}"
                embedding = await self._vectorize_with_protection(combined_text)
                
                session_id = content.session_id or self.current_session_id
                
                memory_id = await self.storage.save(
                    user_input=content.user_input,
                    assistant_response=content.assistant_response,
                    embedding=embedding,
                    metadata=content.metadata,
                    session_id=session_id,
                    is_agent_report=content.is_agent_report,
                    agent_metadata=content.agent_metadata
                )
                
                logger.info(f"记忆已保存（无事务）：{memory_id}")
                return memory_id
            
        except CircuitBreakerOpenError:
            logger.error("记忆保存断路器已打开，拒绝请求")
            raise
        except Exception as e:
            logger.error(f"保存记忆失败：{e}")
            raise
    
    @retry(max_attempts=3, initial_delay=0.5)
    @circuit_breaker("vectorizer", failure_threshold=5, recovery_timeout=60)
    async def _vectorize_with_protection(self, text: str) -> List[float]:
        """带保护的向量化操作"""
        try:
            return await self.vectorizer.vectorize(text)
        except CircuitBreakerOpenError:
            logger.error("向量化断路器已打开，拒绝请求")
            raise
        except Exception as e:
            logger.error(f"向量化失败：{e}")
            raise
    
    @retry(max_attempts=3, initial_delay=0.5)
    @circuit_breaker("memory_search", failure_threshold=5, recovery_timeout=60)
    async def search(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """搜索记忆 - 带重试和断路器保护
        
        Args:
            query: 搜索查询
            options: 搜索选项
            
        Returns:
            搜索结果列表
        """
        try:
            results = []
            
            if options.strategy == "semantic" or options.strategy == "default":
                # 语义搜索
                query_embedding = await self._vectorize_with_protection(query)
                semantic_results = await self.storage.search(
                    query_embedding=query_embedding,
                    limit=options.limit,
                    session_id=options.session_id
                )
                results.extend(semantic_results)
            
            if options.strategy == "recent":
                # 最近记忆
                if options.session_id:
                    recent_results = await self.storage.get_session_memories(
                        session_id=options.session_id,
                        limit=options.limit
                    )
                else:
                    # 获取所有最近的记忆
                    recent_results = await self._get_recent_memories(options.limit)
                results.extend(recent_results)
            
            if options.strategy == "default":
                # 默认策略：结合语义和文本搜索
                text_results = await self.storage.search_by_text(
                    query=query,
                    limit=options.limit // 2,  # 一半配额给文本搜索
                    session_id=options.session_id
                )
                
                # 合并结果，去重
                existing_ids = {r['id'] for r in results}
                for result in text_results:
                    if result['id'] not in existing_ids:
                        results.append(result)
            
            # 按相似度或时间排序
            if options.strategy == "semantic":
                results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            else:
                results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 限制返回数量
            return results[:options.limit]
            
        except CircuitBreakerOpenError:
            logger.error("搜索断路器已打开，拒绝请求")
            raise
        except Exception as e:
            logger.error(f"搜索记忆失败：{e}")
            raise
    
    async def get_context(self, query: str, max_results: int = 10) -> str:
        """获取格式化的上下文
        
        Args:
            query: 查询内容
            max_results: 最大结果数
            
        Returns:
            格式化的上下文文本
        """
        try:
            # 搜索相关记忆 - 使用全局搜索而不限制会话
            options = SearchOptions(
                limit=max_results,
                strategy="default",
                session_id=None  # 修改为None以搜索所有会话的记忆
            )
            
            memories = await self.search(query, options)
            
            if not memories:
                return "没有找到相关的历史记忆。"
            
            # 格式化上下文 - 增强版，包含更多有价值的信息
            context_parts = ["相关历史记忆：\n"]
            
            for i, memory in enumerate(memories, 1):
                context_parts.append(f"\n[记忆 {i}]")
                context_parts.append(f"时间：{memory['created_at']}")
                if 'similarity' in memory:
                    context_parts.append(f"相关度：{memory['similarity']:.2f}")
                
                # 提取元数据中的有用信息
                metadata = memory.get('metadata', {})
                if metadata:
                    # 显示会话信息
                    if metadata.get('session_id'):
                        context_parts.append(f"会话ID：{metadata['session_id'][:8]}...")
                    
                    # 显示消息统计
                    if metadata.get('message_count'):
                        context_parts.append(f"消息数：{metadata['message_count']}")
                    
                    # 显示工具调用信息
                    if metadata.get('tool_call_count'):
                        context_parts.append(f"工具调用：{metadata['tool_call_count']}次")
                        
                    # 显示具体的工具调用（如果有）
                    tool_calls = metadata.get('tool_calls', [])
                    if tool_calls:
                        tool_names = [tc.get('tool_name', 'unknown') for tc in tool_calls[:3]]  # 最多显示3个
                        if tool_names:
                            context_parts.append(f"使用工具：{', '.join(tool_names)}")
                    
                    # 显示处理格式
                    if metadata.get('format'):
                        context_parts.append(f"来源格式：{metadata['format']}")
                
                # 智能显示对话内容
                user_input = memory.get('user_input', '').strip()
                assistant_response = memory.get('assistant_response', '').strip()
                
                # 处理空内容的情况
                if not user_input and not assistant_response:
                    context_parts.append("内容：（空记录）")
                elif not user_input:
                    # 只有助手回复（可能是工具调用结果）
                    if assistant_response.startswith("Tool execution result"):
                        context_parts.append(f"工具执行结果：{assistant_response[22:].strip()}")
                    else:
                        context_parts.append(f"助手：{assistant_response[:200]}{'...' if len(assistant_response) > 200 else ''}")
                elif not assistant_response:
                    # 只有用户输入
                    context_parts.append(f"用户：{user_input[:200]}{'...' if len(user_input) > 200 else ''}")
                else:
                    # 完整对话
                    context_parts.append(f"用户：{user_input[:150]}{'...' if len(user_input) > 150 else ''}")
                    context_parts.append(f"助手：{assistant_response[:150]}{'...' if len(assistant_response) > 150 else ''}")
                
                context_parts.append("-" * 40)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"获取上下文失败：{e}")
            return f"获取上下文时出错：{str(e)}"
    
    async def switch_session(self, session_id: str) -> None:
        """切换会话
        
        Args:
            session_id: 新的会话ID
        """
        self.current_session_id = session_id
        logger.info(f"已切换到会话：{session_id}")
    
    async def create_session(self) -> str:
        """创建新会话
        
        Returns:
            新会话ID
        """
        self.current_session_id = str(uuid.uuid4())
        logger.info(f"创建新会话：{self.current_session_id}")
        return self.current_session_id
    
    async def get_session_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取会话信息
        
        Args:
            session_id: 会话ID，None表示当前会话
            
        Returns:
            会话信息
        """
        target_session = session_id or self.current_session_id
        
        # 获取会话统计
        stats = await self.storage.get_statistics(target_session)
        
        # 获取会话记忆数量
        memories = await self.storage.get_session_memories(target_session, limit=1)
        
        return {
            'session_id': target_session,
            'is_current': target_session == self.current_session_id,
            'memory_count': stats['total_memories'],
            'first_memory': stats['first_memory'],
            'last_memory': stats['last_memory']
        }
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        sessions = await self.storage.list_sessions()
        
        # 标记当前会话
        for session in sessions:
            session['is_current'] = session['session_id'] == self.current_session_id
        
        return sessions
    
    async def export_session(self, session_id: str, format: str = "json") -> Any:
        """导出会话数据
        
        Args:
            session_id: 会话ID
            format: 导出格式 (json/markdown)
            
        Returns:
            导出的数据
        """
        # 获取会话的所有记忆
        memories = await self.storage.get_session_memories(session_id)
        
        if format == "json":
            return {
                'session_id': session_id,
                'exported_at': datetime.utcnow().isoformat(),
                'memory_count': len(memories),
                'memories': memories
            }
        
        elif format == "markdown":
            lines = [
                f"# Sage 会话导出",
                f"\n会话ID：{session_id}",
                f"导出时间：{datetime.utcnow().isoformat()}",
                f"记忆数量：{len(memories)}",
                "\n---\n"
            ]
            
            for memory in memories:
                lines.append(f"## {memory['created_at']}")
                lines.append(f"\n**用户：** {memory['user_input']}")
                lines.append(f"\n**助手：** {memory['assistant_response']}")
                if memory.get('metadata'):
                    lines.append(f"\n**元数据：** {memory['metadata']}")
                lines.append("\n---\n")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"不支持的导出格式：{format}")
    
    async def _get_recent_memories(self, limit: int) -> List[Dict[str, Any]]:
        """获取最近的记忆（跨会话）"""
        query = '''
            SELECT id, session_id, user_input, assistant_response, 
                   metadata, created_at
            FROM memories
            ORDER BY created_at DESC
            LIMIT $1
        '''
        
        results = await self.storage.db.fetch(query, limit)
        
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
    
    async def cleanup(self) -> None:
        """清理资源"""
        await self.storage.disconnect()