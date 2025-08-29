#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vectorizer - 文本向量化处理
"""
import numpy as np
from typing import List, Union, Optional
from transformers import AutoTokenizer, AutoModel
import torch
import logging

logger = logging.getLogger(__name__)


class TextVectorizer:
    """文本向量化器"""
    
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-8B", 
                 device: str = "cpu"):
        """初始化向量化器
        
        Args:
            model_name: 模型名称
            device: 设备类型 (cpu/cuda)
        """
        self.model_name = model_name
        self.device = device
        self.tokenizer = None
        self.model = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """异步初始化模型"""
        if self._initialized:
            return
        
        try:
            logger.info(f"正在加载向量化模型：{self.model_name}")
            
            # 加载分词器和模型
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            
            # 移动到指定设备
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.cuda()
            else:
                self.device = "cpu"
                self.model = self.model.cpu()
            
            self.model.eval()
            self._initialized = True
            
            logger.info(f"向量化模型加载成功，设备：{self.device}")
            
        except Exception as e:
            logger.error(f"加载向量化模型失败：{e}")
            # 降级到简单的哈希向量化
            logger.warning("降级到哈希向量化模式")
            self._initialized = True
    
    async def vectorize(self, text: Union[str, List[str]]) -> np.ndarray:
        """将文本转换为向量
        
        Args:
            text: 输入文本或文本列表
            
        Returns:
            向量数组
        """
        if not self._initialized:
            await self.initialize()
        
        # 如果模型加载失败，使用哈希向量化
        if self.model is None:
            return self._hash_vectorize(text)
        
        # 确保输入是列表
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text
        
        try:
            # 分词
            inputs = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            
            # 移动到设备
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # 获取嵌入
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1)
            
            # 转换为numpy数组
            embeddings_np = embeddings.cpu().numpy()
            
            # 如果输入是单个文本，返回一维数组
            if isinstance(text, str):
                return embeddings_np[0]
            
            return embeddings_np
            
        except Exception as e:
            logger.error(f"向量化失败：{e}")
            return self._hash_vectorize(text)
    
    def _hash_vectorize(self, text: Union[str, List[str]]) -> np.ndarray:
        """简单的哈希向量化（降级方案）
        
        Args:
            text: 输入文本
            
        Returns:
            768维向量
        """
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text
        
        vectors = []
        for t in texts:
            # 使用哈希函数生成固定长度向量
            hash_value = hash(t)
            np.random.seed(abs(hash_value) % (2**32))
            vector = np.random.randn(768).astype(np.float32)
            # 归一化
            vector = vector / np.linalg.norm(vector)
            vectors.append(vector)
        
        result = np.array(vectors)
        if isinstance(text, str):
            return result[0]
        return result
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return 768  # Qwen3-Embedding-8B 的维度