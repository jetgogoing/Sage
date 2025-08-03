#!/usr/bin/env python3
"""
测试完整的Hook功能链路：UserPromptSubmit + 数据保存
"""
import sys
import os
import asyncio
sys.path.insert(0, '/Users/jet/Sage/hooks/scripts')
sys.path.insert(0, '/Users/jet/Sage')

from sage_prompt_enhancer import SagePromptEnhancer

def test_full_hook_chain():
    """测试完整的Hook功能链路"""
    try:
        print("🔍 测试完整Hook功能链路...")
        
        # 创建Hook实例
        enhancer = SagePromptEnhancer()
        
        # 模拟用户输入
        user_input = "看看数据库里有哪些记忆,返回最近10个记忆的内容"
        
        print(f"📤 用户输入: {user_input}")
        
        # 1. 调用UserPromptSubmit Hook (生成增强提示)
        enhanced_prompt = enhancer._call_real_sage_mcp(user_input)
        print(f"📥 增强提示: {enhanced_prompt}")
        
        # 2. 模拟助手回复
        assistant_response = "我来帮您查看数据库中的记忆。通过分析PostgreSQL数据库，我发现了12条记忆记录..."
        
        # 3. 测试数据保存功能
        print("\n🔄 测试数据保存到sage_core...")
        
        async def save_conversation():
            from sage_core import SageCore
            sage = SageCore()
            await sage.initialize({})
            await sage.save_conversation(user_input, assistant_response)
            return True
            
        # 保存对话
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, save_conversation())
                    save_result = future.result(timeout=10)
            else:
                save_result = asyncio.run(save_conversation())
                
            if save_result:
                print("✅ 对话保存成功！")
                
                # 4. 验证数据库中的数据
                print("\n🔍 验证数据库中的最新记录...")
                import subprocess
                
                result = subprocess.run([
                    'docker', 'exec', 'sage-db', 'psql', '-U', 'sage', '-d', 'sage_memory',
                    '-c', "SELECT COUNT(*) as total, MAX(created_at) as latest FROM memories;"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"📊 数据库状态: {result.stdout.strip()}")
                    return True
                else:
                    print(f"❌ 数据库查询失败: {result.stderr}")
                    return False
            else:
                print("❌ 对话保存失败")
                return False
                
        except Exception as e:
            print(f"❌ 保存过程出错: {e}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_hook_chain()
    print(f"\n🎯 完整链路测试结果: {'成功' if success else '失败'}")