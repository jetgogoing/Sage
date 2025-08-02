#!/usr/bin/env python3
"""
测试增强版用户消息解析器
验证 _parse_claude_cli_message_enriched 方法也能正确处理字符串和数组格式
"""

import sys
import os
from pathlib import Path

# 添加hooks路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'hooks' / 'scripts'))

from sage_stop_hook import SageStopHook

def test_enriched_string_content():
    """测试增强版解析器的字符串格式"""
    hook = SageStopHook()
    
    entry = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': '这是增强版解析器测试'
        },
        'timestamp': '2025-08-02T01:00:00.000Z',
        'uuid': 'test-uuid'
    }
    
    result = hook._parse_claude_cli_message_enriched(entry, {})
    print("增强版字符串格式测试:")
    print(f"  输入: {entry['message']['content']}")
    print(f"  输出: {result['content'] if result else 'None'}")
    print(f"  角色: {result['role'] if result else 'None'}")
    
    return result and result['content'] == '这是增强版解析器测试'

def test_enriched_tool_result():
    """测试增强版解析器的工具结果格式"""
    hook = SageStopHook()
    
    entry = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': [
                {
                    'tool_use_id': 'toolu_123',
                    'type': 'tool_result',
                    'content': '增强版工具结果测试',
                    'is_error': False
                }
            ]
        },
        'timestamp': '2025-08-02T01:00:00.000Z',
        'uuid': 'test-uuid'
    }
    
    result = hook._parse_claude_cli_message_enriched(entry, {})
    print("\n增强版工具结果格式测试:")
    print(f"  输入: {entry['message']['content']}")
    print(f"  输出: {result['content'] if result else 'None'}")
    print(f"  角色: {result['role'] if result else 'None'}")
    
    return result and result['content'] == '增强版工具结果测试'

def main():
    print("开始测试增强版用户消息解析器...")
    
    try:
        test1 = test_enriched_string_content()
        test2 = test_enriched_tool_result()
        
        print(f"\n测试结果:")
        print(f"  增强版字符串格式测试: {'✅ 通过' if test1 else '❌ 失败'}")
        print(f"  增强版工具结果格式测试: {'✅ 通过' if test2 else '❌ 失败'}")
        
        if all([test1, test2]):
            print("\n🎉 增强版解析器测试通过！")
            return 0
        else:
            print("\n❌ 部分测试失败")
            return 1
            
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())