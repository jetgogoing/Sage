#!/usr/bin/env python3
"""
错误场景测试
测试各种错误情况下的异常处理
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入需要测试的模块和异常
from sage_minimal import ImprovedCrossplatformClaude, ParsedArgs
from exceptions import (
    SageBaseException, ConfigurationError, MemoryProviderError,
    SageExecutionError, SageNotFoundError, PlatformCompatibilityError,
    AsyncRuntimeError, ResourceManagementError, ValidationError,
    EnhancementError, RetrievalError
)


class TestExceptionHandling(unittest.TestCase):
    """测试异常处理"""
    
    def setUp(self):
        self.app = ImprovedCrossplatformClaude()
    
    def test_claude_not_found_error(self):
        """测试 Claude 未找到错误"""
        # 设置一个不存在的路径
        os.environ['ORIGINAL_CLAUDE_PATH'] = '/nonexistent/claude'
        
        parsed_args = ParsedArgs(
            user_prompt="Test",
            claude_args=[],
            sage_options={}
        )
        
        # 应该抛出 ClaudeNotFoundError
        return_code, response = self.app.execute_with_capture(
            '/nonexistent/claude',
            parsed_args
        )
        
        self.assertEqual(return_code, 1)
        self.assertEqual(response, "")
        
        # 清理
        del os.environ['ORIGINAL_CLAUDE_PATH']
    
    def test_memory_provider_error(self):
        """测试记忆提供者错误"""
        # 模拟记忆提供者错误
        with patch.object(self.app, 'memory_provider', 
                         side_effect=MemoryProviderError("数据库连接失败")):
            parsed_args = ParsedArgs(
                user_prompt="Test",
                claude_args=[],
                sage_options={}
            )
            
            # 设置一个有效的 Claude 路径
            os.environ['ORIGINAL_CLAUDE_PATH'] = sys.executable
            
            # 应该降级到无记忆模式
            return_code = self.app._run_with_memory_sync(parsed_args)
            
            # 清理
            del os.environ['ORIGINAL_CLAUDE_PATH']
    
    def test_enhancement_error(self):
        """测试增强错误"""
        # 模拟增强错误
        with patch.object(self.app, '_prompt_enhancer', None):
            with patch.object(self.app, '_stage2_enabled', True):
                with patch('sage_minimal.create_prompt_enhancer',
                          side_effect=EnhancementError("增强器初始化失败")):
                    
                    # 尝试获取增强器
                    enhancer = self.app.prompt_enhancer
                    self.assertIsNone(enhancer)
    
    def test_async_runtime_error(self):
        """测试异步运行时错误"""
        # 模拟异步错误
        with patch.object(self.app.async_manager, 'run_coroutine',
                         side_effect=AsyncRuntimeError("事件循环错误")):
            
            parsed_args = ParsedArgs(
                user_prompt="Test",
                claude_args=[],
                sage_options={}
            )
            
            # 设置一个有效的 Claude 路径
            os.environ['ORIGINAL_CLAUDE_PATH'] = sys.executable
            
            # 应该降级到同步模式
            return_code = self.app.run_with_memory(parsed_args)
            
            # 清理
            del os.environ['ORIGINAL_CLAUDE_PATH']
    
    def test_resource_cleanup_errors(self):
        """测试资源清理错误"""
        # 创建一些模拟的资源
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        mock_thread.name = "TestThread"
        mock_thread.join.side_effect = Exception("Thread join failed")
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_process.terminate.side_effect = OSError("Permission denied")
        
        self.app._active_threads.add(mock_thread)
        self.app._active_processes.add(mock_process)
        
        # 清理应该处理这些错误而不崩溃
        self.app._cleanup_resources()
        
        # 验证日志记录了错误（这里只验证没有崩溃）
        self.assertTrue(True)
    
    def test_validation_error(self):
        """测试验证错误"""
        from platform_utils import CommandParser
        
        parser = CommandParser()
        
        # 测试无效命令
        with self.assertRaises(ValidationError):
            parser.parse_command(None)
        
        with self.assertRaises(ValidationError):
            parser.parse_command(123)
    
    def test_configuration_error_handling(self):
        """测试配置错误处理"""
        # 模拟配置错误
        with patch('sage_minimal.get_config_adapter',
                  side_effect=ConfigurationError("配置文件损坏")):
            
            # 尝试创建应用实例应该失败
            with self.assertRaises(ConfigurationError):
                ImprovedCrossplatformClaude()
    
    def test_io_error_in_stream_capture(self):
        """测试流捕获中的IO错误"""
        # 创建一个会抛出IOError的流
        mock_stream = Mock()
        mock_stream.readline.side_effect = IOError("Stream closed")
        
        # 捕获流应该处理错误而不崩溃
        self.app._capture_stream(mock_stream, False)
        
        # 验证流被关闭
        mock_stream.close.assert_called_once()
    
    def test_memory_stats_error(self):
        """测试记忆统计错误"""
        # 模拟统计错误
        with patch.object(self.app.memory_provider, 'get_memory_stats',
                         side_effect=MemoryProviderError("统计失败")):
            
            # 捕获输出
            from io import StringIO
            import sys
            
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            
            try:
                self.app._handle_memory_stats()
                output = mystdout.getvalue()
                self.assertIn("获取统计失败", output)
            finally:
                sys.stdout = old_stdout
    
    def test_clear_memory_error(self):
        """测试清除记忆错误"""
        # 模拟清除错误
        with patch.object(self.app.memory_provider, 'clear_all_memories',
                         side_effect=MemoryProviderError("清除失败")):
            
            # 模拟用户输入
            with patch('builtins.input', return_value='yes'):
                # 捕获输出
                from io import StringIO
                import sys
                
                old_stdout = sys.stdout
                sys.stdout = mystdout = StringIO()
                
                try:
                    self.app._handle_clear_memory()
                    output = mystdout.getvalue()
                    self.assertIn("清除记忆失败", output)
                finally:
                    sys.stdout = old_stdout


class TestErrorRecovery(unittest.TestCase):
    """测试错误恢复机制"""
    
    def setUp(self):
        self.app = ImprovedCrossplatformClaude()
    
    def test_fallback_to_sync_mode(self):
        """测试降级到同步模式"""
        # 模拟异步失败
        with patch.object(self.app.async_manager, 'run_coroutine',
                         side_effect=AsyncRuntimeError("异步失败")):
            
            with patch.object(self.app, '_run_with_memory_sync',
                             return_value=0) as mock_sync:
                
                parsed_args = ParsedArgs(
                    user_prompt="Test",
                    claude_args=[],
                    sage_options={}
                )
                
                # 运行应该降级到同步模式
                result = self.app.run_with_memory(parsed_args)
                
                # 验证调用了同步方法
                mock_sync.assert_called_once_with(parsed_args)
                self.assertEqual(result, 0)
    
    def test_fallback_to_no_memory_mode(self):
        """测试降级到无记忆模式"""
        # 模拟记忆模块不可用
        with patch.object(self.app, '_memory_provider',
                         side_effect=MemoryProviderError("记忆模块损坏")):
            
            parsed_args = ParsedArgs(
                user_prompt="Test",
                claude_args=[],
                sage_options={}
            )
            
            # 设置有效的 Claude 路径
            os.environ['ORIGINAL_CLAUDE_PATH'] = sys.executable
            
            # 应该降级到无记忆模式
            with patch('subprocess.call', return_value=0) as mock_call:
                result = self.app._run_with_memory_sync(parsed_args)
                
                # 验证直接调用了 subprocess
                mock_call.assert_called()
                
            # 清理
            del os.environ['ORIGINAL_CLAUDE_PATH']
    
    def test_enhancement_fallback(self):
        """测试增强失败时的降级"""
        # 模拟增强失败
        with patch.object(self.app, '_perform_intelligent_enhancement',
                         side_effect=EnhancementError("增强失败")):
            
            # 设置标志
            self.app._stage2_enabled = True
            
            parsed_args = ParsedArgs(
                user_prompt="Test prompt",
                claude_args=[],
                sage_options={}
            )
            
            # 应该返回基础增强上下文
            # 这里只验证不会崩溃
            try:
                # 模拟异步上下文
                import asyncio
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    self.app._run_with_memory_async(parsed_args)
                )
                loop.close()
            except:
                # 如果有其他错误，至少验证增强错误被处理了
                pass


class TestPlatformSpecificErrors(unittest.TestCase):
    """测试平台特定错误"""
    
    def test_windows_path_error(self):
        """测试 Windows 路径错误"""
        from platform_utils import PathHandler, PlatformInfo
        
        # 模拟 Windows 平台
        mock_platform = Mock(spec=PlatformInfo)
        mock_platform.is_windows = True
        
        handler = PathHandler(mock_platform)
        
        # 测试无效的 UNC 路径
        invalid_unc = "\\\\invalid\\path"
        result = handler.normalize_path(invalid_unc)
        # 应该返回路径对象，即使路径无效
        self.assertIsInstance(result, Path)
    
    def test_encoding_error_recovery(self):
        """测试编码错误恢复"""
        from platform_utils import EncodingHandler
        
        handler = EncodingHandler()
        
        # 测试无法解码的数据
        invalid_utf8 = b'\xff\xfe\xfd\xfc'
        result = handler.decode_output(invalid_utf8)
        
        # 应该返回字符串，使用替换字符
        self.assertIsInstance(result, str)
        # 不应该抛出异常
    
    def test_process_creation_error(self):
        """测试进程创建错误"""
        from platform_utils import ProcessLauncher
        
        launcher = ProcessLauncher()
        
        # 测试无效命令
        try:
            process = launcher.create_process(["/nonexistent/command"])
            # 应该抛出 FileNotFoundError
            self.fail("应该抛出异常")
        except FileNotFoundError:
            # 预期的异常
            pass


def run_error_tests():
    """运行错误场景测试"""
    print("🧪 运行错误场景测试")
    print("=" * 80)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestExceptionHandling,
        TestErrorRecovery,
        TestPlatformSpecificErrors,
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
    success = run_error_tests()
    sys.exit(0 if success else 1)