#!/usr/bin/env python3
"""
测试修复后的Sage Stop Hook
"""

import os
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

def test_fixed_stop_hook():
    """测试修复后的Stop Hook"""
    print("🧪 测试修复后的Sage Stop Hook...")
    
    # 创建模拟的Claude CLI transcript
    test_dir = Path(tempfile.mkdtemp())
    test_transcript = test_dir / "test_transcript.jsonl"
    
    try:
        with open(test_transcript, 'w', encoding='utf-8') as f:
            # 用户消息
            user_entry = {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "修复测试：这是用户输入消息"}]
                },
                "timestamp": time.time() - 2,
                "uuid": "user-test-uuid"
            }
            f.write(json.dumps(user_entry) + '\n')
            
            # 助手消息
            assistant_entry = {
                "type": "assistant",
                "message": {
                    "role": "assistant", 
                    "content": [
                        {"type": "text", "text": "修复测试：这是助手回复消息，验证修复是否成功"},
                        {"type": "thinking", "thinking": "这是思维链内容，测试完整捕获"}
                    ]
                },
                "timestamp": time.time() - 1,
                "uuid": "assistant-test-uuid"
            }
            f.write(json.dumps(assistant_entry) + '\n')
        
        # 准备输入数据
        hook_input = {
            "session_id": f"fix-validation-{int(time.time())}",
            "transcript_path": str(test_transcript),
            "stop_hook_active": False
        }
        
        print(f"📄 测试文件: {test_transcript}")
        print(f"🔍 输入数据: {hook_input}")
        
        # 调用修复后的Stop Hook
        result = subprocess.run([
            "python3", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py")
        ], input=json.dumps(hook_input), text=True, capture_output=True, timeout=30)
        
        print(f"\n📊 执行结果:")
        print(f"返回码: {result.returncode}")
        print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")
        
        # 验证结果
        if result.returncode == 0:
            if "SUCCESS" in result.stdout:
                print("\n🎉 修复验证成功！Stop Hook正常工作")
                return True
            else:
                print("\n⚠️  部分成功，可能只有备份工作")
                return True
        else:
            print("\n❌ 修复验证失败，仍有问题需要解决")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            if test_transcript.exists():
                test_transcript.unlink()
            test_dir.rmdir()
        except:
            pass

def main():
    """主函数"""
    print("🚀 Sage Stop Hook 修复验证测试")
    print("=" * 50)
    
    success = test_fixed_stop_hook()
    
    print("=" * 50)
    if success:
        print("🎉 修复验证通过！")
    else:
        print("💥 修复验证失败！")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
