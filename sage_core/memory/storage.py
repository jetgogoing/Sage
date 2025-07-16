#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Storage - 记忆存储实现
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np
import json
import logging
from ..interfaces.memory import IMemoryProvider
from ..database import DatabaseConnection

logger = logging.getLogger(__name__)


class MemoryStorage(IMemoryProvider):
    """记忆存储实现类"""
    
    def __init__(self, db_connection: DatabaseConnection):
        """初始化存储
        
        Args:
            db_connection: 数据库连接管理器
        """
        self.db = db_connection
    
    async def connect(self) -> None:
        """建立数据库连接"""
        await self.db.connect()
    
    async def disconnect(self) -> None:
        """断开数据库连接"""
        await self.db.disconnect()
    
    async def save(self, user_input: str, assistant_response: str, 
                   embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None,
                   session_id: Optional[str] = None) -> str:
        """保存记忆到数据库"""
        try:
            # 生成记忆ID
            memory_id = str(uuid.uuid4())
            
            # 准备元数据
            if metadata is None:
                metadata = {}
            
            # 将向量转换为列表（PostgreSQL pgvector 需要）
            embedding_list = embedding.tolist()
            
            # 将向量列表转换为 PostgreSQL vector 格式的字符串
            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
            
            # 插入记录
            query = '''
                INSERT INTO memories 
                (id, session_id, user_input, assistant_response, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5::vector, $6)
                RETURNING id
            '''
            
            result = await self.db.fetchval(
                query,
                memory_id,
                session_id,
                user_input,
                assistant_response,
                embedding_str,
                json.dumps(metadata, ensure_ascii=False)
            )
            
            logger.info(f"记忆已保存：{result}")
            return result
            
        except Exception as e:
            logger.error(f"保存记忆失败：{e}")
            raise
    
    async def search(self, query_embedding: np.ndarray, limit: int = 10,
                    session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """向量相似度搜索"""
        try:
            embedding_list = query_embedding.tolist()
            
            # 将向量列表转换为 PostgreSQL vector 格式的字符串
            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
            
            # 构建查询 - 使用 pgvector 的余弦相似度
            if session_id:
                query = '''
                    SELECT id, session_id, user_input, assistant_response, 
                           metadata, created_at,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM memories
                    WHERE session_id = $2
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                '''
                results = await self.db.fetch(query, embedding_str, session_id, limit)
            else:
                query = '''
                    SELECT id, session_id, user_input, assistant_response, 
                           metadata, created_at,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM memories
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                '''
                results = await self.db.fetch(query, embedding_str, limit)
            
            # 转换结果
            memories = []
            for row in results:
                memory = {
                    'id': str(row['id']),
                    'session_id': row['session_id'],
                    'user_input': row['user_input'],
                    'assistant_response': row['assistant_response'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at'].isoformat(),
                    'similarity': float(row['similarity'])
                }
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"搜索记忆失败：{e}")
            raise
    
    async def get_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取记忆"""
        try:
            query = '''
                SELECT id, session_id, user_input, assistant_response, 
                       metadata, created_at
                FROM memories
                WHERE id = $1
            '''
            
            row = await self.db.fetchrow(query, uuid.UUID(memory_id))
            
            if row:
                return {
                    'id': str(row['id']),
                    'session_id': row['session_id'],
                    'user_input': row['user_input'],
                    'assistant_response': row['assistant_response'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at'].isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取记忆失败：{e}")
            raise
    
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """更新记忆"""
        try:
            # 构建更新语句
            set_clauses = []
            values = []
            
            if 'metadata' in updates:
                set_clauses.append(f"metadata = ${len(values) + 1}")
                values.append(json.dumps(updates['metadata'], ensure_ascii=False))
            
            if 'user_input' in updates:
                set_clauses.append(f"user_input = ${len(values) + 1}")
                values.append(updates['user_input'])
            
            if 'assistant_response' in updates:
                set_clauses.append(f"assistant_response = ${len(values) + 1}")
                values.append(updates['assistant_response'])
            
            if not set_clauses:
                return True
            
            # 添加更新时间
            set_clauses.append(f"updated_at = ${len(values) + 1}")
            values.append(datetime.utcnow())
            
            # 添加ID参数
            values.append(uuid.UUID(memory_id))
            
            query = f'''
                UPDATE memories
                SET {', '.join(set_clauses)}
                WHERE id = ${len(values)}
            '''
            
            result = await self.db.execute(query, *values)
            return 'UPDATE' in result
            
        except Exception as e:
            logger.error(f"更新记忆失败：{e}")
            raise
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            query = 'DELETE FROM memories WHERE id = $1'
            result = await self.db.execute(query, uuid.UUID(memory_id))
            return 'DELETE' in result
            
        except Exception as e:
            logger.error(f"删除记忆失败：{e}")
            raise
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        try:
            query = '''
                SELECT session_id, COUNT(*) as memory_count,
                       MIN(created_at) as created_at,
                       MAX(created_at) as last_active
                FROM memories
                WHERE session_id IS NOT NULL
                GROUP BY session_id
                ORDER BY last_active DESC
            '''
            
            results = await self.db.fetch(query)
            
            sessions = []
            for row in results:
                sessions.append({
                    'session_id': row['session_id'],
                    'memory_count': row['memory_count'],
                    'created_at': row['created_at'].isoformat(),
                    'last_active': row['last_active'].isoformat()
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"列出会话失败：{e}")
            raise
    
    async def get_session_memories(self, session_id: str, 
                                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取会话内的所有记忆"""
        try:
            if limit:
                query = '''
                    SELECT id, session_id, user_input, assistant_response, 
                           metadata, created_at
                    FROM memories
                    WHERE session_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                '''
                results = await self.db.fetch(query, session_id, limit)
            else:
                query = '''
                    SELECT id, session_id, user_input, assistant_response, 
                           metadata, created_at
                    FROM memories
                    WHERE session_id = $1
                    ORDER BY created_at DESC
                '''
                results = await self.db.fetch(query, session_id)
            
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
            
        except Exception as e:
            logger.error(f"获取会话记忆失败：{e}")
            raise
    
    async def search_by_text(self, query: str, limit: int = 10,
                           session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """文本搜索"""
        try:
            search_pattern = f'%{query}%'
            
            if session_id:
                query_sql = '''
                    SELECT id, session_id, user_input, assistant_response, 
                           metadata, created_at
                    FROM memories
                    WHERE session_id = $1 
                    AND (user_input ILIKE $2 OR assistant_response ILIKE $2)
                    ORDER BY created_at DESC
                    LIMIT $3
                '''
                results = await self.db.fetch(query_sql, session_id, search_pattern, limit)
            else:
                query_sql = '''
                    SELECT id, session_id, user_input, assistant_response, 
                           metadata, created_at
                    FROM memories
                    WHERE user_input ILIKE $1 OR assistant_response ILIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2
                '''
                results = await self.db.fetch(query_sql, search_pattern, limit)
            
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
            
        except Exception as e:
            logger.error(f"文本搜索失败：{e}")
            raise
    
    async def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            if session_id:
                query = '''
                    SELECT COUNT(*) as total,
                           MIN(created_at) as first_memory,
                           MAX(created_at) as last_memory
                    FROM memories
                    WHERE session_id = $1
                '''
                row = await self.db.fetchrow(query, session_id)
            else:
                query = '''
                    SELECT COUNT(*) as total,
                           COUNT(DISTINCT session_id) as session_count,
                           MIN(created_at) as first_memory,
                           MAX(created_at) as last_memory
                    FROM memories
                '''
                row = await self.db.fetchrow(query)
            
            stats = {
                'total_memories': row['total'],
                'first_memory': row['first_memory'].isoformat() if row['first_memory'] else None,
                'last_memory': row['last_memory'].isoformat() if row['last_memory'] else None
            }
            
            if not session_id and 'session_count' in row:
                stats['session_count'] = row['session_count']
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败：{e}")
            raise