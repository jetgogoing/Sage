# Sage MCP Server Dockerfile
# 多阶段构建以减少镜像大小

# 第一阶段：构建环境
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --user -r requirements.txt

# 第二阶段：运行环境
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/root/.local/bin:$PATH"

# 创建非root用户
RUN useradd --create-home --shell /bin/bash sage && \
    mkdir -p /app && \
    chown -R sage:sage /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖
COPY --from=builder /root/.local /root/.local

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY --chown=sage:sage . .

# 复制并设置entrypoint脚本
COPY --chown=sage:sage docker-entrypoint.sh /docker-entrypoint.sh
USER root
RUN chmod +x /docker-entrypoint.sh
USER sage

# 暴露端口
EXPOSE 17800

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:17800/health || exit 1

# 切换到root用户运行（因为pip packages安装在/root/.local）
USER root

# 使用entrypoint脚本启动
ENTRYPOINT ["/docker-entrypoint.sh"]