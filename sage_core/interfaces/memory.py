#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Provider Interface - 记忆存储接口定义
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np


class IMemoryProvider(ABC):
    """记忆提供者接口"""
    
    @abstractmethod
    async def connect(self) -> None:
        """建立数据库连接"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开数据库连接"""
        pass
    
    @abstractmethod
    async def save(self, user_input: str, assistant_response: str, 
                   embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None,
                   session_id: Optional[str] = None,
                   is_agent_report: bool = False,
                   agent_metadata: Optional[Dict[str, Any]] = None,
                   **kwargs) -> str:
        """保存记忆到数据库
        
        Args:
            user_input: 用户输入
            assistant_response: 助手回复
            embedding: 向量嵌入
            metadata: 元数据
            session_id: 会话ID
            
        Returns:
            memory_id: 记忆ID
        """
        pass
    
    @abstractmethod
    async def search(self, query_embedding: np.ndarray, limit: int = 10,
                    session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """向量相似度搜索
        
        Args:
            query_embedding: 查询向量
            limit: 返回结果数量
            session_id: 会话ID过滤
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆数据或None
        """
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """更新记忆
        
        Args:
            memory_id: 记忆ID
            updates: 更新内容
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话
        
        Returns:
            会话列表
        """
        pass
    
    @abstractmethod
    async def get_session_memories(self, session_id: str, 
                                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取会话内的所有记忆
        
        Args:
            session_id: 会话ID
            limit: 限制数量
            
        Returns:
            记忆列表
        """
        pass
    
    @abstractmethod
    async def search_by_text(self, query: str, limit: int = 10,
                           session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """文本搜索
        
        Args:
            query: 搜索文本
            limit: 返回结果数量
            session_id: 会话ID过滤
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    async def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息
        
        Args:
            session_id: 会话ID，None表示全局统计
            
        Returns:
            统计信息
        """
        pass