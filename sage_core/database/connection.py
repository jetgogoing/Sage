#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Connection Manager - 数据库连接管理
"""
import asyncio
import asyncpg
from typing import Optional, Dict, Any
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """数据库连接管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化连接管理器
        
        Args:
            config: 数据库配置
        """
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """创建连接池"""
        async with self._lock:
            if self.pool is not None:
                return
            
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.config['host'],
                    port=self.config['port'],
                    database=self.config['database'],
                    user=self.config['user'],
                    password=self.config['password'],
                    min_size=5,
                    max_size=20,
                    command_timeout=60
                )
                logger.info("数据库连接池创建成功")
                
                # 初始化数据库结构
                await self._initialize_schema()
                
            except Exception as e:
                logger.error(f"创建数据库连接池失败：{e}")
                raise
    
    async def disconnect(self) -> None:
        """关闭连接池"""
        async with self._lock:
            if self.pool is None:
                return
            
            await self.pool.close()
            self.pool = None
            logger.info("数据库连接池已关闭")
    
    @asynccontextmanager
    async def acquire(self):
        """获取数据库连接
        
        Yields:
            数据库连接对象
        """
        if self.pool is None:
            await self.connect()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args) -> str:
        """执行SQL语句
        
        Args:
            query: SQL语句
            *args: 参数
            
        Returns:
            执行结果
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list:
        """查询多条记录
        
        Args:
            query: SQL查询语句
            *args: 参数
            
        Returns:
            查询结果列表
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """查询单条记录
        
        Args:
            query: SQL查询语句
            *args: 参数
            
        Returns:
            查询结果
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """查询单个值
        
        Args:
            query: SQL查询语句
            *args: 参数
            
        Returns:
            查询结果值
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def _initialize_schema(self) -> None:
        """初始化数据库模式"""
        async with self.acquire() as conn:
            # 创建 pgvector 扩展
            await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
            
            # 创建记忆表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id TEXT,
                    user_input TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    embedding vector(4096),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_session_id 
                ON memories(session_id)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_created_at 
                ON memories(created_at DESC)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_embedding 
                ON memories USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            ''')
            
            logger.info("数据库模式初始化完成")