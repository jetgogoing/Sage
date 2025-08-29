#!/usr/bin/env python3
"""
Sage Hooks 集成测试套件

测试内容：
1. Hook 脚本的基本功能
2. 配置管理器的功能
3. 日志系统的工作
4. 错误处理和降级机制
5. MCP 工具调用模拟
"""

import json
import os
import sys
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加脚本路径到 Python 路径
hooks_scripts_path = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts"))
sys.path.insert(0, str(hooks_scripts_path))

from config_manager import ConfigManager


class TestSageHooksIntegration(unittest.TestCase):
    """Sage Hooks 集成测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.hooks_dir = self.test_dir / "hooks"
        self.hooks_dir.mkdir(exist_ok=True)
        
        # 复制脚本到测试目录
        import shutil
        shutil.copy(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_prompt_enhancer.py"), 
                   self.hooks_dir / "sage_prompt_enhancer.py")
        shutil.copy(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py"), 
                   self.hooks_dir / "sage_stop_hook.py")
        shutil.copy(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "config_manager.py"), 
                   self.hooks_dir / "config_manager.py")
        shutil.copy(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "security_utils.py"), 
                   self.hooks_dir / "security_utils.py")
        shutil.copy(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "logger.py"), 
                   self.hooks_dir / "logger.py")
    
    def tearDown(self):
        """测试后的清理"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_config_manager_functionality(self):
        """测试配置管理器功能"""
        print("Testing ConfigManager functionality...")
        
        config_dir = self.hooks_dir / "configs"
        cm = ConfigManager(str(config_dir))
        
        # 测试默认配置
        self.assertEqual(cm.get('sage_mcp', 'timeout'), 30)
        self.assertEqual(cm.get('enhancer', 'enabled'), True)
        self.assertEqual(cm.get('logging', 'level'), 'INFO')
        
        # 测试配置设置
        cm.set('test_section', 'test_key', 'test_value')
        self.assertEqual(cm.get('test_section', 'test_key'), 'test_value')
        
        # 测试配置验证
        self.assertTrue(cm.validate_config())
        
        print("✓ ConfigManager functionality test passed")
    
    def test_prompt_enhancer_script(self):
        """测试提示增强脚本"""
        print("Testing prompt enhancer script...")
        
        # 准备测试输入
        test_input = {
            "session_id": "test_session_123",
            "prompt": "请帮我写一个Python函数",
            "transcript_path": ""
        }
        
        # 运行脚本
        script_path = self.hooks_dir / "sage_prompt_enhancer.py"
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.hooks_dir) + ':' + env.get('PYTHONPATH', '')
        
        process = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(test_input),
            text=True,
            capture_output=True,
            timeout=10,
            env=env
        )
        
        # 检查结果
        if process.returncode != 0:
            print(f"Script failed with return code {process.returncode}")
            print(f"STDOUT: {process.stdout}")
            print(f"STDERR: {process.stderr}")
        self.assertEqual(process.returncode, 0)
        # 输出应该包含一些增强内容（即使是模拟的）
        output = process.stdout.strip()
        print(f"Enhancer output: {output}")
        
        print("✓ Prompt enhancer script test passed")
    
    def test_archiver_script(self):
        """测试归档脚本"""
        print("Testing archiver script...")
        
        # 创建模拟的 transcript 文件
        transcript_file = self.test_dir / "test_transcript.jsonl"
        transcript_content = [
            {"type": "user_message", "content": "Hello, how are you?", "timestamp": time.time()},
            {"type": "assistant_message", "content": "I'm doing well, thank you for asking!", "timestamp": time.time()}
        ]
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            for entry in transcript_content:
                f.write(json.dumps(entry) + '\n')
        
        # 准备测试输入
        test_input = {
            "session_id": "test_session_456",
            "transcript_path": str(transcript_file),
            "stop_hook_active": False
        }
        
        # 运行脚本
        script_path = self.hooks_dir / "sage_stop_hook.py"
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.hooks_dir) + ':' + env.get('PYTHONPATH', '')
        
        process = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(test_input),
            text=True,
            capture_output=True,
            timeout=10,
            env=env
        )
        
        # 检查结果
        if process.returncode != 0:
            print(f"Archiver script failed with return code {process.returncode}")
            print(f"STDOUT: {process.stdout}")
            print(f"STDERR: {process.stderr}")
        self.assertEqual(process.returncode, 0)
        
        print("✓ Archiver script test passed")
    
    def test_error_handling(self):
        """测试错误处理机制"""
        print("Testing error handling...")
        
        # 测试无效输入的处理
        invalid_inputs = [
            "",  # 空输入
            "invalid json",  # 无效 JSON
            json.dumps({}),  # 空 JSON 对象
            json.dumps({"session_id": "test"})  # 缺少必要字段
        ]
        
        script_path = self.hooks_dir / "sage_prompt_enhancer.py"
        
        for invalid_input in invalid_inputs:
            process = subprocess.run(
                [sys.executable, str(script_path)],
                input=invalid_input,
                text=True,
                capture_output=True,
                timeout=5
            )
            
            # 脚本应该优雅地处理错误，返回码为 0（静默退出）
            self.assertEqual(process.returncode, 0)
        
        print("✓ Error handling test passed")
    
    def test_logging_functionality(self):
        """测试日志功能"""
        print("Testing logging functionality...")
        
        # 设置日志目录
        log_dir = self.hooks_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # 运行脚本生成日志
        test_input = {
            "session_id": "test_logging_session",
            "prompt": "Test logging functionality",
            "transcript_path": ""
        }
        
        script_path = self.hooks_dir / "sage_prompt_enhancer.py"
        
        # 修改脚本中的日志路径（通过环境变量或临时修改）
        env = {"SAGE_LOG_DIR": str(log_dir)}
        
        process = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(test_input),
            text=True,
            capture_output=True,
            timeout=10,
            env={**dict(subprocess.os.environ), **env}
        )
        
        self.assertEqual(process.returncode, 0)
        
        # 检查日志文件是否生成
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            print(f"✓ Log files generated: {[f.name for f in log_files]}")
        
        print("✓ Logging functionality test passed")
    
    def test_performance_benchmarks(self):
        """测试性能基准"""
        print("Testing performance benchmarks...")
        
        test_input = {
            "session_id": "perf_test_session",
            "prompt": "Performance test prompt with some longer content to simulate real usage scenarios",
            "transcript_path": ""
        }
        
        script_path = self.hooks_dir / "sage_prompt_enhancer.py"
        
        # 运行多次测试并记录时间
        execution_times = []
        num_runs = 5
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.hooks_dir) + ':' + env.get('PYTHONPATH', '')
        
        for i in range(num_runs):
            start_time = time.time()
            
            process = subprocess.run(
                [sys.executable, str(script_path)],
                input=json.dumps(test_input),
                text=True,
                capture_output=True,
                timeout=15,
                env=env
            )
            
            execution_time = time.time() - start_time
            execution_times.append(execution_time)
            
            self.assertEqual(process.returncode, 0)
        
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        print(f"✓ Performance test results:")
        print(f"  Average execution time: {avg_time:.2f}s")
        print(f"  Maximum execution time: {max_time:.2f}s")
        print(f"  All runs: {[f'{t:.2f}s' for t in execution_times]}")
        
        # 性能要求：平均执行时间应小于 5 秒
        self.assertLess(avg_time, 5.0, f"Average execution time {avg_time:.2f}s exceeds 5s limit")
        
        print("✓ Performance benchmarks test passed")


def run_integration_tests():
    """运行集成测试套件"""
    print("=" * 60)
    print("Sage Hooks 集成测试套件")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSageHooksIntegration)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要:")
    print(f"总计测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n整体测试结果: {'✓ 通过' if success else '✗ 失败'}")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)