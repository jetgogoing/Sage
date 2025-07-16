#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage Core Service Interface - 核心服务接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryContent:
    """记忆内容数据类"""
    user_input: str
    assistant_response: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None


@dataclass
class SearchOptions:
    """搜索选项数据类"""
    limit: int = 10
    strategy: str = "default"  # default, recent, semantic
    session_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@dataclass
class SessionInfo:
    """会话信息数据类"""
    session_id: str
    created_at: datetime
    memory_count: int
    last_active: datetime
    metadata: Dict[str, Any]


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    patterns: List[Dict[str, Any]]
    insights: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]


class ISageService(ABC):
    """Sage 核心服务接口"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化服务
        
        Args:
            config: 配置字典，包含数据库连接、模型配置等
        """
        pass
    
    @abstractmethod
    async def save_memory(self, content: MemoryContent) -> str:
        """保存记忆
        
        Args:
            content: 记忆内容
            
        Returns:
            memory_id: 记忆ID
        """
        pass
    
    @abstractmethod
    async def search_memory(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """搜索记忆
        
        Args:
            query: 搜索查询
            options: 搜索选项
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    async def get_context(self, query: str, max_results: int = 10) -> str:
        """获取相关上下文
        
        Args:
            query: 查询内容
            max_results: 最大结果数
            
        Returns:
            格式化的上下文文本
        """
        pass
    
    @abstractmethod
    async def manage_session(self, action: str, session_id: Optional[str] = None) -> SessionInfo:
        """管理会话
        
        Args:
            action: 动作类型 (create, switch, info, list)
            session_id: 会话ID
            
        Returns:
            会话信息
        """
        pass
    
    @abstractmethod
    async def analyze_memory(self, session_id: Optional[str] = None, 
                           analysis_type: str = "general") -> AnalysisResult:
        """分析记忆
        
        Args:
            session_id: 会话ID，None表示分析所有记忆
            analysis_type: 分析类型 (general, patterns, insights)
            
        Returns:
            分析结果
        """
        pass
    
    @abstractmethod
    async def generate_prompt(self, context: str, style: str = "default") -> str:
        """生成智能提示
        
        Args:
            context: 上下文信息
            style: 提示风格
            
        Returns:
            生成的提示文本
        """
        pass
    
    @abstractmethod
    async def export_session(self, session_id: str, format: str = "json") -> bytes:
        """导出会话
        
        Args:
            session_id: 会话ID
            format: 导出格式 (json, markdown, csv)
            
        Returns:
            导出的数据
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """获取服务状态
        
        Returns:
            状态信息字典
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass