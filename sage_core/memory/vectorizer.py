#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vectorizer - 文本向量化处理 (使用 SiliconFlow 云端 API)
重构版本：完全基于云端 API，不加载本地模型
"""
import numpy as np
from typing import List, Union, Optional
import requests
import os
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class TextVectorizer:
    """文本向量化器 - 使用 SiliconFlow API"""
    
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-8B", 
                 device: str = "cpu"):
        """初始化向量化器
        
        Args:
            model_name: 模型名称 (用于 API 调用)
            device: 设备类型 (兼容参数，实际使用云端)
        """
        self.model_name = model_name
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY 环境变量未设置")
        self.base_url = "https://api.siliconflow.cn/v1"
        self._initialized = True
    
    async def initialize(self) -> None:
        """异步初始化（使用 API 无需加载模型）"""
        if self._initialized:
            return
        
        logger.info(f"使用 SiliconFlow API 进行向量化：{self.model_name}")
        self._initialized = True
    
    async def vectorize(self, text: Union[str, List[str]]) -> np.ndarray:
        """将文本转换为向量（使用 SiliconFlow API）
        
        Args:
            text: 输入文本或文本列表
            
        Returns:
            向量数组 (4096 维)
        """
        if not self._initialized:
            await self.initialize()
        
        # 确保输入是列表
        if isinstance(text, str):
            texts = [text]
            single_input = True
        else:
            texts = text
            single_input = False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 处理批量请求
            embeddings = []
            for t in texts:
                data = {
                    "model": self.model_name,
                    "input": t,
                    "encoding_format": "float"
                }
                
                response = requests.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                embedding = result['data'][0]['embedding']
                
                # 确保返回 4096 维向量
                if len(embedding) != 4096:
                    raise ValueError(f"期望 4096 维向量，但得到 {len(embedding)} 维")
                
                embeddings.append(embedding)
            
            # 转换为 numpy 数组
            embeddings_np = np.array(embeddings, dtype=np.float32)
            
            # 如果输入是单个文本，返回一维数组
            if single_input:
                return embeddings_np[0]
            
            return embeddings_np
            
        except Exception as e:
            logger.error(f"API 向量化失败：{e}")
            # 降级到哈希向量化，但使用 4096 维
            return self._hash_vectorize(text)
    
    def _hash_vectorize(self, text: Union[str, List[str]]) -> np.ndarray:
        """简单的哈希向量化（降级方案）
        
        Args:
            text: 输入文本
            
        Returns:
            4096维向量
        """
        if isinstance(text, str):
            texts = [text]
            single_input = True
        else:
            texts = text
            single_input = False
        
        vectors = []
        for t in texts:
            # 使用哈希函数生成固定长度向量
            hash_value = hash(t)
            np.random.seed(abs(hash_value) % (2**32))
            vector = np.random.randn(4096).astype(np.float32)
            # 归一化
            vector = vector / np.linalg.norm(vector)
            vectors.append(vector)
        
        result = np.array(vectors)
        if single_input:
            return result[0]
        return result
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return 4096  # Qwen3-Embedding-8B 的实际维度