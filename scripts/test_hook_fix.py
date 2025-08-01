#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Hook 修复效果
"""
import sys
import json
import subprocess
from pathlib import Path

def create_test_hook_data():
    """创建测试用的 hook 数据"""
    return {
        "sessionDir": "/tmp/test_session",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "测试Hook修复功能"}]
            },
            {
                "role": "assistant", 
                "content": [{"type": "text", "text": "这是一个测试Hook修复的响应"}]
            }
        ],
        "metadata": {
            "project_name": "TestHookFix",
            "timestamp": "2025-07-31T16:50:00Z"
        }
    }

def test_hook_directly():
    """直接测试 hook 脚本"""
    print("🧪 直接测试 Hook 脚本...")
    
    # 定位 hook 脚本
    project_root = Path(__file__).parent.parent
    hook_script = project_root / "hooks" / "scripts" / "sage_archiver_enhanced.py"
    
    if not hook_script.exists():
        print(f"❌ Hook 脚本不存在: {hook_script}")
        return False
    
    # 创建测试数据
    test_data = create_test_hook_data()
    
    try:
        # 调用 hook 脚本
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(test_data),
            text=True,
            capture_output=True,
            timeout=30
        )
        
        print(f"📋 返回码: {result.returncode}")
        
        if result.stdout:
            print("📤 标准输出:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️  标准错误:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Hook 脚本执行超时")
        return False
    except Exception as e:
        print(f"❌ 执行Hook脚本时出错: {e}")
        return False

def check_log_file():
    """检查日志文件的最新条目"""
    print("\n📋 检查Hook日志...")
    
    log_file = Path("/Users/jet/Sage/hooks/logs/archiver_enhanced.log")
    
    if not log_file.exists():
        print("❌ 日志文件不存在")
        return
    
    try:
        # 读取最后几行日志
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 显示最后5行
        print("📄 最新日志条目:")
        for line in lines[-5:]:
            print(f"   {line.strip()}")
            
    except Exception as e:
        print(f"❌ 读取日志文件失败: {e}")

def verify_dependencies():
    """验证所有依赖是否已安装"""
    print("\n🔍 验证依赖包...")
    
    dependencies = [
        ("asyncpg", "import asyncpg"),
        ("python-dotenv", "from dotenv import load_dotenv"),
        ("aiofiles", "import aiofiles"),
        ("numpy", "import numpy"),
        ("PyJWT", "import jwt"),
        ("requests", "import requests")
    ]
    
    for name, import_cmd in dependencies:
        try:
            exec(import_cmd)
            print(f"✅ {name}: 已安装")
        except ImportError:
            print(f"❌ {name}: 未安装")
            # 尝试安装
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "install", name], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"   ✅ 自动安装 {name} 成功")
                else:
                    print(f"   ❌ 自动安装 {name} 失败: {result.stderr}")
            except Exception as e:
                print(f"   ❌ 安装过程出错: {e}")

if __name__ == "__main__":
    print("🔧 测试 Hook 修复效果")
    print("=" * 50)
    
    # 1. 验证依赖
    verify_dependencies()
    
    # 2. 测试 hook
    print("\n" + "=" * 50)
    success = test_hook_directly()
    
    # 3. 检查日志
    check_log_file() 
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Hook 测试完成")
    else:
        print("⚠️  Hook 测试存在问题，请检查日志")