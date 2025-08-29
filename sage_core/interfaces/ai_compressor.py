#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Compressor Interface - AI压缩抽象接口
提供统一的AI压缩服务接口，支持多种AI模型实现
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AICompressor(ABC):
    """AI压缩器抽象基类"""
    
    @abstractmethod
    async def compress_context(self, prompt_template: str, context_chunks: List[str], 
                              user_query: str, **kwargs) -> str:
        """压缩上下文内容
        
        Args:
            prompt_template: 压缩提示模板
            context_chunks: 检索到的上下文片段
            user_query: 用户原始查询
            **kwargs: 额外参数
            
        Returns:
            压缩后的上下文文本
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化压缩器"""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息（可选实现）
        
        Returns:
            模型信息字典
        """
        return {
            "provider": "unknown",
            "model": "unknown",
            "version": "unknown"
        }