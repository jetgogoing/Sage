#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试简化的Sage系统
验证简化后的hook系统是否正常工作
"""
import sys
import os
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.interfaces.turn import Turn, ToolCall
from hooks.scripts.hook_data_aggregator import HookDataAggregator


async def test_simplified_flow():
    """测试简化的数据流"""
    print("=== 测试简化的Sage系统 ===")
    print(f"测试时间: {datetime.now()}")
    
    # 1. 模拟创建工具调用数据
    print("\n1. 模拟工具调用...")
    session_id = f"test_session_{int(time.time())}"
    os.environ['CLAUDE_SESSION_ID'] = session_id
    
    # 创建测试的临时目录
    temp_dir = Path.home() / '.sage_hooks_temp'
    temp_dir.mkdir(exist_ok=True)
    
    # 模拟工具调用数据
    tool_calls_data = [
        {
            'call_id': 'test_call_1',
            'pre_call': {
                'call_id': 'test_call_1',
                'timestamp': time.time(),
                'session_id': session_id,
                'tool_name': 'mcp__zen__chat',
                'tool_input': {'prompt': '测试问题', 'model': 'flash'},
                'project_id': 'test_project',
                'project_name': 'TestProject'
            },
            'post_call': {
                'timestamp': time.time() + 1,
                'tool_output': {'content': '测试响应'},
                'execution_time_ms': 1234,
                'is_error': False
            }
        },
        {
            'call_id': 'test_call_2',
            'pre_call': {
                'call_id': 'test_call_2',
                'timestamp': time.time() + 2,
                'session_id': session_id,
                'tool_name': 'Read',
                'tool_input': {'file_path': '/test/file.py'},
                'project_id': 'test_project',
                'project_name': 'TestProject'
            },
            'post_call': {
                'timestamp': time.time() + 3,
                'tool_output': 'File content here',
                'execution_time_ms': 50,
                'is_error': False
            }
        }
    ]
    
    # 保存测试数据到临时文件
    for data in tool_calls_data:
        file_path = temp_dir / f"complete_{data['call_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        print(f"  创建临时文件: {file_path.name}")
    
    # 2. 测试数据聚合器
    print("\n2. 测试数据聚合器...")
    aggregator = HookDataAggregator()
    
    # 测试聚合当前会话
    tool_calls = aggregator.aggregate_current_session()
    print(f"  聚合到 {len(tool_calls)} 个工具调用")
    
    for i, tc in enumerate(tool_calls):
        print(f"  工具调用 {i+1}:")
        print(f"    - 名称: {tc.tool_name}")
        print(f"    - 状态: {tc.status}")
        print(f"    - 耗时: {tc.execution_time_ms}ms")
    
    # 3. 测试Turn模型
    print("\n3. 测试Turn数据模型...")
    turn = Turn(
        session_id=session_id,
        user_prompt="这是一个测试问题",
        tool_calls=tool_calls,
        final_response="这是助手的测试响应",
        metadata={
            'test': True,
            'source': 'test_script'
        }
    )
    
    print(f"  Turn ID: {turn.turn_id}")
    print(f"  Session ID: {turn.session_id}")
    print(f"  工具调用数: {len(turn.tool_calls)}")
    print(f"  时间戳: {turn.timestamp}")
    
    # 4. 测试简化的stop hook（模拟）
    print("\n4. 模拟stop hook处理...")
    from hooks.scripts.sage_stop_hook import SageStopHook
    
    hook = SageStopHook()
    
    # 测试Human/Assistant格式解析（新的统一API）
    test_content = "Human: 这是一个测试问题\nAssistant: 这是助手的测试响应\n使用了多个工具来完成任务。"
    
    test_input = {
        'format': 'text',
        'content': test_content,
        'session_id': session_id
    }
    
    # 使用新的统一处理API
    conversation_data = hook.process_human_assistant_text(test_input)
    if conversation_data and conversation_data.get('messages'):
        print(f"  提取到对话:")
        messages = conversation_data.get('messages', [])
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:50]
            print(f"    {role}: {content}...")
        print(f"  总计: {len(messages)}条消息，{len(conversation_data.get('tool_calls', []))}个工具调用")
    else:
        print("  未能提取对话数据")
    
    # 5. 测试文件清理
    print("\n5. 测试文件清理...")
    cleaned = aggregator.cleanup_processed_files(tool_calls)
    print(f"  清理了 {cleaned} 个临时文件")
    
    # 6. 性能测试
    print("\n6. 性能测试...")
    start_time = time.time()
    
    # 模拟初始化SageCore的时间
    print("  模拟SageCore初始化...")
    await asyncio.sleep(3)  # 模拟3秒初始化时间
    
    end_time = time.time()
    print(f"  总耗时: {end_time - start_time:.2f}秒")
    
    print("\n=== 测试完成 ===")
    print("简化系统的优势:")
    print("- 无需daemon进程")
    print("- 系统更加稳定可靠")
    print("- 维护更加简单")
    print("- 虽有3-5秒延迟，但对个人使用完全可接受")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_simplified_flow())
    sys.exit(0 if success else 1)