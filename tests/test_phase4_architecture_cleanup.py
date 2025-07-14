#!/usr/bin/env python3
"""
阶段4：架构简化测试
测试目标：确保删除CLI模式后系统仍然正常工作
"""

import os
import sys
import subprocess
import pytest
from pathlib import Path
from typing import List

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPhase4ArchitectureCleanup:
    """架构简化测试类"""
    
    def test_cli_files_to_remove(self):
        """列出需要删除的CLI相关文件"""
        project_root = Path(__file__).parent.parent
        
        cli_files = [
            'sage_crossplatform.py',
            'sage_minimal.py',
            'sage_cli',
            'sage-wrapper.sh',
            'tests/test_crossplatform.py',
            'tests/test_cross_platform.py',
            'tests/mock_sage.py',
            'tests/test_sage_code_integration.py',
            'tests/test_sage_memory.py'
        ]
        
        existing_cli_files = []
        for file in cli_files:
            file_path = project_root / file
            if file_path.exists():
                existing_cli_files.append(str(file))
                print(f"✓ 发现CLI文件: {file}")
        
        print(f"\n共发现 {len(existing_cli_files)} 个CLI相关文件需要删除")
        
        # 保存到临时文件供后续使用
        with open('/tmp/cli_files_to_remove.txt', 'w') as f:
            f.write('\n'.join(existing_cli_files))
        
        # 由于文件已被删除，这是预期行为
        if len(existing_cli_files) == 0:
            print("✅ 所有CLI文件已成功删除")
        else:
            assert False, f"仍有 {len(existing_cli_files)} 个CLI文件未删除"
        return existing_cli_files
    
    def test_check_imports(self):
        """检查是否有其他文件导入CLI模块"""
        project_root = Path(__file__).parent.parent
        
        # CLI模块名称
        cli_modules = [
            'sage_crossplatform',
            'sage_minimal',
            'sage_cli',
            'mock_sage'
        ]
        
        # 搜索Python文件
        python_files = list(project_root.glob('**/*.py'))
        
        import_issues = []
        for py_file in python_files:
            # 跳过测试文件和CLI文件本身
            if 'test_' in py_file.name or py_file.name in ['sage_crossplatform.py', 'sage_minimal.py']:
                continue
                
            try:
                content = py_file.read_text()
                for module in cli_modules:
                    if f'import {module}' in content or f'from {module}' in content:
                        import_issues.append(f"{py_file.relative_to(project_root)}: imports {module}")
            except:
                pass
        
        if import_issues:
            print("⚠️  发现以下文件导入CLI模块:")
            for issue in import_issues:
                print(f"  - {issue}")
        else:
            print("✓ 没有发现其他文件导入CLI模块")
        
        # 这里不失败测试，只是警告
        return import_issues
    
    def test_sage_manage_update(self):
        """检查sage_manage文件是否需要更新"""
        sage_manage = Path(__file__).parent.parent / 'sage_manage'
        
        if not sage_manage.exists():
            pytest.skip("sage_manage文件不存在")
        
        content = sage_manage.read_text()
        
        cli_references = []
        cli_keywords = ['crossplatform', 'minimal', 'wrapper', 'CLI mode', 'cli-mode']
        
        for keyword in cli_keywords:
            if keyword in content:
                cli_references.append(keyword)
        
        if cli_references:
            print(f"⚠️  sage_manage包含CLI引用: {', '.join(cli_references)}")
            print("  需要更新sage_manage移除CLI选项")
        else:
            print("✓ sage_manage不包含明显的CLI引用")
        
        return cli_references
    
    def test_integration_config(self):
        """检查集成配置文件"""
        integration_file = Path(__file__).parent.parent / 'app' / 'sage_integration.py'
        
        if not integration_file.exists():
            pytest.skip("sage_integration.py不存在")
        
        content = integration_file.read_text()
        
        # 检查是否只包含MCP配置
        has_mcp_config = 'mcp_servers' in content or 'MCP' in content
        has_cli_config = 'crossplatform' in content or 'cli_mode' in content
        
        print(f"✓ MCP配置: {'存在' if has_mcp_config else '不存在'}")
        print(f"✓ CLI配置: {'存在' if has_cli_config else '不存在'}")
        
        if has_cli_config:
            print("⚠️  需要从集成配置中移除CLI相关内容")
        
        return has_mcp_config and not has_cli_config
    
    def test_startup_scripts(self):
        """检查启动脚本"""
        project_root = Path(__file__).parent.parent
        
        scripts_to_check = [
            'start_all_services.sh',
            'stop_all_services.sh',
            'setup_sage.sh',
            'setup_alias.sh'
        ]
        
        scripts_with_cli = []
        for script_name in scripts_to_check:
            script_path = project_root / script_name
            if script_path.exists():
                content = script_path.read_text()
                if 'crossplatform' in content or 'sage_cli' in content or 'wrapper' in content:
                    scripts_with_cli.append(script_name)
                    print(f"⚠️  {script_name} 包含CLI引用")
                else:
                    print(f"✓ {script_name} 不包含CLI引用")
        
        return scripts_with_cli
    
    def test_dockerfile_check(self):
        """检查Dockerfile是否包含CLI相关内容"""
        dockerfile = Path(__file__).parent.parent / 'Dockerfile'
        
        if not dockerfile.exists():
            pytest.skip("Dockerfile不存在")
        
        content = dockerfile.read_text()
        
        cli_references = []
        if 'sage_crossplatform' in content:
            cli_references.append('sage_crossplatform')
        if 'sage_minimal' in content:
            cli_references.append('sage_minimal')
        if 'sage_cli' in content:
            cli_references.append('sage_cli')
            
        if cli_references:
            print(f"⚠️  Dockerfile包含CLI引用: {', '.join(cli_references)}")
        else:
            print("✓ Dockerfile不包含CLI引用")
        
        return cli_references
    
    def test_mcp_only_functionality(self):
        """测试只使用MCP模式的功能"""
        # 测试MCP stdio是否可以独立工作
        try:
            # 尝试导入MCP相关模块
            import sage_mcp_stdio
            from app.sage_mcp_server import app
            
            print("✓ MCP模块可以正常导入")
            
            # 检查MCP服务器配置
            assert hasattr(app, 'routes'), "FastAPI应用应该有路由"
            print("✓ MCP服务器配置正常")
            
            return True
            
        except ImportError as e:
            pytest.fail(f"MCP模块导入失败: {str(e)}")
        except Exception as e:
            pytest.fail(f"MCP功能测试失败: {str(e)}")
    
    def test_documentation_references(self):
        """检查文档中的CLI引用"""
        project_root = Path(__file__).parent.parent
        
        docs_with_cli = []
        doc_files = list((project_root / 'docs').glob('**/*.md')) + [
            project_root / 'README.md',
            project_root / '使用指南.MD'
        ]
        
        for doc_file in doc_files:
            if doc_file.exists():
                try:
                    content = doc_file.read_text()
                    if 'crossplatform' in content.lower() or 'cli模式' in content or 'CLI mode' in content:
                        docs_with_cli.append(str(doc_file.relative_to(project_root)))
                except:
                    pass
        
        if docs_with_cli:
            print(f"⚠️  以下文档包含CLI引用:")
            for doc in docs_with_cli[:5]:  # 只显示前5个
                print(f"  - {doc}")
            if len(docs_with_cli) > 5:
                print(f"  ... 还有 {len(docs_with_cli) - 5} 个文档")
        else:
            print("✓ 文档中没有CLI引用")
        
        return docs_with_cli


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, '-v', '-s'])