#!/usr/bin/env python3
"""
单元测试：验证sage_stop_hook.py修复后的验证逻辑
直接测试save_to_database方法中的验证逻辑
"""
import unittest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from hooks.scripts.sage_stop_hook import SageStopHook


class TestSageStopHookValidationFix(unittest.TestCase):
    """测试修复后的验证逻辑"""
    
    def setUp(self):
        """测试准备"""
        self.hook = SageStopHook()
        # Mock日志和执行器
        self.hook.logger = Mock()
        self.hook.executor = Mock()
        # Mock Sage core
        self.hook.sage_core = Mock()
        self.hook.sage_core.save_conversation = AsyncMock(return_value="test-id-123")
    
    def test_standard_conversation_accepted(self):
        """测试：标准对话（有user和assistant）应该被接受"""
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': '你好'},
                {'role': 'assistant', 'content': '你好！有什么可以帮助你的吗？'}
            ]
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        self.assertTrue(result)
        # 验证调用了正确的日志
        log_calls = [call[0][0] for call in self.hook.logger.info.call_args_list]
        self.assertTrue(any("Standard conversation" in call for call in log_calls))
        
    def test_assistant_only_tool_call_accepted(self):
        """测试：仅assistant的工具调用结果应该被接受"""
        conversation_data = {
            'messages': [
                {'role': 'assistant', 'content': 'Tool execution result: Success'}
            ]
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        self.assertTrue(result)
        # 验证记录了正确的日志
        log_calls = [call[0][0] for call in self.hook.logger.info.call_args_list]
        self.assertTrue(any("Assistant-only message detected" in call for call in log_calls))
    
    def test_user_only_message_accepted(self):
        """测试：仅user的消息应该被接受"""
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': '这是一个测试命令'}
            ]
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        self.assertTrue(result)
        log_calls = [call[0][0] for call in self.hook.logger.info.call_args_list]
        self.assertTrue(any("User-only message detected" in call for call in log_calls))
    
    def test_both_empty_rejected(self):
        """测试：user和assistant都为空时应该被拒绝"""
        conversation_data = {
            'messages': []
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        self.assertFalse(result)
        self.hook.logger.warning.assert_any_call(
            "Both user_input and assistant_response are empty, rejecting save"
        )
    
    def test_system_message_handled(self):
        """测试：系统消息应该被正确处理"""
        conversation_data = {
            'messages': [
                {'role': 'system', 'content': 'System configuration updated'},
                {'role': 'assistant', 'content': 'Configuration applied'}
            ]
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        self.assertTrue(result)
        # 验证assistant消息被正确提取
        log_calls = [call[0][0] for call in self.hook.logger.info.call_args_list]
        self.assertTrue(any("Assistant-only" in call for call in log_calls))
    
    def test_mixed_messages_correct_extraction(self):
        """测试：混合消息类型的正确提取"""
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': '开始任务'},
                {'role': 'assistant', 'content': '正在执行...'},
                {'role': 'assistant', 'content': '[Tool Result] 执行成功'},
                {'role': 'user', 'content': '继续下一步'}
            ]
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        self.assertTrue(result)
        # 验证提取了最后的user和所有assistant消息
        self.hook.sage_core.save_conversation.assert_called()
        
    def test_empty_content_messages_rejected(self):
        """测试：空内容消息应该被拒绝"""
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': ''},
                {'role': 'assistant', 'content': ''}
            ]
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        self.assertFalse(result)
        self.hook.logger.warning.assert_any_call(
            "Both user_input and assistant_response are empty, rejecting save"
        )
    
    def test_whitespace_only_messages_handled(self):
        """测试：仅空白字符的消息处理"""
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': '   '},
                {'role': 'assistant', 'content': '\n\t'}
            ]
        }
        
        result = self.hook.save_to_database(conversation_data)
        
        # 根据storage.py的验证逻辑，空白字符串会被拒绝
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)