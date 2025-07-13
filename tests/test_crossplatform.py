#!/usr/bin/env python3
"""
Sage MCP 跨平台测试套件
测试所有平台的兼容性和功能
"""

import os
import sys
import json
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入要测试的模块
try:
    from claude_mem_crossplatform import CrossPlatformClaude
    from migrate import MigrationTool
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"项目路径: {project_root}")
    sys.exit(1)

class TestCrossPlatform(unittest.TestCase):
    """跨平台功能测试"""
    
    def setUp(self):
        """测试前设置"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get('HOME', '')
        self.original_userprofile = os.environ.get('USERPROFILE', '')
        
        # 模拟家目录
        if platform.system() == 'Windows':
            os.environ['USERPROFILE'] = str(self.test_dir)
        else:
            os.environ['HOME'] = str(self.test_dir)
        
        # 创建测试配置目录
        self.config_dir = self.test_dir / '.sage-mcp'
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """测试后清理"""
        # 恢复环境变量
        if platform.system() == 'Windows':
            os.environ['USERPROFILE'] = self.original_userprofile
        else:
            os.environ['HOME'] = self.original_home
        
        # 清理测试目录
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_platform_detection(self):
        """测试平台检测"""
        app = CrossPlatformClaude()
        
        # 验证平台检测
        self.assertIn(app.platform, ['Windows', 'Darwin', 'Linux'])
        self.assertIsInstance(app.is_windows, bool)
        self.assertIsInstance(app.is_macos, bool)
        self.assertIsInstance(app.is_linux, bool)
        
        # 验证只有一个平台为真
        platform_count = sum([app.is_windows, app.is_macos, app.is_linux])
        self.assertEqual(platform_count, 1)
    
    def test_config_directory_creation(self):
        """测试配置目录创建"""
        app = CrossPlatformClaude()
        
        # 验证配置目录已创建
        self.assertTrue(app.config_dir.exists())
        self.assertTrue(app.config_dir.is_dir())
    
    def test_config_file_handling(self):
        """测试配置文件处理"""
        # 创建测试配置
        test_config = {
            'claude_paths': ['/test/path/claude'],
            'memory_enabled': False,
            'debug_mode': True,
            'api_key': 'test_key'
        }
        
        config_file = self.config_dir / 'config.json'
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        # 创建新实例并加载配置
        app = CrossPlatformClaude()
        
        # 验证配置加载
        self.assertEqual(app.config['claude_paths'], ['/test/path/claude'])
        self.assertEqual(app.config['memory_enabled'], False)
        self.assertEqual(app.config['debug_mode'], True)
    
    @patch('shutil.which')
    def test_find_claude_executable_unix(self, mock_which):
        """测试 Unix 系统上查找 Claude"""
        if platform.system() == 'Windows':
            self.skipTest("仅在 Unix 系统上运行")
        
        # 模拟 which 命令找到 claude
        mock_which.return_value = '/usr/local/bin/claude'
        
        app = CrossPlatformClaude()
        
        # 创建模拟的 Claude 文件
        claude_path = self.test_dir / '.local' / 'bin' / 'claude'
        claude_path.parent.mkdir(parents=True, exist_ok=True)
        claude_path.touch()
        claude_path.chmod(0o755)
        
        result = app.find_claude_executable()
        self.assertIsNotNone(result)
    
    @patch('shutil.which')
    def test_find_claude_executable_windows(self, mock_which):
        """测试 Windows 系统上查找 Claude"""
        if platform.system() != 'Windows':
            self.skipTest("仅在 Windows 系统上运行")
        
        # 模拟 which 命令找到 claude.exe
        mock_which.return_value = 'C:\\Program Files\\Claude\\claude.exe'
        
        app = CrossPlatformClaude()
        result = app.find_claude_executable()
        self.assertIsNotNone(result)
    
    def test_recursion_guard(self):
        """测试递归保护机制"""
        app = CrossPlatformClaude()
        
        # 第一次检查应该成功
        self.assertTrue(app.check_recursion_guard())
        self.assertTrue(app.recursion_guard_file.exists())
        
        # 第二次检查应该失败（防止递归）
        app2 = CrossPlatformClaude()
        self.assertFalse(app2.check_recursion_guard())
        
        # 清除保护后应该成功
        app.clear_recursion_guard()
        self.assertFalse(app.recursion_guard_file.exists())
        
        app3 = CrossPlatformClaude()
        self.assertTrue(app3.check_recursion_guard())
    
    def test_parse_claude_arguments(self):
        """测试参数解析"""
        app = CrossPlatformClaude()
        
        # 测试简单查询
        args = ['hello world']
        claude_args, user_input = app.parse_claude_arguments(args)
        self.assertEqual(user_input, 'hello world')
        self.assertEqual(claude_args, [])
        
        # 测试带选项的查询
        args = ['-m', 'claude-3', 'hello world']
        claude_args, user_input = app.parse_claude_arguments(args)
        self.assertEqual(user_input, 'hello world')
        self.assertEqual(claude_args, ['-m', 'claude-3'])
        
        # 测试复杂参数
        args = ['-m', 'claude-3', '-t', '0.7', '--output', 'file.txt', 'test query']
        claude_args, user_input = app.parse_claude_arguments(args)
        self.assertEqual(user_input, 'test query')
        self.assertIn('-m', claude_args)
        self.assertIn('claude-3', claude_args)
        self.assertIn('-t', claude_args)
        self.assertIn('0.7', claude_args)
    
    def test_path_handling(self):
        """测试路径处理"""
        app = CrossPlatformClaude()
        
        # 测试路径规范化
        test_paths = [
            'test/path',
            'test\\path',
            '/test/path with spaces/',
            'C:\\Program Files\\test'
        ]
        
        for test_path in test_paths:
            path_obj = Path(test_path)
            # 验证 Path 对象正确处理各种路径格式
            self.assertIsInstance(path_obj, Path)
    
    @patch('subprocess.call')
    @patch('subprocess.Popen')
    def test_execute_without_memory(self, mock_popen, mock_call):
        """测试不带记忆功能的执行"""
        app = CrossPlatformClaude()
        
        mock_call.return_value = 0
        
        result = app.execute_without_memory('/path/to/claude', ['test'])
        
        self.assertEqual(result, 0)
        mock_call.assert_called_once_with(['/path/to/claude', 'test'])
    
    def test_migration_tool_init(self):
        """测试迁移工具初始化"""
        tool = MigrationTool()
        
        self.assertEqual(tool.platform, platform.system())
        self.assertTrue(tool.sage_path.exists())
        self.assertIsInstance(tool.detection_results, dict)

class TestPlatformSpecific(unittest.TestCase):
    """平台特定功能测试"""
    
    def test_windows_specific(self):
        """Windows 特定功能测试"""
        if platform.system() != 'Windows':
            self.skipTest("仅在 Windows 上运行")
        
        app = CrossPlatformClaude()
        
        # 测试 Windows 路径
        self.assertTrue(app.is_windows)
        self.assertFalse(app.is_macos)
        self.assertFalse(app.is_linux)
    
    def test_macos_specific(self):
        """macOS 特定功能测试"""
        if platform.system() != 'Darwin':
            self.skipTest("仅在 macOS 上运行")
        
        app = CrossPlatformClaude()
        
        # 测试 macOS 特性
        self.assertTrue(app.is_macos)
        self.assertFalse(app.is_windows)
        self.assertFalse(app.is_linux)
    
    def test_linux_specific(self):
        """Linux 特定功能测试"""
        if platform.system() != 'Linux':
            self.skipTest("仅在 Linux 上运行")
        
        app = CrossPlatformClaude()
        
        # 测试 Linux 特性
        self.assertTrue(app.is_linux)
        self.assertFalse(app.is_windows)
        self.assertFalse(app.is_macos)

class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """清理测试环境"""
        os.environ.clear()
        os.environ.update(self.original_env)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('subprocess.Popen')
    def test_full_workflow(self, mock_popen):
        """测试完整工作流程"""
        # 设置模拟环境
        os.environ['SAGE_CONFIG_DIR'] = str(self.test_dir / '.sage-mcp')
        
        # 创建模拟的 Claude 响应
        mock_process = MagicMock()
        mock_process.stdout = iter(['Hello from Claude\n'])
        mock_process.wait.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        # 创建应用实例
        app = CrossPlatformClaude()
        
        # 模拟配置
        app.config['claude_paths'] = ['/mock/claude']
        app.config['memory_enabled'] = True
        
        # 执行测试
        with patch.object(app, 'find_claude_executable', return_value='/mock/claude'):
            result = app.run(['test query'])
        
        self.assertEqual(result, 0)

def run_tests(verbose=False):
    """运行所有测试"""
    print(f"\n{'='*60}")
    print(f"Sage MCP 跨平台测试套件")
    print(f"平台: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print(f"{'='*60}\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestCrossPlatform))
    suite.addTests(loader.loadTestsFromTestCase(TestPlatformSpecific))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    # 生成测试报告
    generate_test_report(result)
    
    return result.wasSuccessful()

def generate_test_report(result):
    """生成测试报告"""
    report_dir = Path(__file__).parent / 'reports'
    report_dir.mkdir(exist_ok=True)
    
    report_file = report_dir / f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Sage MCP 跨平台测试报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 测试环境\n")
        f.write(f"- 平台: {platform.system()} {platform.release()}\n")
        f.write(f"- Python: {platform.python_version()}\n")
        f.write(f"- 架构: {platform.machine()}\n\n")
        
        f.write(f"## 测试结果\n")
        f.write(f"- 运行测试: {result.testsRun}\n")
        f.write(f"- 成功: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"- 失败: {len(result.failures)}\n")
        f.write(f"- 错误: {len(result.errors)}\n")
        f.write(f"- 跳过: {len(result.skipped)}\n\n")
        
        if result.failures:
            f.write(f"## 失败的测试\n")
            for test, traceback in result.failures:
                f.write(f"### {test}\n")
                f.write(f"```\n{traceback}\n```\n\n")
        
        if result.errors:
            f.write(f"## 错误的测试\n")
            for test, traceback in result.errors:
                f.write(f"### {test}\n")
                f.write(f"```\n{traceback}\n```\n\n")
    
    print(f"\n测试报告已生成: {report_file}")

if __name__ == '__main__':
    # 支持命令行参数
    import argparse
    
    parser = argparse.ArgumentParser(description='Sage MCP 跨平台测试')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('--platform', help='指定测试平台')
    
    args = parser.parse_args()
    
    # 运行测试
    success = run_tests(verbose=args.verbose)
    sys.exit(0 if success else 1)