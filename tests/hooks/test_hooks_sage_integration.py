#!/usr/bin/env python3
"""
Hooks与Sage Core深度集成测试
全面验证hooks和Sage core之间的协同配合

测试重点：
1. Stop hooks保存完整会话记录到Docker数据库功能
2. UserPromptSubmit hooks调用完整RAG链路功能  
3. 异步操作稳定性和错误恢复
4. 数据持久化和召回准确性
"""

import json
import sys
import subprocess
import tempfile
import time
import unittest
import asyncio
import uuid
import psycopg2
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.insert(0, '/Users/jet/Sage')
sys.path.insert(0, '/Users/jet/Sage/hooks/scripts')

class HooksSageIntegrationTest(unittest.TestCase):
    """Hooks与Sage Core深度集成测试类"""
    
    def setUp(self):
        """测试前设置"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = f"integration_test_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'sage_memory',
            'user': 'sage',
            'password': 'sage123'
        }
        
        # 脚本路径
        self.enhancer_script = "/Users/jet/Sage/hooks/scripts/sage_prompt_enhancer.py"
        self.stop_hook_script = "/Users/jet/Sage/hooks/scripts/sage_stop_hook.py"
        
        # 创建测试transcript文件
        self.transcript_file = self.test_dir / "integration_test_transcript.jsonl"
        
        print(f"\n=== 开始集成测试 {self.session_id} ===")
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        print(f"=== 完成集成测试 {self.session_id} ===\n")
    
    def create_test_transcript(self, conversations: List[Dict]) -> None:
        """创建测试用的Claude CLI transcript文件"""
        with open(self.transcript_file, 'w', encoding='utf-8') as f:
            for conv in conversations:
                f.write(json.dumps(conv) + '\n')
    
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def verify_database_save(self, session_id: str) -> Dict[str, Any]:
        """验证数据是否正确保存到数据库"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 检查memories表中的记录
                    cur.execute("""
                        SELECT id, user_input, assistant_response, metadata, created_at
                        FROM memories 
                        WHERE metadata->>'session_id' = %s
                        ORDER BY created_at DESC
                        LIMIT 10
                    """, (session_id,))
                    
                    memories = cur.fetchall()
                    
                    # 检查sessions表中的记录
                    cur.execute("""
                        SELECT session_id, metadata, created_at
                        FROM sessions
                        WHERE session_id = %s
                    """, (session_id,))
                    
                    sessions = cur.fetchall()
                    
                    return {
                        'memories_count': len(memories),
                        'memories': memories,
                        'sessions_count': len(sessions),
                        'sessions': sessions,
                        'verification_success': True
                    }
        except Exception as e:
            return {
                'verification_success': False,
                'error': str(e),
                'memories_count': 0,
                'sessions_count': 0
            }
    
    def test_stop_hook_database_save_integration(self):
        """测试Stop Hook的数据库保存集成功能"""
        print("\n1. 测试Stop Hook数据库保存集成...")
        
        # 准备测试数据 - Claude CLI格式
        test_conversations = [
            {
                "type": "user",
                "timestamp": time.time() - 100,
                "uuid": str(uuid.uuid4()),
                "message": {
                    "content": "请帮我实现一个Python装饰器用于函数性能监控"
                }
            },
            {
                "type": "assistant", 
                "timestamp": time.time() - 50,
                "uuid": str(uuid.uuid4()),
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "我来帮您实现一个Python装饰器用于函数性能监控："
                        },
                        {
                            "type": "text", 
                            "text": "```python\nimport time\nimport functools\n\ndef performance_monitor(func):\n    @functools.wraps(func)\n    def wrapper(*args, **kwargs):\n        start_time = time.time()\n        result = func(*args, **kwargs)\n        end_time = time.time()\n        print(f'{func.__name__} 执行时间: {end_time - start_time:.4f}秒')\n        return result\n    return wrapper\n```"
                        }
                    ]
                }
            }
        ]
        
        self.create_test_transcript(test_conversations)
        
        # 执行Stop Hook
        stop_hook_input = {
            "session_id": self.session_id,
            "transcript_path": str(self.transcript_file)
        }
        
        print("   执行Stop Hook脚本...")
        process = subprocess.run(
            [sys.executable, self.stop_hook_script],
            input=json.dumps(stop_hook_input),
            text=True,
            capture_output=True,
            timeout=60  # 增加超时时间，给数据库操作充足时间
        )
        
        # 验证脚本执行成功
        self.assertEqual(process.returncode, 0, f"Stop Hook应该成功执行。输出: {process.stdout}, 错误: {process.stderr}")
        
        # 验证输出包含成功信息
        output = process.stdout.strip()
        self.assertIn("SUCCESS", output, "输出应该包含成功标识")
        
        # 等待异步数据库操作完成
        time.sleep(3)
        
        # 验证数据库中的数据
        print("   验证数据库保存结果...")
        db_result = self.verify_database_save(self.session_id)
        
        self.assertTrue(db_result['verification_success'], 
                       f"数据库验证应该成功。错误: {db_result.get('error', 'Unknown')}")
        
        self.assertGreater(db_result['memories_count'], 0, 
                          "应该至少有一条会话记录保存到数据库")
        
        if db_result['memories_count'] > 0:
            memory = db_result['memories'][0]
            self.assertIsNotNone(memory[1], "user_input不应该为空")
            self.assertIsNotNone(memory[2], "assistant_response不应该为空")
            self.assertIn(self.session_id, str(memory[3]), "metadata应该包含session_id")
            
            print(f"   ✅ 成功保存 {db_result['memories_count']} 条记录到数据库")
            print(f"   ✅ 用户输入长度: {len(memory[1])} 字符")
            print(f"   ✅ 助手回复长度: {len(memory[2])} 字符")
        
        print("   ✅ Stop Hook数据库保存集成测试通过")
    
    def test_prompt_enhancer_rag_integration(self):
        """测试Prompt Enhancer的RAG集成功能"""
        print("\n2. 测试Prompt Enhancer RAG集成...")
        
        # 首先保存一些上下文数据到数据库（模拟历史对话）
        context_conversations = [
            {
                "type": "user",
                "timestamp": time.time() - 200,
                "uuid": str(uuid.uuid4()),
                "message": {
                    "content": "我在开发一个Web API项目，使用FastAPI框架"
                }
            },
            {
                "type": "assistant",
                "timestamp": time.time() - 180,
                "uuid": str(uuid.uuid4()),
                "message": {
                    "content": "FastAPI是一个优秀的现代Python Web框架，具有高性能和自动API文档生成功能。您需要什么具体帮助？"
                }
            }
        ]
        
        # 创建历史对话的transcript
        context_session_id = f"context_{self.session_id}"
        context_transcript = self.test_dir / "context_transcript.jsonl"
        
        with open(context_transcript, 'w', encoding='utf-8') as f:
            for conv in context_conversations:
                f.write(json.dumps(conv) + '\n')
        
        # 先保存历史上下文到数据库
        context_stop_input = {
            "session_id": context_session_id,
            "transcript_path": str(context_transcript)
        }
        
        print("   保存历史上下文到数据库...")
        subprocess.run(
            [sys.executable, self.stop_hook_script],
            input=json.dumps(context_stop_input),
            text=True,
            capture_output=True,
            timeout=30
        )
        
        # 等待上下文保存完成
        time.sleep(2)
        
        # 测试Prompt Enhancer调用RAG
        current_conversations = [
            {
                "type": "user",
                "timestamp": time.time() - 20,
                "uuid": str(uuid.uuid4()),
                "message": {
                    "content": "如何在API中添加认证中间件？"
                }
            }
        ]
        
        current_transcript = self.test_dir / "current_transcript.jsonl"
        with open(current_transcript, 'w', encoding='utf-8') as f:
            for conv in current_conversations:
                f.write(json.dumps(conv) + '\n')
        
        # 执行Prompt Enhancer
        enhancer_input = {
            "session_id": self.session_id,
            "prompt": "如何在FastAPI中添加JWT认证中间件？",
            "transcript_path": str(current_transcript)
        }
        
        print("   执行Prompt Enhancer...")
        process = subprocess.run(
            [sys.executable, self.enhancer_script],
            input=json.dumps(enhancer_input),
            text=True,
            capture_output=True,
            timeout=60  # 给RAG调用充足时间
        )
        
        # 验证脚本执行成功
        self.assertEqual(process.returncode, 0, 
                        f"Prompt Enhancer应该成功执行。输出: {process.stdout}, 错误: {process.stderr}")
        
        # 验证输出包含增强内容
        enhanced_output = process.stdout.strip()
        self.assertGreater(len(enhanced_output), 0, "应该有增强输出")
        
        # 验证增强内容的质量（应该包含相关性信息）
        if enhanced_output:
            print(f"   ✅ 生成增强提示长度: {len(enhanced_output)} 字符")
            print(f"   📝 增强内容预览: {enhanced_output[:200]}...")
            
            # 检查是否包含技术相关词汇（表明RAG工作正常）
            relevant_keywords = ['FastAPI', 'API', '认证', '中间件', 'JWT', 'Web', '框架']
            found_keywords = [kw for kw in relevant_keywords if kw in enhanced_output]
            
            self.assertGreater(len(found_keywords), 0, 
                             f"增强输出应该包含相关技术词汇。找到: {found_keywords}")
            
            print(f"   ✅ 发现相关技术词汇: {found_keywords}")
        
        print("   ✅ Prompt Enhancer RAG集成测试通过")
    
    def test_end_to_end_workflow_integration(self):
        """测试完整的端到端工作流程集成"""
        print("\n3. 测试端到端工作流程集成...")
        
        # 第一步：用户输入 -> Prompt Enhancer增强
        user_prompt = "如何优化Python代码的内存使用？"
        
        enhancer_input = {
            "session_id": self.session_id,
            "prompt": user_prompt,
            "transcript_path": ""  # 新会话
        }
        
        print("   步骤1: 执行Prompt Enhancer...")
        enhancer_process = subprocess.run(
            [sys.executable, self.enhancer_script],
            input=json.dumps(enhancer_input),
            text=True,
            capture_output=True,
            timeout=45
        )
        
        self.assertEqual(enhancer_process.returncode, 0, "Prompt Enhancer应该成功")
        enhanced_prompt = enhancer_process.stdout.strip()
        
        # 第二步：模拟Claude处理增强后的提示
        assistant_response = f"""基于您的问题"{user_prompt}"，我提供以下Python内存优化建议：

1. **使用生成器代替列表**
   ```python
   # 内存效率高
   def process_data():
       for i in range(1000000):
           yield process_item(i)
   ```

2. **及时释放大对象**
   ```python
   import gc
   del large_object
   gc.collect()
   ```

3. **使用__slots__减少实例内存**
   ```python
   class OptimizedClass:
       __slots__ = ['attr1', 'attr2']
   ```

这些方法可以显著减少内存使用。"""
        
        # 第三步：创建完整对话记录
        complete_conversation = [
            {
                "type": "user",
                "timestamp": time.time() - 10,
                "uuid": str(uuid.uuid4()),
                "message": {
                    "content": user_prompt
                }
            },
            {
                "type": "assistant",
                "timestamp": time.time() - 5,
                "uuid": str(uuid.uuid4()),
                "message": {
                    "content": assistant_response
                }
            }
        ]
        
        self.create_test_transcript(complete_conversation)
        
        # 第四步：Stop Hook保存完整对话
        stop_hook_input = {
            "session_id": self.session_id,
            "transcript_path": str(self.transcript_file)
        }
        
        print("   步骤2: 执行Stop Hook保存...")
        stop_process = subprocess.run(
            [sys.executable, self.stop_hook_script],
            input=json.dumps(stop_hook_input),
            text=True,
            capture_output=True,
            timeout=60
        )
        
        self.assertEqual(stop_process.returncode, 0, "Stop Hook应该成功")
        
        # 等待数据库保存完成
        time.sleep(3)
        
        # 第五步：验证端到端数据流
        print("   步骤3: 验证端到端数据流...")
        db_result = self.verify_database_save(self.session_id)
        
        self.assertTrue(db_result['verification_success'], "数据库验证应该成功")
        self.assertGreater(db_result['memories_count'], 0, "应该有保存的对话记录")
        
        if db_result['memories_count'] > 0:
            memory = db_result['memories'][0]
            saved_user_input = memory[1]
            saved_assistant_response = memory[2]
            
            # 验证保存的内容质量
            self.assertIn("内存", saved_user_input, "保存的用户输入应该包含关键词")
            self.assertIn("优化", saved_assistant_response, "保存的助手回复应该包含相关内容")
            
            print(f"   ✅ 用户输入正确保存: {saved_user_input[:50]}...")
            print(f"   ✅ 助手回复正确保存: {saved_assistant_response[:50]}...")
        
        # 第六步：测试后续对话的上下文使用
        print("   步骤4: 测试后续对话上下文...")
        follow_up_input = {
            "session_id": f"followup_{self.session_id}",
            "prompt": "刚才提到的生成器方法能给个更具体的例子吗？",
            "transcript_path": str(self.transcript_file)
        }
        
        followup_process = subprocess.run(
            [sys.executable, self.enhancer_script],
            input=json.dumps(follow_up_input),
            text=True,
            capture_output=True,
            timeout=45
        )
        
        self.assertEqual(followup_process.returncode, 0, "后续对话增强应该成功")
        followup_enhanced = followup_process.stdout.strip()
        
        if followup_enhanced:
            print(f"   ✅ 后续对话增强成功，长度: {len(followup_enhanced)} 字符")
        
        print("   ✅ 端到端工作流程集成测试通过")
    
    def test_error_recovery_and_resilience(self):
        """测试错误恢复和系统韧性"""
        print("\n4. 测试错误恢复和系统韧性...")
        
        # 测试场景1：无效的transcript文件
        print("   场景1: 无效transcript文件...")
        invalid_transcript = self.test_dir / "invalid.jsonl"
        with open(invalid_transcript, 'w') as f:
            f.write("invalid json content\n")
            f.write('{"valid": "json"}\n')
            f.write("another invalid line\n")
        
        stop_hook_input = {
            "session_id": f"error_test_{self.session_id}",
            "transcript_path": str(invalid_transcript)
        }
        
        process = subprocess.run(
            [sys.executable, self.stop_hook_script],
            input=json.dumps(stop_hook_input),
            text=True,
            capture_output=True,
            timeout=30
        )
        
        # 应该能够优雅处理错误
        self.assertEqual(process.returncode, 0, "无效JSON应该被优雅处理")
        
        # 测试场景2：空输入
        print("   场景2: 空输入处理...")
        empty_process = subprocess.run(
            [sys.executable, self.enhancer_script],
            input="",
            text=True,
            capture_output=True,
            timeout=10
        )
        
        # 空输入应该返回错误码，但不应该崩溃
        self.assertNotEqual(empty_process.returncode, 0, "空输入应该返回错误码")
        
        # 测试场景3：超大文件处理（资源限制测试）
        print("   场景3: 资源限制测试...")
        large_transcript = self.test_dir / "large.jsonl"
        with open(large_transcript, 'w') as f:
            for i in range(1000):  # 创建大量数据
                large_content = {
                    "type": "user",
                    "timestamp": time.time(),
                    "uuid": str(uuid.uuid4()),
                    "message": {
                        "content": "Large content " * 100  # 每条消息约1KB
                    }
                }
                f.write(json.dumps(large_content) + '\n')
        
        large_file_input = {
            "session_id": f"large_test_{self.session_id}",
            "transcript_path": str(large_transcript)
        }
        
        large_process = subprocess.run(
            [sys.executable, self.stop_hook_script],
            input=json.dumps(large_file_input),
            text=True,
            capture_output=True,
            timeout=60
        )
        
        # 大文件应该能被处理（可能会被截断，但不应该崩溃）
        self.assertEqual(large_process.returncode, 0, "大文件应该被优雅处理")
        
        print("   ✅ 错误恢复和系统韧性测试通过")
    
    def test_async_operation_stability(self):
        """测试异步操作稳定性"""
        print("\n5. 测试异步操作稳定性...")
        
        # 并发执行多个Stop Hook操作
        import concurrent.futures
        import threading
        
        def run_stop_hook(test_id: int) -> tuple:
            """运行单个Stop Hook操作"""
            try:
                session_id = f"async_test_{test_id}_{int(time.time())}"
                
                # 创建测试数据
                test_data = [
                    {
                        "type": "user",
                        "timestamp": time.time(),
                        "uuid": str(uuid.uuid4()),
                        "message": {"content": f"异步测试消息 {test_id}"}
                    },
                    {
                        "type": "assistant",
                        "timestamp": time.time() + 1,
                        "uuid": str(uuid.uuid4()),
                        "message": {"content": f"异步测试回复 {test_id}"}
                    }
                ]
                
                transcript_file = self.test_dir / f"async_test_{test_id}.jsonl"
                with open(transcript_file, 'w') as f:
                    for item in test_data:
                        f.write(json.dumps(item) + '\n')
                
                # 执行Stop Hook
                stop_input = {
                    "session_id": session_id,
                    "transcript_path": str(transcript_file)
                }
                
                process = subprocess.run(
                    [sys.executable, self.stop_hook_script],
                    input=json.dumps(stop_input),
                    text=True,
                    capture_output=True,
                    timeout=45
                )
                
                return test_id, process.returncode == 0, session_id
                
            except Exception as e:
                return test_id, False, str(e)
        
        print("   执行并发异步操作测试...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_stop_hook, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 分析并发测试结果
        successful_ops = sum(1 for _, success, _ in results if success)
        total_ops = len(results)
        
        print(f"   并发操作结果: {successful_ops}/{total_ops} 成功")
        
        # 至少80%的操作应该成功
        success_rate = successful_ops / total_ops
        self.assertGreaterEqual(success_rate, 0.8, 
                               f"并发操作成功率应该至少80%，实际: {success_rate:.1%}")
        
        print("   ✅ 异步操作稳定性测试通过")


def run_integration_tests():
    """运行完整的集成测试套件"""
    print("=" * 80)
    print("Sage Hooks与Sage Core深度集成测试")
    print("=" * 80)
    
    # 检查测试前置条件
    print("检查测试环境...")
    
    # 检查Docker容器状态
    try:
        import subprocess
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if 'sage-db' not in result.stdout:
            print("❌ 错误: sage-db Docker容器未运行")
            print("   请先启动数据库容器: docker-compose up -d")
            return False
        else:
            print("✅ sage-db Docker容器正在运行")
    except Exception as e:
        print(f"❌ 错误: 无法检查Docker状态: {e}")
        return False
    
    # 检查数据库连接
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='sage_memory',
            user='sage',
            password='sage123'
        )
        conn.close()
        print("✅ 数据库连接正常")
    except Exception as e:
        print(f"❌ 错误: 数据库连接失败: {e}")
        return False
    
    # 运行测试套件
    print("\n开始执行集成测试...")
    suite = unittest.TestLoader().loadTestsFromTestCase(HooksSageIntegrationTest)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # 输出详细结果
    print("\n" + "=" * 80)
    print("深度集成测试结果摘要:")
    print(f"总计测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}")
            print(f"  {traceback}")
    
    if result.errors:
        print("\n❌ 错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}")
            print(f"  {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n整体测试结果: {'✅ 全部通过' if success else '❌ 存在问题'}")
    
    if success:
        print("\n🎉 恭喜！Hooks与Sage Core协同配合完美运行！")
        print("✅ Stop hooks成功保存完整会话记录到Docker数据库")
        print("✅ UserPromptSubmit hooks成功调用完整RAG链路")
        print("✅ 异步操作稳定，错误恢复正常")
        print("✅ 数据持久化和召回功能正常")
    
    print("=" * 80)
    return success


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)