#!/usr/bin/env python3
"""
阶段1：环境验证测试
测试目标：验证项目运行所需的基础环境配置
"""

import os
import sys
import subprocess
import psycopg2
import pytest
import importlib.util
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestPhase1Environment:
    """环境验证测试类"""
    
    def test_python_version(self):
        """测试Python版本是否满足要求"""
        assert sys.version_info >= (3, 8), "需要 Python 3.8 或更高版本"
        print(f"✓ Python 版本: {sys.version}")
    
    def test_required_env_vars(self):
        """测试必需的环境变量是否已设置"""
        required_vars = [
            'SILICONFLOW_API_KEY',
            'DATABASE_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            pytest.skip(f"缺少环境变量: {', '.join(missing_vars)}")
        
        print("✓ 所有必需环境变量已设置")
    
    def test_postgresql_connection(self):
        """测试PostgreSQL连接"""
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            pytest.skip("DATABASE_URL 未设置")
        
        try:
            # 尝试连接数据库
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # 检查pgvector扩展
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            assert result is not None, "pgvector 扩展未安装"
            print("✓ PostgreSQL 连接成功，pgvector 已安装")
            
        except Exception as e:
            pytest.fail(f"PostgreSQL 连接失败: {str(e)}")
    
    def test_python_dependencies(self):
        """测试Python依赖是否已安装"""
        required_packages = [
            'fastapi',
            'uvicorn',
            'psycopg2',
            'requests',
            'pydantic',
            'numpy',
            'typing_extensions'
        ]
        
        missing_packages = []
        for package in required_packages:
            spec = importlib.util.find_spec(package)
            if spec is None:
                missing_packages.append(package)
        
        assert not missing_packages, f"缺少Python包: {', '.join(missing_packages)}"
        print("✓ 所有必需的Python包已安装")
    
    def test_project_structure(self):
        """测试项目目录结构是否完整"""
        project_root = Path(__file__).parent.parent
        required_dirs = [
            'app',
            'tests',
            'docs',
            'docs/执行报告'
        ]
        
        required_files = [
            'app/sage_mcp_server.py',
            'sage_mcp_stdio.py',
            'memory.py',
            'memory_interface.py',
            'intelligent_retrieval.py',
            'requirements.txt'
        ]
        
        # 检查目录
        for dir_path in required_dirs:
            assert (project_root / dir_path).exists(), f"缺少目录: {dir_path}"
        
        # 检查文件
        for file_path in required_files:
            assert (project_root / file_path).exists(), f"缺少文件: {file_path}"
        
        print("✓ 项目结构完整")
    
    def test_docker_availability(self):
        """测试Docker是否可用"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ Docker 可用: {result.stdout.strip()}")
            
            # 检查docker-compose
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ Docker Compose 可用: {result.stdout.strip()}")
            
        except subprocess.CalledProcessError:
            pytest.fail("Docker 或 Docker Compose 不可用")
        except FileNotFoundError:
            pytest.fail("Docker 或 Docker Compose 未安装")
    
    def test_git_repository(self):
        """测试Git仓库状态"""
        try:
            # 检查是否在Git仓库中
            result = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                capture_output=True,
                text=True,
                check=True
            )
            assert result.stdout.strip() == 'true', "不在Git仓库中"
            
            # 获取当前分支
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            print(f"✓ Git 仓库正常，当前分支: {branch}")
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Git 操作失败: {str(e)}")
    
    def test_api_key_format(self):
        """测试API密钥格式是否正确"""
        api_key = os.getenv('SILICONFLOW_API_KEY', '')
        
        if not api_key:
            pytest.skip("SILICONFLOW_API_KEY 未设置")
        
        # 基本格式检查
        assert len(api_key) > 20, "API密钥长度似乎不正确"
        assert not api_key.startswith(' '), "API密钥不应以空格开头"
        assert not api_key.endswith(' '), "API密钥不应以空格结尾"
        
        print("✓ API密钥格式检查通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, '-v', '-s'])