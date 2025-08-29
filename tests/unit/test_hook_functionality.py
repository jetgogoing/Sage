#!/usr/bin/env python3
"""
测试修复后的Hook功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts"))

from sage_prompt_enhancer import SagePromptEnhancer

def test_fixed_hook():
    """测试修复后的Hook功能"""
    try:
        print("🔍 测试修复后的Hook功能...")
        
        # 创建Hook实例
        enhancer = SagePromptEnhancer()
        
        # 测试上下文
        test_context = "我需要优化Python代码性能，特别是数据库查询方面"
        
        print(f"📤 测试输入: {test_context}")
        
        # 调用修复后的MCP功能
        result = enhancer._call_real_sage_mcp(test_context)
        
        print(f"📥 Hook响应: {result}")
        print(f"📏 响应长度: {len(result)} 字符")
        
        # 检查是否是降级响应
        fallback_responses = [
            "根据上下文，我可以为您提供更具针对性的技术建议和解决方案",
            "基于您的编程背景，我可以帮您解决技术问题",
            "我来帮您分析和解决这个问题"
        ]
        
        is_fallback = any(fallback in result for fallback in fallback_responses)
        
        if is_fallback:
            print("⚠️  收到降级响应，MCP调用可能仍有问题")
        else:
            print("✅ 收到真实MCP响应，功能修复成功！")
            
        return not is_fallback
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_hook()
    print(f"\n🎯 测试结果: {'成功' if success else '失败'}")