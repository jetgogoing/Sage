#!/usr/bin/env python3
"""
Qwen3-Reranker-8B Integration Module
集成 Qwen3-Reranker-8B 重排序模型
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
import aiohttp
import json
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RerankingMode(Enum):
    """重排序模式"""
    FAST = "fast"           # 快速模式，批量小
    BALANCED = "balanced"   # 平衡模式
    QUALITY = "quality"     # 质量优先，批量大


@dataclass
class RerankingResult:
    """重排序结果"""
    index: int              # 原始索引
    score: float           # 重排序得分
    relevance_score: float # 相关性得分
    
    
class QwenReranker:
    """
    Qwen3-Reranker-8B 重排序器
    
    使用 SiliconFlow API 调用 Qwen3-Reranker 模型
    对检索结果进行神经网络重排序
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化重排序器"""
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY not found in environment")
            
        self.api_url = "https://api.siliconflow.cn/v1/rerank"
        self.model_name = "Qwen/Qwen3-Reranker-8B"
        
        # 配置参数
        self.config = {
            'max_batch_size': 20,       # 最大批处理大小
            'timeout': 30,              # API 超时时间
            'max_retries': 3,           # 最大重试次数
            'temperature': 0.01,        # 温度参数（低温度=更确定性）
        }
        
        logger.info(f"Qwen Reranker initialized with model: {self.model_name}")
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        mode: RerankingMode = RerankingMode.BALANCED,
        top_k: Optional[int] = None
    ) -> List[RerankingResult]:
        """
        对文档进行重排序
        
        Args:
            query: 查询字符串
            documents: 待排序的文档列表
            mode: 重排序模式
            top_k: 返回前 k 个结果（None 表示全部返回）
            
        Returns:
            排序后的结果列表
        """
        if not documents:
            return []
            
        # 根据模式调整批处理大小
        batch_size = self._get_batch_size(mode, len(documents))
        
        # 分批处理
        all_results = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_indices = list(range(i, min(i + batch_size, len(documents))))
            
            try:
                batch_results = await self._rerank_batch(query, batch, batch_indices)
                all_results.extend(batch_results)
            except Exception as e:
                logger.error(f"Reranking batch failed: {e}")
                # 失败时使用默认得分
                for idx, doc in zip(batch_indices, batch):
                    all_results.append(RerankingResult(
                        index=idx,
                        score=0.5,  # 默认中等得分
                        relevance_score=0.5
                    ))
        
        # 按得分排序
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # 返回 top_k 结果
        if top_k is not None and top_k < len(all_results):
            return all_results[:top_k]
        
        return all_results
    
    async def _rerank_batch(
        self,
        query: str,
        documents: List[str],
        indices: List[int]
    ) -> List[RerankingResult]:
        """重排序一个批次的文档"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 准备请求数据
        data = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
            "top_n": len(documents),  # 返回所有结果
            "return_documents": False   # 不返回原文档，节省流量
        }
        
        # 重试逻辑
        for attempt in range(self.config['max_retries']):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.config['timeout'])
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return self._parse_response(result, indices)
                        else:
                            error_text = await response.text()
                            logger.error(f"Reranking API error: {response.status} - {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"Reranking timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Reranking error on attempt {attempt + 1}: {e}")
            
            # 重试前等待
            if attempt < self.config['max_retries'] - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
        
        # 所有重试失败
        raise Exception("Reranking failed after all retries")
    
    def _parse_response(
        self,
        response: Dict[str, Any],
        indices: List[int]
    ) -> List[RerankingResult]:
        """解析 API 响应"""
        results = []
        
        # 响应格式：{"results": [{"index": 0, "relevance_score": 0.95}, ...]}
        rerank_results = response.get("results", [])
        
        for item in rerank_results:
            # 获取批次内索引
            batch_idx = item.get("index", 0)
            if batch_idx < len(indices):
                results.append(RerankingResult(
                    index=indices[batch_idx],
                    score=item.get("relevance_score", 0.0),
                    relevance_score=item.get("relevance_score", 0.0)
                ))
        
        return results
    
    def _get_batch_size(self, mode: RerankingMode, total_docs: int) -> int:
        """根据模式获取批处理大小"""
        if mode == RerankingMode.FAST:
            return min(5, total_docs)
        elif mode == RerankingMode.BALANCED:
            return min(10, total_docs)
        else:  # QUALITY
            return min(self.config['max_batch_size'], total_docs)
    
    async def rerank_with_scores(
        self,
        query: str,
        documents: List[Tuple[str, float]],
        fusion_weight: float = 0.7
    ) -> List[Tuple[int, float]]:
        """
        重排序并融合原始得分
        
        Args:
            query: 查询字符串
            documents: (文档内容, 原始得分) 列表
            fusion_weight: 重排序得分的权重 (0-1)
            
        Returns:
            (索引, 融合得分) 列表
        """
        if not documents:
            return []
        
        # 提取文档内容
        doc_contents = [doc[0] for doc in documents]
        original_scores = [doc[1] for doc in documents]
        
        # 执行重排序
        rerank_results = await self.rerank(
            query=query,
            documents=doc_contents,
            mode=RerankingMode.BALANCED
        )
        
        # 融合得分
        fused_results = []
        for result in rerank_results:
            idx = result.index
            if idx < len(original_scores):
                # 融合公式：final = w * rerank + (1-w) * original
                fused_score = (
                    fusion_weight * result.relevance_score +
                    (1 - fusion_weight) * original_scores[idx]
                )
                fused_results.append((idx, fused_score))
        
        # 按融合得分排序
        fused_results.sort(key=lambda x: x[1], reverse=True)
        
        return fused_results


class HybridReranker:
    """
    混合重排序器
    结合 Qwen3-Reranker 和多维度评分算法
    """
    
    def __init__(self, qwen_reranker: Optional[QwenReranker] = None):
        """初始化混合重排序器"""
        self.qwen_reranker = qwen_reranker or QwenReranker()
        
        # 融合策略配置
        self.fusion_configs = {
            'technical': {'neural': 0.6, 'hybrid': 0.4},      # 技术查询
            'diagnostic': {'neural': 0.7, 'hybrid': 0.3},     # 诊断查询
            'conversational': {'neural': 0.5, 'hybrid': 0.5}, # 对话查询
            'conceptual': {'neural': 0.65, 'hybrid': 0.35},   # 概念查询
            'default': {'neural': 0.6, 'hybrid': 0.4}
        }
    
    async def hybrid_rerank(
        self,
        query: str,
        retrieval_results: List[Dict[str, Any]],
        query_type: str = "default",
        enable_neural: bool = True
    ) -> List[Dict[str, Any]]:
        """
        混合重排序
        
        Args:
            query: 查询字符串
            retrieval_results: 智能检索结果
            query_type: 查询类型
            enable_neural: 是否启用神经网络重排序
            
        Returns:
            重排序后的结果
        """
        if not retrieval_results or not enable_neural:
            return retrieval_results
        
        try:
            # 准备文档和得分
            documents = []
            for i, result in enumerate(retrieval_results):
                doc_content = f"{result.get('role', '')}: {result.get('content', '')}"
                original_score = result.get('final_score', 0.5)
                documents.append((doc_content, original_score))
            
            # 获取融合权重
            fusion_config = self.fusion_configs.get(
                query_type.lower(),
                self.fusion_configs['default']
            )
            
            # 执行神经网络重排序
            rerank_indices = await self.qwen_reranker.rerank_with_scores(
                query=query,
                documents=documents,
                fusion_weight=fusion_config['neural']
            )
            
            # 重新排序结果
            reranked_results = []
            for idx, fused_score in rerank_indices:
                if idx < len(retrieval_results):
                    result = retrieval_results[idx].copy()
                    result['rerank_score'] = fused_score
                    result['rerank_applied'] = True
                    reranked_results.append(result)
            
            logger.info(f"Hybrid reranking completed: {len(reranked_results)} results")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Hybrid reranking failed: {e}")
            # 失败时返回原始结果
            return retrieval_results
    
    def get_fusion_config(self, query_type: str) -> Dict[str, float]:
        """获取融合配置"""
        return self.fusion_configs.get(
            query_type.lower(),
            self.fusion_configs['default']
        )
    
    def update_fusion_config(self, query_type: str, neural_weight: float):
        """更新融合配置"""
        if 0 <= neural_weight <= 1:
            self.fusion_configs[query_type.lower()] = {
                'neural': neural_weight,
                'hybrid': 1 - neural_weight
            }
            logger.info(f"Updated fusion config for {query_type}: neural={neural_weight}")


# 测试函数
async def test_reranker():
    """测试重排序器"""
    reranker = QwenReranker()
    
    query = "Python 中如何实现单例模式？"
    documents = [
        "Python 实现单例模式有多种方法，最常用的是使用 __new__ 方法。",
        "装饰器模式是一种结构型设计模式。",
        "单例模式确保一个类只有一个实例，可以使用元类实现。",
        "Python 的模块本身就是单例的。",
        "工厂模式用于创建对象。"
    ]
    
    results = await reranker.rerank(query, documents, top_k=3)
    
    print("Reranking results:")
    for result in results:
        print(f"  Index {result.index}: Score={result.score:.3f}")
        print(f"    Document: {documents[result.index][:50]}...")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_reranker())