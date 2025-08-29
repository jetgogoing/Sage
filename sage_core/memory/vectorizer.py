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
    
    async def vectorize(self, text: Union[str, List[str]], enable_chunking: bool = True, chunk_size: int = 8000) -> np.ndarray:
        """将文本转换为向量（使用 SiliconFlow API）
        
        Args:
            text: 输入文本或文本列表
            enable_chunking: 是否启用智能分块
            chunk_size: 单个块的大小（字符数）
            
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
        
        # 处理超长文本的分块向量化
        all_embeddings = []
        for t in texts:
            if enable_chunking and len(t) > chunk_size:
                # 智能分块处理
                chunks = self._smart_chunk_text(t, chunk_size)
                chunk_embeddings = []
                
                for chunk in chunks:
                    chunk_embedding = await self._vectorize_single_text(chunk)
                    chunk_embeddings.append(chunk_embedding)
                
                # 聚合块向量（取平均值）
                aggregated_embedding = np.mean(chunk_embeddings, axis=0)
                all_embeddings.append(aggregated_embedding)
                
                logger.info(f"长文本分块处理：{len(chunks)}个块，原文本{len(t)}字符")
            else:
                # 正常单文本向量化
                embedding = await self._vectorize_single_text(t)
                all_embeddings.append(embedding)
        
        # 转换为 numpy 数组
        embeddings_np = np.array(all_embeddings, dtype=np.float32)
        
        # 如果输入是单个文本，返回一维数组
        if single_input:
            return embeddings_np[0]
        
        return embeddings_np
    
    async def _vectorize_single_text(self, text: str) -> np.ndarray:
        """向量化单个文本（内部方法）"""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_name,
                "input": text,
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
            
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"API 向量化失败：{e}")
            # 降级到哈希向量化，但使用 4096 维
            return self._hash_vectorize_single(text)
    
    def _smart_chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """智能分块文本，保持语义完整性"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        
        # 优先按段落分割
        paragraphs = text.split('\n\n')
        
        # 特殊情况：如果没有段落分隔符且文本超长，强制按长度分割
        if len(paragraphs) == 1 and len(text) > chunk_size:
            # 没有段落分隔符的长文本，强制按字符长度分割
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())
            return chunks
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 如果单个段落就超过限制，按句子分割
            if len(paragraph) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # 按句子分割大段落
                sentences = self._split_sentences(paragraph)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += sentence
                
                # 如果句子分割后仍然过长，强制按长度分割
                if len(current_chunk) > chunk_size:
                    for i in range(0, len(current_chunk), chunk_size):
                        chunk = current_chunk[i:i + chunk_size]
                        if chunk.strip():
                            chunks.append(chunk.strip())
                    current_chunk = ""
            else:
                # 正常段落处理
                if len(current_chunk) + len(paragraph) > chunk_size:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    current_chunk += ("\n\n" if current_chunk else "") + paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        import re
        # 简单的句子分割规则
        sentences = re.split(r'[.!?\u3002\uff01\uff1f]+', text)
        return [s.strip() + '.' for s in sentences if s.strip()]
    
    def _hash_vectorize_single(self, text: str) -> np.ndarray:
        """单个文本的哈希向量化（降级方案）"""
        # 使用哈希函数生成固定长度向量
        hash_value = hash(text)
        np.random.seed(abs(hash_value) % (2**32))
        vector = np.random.randn(4096).astype(np.float32)
        # 归一化
        vector = vector / np.linalg.norm(vector)
        return vector
    
    def _hash_vectorize(self, text: Union[str, List[str]]) -> np.ndarray:
        """简单的哈希向量化（降级方案） - 兼容性保留
        
        Args:
            text: 输入文本
            
        Returns:
            4096维向量
        """
        if isinstance(text, str):
            return self._hash_vectorize_single(text)
        else:
            vectors = [self._hash_vectorize_single(t) for t in text]
            return np.array(vectors)
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return 4096  # Qwen3-Embedding-8B 的实际维度