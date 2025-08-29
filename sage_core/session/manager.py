#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Manager - 会话管理器
"""
import uuid
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器"""
    
    def __init__(self, memory_manager):
        """初始化会话管理器
        
        Args:
            memory_manager: 记忆管理器实例
        """
        self.memory_manager = memory_manager
        self.current_session_id = memory_manager.current_session_id
    
    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """创建新会话
        
        Args:
            metadata: 会话元数据
            
        Returns:
            新会话ID
        """
        session_id = await self.memory_manager.create_session()
        self.current_session_id = session_id
        
        logger.info(f"创建新会话：{session_id}")
        return session_id
    
    async def switch_session(self, session_id: str) -> None:
        """切换到指定会话
        
        Args:
            session_id: 目标会话ID
        """
        # 验证会话是否存在
        sessions = await self.list_sessions()
        session_ids = [s['session_id'] for s in sessions]
        
        if session_id not in session_ids:
            # 如果会话不存在，创建一个新的
            logger.warning(f"会话 {session_id} 不存在，将创建新会话")
        
        await self.memory_manager.switch_session(session_id)
        self.current_session_id = session_id
        
        logger.info(f"已切换到会话：{session_id}")
    
    async def get_current_session(self) -> str:
        """获取当前会话ID
        
        Returns:
            当前会话ID
        """
        return self.current_session_id
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话
        
        Returns:
            会话列表
        """
        return await self.memory_manager.list_sessions()
    
    async def get_session_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取会话信息
        
        Args:
            session_id: 会话ID，None表示当前会话
            
        Returns:
            会话信息
        """
        target_session = session_id or self.current_session_id
        return await self.memory_manager.get_session_info(target_session)
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话（删除该会话的所有记忆）
        
        Args:
            session_id: 要删除的会话ID
            
        Returns:
            是否成功
        """
        if session_id == self.current_session_id:
            logger.warning("不能删除当前会话")
            return False
        
        # 获取会话的所有记忆
        memories = await self.memory_manager.storage.get_session_memories(session_id)
        
        # 删除每个记忆
        for memory in memories:
            await self.memory_manager.storage.delete(memory['id'])
        
        logger.info(f"已删除会话 {session_id} 的 {len(memories)} 条记忆")
        return True
    
    async def merge_sessions(self, source_session_id: str, 
                           target_session_id: str) -> int:
        """合并两个会话
        
        Args:
            source_session_id: 源会话ID
            target_session_id: 目标会话ID
            
        Returns:
            合并的记忆数量
        """
        # 获取源会话的所有记忆
        memories = await self.memory_manager.storage.get_session_memories(source_session_id)
        
        # 更新每个记忆的会话ID
        for memory in memories:
            await self.memory_manager.storage.update(
                memory['id'],
                {'session_id': target_session_id}
            )
        
        logger.info(f"已将 {len(memories)} 条记忆从会话 {source_session_id} 合并到 {target_session_id}")
        return len(memories)