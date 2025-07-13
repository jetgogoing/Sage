#!/usr/bin/env python3
"""
数据库性能测试工具
测试数据库查询性能、索引效率和向量检索速度
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import asyncpg
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import get_config_manager
from memory_interface import get_memory_provider

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabasePerformanceTest:
    """数据库性能测试类"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.db_config = self.config_manager.config.db_config
        
        # 性能测试参数
        self.test_iterations = 100
        self.batch_sizes = [1, 10, 50, 100]
        self.vector_query_limits = [5, 10, 20, 50]
        
    async def get_db_connection(self) -> asyncpg.Connection:
        """获取数据库连接"""
        try:
            conn = await asyncpg.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.database,
                user=self.db_config.user,
                password=self.db_config.password
            )
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    async def test_basic_queries(self) -> Dict[str, Any]:
        """测试基础查询性能"""
        logger.info("测试基础查询性能...")
        
        test_result = {
            'status': 'success',
            'query_tests': {},
            'errors': []
        }
        
        conn = await self.get_db_connection()
        
        try:
            # 测试不同的查询类型
            queries = {
                'count_all': "SELECT COUNT(*) FROM conversations",
                'count_with_embedding': "SELECT COUNT(*) FROM conversations WHERE embedding IS NOT NULL",
                'recent_records': "SELECT * FROM conversations ORDER BY created_at DESC LIMIT 10",
                'session_count': "SELECT COUNT(DISTINCT session_id) FROM conversations",
                'role_distribution': "SELECT role, COUNT(*) FROM conversations GROUP BY role"
            }
            
            for query_name, sql in queries.items():
                try:
                    # 预热查询
                    await conn.fetch(sql)
                    
                    # 性能测试
                    start_time = time.time()
                    for _ in range(10):
                        await conn.fetch(sql)
                    end_time = time.time()
                    
                    avg_time = (end_time - start_time) / 10
                    
                    test_result['query_tests'][query_name] = {
                        'sql': sql,
                        'average_time': avg_time,
                        'status': 'success'
                    }
                    
                except Exception as e:
                    test_result['query_tests'][query_name] = {
                        'sql': sql,
                        'status': 'error',
                        'error': str(e)
                    }
                    test_result['errors'].append(f"查询 {query_name} 失败: {e}")
            
            # 检查是否有错误
            if test_result['errors']:
                test_result['status'] = 'warning'
            
            logger.info("基础查询性能测试完成")
            return test_result
            
        finally:
            await conn.close()
    
    async def test_vector_search_performance(self) -> Dict[str, Any]:
        """测试向量检索性能"""
        logger.info("测试向量检索性能...")
        
        test_result = {
            'status': 'success',
            'vector_tests': {},
            'performance_summary': {},
            'errors': []
        }
        
        conn = await self.get_db_connection()
        
        try:
            # 检查是否有向量数据
            vector_count = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE embedding IS NOT NULL"
            )
            
            if vector_count == 0:
                test_result['status'] = 'warning'
                test_result['errors'].append("数据库中没有向量数据，跳过向量检索测试")
                return test_result
            
            # 获取一个示例向量用于测试
            sample_vector = await conn.fetchval(
                "SELECT embedding FROM conversations WHERE embedding IS NOT NULL LIMIT 1"
            )
            
            if not sample_vector:
                test_result['status'] = 'error'
                test_result['errors'].append("无法获取示例向量")
                return test_result
            
            # 测试不同的检索限制
            for limit in self.vector_query_limits:
                test_name = f"vector_search_limit_{limit}"
                
                try:
                    # 预热查询
                    await conn.fetch("""
                        SELECT id, role, content, 
                               (embedding <=> $1) as distance
                        FROM conversations 
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> $1
                        LIMIT $2
                    """, sample_vector, limit)
                    
                    # 性能测试
                    times = []
                    for _ in range(10):
                        start_time = time.time()
                        
                        results = await conn.fetch("""
                            SELECT id, role, content, 
                                   (embedding <=> $1) as distance
                            FROM conversations 
                            WHERE embedding IS NOT NULL
                            ORDER BY embedding <=> $1
                            LIMIT $2
                        """, sample_vector, limit)
                        
                        end_time = time.time()
                        times.append(end_time - start_time)
                    
                    test_result['vector_tests'][test_name] = {
                        'limit': limit,
                        'average_time': np.mean(times),
                        'min_time': np.min(times),
                        'max_time': np.max(times),
                        'std_time': np.std(times),
                        'results_count': len(results),
                        'status': 'success'
                    }
                    
                except Exception as e:
                    test_result['vector_tests'][test_name] = {
                        'limit': limit,
                        'status': 'error',
                        'error': str(e)
                    }
                    test_result['errors'].append(f"向量检索测试 {test_name} 失败: {e}")
            
            # 生成性能总结
            successful_tests = [
                test for test in test_result['vector_tests'].values() 
                if test['status'] == 'success'
            ]
            
            if successful_tests:
                avg_times = [test['average_time'] for test in successful_tests]
                test_result['performance_summary'] = {
                    'overall_avg_time': np.mean(avg_times),
                    'fastest_query': np.min(avg_times),
                    'slowest_query': np.max(avg_times),
                    'performance_rating': self._rate_performance(np.mean(avg_times))
                }
            
            if test_result['errors']:
                test_result['status'] = 'warning'
            
            logger.info("向量检索性能测试完成")
            return test_result
            
        finally:
            await conn.close()
    
    async def test_index_efficiency(self) -> Dict[str, Any]:
        """测试索引效率"""
        logger.info("测试索引效率...")
        
        test_result = {
            'status': 'success',
            'index_tests': {},
            'index_usage_analysis': {},
            'errors': []
        }
        
        conn = await self.get_db_connection()
        
        try:
            # 检查现有索引
            indexes = await conn.fetch("""
                SELECT 
                    indexname, 
                    indexdef,
                    schemaname,
                    tablename
                FROM pg_indexes 
                WHERE tablename = 'conversations'
                ORDER BY indexname
            """)
            
            test_result['existing_indexes'] = [dict(idx) for idx in indexes]
            
            # 测试索引使用情况的查询
            index_test_queries = {
                'session_id_lookup': {
                    'sql': "SELECT * FROM conversations WHERE session_id = $1",
                    'uses_index': 'idx_conversations_session_id'
                },
                'time_range_query': {
                    'sql': "SELECT * FROM conversations WHERE created_at >= $1 ORDER BY created_at DESC",
                    'uses_index': 'idx_conversations_created_at'
                },
                'vector_similarity': {
                    'sql': "SELECT * FROM conversations WHERE embedding IS NOT NULL ORDER BY embedding <=> $1 LIMIT 5",
                    'uses_index': 'idx_conversations_embedding'
                }
            }
            
            # 获取测试数据
            sample_session = await conn.fetchval("SELECT session_id FROM conversations LIMIT 1")
            recent_time = datetime.now() - timedelta(days=7)
            sample_vector = await conn.fetchval(
                "SELECT embedding FROM conversations WHERE embedding IS NOT NULL LIMIT 1"
            )
            
            for test_name, query_info in index_test_queries.items():
                try:
                    # 准备查询参数
                    if test_name == 'session_id_lookup':
                        params = [sample_session] if sample_session else [None]
                    elif test_name == 'time_range_query':
                        params = [recent_time]
                    elif test_name == 'vector_similarity':
                        params = [sample_vector] if sample_vector else [None]
                    else:
                        params = []
                    
                    if None in params:
                        test_result['index_tests'][test_name] = {
                            'status': 'skipped',
                            'reason': 'No test data available'
                        }
                        continue
                    
                    # 分析查询计划
                    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS) {query_info['sql']}"
                    explain_result = await conn.fetch(explain_sql, *params)
                    
                    plan_text = '\n'.join([row[0] for row in explain_result])
                    
                    # 执行性能测试
                    times = []
                    for _ in range(5):
                        start_time = time.time()
                        await conn.fetch(query_info['sql'], *params)
                        end_time = time.time()
                        times.append(end_time - start_time)
                    
                    # 检查是否使用了预期的索引
                    index_used = query_info['uses_index'] in plan_text
                    
                    test_result['index_tests'][test_name] = {
                        'average_time': np.mean(times),
                        'index_used': index_used,
                        'expected_index': query_info['uses_index'],
                        'execution_plan': plan_text,
                        'status': 'success'
                    }
                    
                except Exception as e:
                    test_result['index_tests'][test_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    test_result['errors'].append(f"索引测试 {test_name} 失败: {e}")
            
            # 分析索引使用情况
            successful_tests = [
                test for test in test_result['index_tests'].values() 
                if test['status'] == 'success'
            ]
            
            if successful_tests:
                index_usage_rate = sum(1 for test in successful_tests if test.get('index_used', False)) / len(successful_tests)
                avg_query_time = np.mean([test['average_time'] for test in successful_tests])
                
                test_result['index_usage_analysis'] = {
                    'index_usage_rate': index_usage_rate,
                    'average_query_time': avg_query_time,
                    'total_indexes': len(test_result['existing_indexes']),
                    'performance_rating': self._rate_performance(avg_query_time)
                }
            
            if test_result['errors']:
                test_result['status'] = 'warning'
            
            logger.info("索引效率测试完成")
            return test_result
            
        finally:
            await conn.close()
    
    async def test_concurrent_performance(self) -> Dict[str, Any]:
        """测试并发性能"""
        logger.info("测试并发性能...")
        
        test_result = {
            'status': 'success',
            'concurrency_tests': {},
            'errors': []
        }
        
        try:
            # 测试不同并发级别
            concurrency_levels = [1, 5, 10, 20]
            
            for concurrency in concurrency_levels:
                test_name = f"concurrent_{concurrency}"
                
                try:
                    # 创建并发任务
                    async def query_task():
                        conn = await self.get_db_connection()
                        try:
                            start_time = time.time()
                            
                            # 执行一系列查询
                            await conn.fetch("SELECT COUNT(*) FROM conversations")
                            await conn.fetch("SELECT * FROM conversations ORDER BY created_at DESC LIMIT 5")
                            
                            # 如果有向量数据，执行向量查询
                            sample_vector = await conn.fetchval(
                                "SELECT embedding FROM conversations WHERE embedding IS NOT NULL LIMIT 1"
                            )
                            if sample_vector:
                                await conn.fetch("""
                                    SELECT * FROM conversations 
                                    WHERE embedding IS NOT NULL
                                    ORDER BY embedding <=> $1 
                                    LIMIT 3
                                """, sample_vector)
                            
                            end_time = time.time()
                            return end_time - start_time
                            
                        finally:
                            await conn.close()
                    
                    # 执行并发测试
                    start_time = time.time()
                    
                    tasks = [query_task() for _ in range(concurrency)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    # 分析结果
                    successful_results = [r for r in results if isinstance(r, float)]
                    failed_results = [r for r in results if isinstance(r, Exception)]
                    
                    test_result['concurrency_tests'][test_name] = {
                        'concurrency_level': concurrency,
                        'total_time': total_time,
                        'successful_queries': len(successful_results),
                        'failed_queries': len(failed_results),
                        'average_query_time': np.mean(successful_results) if successful_results else 0,
                        'queries_per_second': len(successful_results) / total_time if total_time > 0 else 0,
                        'status': 'success' if not failed_results else 'warning'
                    }
                    
                    if failed_results:
                        test_result['errors'].extend([str(e) for e in failed_results[:3]])  # 只显示前3个错误
                
                except Exception as e:
                    test_result['concurrency_tests'][test_name] = {
                        'concurrency_level': concurrency,
                        'status': 'error',
                        'error': str(e)
                    }
                    test_result['errors'].append(f"并发测试 {test_name} 失败: {e}")
            
            if test_result['errors']:
                test_result['status'] = 'warning'
            
            logger.info("并发性能测试完成")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['errors'].append(f"并发测试失败: {str(e)}")
            return test_result
    
    def _rate_performance(self, avg_time: float) -> str:
        """评级性能"""
        if avg_time < 0.01:
            return 'excellent'
        elif avg_time < 0.05:
            return 'good'
        elif avg_time < 0.1:
            return 'fair'
        elif avg_time < 0.5:
            return 'poor'
        else:
            return 'very_poor'
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合性能测试"""
        logger.info("开始综合数据库性能测试...")
        
        comprehensive_result = {
            'test_timestamp': datetime.now().isoformat(),
            'overall_status': 'success',
            'test_results': {},
            'performance_summary': {},
            'recommendations': []
        }
        
        # 运行所有测试
        tests = [
            ('basic_queries', self.test_basic_queries),
            ('vector_search', self.test_vector_search_performance),
            ('index_efficiency', self.test_index_efficiency),
            ('concurrent_performance', self.test_concurrent_performance)
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
        
        # 生成性能总结和建议
        comprehensive_result['performance_summary'] = self._generate_performance_summary(comprehensive_result['test_results'])
        comprehensive_result['recommendations'] = self._generate_performance_recommendations(comprehensive_result['test_results'])
        
        logger.info(f"综合性能测试完成，总体状态: {comprehensive_result['overall_status']}")
        return comprehensive_result
    
    def _generate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成性能总结"""
        summary = {
            'overall_rating': 'unknown',
            'key_metrics': {},
            'bottlenecks': []
        }
        
        # 基础查询性能
        if 'basic_queries' in test_results and test_results['basic_queries']['status'] != 'error':
            basic_tests = test_results['basic_queries']['query_tests']
            successful_basic = [test for test in basic_tests.values() if test['status'] == 'success']
            if successful_basic:
                avg_basic_time = np.mean([test['average_time'] for test in successful_basic])
                summary['key_metrics']['avg_basic_query_time'] = avg_basic_time
        
        # 向量检索性能
        if 'vector_search' in test_results and test_results['vector_search']['status'] != 'error':
            if 'performance_summary' in test_results['vector_search']:
                vector_perf = test_results['vector_search']['performance_summary']
                summary['key_metrics']['avg_vector_search_time'] = vector_perf.get('overall_avg_time', 0)
        
        # 并发性能
        if 'concurrent_performance' in test_results and test_results['concurrent_performance']['status'] != 'error':
            concurrent_tests = test_results['concurrent_performance']['concurrency_tests']
            successful_concurrent = [test for test in concurrent_tests.values() if test['status'] != 'error']
            if successful_concurrent:
                max_qps = max(test.get('queries_per_second', 0) for test in successful_concurrent)
                summary['key_metrics']['max_queries_per_second'] = max_qps
        
        # 综合评级
        ratings = []
        for metric_name, metric_value in summary['key_metrics'].items():
            if 'time' in metric_name:
                ratings.append(self._rate_performance(metric_value))
        
        if ratings:
            rating_scores = {'excellent': 5, 'good': 4, 'fair': 3, 'poor': 2, 'very_poor': 1}
            avg_score = np.mean([rating_scores.get(r, 0) for r in ratings])
            
            if avg_score >= 4.5:
                summary['overall_rating'] = 'excellent'
            elif avg_score >= 3.5:
                summary['overall_rating'] = 'good'
            elif avg_score >= 2.5:
                summary['overall_rating'] = 'fair'
            else:
                summary['overall_rating'] = 'poor'
        
        return summary
    
    def _generate_performance_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """生成性能优化建议"""
        recommendations = []
        
        # 基础查询优化建议
        if 'basic_queries' in test_results:
            basic_result = test_results['basic_queries']
            if basic_result.get('errors'):
                recommendations.append("基础查询存在错误，检查数据库结构和连接")
        
        # 向量检索优化建议
        if 'vector_search' in test_results:
            vector_result = test_results['vector_search']
            if vector_result.get('performance_summary', {}).get('overall_avg_time', 0) > 0.1:
                recommendations.append("向量检索性能较慢，考虑调整 ivfflat 索引参数或增加 shared_buffers")
        
        # 索引优化建议
        if 'index_efficiency' in test_results:
            index_result = test_results['index_efficiency']
            if index_result.get('index_usage_analysis', {}).get('index_usage_rate', 0) < 0.8:
                recommendations.append("索引使用率较低，检查查询是否正确使用索引")
        
        # 并发性能建议
        if 'concurrent_performance' in test_results:
            concurrent_result = test_results['concurrent_performance']
            concurrent_tests = concurrent_result.get('concurrency_tests', {})
            if any(test.get('failed_queries', 0) > 0 for test in concurrent_tests.values()):
                recommendations.append("高并发下存在查询失败，考虑增加连接池大小或优化锁策略")
        
        if not recommendations:
            recommendations.append("数据库性能良好，无需优化")
        
        return recommendations

# CLI接口
async def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库性能测试')
    parser.add_argument('--output', '-o', help='输出结果到文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = DatabasePerformanceTest()
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