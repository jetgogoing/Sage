#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reranker - 语义重排服务 (使用 SiliconFlow 云端 API)
用于优化召回结果，减少 token 消耗
"""
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
import requests
import os
import logging
import asyncio
import json
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)


class RerankerCache:
    """简单的 LRU 缓存实现"""
    
    def __init__(self, max_size: int = 100, ttl_minutes: int = 30):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, key: str) -> Optional[List[float]]:
        """获取缓存值"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                # 移到最后（LRU）
                self.cache.move_to_end(key)
                return value
            else:
                # 过期删除
                del self.cache[key]
        return None
    
    def set(self, key: str, value: List[float]) -> None:
        """设置缓存值"""
        self.cache[key] = (value, datetime.now())
        self.cache.move_to_end(key)
        
        # 超过大小限制时删除最旧的
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)


class TextReranker:
    """文本重排器 - 使用 SiliconFlow API"""
    
    def __init__(self, 
                 model_name: str = "Qwen/Qwen3-Reranker-8B",
                 api_key: Optional[str] = None):
        """初始化重排器
        
        Args:
            model_name: 模型名称
            api_key: API 密钥（优先使用参数，其次环境变量）
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY 未设置")
        
        self.base_url = "https://api.siliconflow.cn/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 初始化缓存
        self.cache = RerankerCache()
        
        # 性能统计
        self.stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "total_latency": 0.0
        }
    
    async def rerank(self, 
                    query: str, 
                    documents: List[str],
                    top_k: Optional[int] = None,
                    return_scores: bool = False) -> Union[List[str], List[Tuple[str, float]]]:
        """对文档进行重排
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            top_k: 返回前 k 个结果（None 表示返回全部）
            return_scores: 是否返回分数
            
        Returns:
            重排后的文档列表，或 (文档, 分数) 元组列表
        """
        self.stats["total_calls"] += 1
        start_time = datetime.now()
        
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(query, documents)
            
            # 尝试从缓存获取
            cached_scores = self.cache.get(cache_key)
            if cached_scores:
                self.stats["cache_hits"] += 1
                logger.info(f"[Reranker] 缓存命中")
                scores = cached_scores
            else:
                # 调用 API
                scores = await self._call_rerank_api(query, documents)
                # 保存到缓存
                self.cache.set(cache_key, scores)
                self.stats["api_calls"] += 1
            
            # 排序
            doc_scores = list(zip(documents, scores))
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 截取 top_k
            if top_k:
                doc_scores = doc_scores[:top_k]
            
            # 记录延迟
            latency = (datetime.now() - start_time).total_seconds()
            self.stats["total_latency"] += latency
            logger.info(f"[Reranker] 重排完成：{len(documents)}→{len(doc_scores)}，耗时 {latency:.2f}s")
            
            # 返回结果
            if return_scores:
                return doc_scores
            else:
                return [doc for doc, _ in doc_scores]
                
        except Exception as e:
            logger.error(f"[Reranker] 重排失败：{e}")
            # 降级处理：按原顺序返回
            if top_k:
                documents = documents[:top_k]
            if return_scores:
                # 使用简单的长度相似度作为分数
                scores = [self._simple_similarity(query, doc) for doc in documents]
                return list(zip(documents, scores))
            return documents
    
    async def _call_rerank_api(self, query: str, documents: List[str]) -> List[float]:
        """调用重排 API
        
        Args:
            query: 查询文本
            documents: 文档列表
            
        Returns:
            每个文档的相关性分数
        """
        # 构建请求
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
            "return_documents": False,
            "top_n": len(documents)  # 返回所有文档的分数
        }
        
        # 发送请求
        async with asyncio.timeout(30):  # 30秒超时
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/rerank",
                    json=payload,
                    headers=self.headers,
                    timeout=30
                )
            )
        
        if response.status_code != 200:
            raise Exception(f"API 调用失败：{response.status_code} - {response.text}")
        
        # 解析结果
        result = response.json()
        
        # 提取分数
        if "results" in result:
            # 按文档顺序返回分数
            scores = [0.0] * len(documents)
            for item in result["results"]:
                idx = item.get("index", 0)
                score = item.get("relevance_score", 0.0)
                if 0 <= idx < len(scores):
                    scores[idx] = score
            return scores
        else:
            raise Exception(f"API 返回格式错误：{result}")
    
    def _generate_cache_key(self, query: str, documents: List[str]) -> str:
        """生成缓存键"""
        # 使用查询和文档的前 50 个字符生成键
        doc_preview = "|".join([doc[:50] for doc in documents])
        content = f"{query}||{doc_preview}"
        # 简单哈希
        return str(hash(content))
    
    def _simple_similarity(self, query: str, document: str) -> float:
        """简单的相似度计算（降级用）"""
        # 基于共同词的简单相似度
        query_words = set(query.lower().split())
        doc_words = set(document.lower().split())
        
        if not query_words or not doc_words:
            return 0.0
        
        intersection = query_words & doc_words
        union = query_words | doc_words
        
        return len(intersection) / len(union)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        total = self.stats["total_calls"]
        if total == 0:
            return self.stats
            
        return {
            **self.stats,
            "cache_hit_rate": self.stats["cache_hits"] / total,
            "avg_latency": self.stats["total_latency"] / total
        }


async def test_reranker():
    """测试 Reranker"""
    reranker = TextReranker()
    
    query = "如何优化数据库查询性能"
    documents = [
        "使用索引可以显著提升查询速度",
        "今天天气很好",
        "查询优化的关键是理解执行计划",
        "数据库性能调优需要考虑多个因素",
        "我喜欢吃苹果"
    ]
    
    # 测试重排
    print("测试基本重排...")
    ranked_docs = await reranker.rerank(query, documents, top_k=3)
    for i, doc in enumerate(ranked_docs):
        print(f"{i+1}. {doc}")
    
    # 测试带分数的重排
    print("\n测试带分数重排...")
    ranked_with_scores = await reranker.rerank(query, documents, top_k=3, return_scores=True)
    for i, (doc, score) in enumerate(ranked_with_scores):
        print(f"{i+1}. {doc} (分数: {score:.3f})")
    
    # 测试缓存
    print("\n测试缓存...")
    await reranker.rerank(query, documents)  # 应该命中缓存
    
    # 打印统计
    print("\n性能统计:")
    stats = reranker.get_stats()
    print(f"总调用: {stats['total_calls']}")
    print(f"缓存命中: {stats['cache_hits']} ({stats['cache_hit_rate']:.1%})")
    print(f"API 调用: {stats['api_calls']}")
    print(f"平均延迟: {stats['avg_latency']:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_reranker())