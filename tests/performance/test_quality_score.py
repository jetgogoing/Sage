#!/usr/bin/env python3
"""
测试质量评分修复效果
"""

import sys
import os
sys.path.append('/Users/jet/Sage/hooks/scripts')

from hook_data_aggregator import HookDataAggregator

def test_quality_scoring():
    """测试质量评分机制"""
    print("=== 测试质量评分修复效果 ===")
    
    aggregator = HookDataAggregator()
    
    # 获取最近的会话数据
    sessions = aggregator.get_cross_project_sessions(1)  # 最近1小时
    
    if not sessions:
        print("❌ 没有找到最近的会话数据")
        return False
    
    latest_session = sessions[0]
    session_id = latest_session['session_id']
    
    print(f"📊 分析会话: {session_id}")
    print(f"   工具调用总数: {latest_session['tool_count']}")
    
    # 聚合会话数据
    session_data = aggregator.aggregate_session_tools(session_id)
    
    print(f"   Pre/Post配对记录: {len(session_data['tool_records'])}")
    
    # 检查最新记录的数据质量
    if session_data['tool_records']:
        latest_record = session_data['tool_records'][-1]
        pre_call = latest_record.get('pre_call', {})
        post_call = latest_record.get('post_call', {})
        
        print(f"\n🔍 最新工具调用分析:")
        print(f"   工具名: {pre_call.get('tool_name', 'unknown')}")
        print(f"   有输入数据: {'✅' if pre_call.get('tool_input') else '❌'}")
        print(f"   有输出数据: {'✅' if post_call.get('tool_output') else '❌'}")
        
        tool_output = post_call.get('tool_output', {})
        if isinstance(tool_output, dict):
            print(f"   输出字段数: {len(tool_output)}")
            print(f"   输出内容预览: {str(tool_output)[:100]}...")
        
        # 测试质量评分逻辑
        mock_tool_calls = [{'name': 'test', 'input': {}}]
        mock_tool_results = [{'content': 'test result'}] 
        mock_enhanced_chain = [latest_record.get('pre_call', {})]
        
        # 直接调用评分函数
        score = aggregator.calculate_completeness_score(
            mock_tool_calls, mock_tool_results, 
            [{'tool_input': pre_call.get('tool_input'), 'tool_output': post_call.get('tool_output')}]
        )
        
        print(f"\n🎯 质量评分测试结果: {score:.2%}")
        
        return score > 0.5
    
    return False

if __name__ == "__main__":
    success = test_quality_scoring()
    sys.exit(0 if success else 1)