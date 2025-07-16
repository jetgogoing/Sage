#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage Core Service Implementation - 核心服务实现
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .interfaces import (
    ISageService, 
    MemoryContent, 
    SearchOptions, 
    SessionInfo, 
    AnalysisResult
)
from .config import ConfigManager
from .database import DatabaseConnection
from .memory import MemoryManager, TextVectorizer
from .analysis import MemoryAnalyzer
from .session import SessionManager

logger = logging.getLogger(__name__)


class SageCore(ISageService):
    """Sage 核心服务实现"""
    
    def __init__(self):
        """初始化核心服务"""
        self.config_manager: Optional[ConfigManager] = None
        self.db_connection: Optional[DatabaseConnection] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.session_manager: Optional[SessionManager] = None
        self.analyzer: Optional[MemoryAnalyzer] = None
        self._initialized = False
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化服务"""
        if self._initialized:
            return
        
        try:
            logger.info("正在初始化 Sage Core 服务...")
            
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            if config:
                # 更新配置
                for key, value in config.items():
                    self.config_manager.set(key, value)
            
            # 初始化数据库连接
            db_config = self.config_manager.get_database_config()
            self.db_connection = DatabaseConnection(db_config)
            await self.db_connection.connect()
            
            # 初始化向量化器
            embedding_config = self.config_manager.get_embedding_config()
            vectorizer = TextVectorizer(
                model_name=embedding_config.get('model', 'Qwen/Qwen3-Embedding-8B'),
                device=embedding_config.get('device', 'cpu')
            )
            
            # 初始化记忆管理器
            self.memory_manager = MemoryManager(self.db_connection, vectorizer)
            await self.memory_manager.initialize()
            
            # 初始化会话管理器
            self.session_manager = SessionManager(self.memory_manager)
            
            # 初始化分析器
            self.analyzer = MemoryAnalyzer(self.memory_manager)
            
            self._initialized = True
            logger.info("Sage Core 服务初始化完成")
            
        except Exception as e:
            logger.error(f"初始化服务失败：{e}")
            raise
    
    async def save_memory(self, content: MemoryContent) -> str:
        """保存记忆"""
        self._ensure_initialized()
        return await self.memory_manager.save(content)
    
    async def search_memory(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """搜索记忆"""
        self._ensure_initialized()
        return await self.memory_manager.search(query, options)
    
    async def get_context(self, query: str, max_results: int = 10) -> str:
        """获取相关上下文"""
        self._ensure_initialized()
        return await self.memory_manager.get_context(query, max_results)
    
    async def manage_session(self, action: str, session_id: Optional[str] = None) -> SessionInfo:
        """管理会话"""
        self._ensure_initialized()
        
        if action == "create":
            new_session_id = await self.session_manager.create_session()
            return await self._get_session_info(new_session_id)
        
        elif action == "switch":
            if not session_id:
                raise ValueError("切换会话需要提供 session_id")
            await self.session_manager.switch_session(session_id)
            return await self._get_session_info(session_id)
        
        elif action == "info":
            target_session = session_id or self.session_manager.current_session_id
            return await self._get_session_info(target_session)
        
        elif action == "list":
            sessions = await self.session_manager.list_sessions()
            # 返回当前会话信息，并附带会话列表
            current_info = await self._get_session_info(self.session_manager.current_session_id)
            current_info.metadata['all_sessions'] = sessions
            return current_info
        
        else:
            raise ValueError(f"未知的会话操作：{action}")
    
    async def analyze_memory(self, session_id: Optional[str] = None, 
                           analysis_type: str = "general") -> AnalysisResult:
        """分析记忆"""
        self._ensure_initialized()
        return await self.analyzer.analyze(session_id, analysis_type)
    
    async def generate_prompt(self, context: str, style: str = "default") -> str:
        """生成智能提示"""
        self._ensure_initialized()
        
        # 简单的提示生成逻辑
        if style == "question":
            prompts = [
                "基于以上信息，您还想了解什么？",
                "有什么具体的问题需要深入探讨吗？",
                "这些信息中哪个部分您最感兴趣？"
            ]
        elif style == "suggestion":
            prompts = [
                "也许您可以尝试...",
                "根据历史记录，建议您...",
                "下一步可以考虑..."
            ]
        else:  # default
            prompts = [
                "有什么我可以帮助您的吗？",
                "请告诉我您的想法。",
                "让我们继续探讨这个话题。"
            ]
        
        import random
        return random.choice(prompts)
    
    async def export_session(self, session_id: str, format: str = "json") -> bytes:
        """导出会话"""
        self._ensure_initialized()
        
        data = await self.memory_manager.export_session(session_id, format)
        
        if format == "json":
            import json
            return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        elif format == "markdown":
            return data.encode('utf-8')
        else:
            raise ValueError(f"不支持的导出格式：{format}")
    
    async def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            'initialized': self._initialized,
            'service': 'sage_core',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self._initialized:
            # 添加各组件状态
            status['components'] = {
                'config_manager': self.config_manager is not None,
                'database': self.db_connection is not None,
                'memory_manager': self.memory_manager is not None,
                'session_manager': self.session_manager is not None,
                'analyzer': self.analyzer is not None
            }
            
            # 添加当前会话信息
            if self.session_manager:
                status['current_session'] = self.session_manager.current_session_id
            
            # 添加统计信息
            try:
                stats = await self.memory_manager.storage.get_statistics()
                status['statistics'] = stats
            except:
                pass
        
        return status
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self.memory_manager:
            await self.memory_manager.cleanup()
        
        if self.db_connection:
            await self.db_connection.disconnect()
        
        self._initialized = False
        logger.info("Sage Core 服务已清理")
    
    def _ensure_initialized(self) -> None:
        """确保服务已初始化"""
        if not self._initialized:
            raise RuntimeError("服务未初始化，请先调用 initialize()")
    
    async def _get_session_info(self, session_id: str) -> SessionInfo:
        """获取会话信息并转换为 SessionInfo 对象"""
        info = await self.memory_manager.get_session_info(session_id)
        
        return SessionInfo(
            session_id=info['session_id'],
            created_at=datetime.fromisoformat(info['first_memory']) if info['first_memory'] else datetime.utcnow(),
            memory_count=info['memory_count'],
            last_active=datetime.fromisoformat(info['last_memory']) if info['last_memory'] else datetime.utcnow(),
            metadata={
                'is_current': info['is_current']
            }
        )