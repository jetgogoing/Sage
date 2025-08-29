#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Storage - 记忆存储实现
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import numpy as np
import json
import logging
from ..interfaces.memory import IMemoryProvider
from ..database import DatabaseConnection
from ..database.transaction import TransactionManager, TransactionalStorage
from ..resilience import retry, circuit_breaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class MemoryStorage(IMemoryProvider, TransactionalStorage):
    """记忆存储实现类 - 支持事务管理"""
    
    def __init__(self, db_connection: DatabaseConnection, transaction_manager: Optional[TransactionManager] = None):
        """初始化存储
        
        Args:
            db_connection: 数据库连接管理器
            transaction_manager: 事务管理器（可选）
        """
        self.db = db_connection
        # 如果提供了事务管理器，初始化事务支持
        if transaction_manager:
            TransactionalStorage.__init__(self, transaction_manager)
        self._transaction_manager = transaction_manager
    
    async def connect(self) -> None:
        """建立数据库连接"""
        await self.db.connect()
    
    async def disconnect(self) -> None:
        """断开数据库连接"""
        await self.db.disconnect()
    
    @retry(max_attempts=3, initial_delay=0.5)
    @circuit_breaker("memory_storage_save", failure_threshold=5, recovery_timeout=60)
    async def save(self, user_input: str, assistant_response: str, 
                   embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None,
                   session_id: Optional[str] = None, 
                   is_agent_report: bool = False,
                   agent_metadata: Optional[Dict[str, Any]] = None,
                   **kwargs) -> str:
        """保存记忆到数据库 - 带重试和断路器保护"""
        try:
            # 数据完整性验证 - 改进逻辑以支持单边消息
            if not user_input and not assistant_response:
                raise ValueError("user_input 和 assistant_response 不能同时为空")
            
            # 至少需要一个非空内容
            if user_input and not user_input.strip() and assistant_response and not assistant_response.strip():
                raise ValueError("user_input 和 assistant_response 不能同时为空字符串")
            
            if embedding is None:
                raise ValueError("embedding 不能为 None")
            
            if not hasattr(embedding, 'tolist'):
                raise ValueError("embedding 必须是 numpy array 或具有 tolist 方法的对象")
            
            if session_id is not None and (not isinstance(session_id, str) or not session_id.strip()):
                raise ValueError("session_id 必须是非空字符串或 None")
            
            # 生成内容哈希用于去重 - 增强版本
            import hashlib
            from datetime import datetime, timezone
            
            # 基础内容哈希
            content_for_hash = f"{user_input or ''}{assistant_response or ''}"
            content_hash = hashlib.sha256(content_for_hash.encode('utf-8')).hexdigest()
            
            # 时间窗口哈希（每小时为一个窗口）
            time_window = datetime.now(timezone.utc).strftime("%Y%m%d%H")
            time_aware_hash = hashlib.sha256(f"{content_for_hash}{time_window}".encode('utf-8')).hexdigest()
            
            # 检查是否已存在相同内容的记录（在近期时间窗口内）
            existing_query = '''
                SELECT id, created_at, metadata FROM memories 
                WHERE (
                    metadata->>'content_hash' = $1 
                    OR metadata->>'time_aware_hash' = $2
                )
                AND session_id = $3
                AND created_at > NOW() - INTERVAL '2 hours'
                ORDER BY created_at DESC
                LIMIT 1
            '''
            
            # 根据连接类型执行查询
            if self._transaction_manager and '_transaction_conn' in kwargs:
                conn = kwargs['_transaction_conn']
                existing_record = await conn.fetchrow(existing_query, content_hash, time_aware_hash, session_id)
            else:
                existing_record = await self.db.fetchrow(existing_query, content_hash, time_aware_hash, session_id)
            
            if existing_record:
                # 检查是否为真正的重复记录
                existing_metadata = json.loads(existing_record['metadata']) if existing_record['metadata'] else {}
                
                # 如果是时间窗口内的相同内容，检查是否有新的元数据
                if metadata and existing_metadata:
                    # 比较元数据的关键字段
                    key_fields = ['tool_calls', 'message_count', 'thinking_content']
                    has_new_info = any(
                        metadata.get(field) != existing_metadata.get(field) 
                        for field in key_fields
                    )
                    
                    if has_new_info:
                        logger.info(f"发现相似内容但有新信息，允许保存: {content_hash[:8]}...")
                    else:
                        logger.info(f"跳过重复记录，返回已存在的ID: {existing_record['id']} (hash: {content_hash[:8]}...)")
                        return str(existing_record['id'])
                else:
                    logger.info(f"跳过重复记录，返回已存在的ID: {existing_record['id']} (hash: {content_hash[:8]}...)")
                    return str(existing_record['id'])
            
            # 生成记忆ID
            memory_id = str(uuid.uuid4())
            
            # 准备元数据
            if metadata is None:
                metadata = {}
            
            # 添加内容哈希到元数据
            metadata['content_hash'] = content_hash
            metadata['time_aware_hash'] = time_aware_hash
            metadata['time_window'] = time_window
            
            # 将向量转换为列表（PostgreSQL pgvector 需要）
            try:
                embedding_list = embedding.tolist()
            except (AttributeError, TypeError) as e:
                raise ValueError(f"embedding 转换失败: {e}")
            
            # 将向量列表转换为 PostgreSQL vector 格式的字符串
            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
            
            # 长期优化：处理Agent元数据
            # 现在是作为显式参数传入
            agent_metadata_json = None
            
            # 调试：打印所有接收到的参数
            logger.info(f"[DEBUG] save方法接收到的参数:")
            logger.info(f"  - is_agent_report参数: {is_agent_report}")
            logger.info(f"  - agent_metadata参数: {agent_metadata}")
            logger.info(f"  - metadata内容: {metadata}")
            logger.info(f"  - kwargs内容: {kwargs}")
            
            # 如果有agent_metadata参数，使用它
            if agent_metadata:
                is_agent_report = True
                agent_metadata_json = json.dumps(agent_metadata)
                logger.info(f"使用agent_metadata参数: {agent_metadata}")
            # 否则从metadata中提取（向后兼容）
            elif metadata and 'agent_metadata' in metadata:
                is_agent_report = True
                agent_metadata_json = json.dumps(metadata['agent_metadata'])
                logger.info(f"从metadata提取agent_metadata: {metadata['agent_metadata']}")
            
            # 确保is_agent_report一致性
            if not is_agent_report and metadata:
                is_agent_report = metadata.get('is_agent_report', False)
            
            logger.info(f"最终: is_agent_report={is_agent_report}, agent_metadata_json={agent_metadata_json[:50] if agent_metadata_json else None}")
            
            # 插入记录 - 支持事务和Agent元数据
            query = '''
                INSERT INTO memories 
                (id, session_id, user_input, assistant_response, embedding, metadata, is_agent_report, agent_metadata)
                VALUES ($1, $2, $3, $4, $5::vector, $6, $7, $8::jsonb)
                RETURNING id
            '''
            
            # 如果有事务管理器，使用事务连接
            if self._transaction_manager and '_transaction_conn' in kwargs:
                conn = kwargs['_transaction_conn']
                result = await conn.fetchval(
                    query,
                    memory_id,
                    session_id,
                    user_input,
                    assistant_response,
                    embedding_str,
                    json.dumps(metadata, ensure_ascii=False),
                    is_agent_report,
                    agent_metadata_json
                )
            else:
                # 否则使用普通连接
                result = await self.db.fetchval(
                    query,
                    memory_id,
                    session_id,
                    user_input,
                    assistant_response,
                    embedding_str,
                    json.dumps(metadata, ensure_ascii=False),
                    is_agent_report,
                    agent_metadata_json
                )
            
            logger.info(f"记忆已保存：{result}")
            return result
            
        except CircuitBreakerOpenError:
            logger.error("存储保存断路器已打开，拒绝请求")
            raise
        except Exception as e:
            logger.error(f"保存记忆失败：{e}")
            raise
    
    @retry(max_attempts=3, initial_delay=0.5)
    @circuit_breaker("memory_storage_search", failure_threshold=5, recovery_timeout=60)
    async def search(self, query_embedding: np.ndarray, limit: int = 10,
                    session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """向量相似度搜索 - 带重试和断路器保护"""
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
                    'created_at': row['created_at'].astimezone().isoformat(),
                    'similarity': float(row['similarity'])
                }
                memories.append(memory)
            
            return memories
            
        except CircuitBreakerOpenError:
            logger.error("存储搜索断路器已打开，拒绝请求")
            raise
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
                    'created_at': row['created_at'].astimezone().isoformat()
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
            values.append(datetime.now(timezone.utc))
            
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
                    'created_at': row['created_at'].astimezone().isoformat(),
                    'last_active': row['last_active'].astimezone().isoformat()
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
                    'created_at': row['created_at'].astimezone().isoformat()
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"获取会话记忆失败：{e}")
            raise
    
    @retry(max_attempts=3, initial_delay=0.5)
    @circuit_breaker("memory_storage_text_search", failure_threshold=5, recovery_timeout=60)
    async def search_by_text(self, query: str, limit: int = 10,
                           session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """文本搜索 - 带重试和断路器保护"""
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
                    'created_at': row['created_at'].astimezone().isoformat()
                })
            
            return memories
            
        except CircuitBreakerOpenError:
            logger.error("文本搜索断路器已打开，拒绝请求")
            raise
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
                'first_memory': row['first_memory'].astimezone().isoformat() if row['first_memory'] else None,
                'last_memory': row['last_memory'].astimezone().isoformat() if row['last_memory'] else None
            }
            
            if not session_id and 'session_count' in row:
                stats['session_count'] = row['session_count']
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败：{e}")
            raise
    
    def _validate_and_optimize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """验证和优化元数据大小"""
        if not metadata:
            return {}
        
        # 序列化检查大小
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        metadata_size = len(metadata_json.encode('utf-8'))
        
        # 设置合理的限制（100KB）
        MAX_METADATA_SIZE = 100 * 1024
        
        if metadata_size > MAX_METADATA_SIZE:
            logger.warning(f"元数据过大：{metadata_size} bytes，开始优化")
            
            # 优化策略
            optimized_metadata = {}
            
            # 保留必要字段
            essential_fields = [
                'content_hash', 'time_aware_hash', 'time_window',
                'session_id', 'message_count', 'tool_call_count'
            ]
            
            for field in essential_fields:
                if field in metadata:
                    optimized_metadata[field] = metadata[field]
            
            # 压缩大型字段
            if 'tool_calls' in metadata:
                tool_calls = metadata['tool_calls']
                if isinstance(tool_calls, list) and len(tool_calls) > 10:
                    # 只保留前10个工具调用
                    optimized_metadata['tool_calls'] = tool_calls[:10]
                    optimized_metadata['tool_calls_truncated'] = len(tool_calls)
                else:
                    optimized_metadata['tool_calls'] = tool_calls
            
            # 截断过长的文本字段
            text_fields = ['thinking_content', 'error_message', 'notes']
            for field in text_fields:
                if field in metadata:
                    value = metadata[field]
                    if isinstance(value, str) and len(value) > 1000:
                        optimized_metadata[field] = value[:1000] + "...[truncated]"
                    else:
                        optimized_metadata[field] = value
            
            # 检查优化后的大小
            optimized_json = json.dumps(optimized_metadata, ensure_ascii=False)
            optimized_size = len(optimized_json.encode('utf-8'))
            
            logger.info(f"元数据优化完成：{metadata_size} -> {optimized_size} bytes")
            
            return optimized_metadata
        
        return metadata