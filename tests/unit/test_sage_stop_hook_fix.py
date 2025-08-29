#!/usr/bin/env python3
"""
单元测试：验证sage_stop_hook.py修复后的验证逻辑
"""
import unittest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from hooks.scripts.sage_stop_hook import SageStopHook


class TestSageStopHookFix(unittest.TestCase):
    """测试修复后的验证逻辑"""
    
    def setUp(self):
        """测试准备"""
        self.hook = SageStopHook()
        self.hook.logger = Mock()
        self.hook.executor = Mock()
    
    def test_standard_conversation_accepted(self):
        """测试：标准对话（有user和assistant）应该被接受"""
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': '你好'},
                {'role': 'assistant', 'content': '你好！有什么可以帮助你的吗？'}
            ]
        }
        
        with patch.object(self.hook, '_save_to_database_sync') as mock_save:
            mock_save.return_value = True
            result = self.hook.save_conversation(conversation_data)
            
        self.assertTrue(result)
        self.hook.logger.info.assert_called()
        
    def test_assistant_only_tool_call_accepted(self):
        """测试：仅assistant的工具调用结果应该被接受"""
        conversation_data = {
            'messages': [
                {'role': 'assistant', 'content': 'Tool execution result: Success'}
            ]
        }
        
        with patch.object(self.hook, '_save_to_database_sync') as mock_save:
            mock_save.return_value = True
            result = self.hook.save_conversation(conversation_data)
            
        self.assertTrue(result)
        # 验证记录了正确的日志
        self.hook.logger.info.assert_any_call(
            "Assistant-only message detected (tool call result or system message): 32 chars"
        )
    
    def test_user_only_message_accepted(self):
        """测试：仅user的消息应该被接受"""
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': '这是一个测试命令'}
            ]
        }
        
        with patch.object(self.hook, '_save_to_database_sync') as mock_save:
            mock_save.return_value = True
            result = self.hook.save_conversation(conversation_data)
            
        self.assertTrue(result)
        self.hook.logger.info.assert_any_call(
            "User-only message detected: 8 chars"
        )
    
    def test_both_empty_rejected(self):
        """测试：user和assistant都为空时应该被拒绝"""
        conversation_data = {
            'messages': []
        }
        
        result = self.hook.save_conversation(conversation_data)
        
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
        
        with patch.object(self.hook, '_save_to_database_sync') as mock_save:
            mock_save.return_value = True
            result = self.hook.save_conversation(conversation_data)
            
        self.assertTrue(result)
    
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
        
        with patch.object(self.hook, '_save_to_database_sync') as mock_save:
            mock_save.return_value = True
            result = self.hook.save_conversation(conversation_data)
            
        self.assertTrue(result)
        # 验证正确提取了最后的user-assistant对
        mock_save.assert_called_once()
        args = mock_save.call_args[0]
        self.assertEqual(args[0], '继续下一步')  # user_input
        self.assertIn('[Tool Result] 执行成功', args[1])  # assistant_response包含工具结果


if __name__ == '__main__':
    unittest.main(verbosity=2)