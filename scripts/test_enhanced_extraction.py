#!/usr/bin/env python3
"""
测试增强版Stop Hook数据提取功能
"""

import sys
import os
sys.path.append('/Users/jet/Sage/hooks/scripts')

from sage_archiver_enhanced import EnhancedSageArchiver

def test_extraction():
    """测试新的数据提取功能"""
    print("=== 测试增强版数据提取功能 ===")
    
    archiver = EnhancedSageArchiver()
    
    # 使用一个真实的transcript文件进行测试
    transcript_path = "/Users/jet/.claude/projects/-Users-jet-sage/048573a6-dac5-4859-8d18-974b245340ea.jsonl"
    
    if not os.path.exists(transcript_path):
        print("❌ 测试文件不存在")
        return False
    
    print(f"📂 测试文件: {transcript_path}")
    
    # 执行提取
    user_msg, assistant_msg, tool_calls, tool_results = archiver.extract_complete_interaction(transcript_path)
    
    print(f"\n📊 提取结果:")
    print(f"   用户消息长度: {len(user_msg) if user_msg else 0}")
    print(f"   助手消息长度: {len(assistant_msg) if assistant_msg else 0}")
    print(f"   工具调用数量: {len(tool_calls)}")
    print(f"   工具结果数量: {len(tool_results)}")
    
    # 检查是否包含思维链
    has_thinking = assistant_msg and "[思维过程]" in assistant_msg if assistant_msg else False
    print(f"   包含思维链: {'✅' if has_thinking else '❌'}")
    
    # 检查是否包含完整历史
    has_history = assistant_msg and "[完整会话历史]" in assistant_msg if assistant_msg else False
    print(f"   包含完整历史: {'✅' if has_history else '❌'}")
    
    # 检查工具结果匹配
    results_match = len(tool_results) > 0
    print(f"   工具结果匹配: {'✅' if results_match else '❌'}")
    
    # 显示部分内容示例
    if assistant_msg:
        print(f"\n📝 助手消息预览 (前200字符):")
        print(f"   {assistant_msg[:200]}...")
    
    if tool_calls:
        print(f"\n🔧 工具调用示例:")
        for i, call in enumerate(tool_calls[:3]):
            print(f"   {i+1}. {call['name']} (ID: {call['id'][:8]}...)")
    
    if tool_results:
        print(f"\n📋 工具结果示例:")
        for i, result in enumerate(tool_results[:3]):
            content_preview = str(result['content'])[:100]
            print(f"   {i+1}. {result['tool_use_id'][:8]}... - {content_preview}...")
    
    # 总体评估
    score = 0
    if user_msg: score += 20
    if assistant_msg: score += 20
    if has_thinking: score += 25
    if has_history: score += 25
    if results_match: score += 10
    
    print(f"\n🎯 功能完整性评分: {score}/100")
    
    if score >= 80:
        print("✅ 增强版数据提取功能正常工作")
        return True
    else:
        print("❌ 数据提取功能需要进一步优化")
        return False

if __name__ == "__main__":
    success = test_extraction()
    sys.exit(0 if success else 1)