#!/usr/bin/env python3
"""
向量化功能质量测试
测试SiliconFlow API连接、向量生成质量和检索准确性
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import aiohttp
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import get_config_manager
from memory_interface import get_memory_provider
from intelligent_retrieval import IntelligentRetrievalEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorizationQualityTest:
    """向量化质量测试类"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.api_key = self.config_manager.config.api_key
        self.base_url = "https://api.siliconflow.cn/v1"
        self.embedding_model = "Qwen/Qwen3-Embedding-8B"
        
        # 测试数据
        self.test_texts = [
            "Python是一种高级编程语言，具有简洁的语法。",
            "机器学习是人工智能的一个分支，专注于让计算机从数据中学习。",
            "数据库是存储和管理数据的系统。",
            "Web开发涉及创建网站和网络应用程序。",
            "算法是解决问题的一系列步骤。",
            "API是应用程序编程接口的缩写。",
            "云计算提供按需计算资源和服务。",
            "区块链是一种分布式账本技术。",
            "深度学习是机器学习的一个子集，使用神经网络。",
            "DevOps结合了开发和运维实践。"
        ]
        
        # 相似文本对（用于测试相似性）
        self.similar_pairs = [
            ("Python编程语言", "Python是一种编程语言"),
            ("机器学习算法", "ML算法和模型"),
            ("数据库系统", "数据存储系统"),
            ("网站开发", "Web应用开发"),
            ("深度神经网络", "深度学习网络")
        ]
        
        # 不相似文本对
        self.dissimilar_pairs = [
            ("Python编程", "汽车维修"),
            ("机器学习", "烹饪食谱"),
            ("数据库", "天气预报"),
            ("Web开发", "园艺种植"),
            ("算法设计", "音乐创作")
        ]
    
    async def test_api_connection(self) -> Dict[str, Any]:
        """测试SiliconFlow API连接"""
        logger.info("测试SiliconFlow API连接...")
        
        test_result = {
            'status': 'success',
            'response_time': 0,
            'api_available': False,
            'model_available': False,
            'error': None
        }
        
        if not self.api_key:
            test_result['status'] = 'error'
            test_result['error'] = 'API密钥未配置'
            return test_result
        
        try:
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                # 测试API基础连接
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        test_result['api_available'] = True
                        models_data = await response.json()
                        
                        # 检查嵌入模型是否可用
                        if 'data' in models_data:
                            model_ids = [model.get('id', '') for model in models_data['data']]
                            test_result['model_available'] = self.embedding_model in model_ids
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = f'API响应错误: {response.status}'
                
                end_time = datetime.now()
                test_result['response_time'] = (end_time - start_time).total_seconds()
            
            logger.info(f"API连接测试完成: {test_result['status']}")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
            logger.error(f"API连接测试失败: {e}")
            return test_result
    
    async def test_embedding_generation(self) -> Dict[str, Any]:
        """测试向量生成质量"""
        logger.info("测试向量生成质量...")
        
        test_result = {
            'status': 'success',
            'vectors_generated': 0,
            'average_response_time': 0,
            'dimension_check': False,
            'vector_quality_metrics': {},
            'errors': []
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                total_time = 0
                generated_vectors = []
                
                for i, text in enumerate(self.test_texts):
                    try:
                        start_time = datetime.now()
                        
                        payload = {
                            "model": self.embedding_model,
                            "input": text,
                            "encoding_format": "float"
                        }
                        
                        async with session.post(
                            f"{self.base_url}/embeddings",
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                embedding = data['data'][0]['embedding']
                                generated_vectors.append(embedding)
                                
                                end_time = datetime.now()
                                total_time += (end_time - start_time).total_seconds()
                                
                                # 检查向量维度
                                if len(embedding) == 4096:
                                    test_result['dimension_check'] = True
                                else:
                                    test_result['errors'].append(f"向量维度错误: {len(embedding)} != 4096")
                            else:
                                error_text = await response.text()
                                test_result['errors'].append(f"API请求失败 {i}: {response.status} - {error_text}")
                    
                    except Exception as e:
                        test_result['errors'].append(f"向量生成失败 {i}: {str(e)}")
                
                test_result['vectors_generated'] = len(generated_vectors)
                test_result['average_response_time'] = total_time / len(generated_vectors) if generated_vectors else 0
                
                # 分析向量质量
                if generated_vectors:
                    vectors_array = np.array(generated_vectors)
                    
                    test_result['vector_quality_metrics'] = {
                        'mean_magnitude': float(np.mean(np.linalg.norm(vectors_array, axis=1))),
                        'std_magnitude': float(np.std(np.linalg.norm(vectors_array, axis=1))),
                        'mean_cosine_similarity': float(np.mean(np.corrcoef(vectors_array))),
                        'vector_diversity': float(np.mean(np.std(vectors_array, axis=0)))
                    }
                
                if test_result['errors']:
                    test_result['status'] = 'warning' if generated_vectors else 'error'
                
                logger.info(f"向量生成测试完成: {test_result['vectors_generated']} 个向量")
                return test_result
                
        except Exception as e:
            test_result['status'] = 'error'
            test_result['errors'].append(f"测试过程出错: {str(e)}")
            logger.error(f"向量生成测试失败: {e}")
            return test_result
    
    async def test_similarity_accuracy(self) -> Dict[str, Any]:
        """测试相似性计算准确性"""
        logger.info("测试相似性计算准确性...")
        
        test_result = {
            'status': 'success',
            'similar_pairs_accuracy': 0,
            'dissimilar_pairs_accuracy': 0,
            'average_similar_score': 0,
            'average_dissimilar_score': 0,
            'threshold_analysis': {},
            'errors': []
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                async def get_embedding(text: str) -> List[float]:
                    payload = {
                        "model": self.embedding_model,
                        "input": text,
                        "encoding_format": "float"
                    }
                    
                    async with session.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data['data'][0]['embedding']
                        else:
                            raise Exception(f"API请求失败: {response.status}")
                
                def cosine_similarity(a: List[float], b: List[float]) -> float:
                    a = np.array(a)
                    b = np.array(b)
                    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
                
                # 测试相似文本对
                similar_scores = []
                for text1, text2 in self.similar_pairs:
                    try:
                        emb1 = await get_embedding(text1)
                        emb2 = await get_embedding(text2)
                        score = cosine_similarity(emb1, emb2)
                        similar_scores.append(score)
                    except Exception as e:
                        test_result['errors'].append(f"相似文本对测试失败: {e}")
                
                # 测试不相似文本对
                dissimilar_scores = []
                for text1, text2 in self.dissimilar_pairs:
                    try:
                        emb1 = await get_embedding(text1)
                        emb2 = await get_embedding(text2)
                        score = cosine_similarity(emb1, emb2)
                        dissimilar_scores.append(score)
                    except Exception as e:
                        test_result['errors'].append(f"不相似文本对测试失败: {e}")
                
                # 计算准确性
                if similar_scores:
                    test_result['average_similar_score'] = float(np.mean(similar_scores))
                    # 相似文本应该有较高的相似度分数（> 0.7）
                    similar_correct = sum(1 for score in similar_scores if score > 0.7)
                    test_result['similar_pairs_accuracy'] = similar_correct / len(similar_scores)
                
                if dissimilar_scores:
                    test_result['average_dissimilar_score'] = float(np.mean(dissimilar_scores))
                    # 不相似文本应该有较低的相似度分数（< 0.5）
                    dissimilar_correct = sum(1 for score in dissimilar_scores if score < 0.5)
                    test_result['dissimilar_pairs_accuracy'] = dissimilar_correct / len(dissimilar_scores)
                
                # 阈值分析
                all_scores = similar_scores + dissimilar_scores
                if all_scores:
                    test_result['threshold_analysis'] = {
                        'min_score': float(np.min(all_scores)),
                        'max_score': float(np.max(all_scores)),
                        'mean_score': float(np.mean(all_scores)),
                        'recommended_threshold': 0.6  # 基于经验的推荐阈值
                    }
                
                overall_accuracy = (test_result['similar_pairs_accuracy'] + test_result['dissimilar_pairs_accuracy']) / 2
                if overall_accuracy < 0.8:
                    test_result['status'] = 'warning'
                
                logger.info(f"相似性测试完成，总体准确率: {overall_accuracy:.3f}")
                return test_result
                
        except Exception as e:
            test_result['status'] = 'error'
            test_result['errors'].append(f"相似性测试失败: {str(e)}")
            logger.error(f"相似性测试失败: {e}")
            return test_result
    
    async def test_retrieval_system(self) -> Dict[str, Any]:
        """测试检索系统完整性"""
        logger.info("测试检索系统完整性...")
        
        test_result = {
            'status': 'success',
            'memory_provider_available': False,
            'intelligent_retrieval_available': False,
            'sample_retrieval_test': {},
            'performance_metrics': {},
            'errors': []
        }
        
        try:
            # 测试memory provider
            try:
                memory_provider = get_memory_provider()
                stats = memory_provider.get_memory_stats()
                test_result['memory_provider_available'] = True
                test_result['memory_stats'] = stats
            except Exception as e:
                test_result['errors'].append(f"Memory provider不可用: {e}")
            
            # 测试intelligent retrieval
            try:
                if test_result['memory_provider_available']:
                    retrieval_engine = IntelligentRetrievalEngine(memory_provider)
                    test_result['intelligent_retrieval_available'] = True
                    
                    # 简单检索测试
                    test_query = "Python编程"
                    start_time = datetime.now()
                    
                    results = await retrieval_engine.retrieve_relevant_context(
                        query=test_query,
                        k=5
                    )
                    
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    
                    test_result['sample_retrieval_test'] = {
                        'query': test_query,
                        'results_count': len(results),
                        'response_time': response_time,
                        'has_scores': len(results) > 0 and hasattr(results[0], 'score')
                    }
                    
                    test_result['performance_metrics'] = {
                        'retrieval_response_time': response_time,
                        'results_per_query': len(results)
                    }
                    
            except Exception as e:
                test_result['errors'].append(f"Intelligent retrieval测试失败: {e}")
            
            if test_result['errors']:
                test_result['status'] = 'warning'
            
            logger.info("检索系统测试完成")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['errors'].append(f"检索系统测试失败: {str(e)}")
            logger.error(f"检索系统测试失败: {e}")
            return test_result
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合测试"""
        logger.info("开始综合向量化质量测试...")
        
        comprehensive_result = {
            'test_timestamp': datetime.now().isoformat(),
            'overall_status': 'success',
            'test_results': {},
            'summary': {},
            'recommendations': []
        }
        
        # 运行所有测试
        tests = [
            ('api_connection', self.test_api_connection),
            ('embedding_generation', self.test_embedding_generation),
            ('similarity_accuracy', self.test_similarity_accuracy),
            ('retrieval_system', self.test_retrieval_system)
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"执行测试: {test_name}")
                result = await test_func()
                comprehensive_result['test_results'][test_name] = result
                
                if result['status'] == 'error':
                    comprehensive_result['overall_status'] = 'error'
                elif result['status'] == 'warning' and comprehensive_result['overall_status'] != 'error':
                    comprehensive_result['overall_status'] = 'warning'
                    
            except Exception as e:
                logger.error(f"测试 {test_name} 执行失败: {e}")
                comprehensive_result['test_results'][test_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                comprehensive_result['overall_status'] = 'error'
        
        # 生成总结和建议
        comprehensive_result['summary'] = self._generate_summary(comprehensive_result['test_results'])
        comprehensive_result['recommendations'] = self._generate_recommendations(comprehensive_result['test_results'])
        
        logger.info(f"综合测试完成，总体状态: {comprehensive_result['overall_status']}")
        return comprehensive_result
    
    def _generate_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试总结"""
        summary = {
            'tests_passed': 0,
            'tests_warning': 0,
            'tests_failed': 0,
            'key_metrics': {}
        }
        
        for test_name, result in test_results.items():
            if result['status'] == 'success':
                summary['tests_passed'] += 1
            elif result['status'] == 'warning':
                summary['tests_warning'] += 1
            else:
                summary['tests_failed'] += 1
        
        # 提取关键指标
        if 'embedding_generation' in test_results:
            eg_result = test_results['embedding_generation']
            summary['key_metrics']['vectors_generated'] = eg_result.get('vectors_generated', 0)
            summary['key_metrics']['avg_generation_time'] = eg_result.get('average_response_time', 0)
        
        if 'similarity_accuracy' in test_results:
            sa_result = test_results['similarity_accuracy']
            summary['key_metrics']['similarity_accuracy'] = (
                sa_result.get('similar_pairs_accuracy', 0) + 
                sa_result.get('dissimilar_pairs_accuracy', 0)
            ) / 2
        
        return summary
    
    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # API连接建议
        if 'api_connection' in test_results:
            api_result = test_results['api_connection']
            if api_result['status'] == 'error':
                recommendations.append("检查SILICONFLOW_API_KEY配置和网络连接")
            elif not api_result.get('model_available', False):
                recommendations.append(f"确认{self.embedding_model}模型在API中可用")
        
        # 向量生成建议
        if 'embedding_generation' in test_results:
            eg_result = test_results['embedding_generation']
            if eg_result.get('average_response_time', 0) > 2.0:
                recommendations.append("向量生成响应时间较慢，考虑优化网络或使用更快的模型")
            if not eg_result.get('dimension_check', False):
                recommendations.append("向量维度验证失败，检查模型配置")
        
        # 相似性准确性建议
        if 'similarity_accuracy' in test_results:
            sa_result = test_results['similarity_accuracy']
            accuracy = (sa_result.get('similar_pairs_accuracy', 0) + sa_result.get('dissimilar_pairs_accuracy', 0)) / 2
            if accuracy < 0.8:
                recommendations.append("相似性检测准确率较低，考虑调整相似度阈值或使用不同的嵌入模型")
        
        # 检索系统建议
        if 'retrieval_system' in test_results:
            rs_result = test_results['retrieval_system']
            if not rs_result.get('memory_provider_available', False):
                recommendations.append("Memory provider不可用，检查数据库连接和配置")
            if not rs_result.get('intelligent_retrieval_available', False):
                recommendations.append("智能检索系统不可用，检查相关组件配置")
        
        if not recommendations:
            recommendations.append("所有测试通过，系统运行正常")
        
        return recommendations

# CLI接口
async def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='向量化功能质量测试')
    parser.add_argument('--output', '-o', help='输出结果到文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = VectorizationQualityTest()
    result = await tester.run_comprehensive_test()
    
    # 输出结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"测试结果已保存到: {args.output}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 返回适当的退出码
    if result['overall_status'] == 'error':
        sys.exit(1)
    elif result['overall_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == '__main__':
    asyncio.run(main())