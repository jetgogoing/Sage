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
from .storage import MemoryStorage
from .vectorizer import TextVectorizer

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 整合存储和向量化"""
    
    def __init__(self, db_connection: DatabaseConnection, 
                 vectorizer: TextVectorizer):
        """初始化记忆管理器
        
        Args:
            db_connection: 数据库连接
            vectorizer: 向量化器
        """
        self.storage = MemoryStorage(db_connection)
        self.vectorizer = vectorizer
        self.current_session_id: Optional[str] = None
    
    async def initialize(self) -> None:
        """初始化管理器"""
        await self.storage.connect()
        await self.vectorizer.initialize()
        
        # 创建默认会话
        self.current_session_id = str(uuid.uuid4())
        logger.info(f"记忆管理器初始化完成，会话ID：{self.current_session_id}")
    
    async def save(self, content: MemoryContent) -> str:
        """保存记忆
        
        Args:
            content: 记忆内容
            
        Returns:
            记忆ID
        """
        try:
            # 合并用户输入和助手回复进行向量化
            combined_text = f"{content.user_input}\n{content.assistant_response}"
            embedding = await self.vectorizer.vectorize(combined_text)
            
            # 使用当前会话ID（如果内容中没有指定）
            session_id = content.session_id or self.current_session_id
            
            # 保存到存储
            memory_id = await self.storage.save(
                user_input=content.user_input,
                assistant_response=content.assistant_response,
                embedding=embedding,
                metadata=content.metadata,
                session_id=session_id
            )
            
            logger.info(f"记忆已保存：{memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"保存记忆失败：{e}")
            raise
    
    async def search(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """搜索记忆
        
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
                query_embedding = await self.vectorizer.vectorize(query)
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
            # 搜索相关记忆
            options = SearchOptions(
                limit=max_results,
                strategy="default",
                session_id=self.current_session_id
            )
            
            memories = await self.search(query, options)
            
            if not memories:
                return "没有找到相关的历史记忆。"
            
            # 格式化上下文
            context_parts = ["相关历史记忆：\n"]
            
            for i, memory in enumerate(memories, 1):
                context_parts.append(f"\n[记忆 {i}]")
                context_parts.append(f"时间：{memory['created_at']}")
                if 'similarity' in memory:
                    context_parts.append(f"相关度：{memory['similarity']:.2f}")
                context_parts.append(f"用户：{memory['user_input']}")
                context_parts.append(f"助手：{memory['assistant_response']}")
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