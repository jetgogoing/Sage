#!/usr/bin/env python3
"""
端到端功能验证测试
模拟完整的 Claude CLI Hooks 工作流程

测试场景：
1. 用户输入提示 → UserPromptSubmit Hook 触发 → 提示增强 → Claude 处理
2. Claude 响应完成 → Stop Hook 触发 → 对话归档 → 数据持久化
3. 多轮对话的完整流程验证
4. 异常情况和错误恢复测试
5. 性能和稳定性测试
"""

import os
import json
import sys
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import uuid

# 添加脚本路径
hooks_scripts_path = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts"))
sys.path.insert(0, str(hooks_scripts_path))

from config_manager import ConfigManager


class EndToEndTest(unittest.TestCase):
    """端到端测试类"""
    
    def setUp(self):
        """测试前设置"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_id = str(uuid.uuid4())
        
        # 创建测试用的 transcript 文件
        self.transcript_file = self.test_dir / "test_transcript.jsonl"
        
        # 脚本路径
        self.enhancer_script = os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_prompt_enhancer.py")
        self.archiver_script = os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py")
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_mock_transcript(self, conversations: list):
        """创建模拟的对话记录文件"""
        with open(self.transcript_file, 'w', encoding='utf-8') as f:
            for conv in conversations:
                f.write(json.dumps(conv) + '\n')
    
    def test_single_conversation_flow(self):
        """测试单轮对话的完整流程"""
        print("\n=== 测试单轮对话流程 ===")
        
        # 阶段1: UserPromptSubmit Hook - 提示增强
        user_prompt = "请帮我写一个Python函数来计算斐波那契数列"
        
        enhancer_input = {
            "session_id": self.session_id,
            "prompt": user_prompt,
            "transcript_path": ""  # 新会话，没有历史记录
        }
        
        print("1. 执行 UserPromptSubmit Hook...")
        enhancer_process = subprocess.run(
            [sys.executable, self.enhancer_script],
            input=json.dumps(enhancer_input),
            text=True,
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(enhancer_process.returncode, 0, "提示增强器应该成功执行")
        enhanced_output = enhancer_process.stdout.strip()
        print(f"   增强输出: {enhanced_output}")
        
        # 阶段2: 模拟 Claude 处理和响应
        claude_response = """这里是一个计算斐波那契数列的Python函数：

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 更高效的版本
def fibonacci_optimized(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

这个函数提供了两种实现方式：递归版本和优化的迭代版本。"""
        
        # 阶段3: 创建完整的对话记录
        conversation_history = [
            {
                "type": "user_message",
                "content": user_prompt,
                "timestamp": time.time() - 1
            },
            {
                "type": "assistant_message", 
                "content": claude_response,
                "timestamp": time.time()
            }
        ]
        
        self.create_mock_transcript(conversation_history)
        
        # 阶段4: Stop Hook - 对话归档
        archiver_input = {
            "session_id": self.session_id,
            "transcript_path": str(self.transcript_file),
            "stop_hook_active": False
        }
        
        print("2. 执行 Stop Hook...")
        archiver_process = subprocess.run(
            [sys.executable, self.archiver_script],
            input=json.dumps(archiver_input),
            text=True,
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(archiver_process.returncode, 0, "归档器应该成功执行")
        
        # 验证备份文件是否创建
        backup_dir = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "logs", "backup"))
        if backup_dir.exists():
            backup_files = list(backup_dir.glob("conversation_*.json"))
            print(f"   创建的备份文件: {len(backup_files)} 个")
        
        print("✓ 单轮对话流程测试通过")
    
    def test_multi_turn_conversation(self):
        """测试多轮对话流程"""
        print("\n=== 测试多轮对话流程 ===")
        
        # 构建多轮对话历史
        conversation_turns = [
            ("用户第一轮输入", "助手第一轮回复"),
            ("用户第二轮输入", "助手第二轮回复"),
            ("用户第三轮输入", "助手第三轮回复")
        ]
        
        for turn_idx, (user_msg, assistant_msg) in enumerate(conversation_turns, 1):
            print(f"{turn_idx}. 处理第 {turn_idx} 轮对话...")
            
            # 构建当前对话历史
            current_history = []
            for i, (u_msg, a_msg) in enumerate(conversation_turns[:turn_idx]):
                current_history.extend([
                    {
                        "type": "user_message",
                        "content": u_msg,
                        "timestamp": time.time() - (len(conversation_turns) - i) * 2
                    },
                    {
                        "type": "assistant_message",
                        "content": a_msg,
                        "timestamp": time.time() - (len(conversation_turns) - i) * 2 + 1
                    }
                ])
            
            self.create_mock_transcript(current_history)
            
            # 测试提示增强（使用上下文）
            enhancer_input = {
                "session_id": self.session_id,
                "prompt": user_msg,
                "transcript_path": str(self.transcript_file)
            }
            
            enhancer_process = subprocess.run(
                [sys.executable, self.enhancer_script],
                input=json.dumps(enhancer_input),
                text=True,
                capture_output=True,
                timeout=10
            )
            
            self.assertEqual(enhancer_process.returncode, 0)
            
            # 测试对话归档
            archiver_input = {
                "session_id": self.session_id,
                "transcript_path": str(self.transcript_file),
                "stop_hook_active": False
            }
            
            archiver_process = subprocess.run(
                [sys.executable, self.archiver_script],
                input=json.dumps(archiver_input),
                text=True,
                capture_output=True,
                timeout=10
            )
            
            self.assertEqual(archiver_process.returncode, 0)
        
        print("✓ 多轮对话流程测试通过")
    
    def test_error_scenarios(self):
        """测试错误场景的处理"""
        print("\n=== 测试错误场景处理 ===")
        
        # 场景1: 空的 transcript 文件
        print("1. 测试空 transcript 文件...")
        empty_transcript = self.test_dir / "empty_transcript.jsonl"
        empty_transcript.touch()
        
        archiver_input = {
            "session_id": self.session_id,
            "transcript_path": str(empty_transcript),
            "stop_hook_active": False
        }
        
        process = subprocess.run(
            [sys.executable, self.archiver_script],
            input=json.dumps(archiver_input),
            text=True,
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(process.returncode, 0, "空文件应该被优雅处理")
        
        # 场景2: 不存在的 transcript 文件
        print("2. 测试不存在的 transcript 文件...")
        archiver_input = {
            "session_id": self.session_id,
            "transcript_path": "/nonexistent/path/transcript.jsonl",
            "stop_hook_active": False
        }
        
        process = subprocess.run(
            [sys.executable, self.archiver_script],
            input=json.dumps(archiver_input),
            text=True,
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(process.returncode, 0, "不存在的文件应该被优雅处理")
        
        # 场景3: 损坏的 JSON 数据
        print("3. 测试损坏的 JSON 数据...")
        corrupted_transcript = self.test_dir / "corrupted_transcript.jsonl"
        with open(corrupted_transcript, 'w') as f:
            f.write('{"type": "user_message", "content": "valid json"}\n')
            f.write('invalid json line\n')
            f.write('{"type": "assistant_message", "content": "another valid json"}\n')
        
        archiver_input = {
            "session_id": self.session_id,
            "transcript_path": str(corrupted_transcript),
            "stop_hook_active": False
        }
        
        process = subprocess.run(
            [sys.executable, self.archiver_script],
            input=json.dumps(archiver_input),
            text=True,
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(process.returncode, 0, "损坏的 JSON 应该被优雅处理")
        
        # 场景4: stop_hook_active 防护测试
        print("4. 测试 stop_hook_active 防护...")
        archiver_input = {
            "session_id": self.session_id,
            "transcript_path": str(self.transcript_file),
            "stop_hook_active": True  # 应该触发防护机制
        }
        
        process = subprocess.run(
            [sys.executable, self.archiver_script],
            input=json.dumps(archiver_input),
            text=True,
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(process.returncode, 0, "stop_hook_active 防护应该工作")
        
        print("✓ 错误场景处理测试通过")
    
    def test_performance_under_load(self):
        """测试负载下的性能表现"""
        print("\n=== 测试性能表现 ===")
        
        # 创建大量对话数据
        large_conversation = []
        for i in range(50):  # 50轮对话
            large_conversation.extend([
                {
                    "type": "user_message",
                    "content": f"用户消息 {i+1}: " + "这是一个比较长的用户输入消息，用来测试系统在处理大量数据时的性能表现。" * 3,
                    "timestamp": time.time() - (50 - i) * 2
                },
                {
                    "type": "assistant_message",
                    "content": f"助手回复 {i+1}: " + "这是一个详细的助手回复，包含了大量的信息和解释，用来模拟真实场景下的对话内容。" * 5,
                    "timestamp": time.time() - (50 - i) * 2 + 1
                }
            ])
        
        self.create_mock_transcript(large_conversation)
        
        # 测试提示增强器性能
        print("1. 测试提示增强器处理大量上下文的性能...")
        enhancer_times = []
        
        for i in range(5):
            start_time = time.time()
            
            enhancer_input = {
                "session_id": self.session_id,
                "prompt": f"测试提示 {i+1}",
                "transcript_path": str(self.transcript_file)
            }
            
            process = subprocess.run(
                [sys.executable, self.enhancer_script],
                input=json.dumps(enhancer_input),
                text=True,
                capture_output=True,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            enhancer_times.append(execution_time)
            
            self.assertEqual(process.returncode, 0)
        
        avg_enhancer_time = sum(enhancer_times) / len(enhancer_times)
        print(f"   平均执行时间: {avg_enhancer_time:.3f}s")
        print(f"   执行时间范围: {min(enhancer_times):.3f}s - {max(enhancer_times):.3f}s")
        
        # 测试归档器性能
        print("2. 测试归档器处理大量数据的性能...")
        archiver_times = []
        
        for i in range(5):
            start_time = time.time()
            
            archiver_input = {
                "session_id": f"{self.session_id}_{i}",
                "transcript_path": str(self.transcript_file),
                "stop_hook_active": False
            }
            
            process = subprocess.run(
                [sys.executable, self.archiver_script],
                input=json.dumps(archiver_input),
                text=True,
                capture_output=True,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            archiver_times.append(execution_time)
            
            self.assertEqual(process.returncode, 0)
        
        avg_archiver_time = sum(archiver_times) / len(archiver_times)
        print(f"   平均执行时间: {avg_archiver_time:.3f}s")
        print(f"   执行时间范围: {min(archiver_times):.3f}s - {max(archiver_times):.3f}s")
        
        # 性能断言
        self.assertLess(avg_enhancer_time, 5.0, "提示增强器平均执行时间应小于5秒")
        self.assertLess(avg_archiver_time, 3.0, "归档器平均执行时间应小于3秒")
        
        print("✓ 性能测试通过")
    
    def test_concurrent_execution(self):
        """测试并发执行能力"""
        print("\n=== 测试并发执行 ===")
        
        import concurrent.futures
        import threading
        
        # 创建测试数据
        test_conversations = []
        for i in range(10):
            conv = [
                {
                    "type": "user_message",
                    "content": f"并发测试用户消息 {i+1}",
                    "timestamp": time.time() - 1
                },
                {
                    "type": "assistant_message",
                    "content": f"并发测试助手回复 {i+1}",
                    "timestamp": time.time()
                }
            ]
            test_conversations.append(conv)
        
        def run_single_flow(test_id):
            """运行单个对话流程"""
            try:
                # 创建独立的测试文件
                test_transcript = self.test_dir / f"concurrent_test_{test_id}.jsonl"
                with open(test_transcript, 'w', encoding='utf-8') as f:
                    for entry in test_conversations[test_id % len(test_conversations)]:
                        f.write(json.dumps(entry) + '\n')
                
                session_id = f"{self.session_id}_concurrent_{test_id}"
                
                # 运行提示增强器
                enhancer_input = {
                    "session_id": session_id,
                    "prompt": f"并发测试提示 {test_id}",
                    "transcript_path": str(test_transcript)
                }
                
                enhancer_process = subprocess.run(
                    [sys.executable, self.enhancer_script],
                    input=json.dumps(enhancer_input),
                    text=True,
                    capture_output=True,
                    timeout=15
                )
                
                if enhancer_process.returncode != 0:
                    return False, f"Enhancer failed for test {test_id}"
                
                # 运行归档器
                archiver_input = {
                    "session_id": session_id,
                    "transcript_path": str(test_transcript),
                    "stop_hook_active": False
                }
                
                archiver_process = subprocess.run(
                    [sys.executable, self.archiver_script],
                    input=json.dumps(archiver_input),
                    text=True,
                    capture_output=True,
                    timeout=15
                )
                
                if archiver_process.returncode != 0:
                    return False, f"Archiver failed for test {test_id}"
                
                return True, f"Test {test_id} completed successfully"
                
            except Exception as e:
                return False, f"Test {test_id} failed with exception: {str(e)}"
        
        # 并发执行测试
        print("执行10个并发任务...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_single_flow, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 统计结果
        successful_tests = sum(1 for success, _ in results if success)
        failed_tests = sum(1 for success, _ in results if not success)
        
        print(f"   成功: {successful_tests}/10")
        print(f"   失败: {failed_tests}/10")
        
        if failed_tests > 0:
            print("   失败详情:")
            for success, message in results:
                if not success:
                    print(f"     - {message}")
        
        # 至少80%的并发测试应该成功
        self.assertGreaterEqual(successful_tests, 8, "至少80%的并发测试应该成功")
        
        print("✓ 并发执行测试通过")


def run_end_to_end_tests():
    """运行端到端测试套件"""
    print("=" * 70)
    print("Sage Hooks 端到端功能验证测试")
    print("=" * 70)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(EndToEndTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出详细结果
    print("\n" + "=" * 70)
    print("端到端测试结果摘要:")
    print(f"总计测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}")
            print(f"  {traceback}")
    
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}")
            print(f"  {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n整体测试结果: {'✓ 全部通过' if success else '✗ 存在问题'}")
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    success = run_end_to_end_tests()
    sys.exit(0 if success else 1)