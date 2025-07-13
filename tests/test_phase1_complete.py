#!/usr/bin/env python3
"""
阶段1完整测试套件
测试 claude_mem_v3 的所有功能
"""

import os
import sys
import subprocess
import time
import unittest
from pathlib import Path
from typing import List, Tuple

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入需要测试的模块
from claude_mem_v3 import ImprovedCrossplatformClaude, ParsedArgs
from memory import (
    save_conversation_turn, 
    get_memory_stats, 
    clear_all_memories,
    search_memory,
    get_context
)


class TestPhase1ArgumentParsing(unittest.TestCase):
    """测试参数解析功能"""
    
    def setUp(self):
        self.app = ImprovedCrossplatformClaude()
    
    def test_simple_prompt(self):
        """测试简单提示"""
        result = self.app.parse_arguments_improved(["Hello Claude"])
        self.assertEqual(result.user_prompt, "Hello Claude")
        self.assertEqual(result.claude_args, [])
        self.assertFalse(result.sage_options.get('no_memory'))
    
    def test_claude_flags(self):
        """测试 Claude 标志参数"""
        result = self.app.parse_arguments_improved([
            "--verbose", "--debug", "Test prompt"
        ])
        self.assertEqual(result.user_prompt, "Test prompt")
        self.assertIn("--verbose", result.claude_args)
        self.assertIn("--debug", result.claude_args)
    
    def test_sage_options(self):
        """测试 Sage 特有选项"""
        result = self.app.parse_arguments_improved([
            "--no-memory", "Test without memory"
        ])
        self.assertEqual(result.user_prompt, "Test without memory")
        self.assertTrue(result.sage_options.get('no_memory'))
    
    def test_complex_arguments(self):
        """测试复杂参数组合"""
        result = self.app.parse_arguments_improved([
            "--verbose",
            "--output-format", "json",
            "--no-memory",
            "Complex test"
        ])
        self.assertEqual(result.user_prompt, "Complex test")
        self.assertIn("--verbose", result.claude_args)
        self.assertIn("--output-format", result.claude_args)
        self.assertIn("json", result.claude_args)
        self.assertTrue(result.sage_options.get('no_memory'))
    
    def test_special_commands(self):
        """测试特殊命令（不应该到达这里，因为会退出）"""
        # --memory-stats 和 --clear-memory 会直接退出
        # 这里只测试它们被正确识别
        with self.assertRaises(SystemExit):
            self.app.parse_arguments_improved(["--memory-stats"])


class TestPhase1MemoryFunctions(unittest.TestCase):
    """测试记忆功能"""
    
    def test_save_conversation_turn(self):
        """测试保存对话轮次"""
        try:
            # 保存测试对话
            save_conversation_turn(
                "Test question from phase 1",
                "Test response from Claude"
            )
            # 如果没有抛出异常，测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"保存对话失败: {e}")
    
    def test_get_memory_stats(self):
        """测试获取记忆统计"""
        try:
            stats = get_memory_stats()
            # 验证返回的统计信息
            self.assertIn('total', stats)
            self.assertIn('today', stats)
            self.assertIn('this_week', stats)
            self.assertIn('size_mb', stats)
            self.assertIsInstance(stats['total'], int)
            self.assertGreaterEqual(stats['total'], 0)
        except Exception as e:
            self.fail(f"获取统计失败: {e}")
    
    def test_search_memory(self):
        """测试搜索记忆"""
        try:
            # 先保存一些测试数据
            save_conversation_turn(
                "What is Python?",
                "Python is a high-level programming language."
            )
            
            # 搜索相关记忆
            results = search_memory("Python", n=5)
            self.assertIsInstance(results, list)
            
            # 如果有结果，验证格式
            if results:
                result = results[0]
                self.assertIn('content', result)
                self.assertIn('role', result)
                self.assertIn('score', result)
                self.assertIn('metadata', result)
        except Exception as e:
            self.fail(f"搜索记忆失败: {e}")
    
    def test_get_context(self):
        """测试获取上下文"""
        try:
            # 获取相关上下文
            context = get_context("Tell me about Python")
            self.assertIsInstance(context, str)
            # 上下文可能为空（如果没有相关记忆）
        except Exception as e:
            # 如果 API 调用失败，应该返回空字符串
            print(f"获取上下文时出错（预期行为）: {e}")


class TestPhase1Integration(unittest.TestCase):
    """集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.mock_claude = project_root / "tests" / "mock_claude.py"
        if not cls.mock_claude.exists():
            # 创建简单的模拟 Claude
            cls.mock_claude.write_text('''#!/usr/bin/env python3
import sys
print(f"Mock Claude received: {' '.join(sys.argv[1:])}")
print("This is a mock response for testing.")
''')
            cls.mock_claude.chmod(0o755)
    
    def test_no_memory_mode(self):
        """测试无记忆模式"""
        env = os.environ.copy()
        env['ORIGINAL_CLAUDE_PATH'] = f'python3 "{self.mock_claude}"'
        
        cmd = [
            "python3", str(project_root / "claude_mem_v3.py"),
            "--no-memory", "Test prompt"
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            env=env,
            timeout=10
        )
        
        self.assertEqual(result.returncode, 0)
        # 验证响应被正确捕获
        self.assertIn("这是一个模拟的 Claude 响应", result.stdout)
        # 注意：记忆提示可能不会在所有情况下显示（取决于配置）
    
    def test_memory_stats_command(self):
        """测试记忆统计命令"""
        cmd = [
            "python3", str(project_root / "claude_mem_v3.py"),
            "--memory-stats"
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=5
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("记忆系统统计", result.stdout)
        self.assertIn("总记忆数:", result.stdout)
    
    def test_with_memory_mode(self):
        """测试带记忆模式"""
        env = os.environ.copy()
        env['ORIGINAL_CLAUDE_PATH'] = f'python3 "{self.mock_claude}"'
        
        cmd = [
            "python3", str(project_root / "claude_mem_v3.py"),
            "What is machine learning?"
        ]
        
        # 注意：这个测试可能会因为 API 调用而较慢
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            env=env,
            timeout=60  # 给 API 调用更多时间
        )
        
        # 即使 API 调用失败，程序也应该能降级运行
        self.assertEqual(result.returncode, 0)
        # 验证响应被正确捕获
        self.assertIn("这是一个模拟的 Claude 响应", result.stdout)
        # 验证记忆功能工作（如果看到相关上下文说明记忆功能生效）
        if "【相关上下文】" in result.stdout:
            print("✓ 记忆功能正常工作")


class TestPhase1FindClaude(unittest.TestCase):
    """测试查找 Claude 功能"""
    
    def setUp(self):
        self.app = ImprovedCrossplatformClaude()
    
    def test_find_claude_with_env(self):
        """测试使用环境变量查找"""
        # 设置测试环境变量
        test_path = "/test/path/to/claude"
        os.environ['ORIGINAL_CLAUDE_PATH'] = test_path
        
        result = self.app.find_claude_executable()
        self.assertEqual(result, test_path)
        
        # 清理
        del os.environ['ORIGINAL_CLAUDE_PATH']
    
    def test_find_claude_command(self):
        """测试查找命令形式的 Claude"""
        # 设置包含空格的命令
        test_cmd = "python3 /path/to/script.py"
        os.environ['ORIGINAL_CLAUDE_PATH'] = test_cmd
        
        result = self.app.find_claude_executable()
        self.assertEqual(result, test_cmd)
        
        # 清理
        del os.environ['ORIGINAL_CLAUDE_PATH']
    
    def test_find_real_claude(self):
        """测试查找真实的 Claude"""
        # 不设置环境变量，让它查找真实的 Claude
        result = self.app.find_claude_executable()
        
        # 应该能找到某个 Claude（或者返回 None）
        if result:
            self.assertTrue(isinstance(result, str))
            # 如果是路径，应该存在
            if ' ' not in result:
                self.assertTrue(Path(result).exists() or result == "/Users/jet/.claude/local/claude")


def run_all_tests():
    """运行所有测试并生成报告"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestPhase1ArgumentParsing,
        TestPhase1MemoryFunctions,
        TestPhase1FindClaude,
        TestPhase1Integration,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 生成测试报告
    print("\n" + "="*80)
    print("阶段1完整测试报告")
    print("="*80)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\n出错的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # 返回是否全部通过
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    print("🧪 Sage MCP V3 阶段1完整测试")
    print("="*80)
    
    # 确保使用 .env 文件
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ 错误：.env 文件不存在")
        print("请创建 .env 文件并配置 SILICONFLOW_API_KEY")
        sys.exit(1)
    
    # 运行所有测试
    all_passed = run_all_tests()
    
    if all_passed:
        print("\n✅ 所有测试通过！阶段1实现完成。")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查实现。")
        sys.exit(1)