#!/usr/bin/env python3
"""
Sage项目智能权限管理工具
一劳永逸解决跨平台文件权限问题

功能：
1. 自动识别需要执行权限的脚本
2. 批量修复权限问题  
3. 跨平台兼容(Windows/macOS/Linux)
4. 集成验证和诊断功能
5. 预防性检查机制

使用方法：
    python permission_manager.py --fix-all      # 修复所有权限问题
    python permission_manager.py --check        # 检查权限状态
    python permission_manager.py --verify       # 验证修复结果
"""

import os
import sys
import stat
import platform
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import subprocess
import json

class PermissionManager:
    """智能权限管理器"""
    
    def __init__(self, hooks_dir: Optional[Path] = None):
        """
        初始化权限管理器
        
        Args:
            hooks_dir: hooks目录路径，默认自动检测
        """
        # 项目根目录自动检测
        if hooks_dir is None:
            script_path = Path(__file__).resolve()
            if script_path.parent.name == "scripts" and script_path.parent.parent.name == "hooks":
                self.hooks_dir = script_path.parent.parent
                self.scripts_dir = script_path.parent
            else:
                # 回退到相对路径查找
                self.hooks_dir = Path.cwd() / "hooks"
                self.scripts_dir = self.hooks_dir / "scripts"
        else:
            self.hooks_dir = Path(hooks_dir)
            self.scripts_dir = self.hooks_dir / "scripts"
        
        # 平台信息
        self.platform_info = {
            "system": platform.system(),
            "is_windows": platform.system() == "Windows",
            "is_unix": platform.system() in ["Darwin", "Linux"]
        }
        
        # 权限配置
        self.executable_permission = 0o755  # Unix executable permission
        self.readable_permission = 0o644    # Unix readable permission
        
        print(f"🔧 权限管理器初始化")
        print(f"   平台: {self.platform_info['system']}")
        print(f"   Hooks目录: {self.hooks_dir}")
        print(f"   Scripts目录: {self.scripts_dir}")
    
    def identify_executable_scripts(self) -> List[Path]:
        """
        智能识别需要执行权限的脚本
        
        识别标准：
        1. 包含shebang行 (#!/usr/bin/env python3)
        2. 包含if __name__ == "__main__": 
        3. 明确的hook脚本模式 (sage_*.py)
        """
        executable_scripts = []
        
        if not self.scripts_dir.exists():
            print(f"⚠️  Scripts目录不存在: {self.scripts_dir}")
            return executable_scripts
        
        for script_file in self.scripts_dir.glob("*.py"):
            if self._should_be_executable(script_file):
                executable_scripts.append(script_file)
        
        return executable_scripts
    
    def _should_be_executable(self, script_file: Path) -> bool:
        """判断脚本是否应该具有执行权限"""
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查条件
            has_shebang = content.startswith('#!/')
            has_main = 'if __name__ == "__main__":' in content
            is_hook_script = script_file.name.startswith('sage_')
            
            # 满足任一条件即认为应该可执行
            return has_shebang or has_main or is_hook_script
            
        except Exception as e:
            print(f"⚠️  读取文件失败 {script_file}: {e}")
            return False
    
    def check_permissions(self) -> Dict[str, List[Path]]:
        """
        检查所有脚本的权限状态
        
        Returns:
            {
                "executable": [已有执行权限的脚本],
                "need_fix": [需要修复权限的脚本], 
                "ignored": [非执行脚本]
            }
        """
        results = {
            "executable": [],
            "need_fix": [],
            "ignored": []
        }
        
        executable_scripts = self.identify_executable_scripts()
        
        for script_file in self.scripts_dir.glob("*.py"):
            if script_file in executable_scripts:
                if self._has_execute_permission(script_file):
                    results["executable"].append(script_file)
                else:
                    results["need_fix"].append(script_file)
            else:
                results["ignored"].append(script_file)
        
        return results
    
    def _has_execute_permission(self, file_path: Path) -> bool:
        """检查文件是否有执行权限"""
        if self.platform_info["is_windows"]:
            # Windows下检查文件是否存在即可，.py文件通过文件关联执行
            return file_path.exists()
        else:
            # Unix系统检查实际的执行权限位
            try:
                file_stat = file_path.stat()
                return bool(file_stat.st_mode & stat.S_IEXEC)
            except OSError:
                return False
    
    def fix_permissions(self, script_files: List[Path] = None) -> Dict[str, int]:
        """
        修复脚本权限
        
        Args:
            script_files: 指定要修复的脚本列表，默认修复所有需要的脚本
            
        Returns:
            {"success": count, "failed": count}
        """
        if script_files is None:
            permission_status = self.check_permissions()
            script_files = permission_status["need_fix"]
        
        results = {"success": 0, "failed": 0}
        
        print(f"🔧 开始修复 {len(script_files)} 个脚本的权限...")
        
        for script_file in script_files:
            if self._fix_single_permission(script_file):
                results["success"] += 1
                print(f"   ✅ {script_file.name}")
            else:
                results["failed"] += 1
                print(f"   ❌ {script_file.name}")
        
        return results
    
    def _fix_single_permission(self, script_file: Path) -> bool:
        """修复单个文件的权限"""
        try:
            if self.platform_info["is_windows"]:
                # Windows下确保文件存在且可读即可
                # Python脚本通过文件关联执行，不需要额外权限设置
                return script_file.exists()
            else:
                # Unix系统设置执行权限
                script_file.chmod(self.executable_permission)
                return True
        except OSError as e:
            print(f"     权限设置失败: {e}")
            return False
    
    def verify_fixes(self) -> bool:
        """验证权限修复是否成功"""
        permission_status = self.check_permissions() 
        need_fix_count = len(permission_status["need_fix"])
        
        if need_fix_count == 0:
            print("✅ 所有脚本权限验证通过！")
            return True
        else:
            print(f"❌ 仍有 {need_fix_count} 个脚本需要修复权限")
            for script in permission_status["need_fix"]:
                print(f"   - {script.name}")
            return False
    
    def test_script_execution(self, script_file: Path) -> bool:
        """测试脚本是否可以正常执行"""
        try:
            if self.platform_info["is_windows"]:
                # Windows下使用python解释器执行
                result = subprocess.run([sys.executable, str(script_file), "--help"], 
                                      capture_output=True, timeout=5)
            else:
                # Unix系统直接执行
                result = subprocess.run([str(script_file), "--help"], 
                                      capture_output=True, timeout=5)
            
            # 返回码不是126(权限错误)即认为权限正常
            return result.returncode != 126
            
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            return False
    
    def generate_report(self) -> Dict:
        """生成权限状态报告"""
        permission_status = self.check_permissions()
        
        report = {
            "platform": self.platform_info["system"],
            "timestamp": __import__('time').time(),
            "hooks_directory": str(self.hooks_dir),
            "scripts_directory": str(self.scripts_dir),
            "summary": {
                "total_scripts": len(list(self.scripts_dir.glob("*.py"))),
                "executable_scripts": len(permission_status["executable"]),
                "need_fix_scripts": len(permission_status["need_fix"]),
                "ignored_scripts": len(permission_status["ignored"])
            },
            "details": {
                "executable": [str(f.name) for f in permission_status["executable"]],
                "need_fix": [str(f.name) for f in permission_status["need_fix"]],
                "ignored": [str(f.name) for f in permission_status["ignored"]]
            }
        }
        
        return report
    
    def create_prevention_hook(self) -> Path:
        """创建预防性Git Hook"""
        git_hooks_dir = self.hooks_dir.parent / ".git" / "hooks"
        if not git_hooks_dir.exists():
            git_hooks_dir = self.hooks_dir.parent / ".githooks"
            git_hooks_dir.mkdir(exist_ok=True)
        
        hook_file = git_hooks_dir / "pre-commit"
        hook_content = f"""#!/bin/bash
# Sage项目权限检查预防Hook
# 自动检查和修复脚本权限问题

echo "🔍 检查hook脚本权限..."
python3 "{self.scripts_dir}/permission_manager.py" --check --quiet

if [ $? -ne 0 ]; then
    echo "⚠️  发现权限问题，自动修复中..."
    python3 "{self.scripts_dir}/permission_manager.py" --fix-all --quiet
    echo "✅ 权限问题已修复"
fi
"""
        
        try:
            with open(hook_file, 'w') as f:
                f.write(hook_content)
            hook_file.chmod(0o755)
            print(f"✅ 创建预防性Git Hook: {hook_file}")
            return hook_file
        except Exception as e:
            print(f"⚠️  创建Git Hook失败: {e}")
            return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sage项目智能权限管理工具")
    parser.add_argument("--check", action="store_true", help="检查权限状态")
    parser.add_argument("--fix-all", action="store_true", help="修复所有权限问题")
    parser.add_argument("--verify", action="store_true", help="验证修复结果")
    parser.add_argument("--report", action="store_true", help="生成详细报告")
    parser.add_argument("--create-hook", action="store_true", help="创建预防性Git Hook")
    parser.add_argument("--test", metavar="SCRIPT", help="测试指定脚本的执行权限")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    # 初始化权限管理器
    try:
        manager = PermissionManager()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)
    
    # 执行操作
    if args.check:
        permission_status = manager.check_permissions()
        if not args.quiet:
            print(f"\n📊 权限检查结果:")
            print(f"   ✅ 已有执行权限: {len(permission_status['executable'])} 个")
            print(f"   🔧 需要修复: {len(permission_status['need_fix'])} 个")
            print(f"   ⏭️  忽略: {len(permission_status['ignored'])} 个")
            
            if permission_status['need_fix']:
                print(f"\n🔧 需要修复的脚本:")
                for script in permission_status['need_fix']:
                    print(f"   - {script.name}")
        
        sys.exit(0 if len(permission_status['need_fix']) == 0 else 1)
    
    elif args.fix_all:
        results = manager.fix_permissions()
        if not args.quiet:
            print(f"\n📊 修复结果:")
            print(f"   ✅ 成功: {results['success']} 个")
            print(f"   ❌ 失败: {results['failed']} 个")
        
        sys.exit(0 if results['failed'] == 0 else 1)
    
    elif args.verify:
        success = manager.verify_fixes()
        sys.exit(0 if success else 1)
    
    elif args.report:
        report = manager.generate_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    elif args.create_hook:
        manager.create_prevention_hook()
    
    elif args.test:
        script_path = Path(args.test)
        if not script_path.is_absolute():
            script_path = manager.scripts_dir / script_path
        
        if manager.test_script_execution(script_path):
            print(f"✅ {script_path.name} 执行权限正常")
            sys.exit(0)
        else:
            print(f"❌ {script_path.name} 执行权限异常")
            sys.exit(1)
    
    else:
        # 默认：检查并修复
        print("🔍 执行智能权限检查和修复...")
        permission_status = manager.check_permissions()
        
        if permission_status['need_fix']:
            print(f"发现 {len(permission_status['need_fix'])} 个脚本需要修复权限")
            results = manager.fix_permissions()
            print(f"修复完成: {results['success']} 成功, {results['failed']} 失败")
        else:
            print("✅ 所有脚本权限正常")
        
        # 验证修复结果
        if manager.verify_fixes():
            print("🎉 权限管理完成！系统已准备就绪。")
        else:
            print("⚠️  部分权限修复失败，请检查错误信息")
            sys.exit(1)


if __name__ == "__main__":
    main()