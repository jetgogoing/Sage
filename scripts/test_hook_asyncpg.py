#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Hook 脚本中 asyncpg 导入问题的修复
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_sage_imports():
    """测试 sage_core 相关导入"""
    print("🔍 测试 Sage Core 导入...")
    
    try:
        # 测试基本导入
        from sage_core import MemoryContent
        print("✅ MemoryContent 导入成功")
        
        from sage_core.singleton_manager import get_sage_core
        print("✅ get_sage_core 导入成功")
        
        # 测试 asyncpg 导入
        import asyncpg
        print(f"✅ asyncpg 导入成功，版本: {asyncpg.__version__}")
        
        # 测试数据库连接模块
        from sage_core.database.connection import DatabaseConnection
        print("✅ DatabaseConnection 导入成功")
        
        print("\n🎉 所有关键模块导入测试通过！")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        if "asyncpg" in str(e):
            print("💡 解决方案: pip install asyncpg>=0.29.0")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_hook_script():
    """测试 hook 脚本路径"""
    hook_script = project_root / "hooks" / "scripts" / "sage_archiver_enhanced.py"
    
    if hook_script.exists():
        print(f"✅ Hook 脚本存在: {hook_script}")
        
        # 检查脚本是否可执行
        if os.access(hook_script, os.R_OK):
            print("✅ Hook 脚本可读")
        else:
            print("❌ Hook 脚本不可读")
            
    else:
        print(f"❌ Hook 脚本不存在: {hook_script}")

if __name__ == "__main__":
    print("🚀 开始测试 Hook AsyncPG 修复...")
    print("=" * 50)
    
    # 测试导入
    import_success = test_sage_imports()
    
    print("\n" + "=" * 50)
    
    # 测试文件
    test_hook_script()
    
    print("\n" + "=" * 50)
    
    if import_success:
        print("✅ 修复验证成功！Hook 脚本应该能正常工作了。")
    else:
        print("❌ 仍存在问题，需要进一步检查。")