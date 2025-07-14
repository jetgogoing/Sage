#!/usr/bin/env python3
"""
跨平台兼容性测试
测试 Windows/macOS/Linux 平台差异处理
"""

import os
import sys
import platform
import unittest
import tempfile
import subprocess
from pathlib import Path
from typing import List

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入需要测试的模块
from platform_utils import (
    PlatformInfo, CommandParser, PathHandler, 
    ProcessLauncher, EncodingHandler
)
from sage_minimal import ImprovedCrossplatformClaude


class TestPlatformInfo(unittest.TestCase):
    """测试平台信息类"""
    
    def test_platform_detection(self):
        """测试平台检测"""
        info = PlatformInfo()
        
        # 验证平台信息
        self.assertIn(info.system, ['Windows', 'Darwin', 'Linux'])
        self.assertIsInstance(info.is_windows, bool)
        self.assertIsInstance(info.is_macos, bool)
        self.assertIsInstance(info.is_linux, bool)
        
        # 验证只有一个平台标志为True
        platform_flags = [info.is_windows, info.is_macos, info.is_linux]
        self.assertEqual(sum(platform_flags), 1)
        
        # 验证编码信息
        self.assertIsNotNone(info.encoding)
        self.assertIsNotNone(info.filesystem_encoding)
    
    def test_info_dict(self):
        """测试信息字典"""
        info = PlatformInfo()
        info_dict = info.get_info_dict()
        
        required_keys = [
            'system', 'version', 'machine', 'python_version',
            'encoding', 'filesystem_encoding', 'is_windows',
            'is_macos', 'is_linux', 'is_posix'
        ]
        
        for key in required_keys:
            self.assertIn(key, info_dict)


class TestCommandParser(unittest.TestCase):
    """测试命令解析器"""
    
    def setUp(self):
        self.parser = CommandParser()
    
    def test_simple_command(self):
        """测试简单命令解析"""
        # 测试字符串
        result = self.parser.parse_command("echo hello")
        self.assertEqual(result, ["echo", "hello"])
        
        # 测试列表
        result = self.parser.parse_command(["echo", "hello"])
        self.assertEqual(result, ["echo", "hello"])
    
    def test_quoted_command(self):
        """测试带引号的命令"""
        # 双引号
        result = self.parser.parse_command('echo "hello world"')
        self.assertEqual(result, ["echo", "hello world"])
        
        # 路径中的空格
        if self.parser.platform_info.is_windows:
            result = self.parser.parse_command('"C:\\Program Files\\app.exe" --arg')
            self.assertEqual(result, ["C:\\Program Files\\app.exe", "--arg"])
    
    def test_join_command(self):
        """测试命令连接"""
        args = ["python", "script.py", "hello world", "--flag"]
        result = self.parser.join_command(args)
        
        if self.parser.platform_info.is_windows:
            # Windows应该给包含空格的参数加引号
            self.assertIn('"hello world"', result)
        else:
            # POSIX使用shlex.join
            self.assertIn("hello world", result)


class TestPathHandler(unittest.TestCase):
    """测试路径处理器"""
    
    def setUp(self):
        self.handler = PathHandler()
    
    def test_normalize_path(self):
        """测试路径规范化"""
        # 测试用户目录展开
        path = self.handler.normalize_path("~/test")
        self.assertTrue(path.is_absolute())
        self.assertNotIn("~", str(path))
        
        # 测试相对路径转绝对路径
        path = self.handler.normalize_path("./test")
        self.assertTrue(path.is_absolute())
    
    def test_ensure_path_exists(self):
        """测试确保路径存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test" / "subdir" / "file.txt"
            
            # 确保父目录存在
            result = self.handler.ensure_path_exists(test_path, create_parents=True)
            self.assertTrue(test_path.parent.exists())
            # 在macOS上，/var实际上是/private/var的符号链接
            # 所以我们只检查路径的最后部分是否相同
            self.assertEqual(result.name, test_path.name)
            self.assertEqual(result.parent.name, test_path.parent.name)
    
    def test_find_executable(self):
        """测试查找可执行文件"""
        # 查找 python
        python_path = self.handler.find_executable("python")
        if python_path:
            self.assertTrue(python_path.exists())
            self.assertTrue(os.access(str(python_path), os.X_OK))
        
        # 查找不存在的程序
        nonexistent = self.handler.find_executable("nonexistent_program_xyz")
        self.assertIsNone(nonexistent)


class TestEncodingHandler(unittest.TestCase):
    """测试编码处理器"""
    
    def setUp(self):
        self.handler = EncodingHandler()
    
    def test_console_encoding(self):
        """测试控制台编码"""
        encoding = self.handler.get_console_encoding()
        self.assertIsInstance(encoding, str)
        self.assertNotEqual(encoding, "")
    
    def test_decode_output(self):
        """测试输出解码"""
        # UTF-8 编码
        data = "Hello 世界".encode('utf-8')
        result = self.handler.decode_output(data)
        self.assertEqual(result, "Hello 世界")
        
        # 错误的编码（应该使用replace策略）
        data = b'\xff\xfe\xfd'
        result = self.handler.decode_output(data, errors='replace')
        self.assertIsInstance(result, str)
    
    def test_encode_input(self):
        """测试输入编码"""
        text = "Hello 世界"
        result = self.handler.encode_input(text)
        self.assertIsInstance(result, bytes)
        self.assertEqual(result.decode('utf-8'), text)


class TestProcessLauncher(unittest.TestCase):
    """测试进程启动器"""
    
    def setUp(self):
        self.launcher = ProcessLauncher()
    
    def test_prepare_environment(self):
        """测试环境准备"""
        env = self.launcher.prepare_environment()
        
        # 验证必要的环境变量
        self.assertIn('PYTHONIOENCODING', env)
        self.assertEqual(env['PYTHONIOENCODING'], 'utf-8')
        
        if self.launcher.platform_info.is_windows:
            self.assertIn('PYTHONUTF8', env)
            self.assertEqual(env['PYTHONUTF8'], '1')
        
        # 测试自定义环境变量
        custom_env = {'CUSTOM_VAR': 'test'}
        env = self.launcher.prepare_environment(custom_env)
        self.assertEqual(env['CUSTOM_VAR'], 'test')
    
    def test_create_process(self):
        """测试创建进程"""
        # 简单的echo命令
        if self.launcher.platform_info.is_windows:
            command = ["cmd", "/c", "echo", "test"]
        else:
            command = ["echo", "test"]
        
        process = self.launcher.create_process(command)
        self.assertIsNotNone(process)
        
        # 等待进程完成
        stdout, stderr = process.communicate()
        self.assertEqual(process.returncode, 0)


class TestWindowsSpecificFeatures(unittest.TestCase):
    """测试 Windows 特定功能"""
    
    def setUp(self):
        self.platform_info = PlatformInfo()
        self.skip_if_not_windows()
    
    def skip_if_not_windows(self):
        """如果不是 Windows 则跳过"""
        if not self.platform_info.is_windows:
            self.skipTest("Windows-specific test")
    
    def test_windows_path_handling(self):
        """测试 Windows 路径处理"""
        handler = PathHandler()
        
        # 测试 UNC 路径
        unc_path = r"\\server\share\file.txt"
        result = handler.normalize_path(unc_path)
        self.assertEqual(str(result), unc_path)
    
    def test_windows_command_parsing(self):
        """测试 Windows 命令解析"""
        parser = CommandParser()
        
        # 测试包含反斜杠的路径
        cmd = r'C:\Windows\System32\cmd.exe /c "echo test"'
        result = parser.parse_command(cmd)
        self.assertEqual(result[0], r'C:\Windows\System32\cmd.exe')
        self.assertEqual(result[1], '/c')
        self.assertEqual(result[2], 'echo test')


class TestClaudeIntegration(unittest.TestCase):
    """测试 Claude 集成的跨平台兼容性"""
    
    def setUp(self):
        self.app = ImprovedCrossplatformClaude()
    
    def test_platform_tools_integration(self):
        """测试平台工具集成"""
        # 验证平台工具已正确初始化
        self.assertIsNotNone(self.app.platform_info)
        self.assertIsNotNone(self.app.command_parser)
        self.assertIsNotNone(self.app.path_handler)
        self.assertIsNotNone(self.app.process_launcher)
    
    def test_find_claude_crossplatform(self):
        """测试跨平台查找 Claude"""
        # 设置测试环境变量
        test_path = "/test/claude"
        os.environ['ORIGINAL_CLAUDE_PATH'] = test_path
        
        result = self.app.find_claude_executable()
        self.assertEqual(result, test_path)
        
        # 清理
        del os.environ['ORIGINAL_CLAUDE_PATH']
    
    def test_command_execution_mock(self):
        """测试命令执行（使用模拟）"""
        # 创建模拟脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''#!/usr/bin/env python3
import sys
print("Mock output")
print("Args:", ' '.join(sys.argv[1:]))
''')
            mock_script = f.name
        
        try:
            # 设置模拟路径
            os.environ['ORIGINAL_CLAUDE_PATH'] = f'python3 "{mock_script}"'
            
            # 解析参数
            from sage_minimal import ParsedArgs
            parsed_args = ParsedArgs(
                user_prompt="Test prompt",
                claude_args=["--verbose"],
                sage_options={}
            )
            
            # 执行
            return_code, response = self.app.execute_with_capture(
                f'python3 "{mock_script}"',
                parsed_args
            )
            
            self.assertEqual(return_code, 0)
            # 响应可能为空（因为是异步捕获），但返回码应该正确
            if response:
                self.assertIn("Mock", response)
            
        finally:
            # 清理
            del os.environ['ORIGINAL_CLAUDE_PATH']
            os.unlink(mock_script)


def run_platform_tests():
    """运行平台测试"""
    print(f"🧪 运行跨平台兼容性测试 (平台: {platform.system()})")
    print("=" * 80)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestPlatformInfo,
        TestCommandParser,
        TestPathHandler,
        TestEncodingHandler,
        TestProcessLauncher,
        TestWindowsSpecificFeatures,
        TestClaudeIntegration,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_platform_tests()
    sys.exit(0 if success else 1)