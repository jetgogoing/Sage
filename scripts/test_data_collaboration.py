#!/usr/bin/env python3
"""
测试Hooks数据协作机制
验证Stop Hook能够成功整合Pre/Post Tool数据
"""

import json
import sys
import time
import subprocess
from pathlib import Path
import uuid

# 添加hooks脚本路径
sys.path.append('/Users/jet/Sage/hooks/scripts')

from hook_data_aggregator import get_aggregator
from sage_pre_tool_capture import SagePreToolCapture
from sage_post_tool_capture import SagePostToolCapture
from sage_archiver_enhanced import EnhancedSageArchiver

def simulate_complete_workflow():
    """模拟完整的工具调用工作流"""
    print("=== 测试完整的Hooks数据协作机制 ===\n")
    
    session_id = f"collab_test_{int(time.time())}"
    
    # 1. 模拟多个工具调用
    tool_calls = [
        {"name": "Read", "input": {"file_path": "/test/file1.py"}},
        {"name": "Edit", "input": {"file_path": "/test/file1.py", "old_string": "foo", "new_string": "bar"}},
        {"name": "mcp__zen__debug", "input": {"step": "Analyzing issue", "model": "openai/o3"}},
        {"name": "Bash", "input": {"command": "pytest tests/"}}
    ]
    
    call_ids = []
    
    print("1. 执行工具调用序列...")
    for i, tool_info in enumerate(tool_calls):
        print(f"   调用 {i+1}: {tool_info['name']}")
        
        # PreToolUse
        pre_input = {
            "sessionId": session_id,
            "toolName": tool_info['name'],
            "toolInput": tool_info['input'],
            "user": "test_user",
            "environment": {"cwd": "/Users/jet/Sage"}
        }
        
        pre_capturer = SagePreToolCapture()
        pre_result = pre_capturer.process_hook(pre_input)
        call_id = pre_result.get('call_id')
        call_ids.append(call_id)
        
        # 模拟工具执行
        time.sleep(0.05)
        
        # PostToolUse
        post_input = {
            "sessionId": session_id,
            "toolName": tool_info['name'],
            "toolOutput": generate_mock_output(tool_info['name']),
            "executionTimeMs": 100 + i * 50,
            "isError": False
        }
        
        post_capturer = SagePostToolCapture()
        post_capturer.process_hook(post_input)
    
    print(f"   ✅ 完成 {len(tool_calls)} 个工具调用\n")
    
    # 2. 测试数据聚合
    print("2. 测试数据聚合器...")
    aggregator = get_aggregator()
    
    # 聚合会话数据
    aggregated = aggregator.aggregate_session_tools(session_id)
    
    print(f"   - 捕获工具调用: {aggregated['stats']['total_tools']}")
    print(f"   - 成功调用: {aggregated['stats']['successful_tools']}")
    print(f"   - ZEN工具: {aggregated['stats']['zen_tools']}")
    print(f"   - 总执行时间: {aggregated['stats']['total_execution_time']}ms")
    
    # 验证数据完整性
    if aggregated['stats']['total_tools'] == len(tool_calls):
        print("   ✅ 数据聚合成功\n")
    else:
        print(f"   ❌ 数据聚合失败: 期望 {len(tool_calls)}, 实际 {aggregated['stats']['total_tools']}\n")
        return False
    
    # 3. 测试Stop Hook增强
    print("3. 测试Stop Hook数据增强...")
    
    # 准备transcript数据
    transcript_dir = Path.home() / '.sage_test_transcript'
    transcript_dir.mkdir(exist_ok=True)
    transcript_file = transcript_dir / 'transcript.jsonl'
    
    # 写入模拟transcript
    with open(transcript_file, 'w') as f:
        # User消息
        f.write(json.dumps({
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Test collaboration mechanism"}]
            }
        }) + "\n")
        
        # Assistant消息（包含工具调用）
        tool_use_content = []
        for i, tool_info in enumerate(tool_calls):
            tool_use_content.append({
                "type": "tool_use",
                "name": tool_info['name'],
                "input": tool_info['input'],
                "id": call_ids[i]
            })
        
        f.write(json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Executing tools..."},
                    *tool_use_content
                ]
            }
        }) + "\n")
    
    # 调用Stop Hook
    archiver = EnhancedSageArchiver()
    
    # Mock process_hook的部分逻辑
    user_msg, assistant_msg, tools, results = archiver.extract_complete_interaction(str(transcript_file))
    
    if tools and len(tools) == len(tool_calls):
        print(f"   ✅ Stop Hook提取到 {len(tools)} 个工具调用")
    else:
        print(f"   ❌ Stop Hook提取失败")
        return False
    
    # 测试数据增强
    enhanced_chain, enhanced_metadata = aggregator.enhance_stop_hook_data(
        session_id, user_msg, assistant_msg, tools, results
    )
    
    print(f"   - 增强工具链长度: {len(enhanced_chain)}")
    print(f"   - 数据完整性评分: {enhanced_metadata['data_completeness_score']:.2%}")
    print(f"   - 数据源: {enhanced_metadata['data_sources']}")
    
    # 验证增强数据
    if len(enhanced_chain) == len(tool_calls):
        print("   ✅ 数据增强成功")
        
        # 检查增强内容
        for i, enhanced_call in enumerate(enhanced_chain):
            if not enhanced_call.get('tool_input') or not enhanced_call.get('tool_output'):
                print(f"   ❌ 工具 {i+1} 缺少输入或输出数据")
                return False
    else:
        print("   ❌ 数据增强失败")
        return False
    
    # 清理
    transcript_file.unlink()
    transcript_dir.rmdir()
    
    # 清理测试数据
    for call_id in call_ids:
        complete_file = Path.home() / '.sage_hooks_temp' / f'complete_{call_id}.json'
        if complete_file.exists():
            complete_file.unlink()
    
    return True

def generate_mock_output(tool_name):
    """生成模拟的工具输出"""
    if tool_name == "Read":
        return {
            "content": "File content here...",
            "lines": 100
        }
    elif tool_name == "Edit":
        return {
            "status": "success",
            "message": "File edited successfully"
        }
    elif tool_name.startswith("mcp__zen__"):
        return {
            "status": "complete",
            "content": "Deep analysis complete",
            "metadata": {
                "model_used": "openai/o3",
                "provider": "openrouter"
            },
            "confidence": "high",
            "findings": "Key insights from analysis"
        }
    elif tool_name == "Bash":
        return {
            "stdout": "All tests passed",
            "stderr": "",
            "exit_code": 0
        }
    else:
        return {"result": "success"}

def test_cross_project_tracking():
    """测试跨项目会话追踪"""
    print("\n=== 测试跨项目会话追踪 ===\n")
    
    aggregator = get_aggregator()
    
    # 获取跨项目会话信息
    cross_sessions = aggregator.get_cross_project_sessions(hours=1)
    
    print(f"最近1小时的会话数: {len(cross_sessions)}")
    
    for session in cross_sessions[:3]:  # 显示前3个
        print(f"\n会话 {session['session_id'][:8]}...")
        print(f"  - 涉及项目: {len(session['projects'])}")
        print(f"  - 工具调用: {session['tool_count']}")
        print(f"  - 跨项目: {'是' if session['is_cross_project'] else '否'}")
    
    return True

def test_session_report():
    """测试会话报告生成"""
    print("\n=== 测试会话报告生成 ===\n")
    
    # 创建测试会话
    session_id = f"report_test_{int(time.time())}"
    
    # 生成一些测试数据
    tool_names = ["Read", "mcp__zen__debug", "Edit", "Bash"]
    for tool_name in tool_names:
        # Pre
        pre_input = {
            "sessionId": session_id,
            "toolName": tool_name,
            "toolInput": {"test": "data"}
        }
        pre_capturer = SagePreToolCapture()
        pre_result = pre_capturer.process_hook(pre_input)
        
        # Post
        post_input = {
            "sessionId": session_id,
            "toolName": tool_name,
            "toolOutput": generate_mock_output(tool_name),
            "executionTimeMs": 100,
            "isError": False
        }
        post_capturer = SagePostToolCapture()
        post_capturer.process_hook(post_input)
    
    # 生成报告
    aggregator = get_aggregator()
    report = aggregator.generate_session_report(session_id)
    
    print(f"会话ID: {report['session_id'][:16]}...")
    print(f"\n摘要:")
    print(f"  - 总工具调用: {report['summary']['total_tools']}")
    print(f"  - 成功率: {report['summary']['success_rate']:.1f}%")
    print(f"  - ZEN工具使用: {report['summary']['zen_tools_used']}")
    print(f"  - 总执行时间: {report['summary']['total_execution_time_ms']}ms")
    print(f"\n工具分布:")
    for tool, count in report['tool_breakdown'].items():
        print(f"  - {tool}: {count}")
    
    return True

def test_data_completeness_scoring():
    """测试数据完整性评分算法"""
    print("\n=== 测试数据完整性评分 ===\n")
    
    aggregator = get_aggregator()
    
    # 场景1: 完美匹配
    transcript_tools = [{"name": "Read"}, {"name": "Edit"}]
    enhanced_chain = [
        {"tool_input": {"file": "test"}, "tool_output": {"content": "data"}},
        {"tool_input": {"old": "a"}, "tool_output": {"status": "ok"}}
    ]
    
    score1 = aggregator.calculate_completeness_score(transcript_tools, [], enhanced_chain)
    print(f"场景1 (完美匹配): {score1:.2%}")
    
    # 场景2: 部分捕获
    transcript_tools = [{"name": "Read"}, {"name": "Edit"}, {"name": "Bash"}]
    enhanced_chain = [
        {"tool_input": {"file": "test"}, "tool_output": {"content": "data"}},
        {"tool_input": {"old": "a"}, "tool_output": None}  # 缺少输出
    ]
    
    score2 = aggregator.calculate_completeness_score(transcript_tools, [], enhanced_chain)
    print(f"场景2 (部分捕获): {score2:.2%}")
    
    # 场景3: 无工具调用
    score3 = aggregator.calculate_completeness_score([], [], [])
    print(f"场景3 (无工具调用): {score3:.2%}")
    
    return True

if __name__ == "__main__":
    print("开始测试Hooks数据协作机制\n")
    
    # 运行测试
    test1 = simulate_complete_workflow()
    test2 = test_cross_project_tracking()
    test3 = test_session_report()
    test4 = test_data_completeness_scoring()
    
    # 总结
    print("\n=== 测试总结 ===")
    print(f"完整工作流测试: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"跨项目追踪测试: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"会话报告测试: {'✅ 通过' if test3 else '❌ 失败'}")
    print(f"完整性评分测试: {'✅ 通过' if test4 else '❌ 失败'}")
    
    all_passed = test1 and test2 and test3 and test4
    print(f"\n总体结果: {'✅ 全部通过' if all_passed else '❌ 有失败项'}")
    
    # 清理旧数据
    if all_passed:
        aggregator = get_aggregator()
        cleaned = aggregator.cleanup_old_data(48)
        print(f"\n清理了 {cleaned} 个旧文件")
    
    sys.exit(0 if all_passed else 1)