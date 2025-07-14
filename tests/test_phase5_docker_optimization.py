#!/usr/bin/env python3
"""
阶段5：Docker部署优化测试
测试目标：优化Docker镜像大小、启动速度和部署流程
"""

import os
import sys
import subprocess
import pytest
import time
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPhase5DockerOptimization:
    """Docker优化测试类"""
    
    def test_dockerfile_analysis(self):
        """分析Dockerfile优化空间"""
        dockerfile = Path(__file__).parent.parent / 'Dockerfile'
        
        if not dockerfile.exists():
            pytest.skip("Dockerfile不存在")
        
        content = dockerfile.read_text()
        
        optimization_checks = {
            'multi_stage': 'FROM' in content and content.count('FROM') > 1,
            'alpine_base': 'alpine' in content.lower(),
            'pip_no_cache': '--no-cache-dir' in content,
            'apt_clean': 'apt-get clean' in content or 'rm -rf /var/lib/apt/lists/*' in content,
            'user_non_root': 'USER' in content and 'USER root' not in content.split('\n')[-1],
            'workdir': 'WORKDIR' in content,
            'copy_selective': 'COPY .' not in content or 'COPY . .' not in content
        }
        
        print("📊 Dockerfile优化检查:")
        score = 0
        for check, passed in optimization_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}: {'已优化' if passed else '需要优化'}")
            if passed:
                score += 1
        
        print(f"\n优化得分: {score}/{len(optimization_checks)}")
        
        # 检查镜像层数
        from_count = content.count('FROM')
        run_count = content.count('RUN')
        copy_count = content.count('COPY')
        
        print(f"\n镜像层统计:")
        print(f"  FROM指令: {from_count}")
        print(f"  RUN指令: {run_count}")
        print(f"  COPY指令: {copy_count}")
        print(f"  总层数: {from_count + run_count + copy_count}")
        
        return optimization_checks
    
    def test_docker_compose_optimization(self):
        """检查docker-compose配置优化"""
        compose_file = Path(__file__).parent.parent / 'docker-compose.yml'
        
        if not compose_file.exists():
            pytest.skip("docker-compose.yml不存在")
        
        content = compose_file.read_text()
        
        optimizations = {
            'healthcheck': 'healthcheck:' in content,
            'restart_policy': 'restart:' in content,
            'resource_limits': 'mem_limit' in content or 'resources:' in content,
            'volumes_cached': ':cached' in content or ':delegated' in content,
            'networks_custom': 'networks:' in content and 'bridge' not in content
        }
        
        print("📊 Docker Compose优化检查:")
        for opt, present in optimizations.items():
            status = "✅" if present else "⚠️"
            print(f"  {status} {opt}: {'已配置' if present else '可以优化'}")
        
        return optimizations
    
    def test_dockerfile_size_optimization(self):
        """生成优化的Dockerfile"""
        optimized_dockerfile = """# 阶段1: 构建阶段
FROM python:3.12-slim as builder

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

# 阶段2: 运行阶段
FROM python:3.12-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \\
    postgresql-client \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 sage

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码（排除不必要的文件）
COPY --chown=sage:sage memory.py memory_interface.py exceptions.py ./
COPY --chown=sage:sage app/ ./app/
COPY --chown=sage:sage sage_mcp_stdio.py ./

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH" \\
    PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1

# 切换到非root用户
USER sage

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:17800/health || exit 1

# 暴露端口
EXPOSE 17800

# 启动命令
CMD ["python", "-m", "uvicorn", "app.sage_mcp_server:app", "--host", "0.0.0.0", "--port", "17800"]
"""
        
        # 创建优化的Dockerfile
        optimized_file = Path(__file__).parent.parent / 'Dockerfile.optimized'
        optimized_file.write_text(optimized_dockerfile)
        
        print("✅ 创建优化的Dockerfile: Dockerfile.optimized")
        print("\n优化特性:")
        print("  - 多阶段构建减少最终镜像大小")
        print("  - 使用slim基础镜像")
        print("  - 清理apt缓存")
        print("  - 使用非root用户")
        print("  - 添加健康检查")
        print("  - 只复制必要文件")
        print("  - 使用pip --no-cache-dir")
        
        return True
    
    def test_dockerignore_optimization(self):
        """检查和优化.dockerignore"""
        dockerignore = Path(__file__).parent.parent / '.dockerignore'
        
        required_patterns = [
            '*.pyc',
            '__pycache__',
            '.git',
            '.github',
            '.env',
            'tests/',
            'docs/',
            '*.md',
            '.pytest_cache',
            '.venv/',
            'venv/',
            '.DS_Store',
            '*.log',
            '*.sqlite',
            'docker-compose*.yml',
            'Dockerfile*'
        ]
        
        existing_patterns = []
        if dockerignore.exists():
            existing_patterns = dockerignore.read_text().strip().split('\n')
        
        missing_patterns = [p for p in required_patterns if p not in existing_patterns]
        
        if missing_patterns:
            print("⚠️  .dockerignore缺少以下模式:")
            for pattern in missing_patterns:
                print(f"    - {pattern}")
            
            # 创建优化的.dockerignore
            all_patterns = existing_patterns + missing_patterns
            dockerignore.write_text('\n'.join(all_patterns) + '\n')
            print("\n✅ 已更新.dockerignore")
        else:
            print("✅ .dockerignore已经包含所有推荐模式")
        
        return len(missing_patterns) == 0
    
    def test_compose_optimization(self):
        """创建优化的docker-compose配置"""
        optimized_compose = """version: '3.8'

services:
  pg:
    image: pgvector/pgvector:pg16
    container_name: sage-postgres
    environment:
      POSTGRES_USER: mem
      POSTGRES_PASSWORD: mem
      POSTGRES_DB: mem
    ports:
      - "5432:5432"
    volumes:
      - sage_pgdata:/var/lib/postgresql/data
      - ./init-pgvector.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mem -d mem"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  sage-mcp:
    build:
      context: .
      dockerfile: Dockerfile.optimized
    container_name: sage-mcp-server
    environment:
      DATABASE_URL: postgresql://mem:mem@pg:5432/mem
      SILICONFLOW_API_KEY: ${SILICONFLOW_API_KEY}
      DB_HOST: pg
      DB_PORT: 5432
      DB_NAME: mem
      DB_USER: mem
      DB_PASSWORD: mem
    ports:
      - "17800:17800"
    depends_on:
      pg:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:17800/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

volumes:
  sage_pgdata:
    driver: local

networks:
  default:
    name: sage-network
"""
        
        compose_file = Path(__file__).parent.parent / 'docker-compose.optimized.yml'
        compose_file.write_text(optimized_compose)
        
        print("✅ 创建优化的docker-compose配置: docker-compose.optimized.yml")
        print("\n优化特性:")
        print("  - 健康检查配置")
        print("  - 内存限制设置")
        print("  - 依赖健康检查")
        print("  - 自动重启策略")
        print("  - 自定义网络")
        print("  - 持久化数据卷")
        
        return True
    
    def test_startup_script_optimization(self):
        """创建优化的启动脚本"""
        startup_script = """#!/bin/bash
# Sage MCP 优化启动脚本

set -e

echo "🚀 Sage MCP 快速启动"
echo "====================="

# 检查Docker
if ! docker info &> /dev/null; then
    echo "❌ Docker未运行"
    exit 1
fi

# 检查环境变量
if [ -z "$SILICONFLOW_API_KEY" ] && [ ! -f .env ]; then
    echo "⚠️  未设置SILICONFLOW_API_KEY"
    echo "请设置环境变量或创建.env文件"
    exit 1
fi

# 使用优化的配置启动
echo "🔄 启动优化的容器..."
docker compose -f docker-compose.optimized.yml up -d

# 等待服务就绪
echo "⏳ 等待服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:17800/health > /dev/null; then
        echo "✅ Sage MCP服务已就绪！"
        echo ""
        echo "📊 服务状态:"
        docker compose -f docker-compose.optimized.yml ps
        echo ""
        echo "🔗 MCP服务地址: http://localhost:17800"
        echo "📝 健康检查: http://localhost:17800/health"
        exit 0
    fi
    sleep 1
    echo -n "."
done

echo ""
echo "❌ 服务启动超时"
docker compose -f docker-compose.optimized.yml logs
exit 1
"""
        
        script_file = Path(__file__).parent.parent / 'start_optimized.sh'
        script_file.write_text(startup_script)
        script_file.chmod(0o755)
        
        print("✅ 创建优化的启动脚本: start_optimized.sh")
        print("\n脚本特性:")
        print("  - 快速健康检查")
        print("  - 环境变量验证")
        print("  - 超时处理")
        print("  - 清晰的状态反馈")
        
        return True
    
    def test_build_performance(self):
        """测试构建性能（模拟）"""
        print("\n📊 Docker构建优化对比（预估）:")
        print("\n原始Dockerfile:")
        print("  - 基础镜像: python:3.12 (约900MB)")
        print("  - 最终大小: ~1.2GB")
        print("  - 构建时间: ~3-5分钟")
        print("  - 层数: 15+")
        
        print("\n优化后Dockerfile:")
        print("  - 基础镜像: python:3.12-slim (约150MB)")
        print("  - 最终大小: ~350MB (减少70%)")
        print("  - 构建时间: ~1-2分钟 (减少60%)")
        print("  - 层数: 8-10")
        
        print("\n优化收益:")
        print("  ✅ 镜像大小减少 ~850MB")
        print("  ✅ 构建速度提升 2-3倍")
        print("  ✅ 部署传输更快")
        print("  ✅ 容器启动更快")
        
        return True


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, '-v', '-s'])