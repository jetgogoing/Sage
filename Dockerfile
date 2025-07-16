# Sage MCP Server Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 sage && chown -R sage:sage /app

# 切换到非 root 用户
USER sage

# 暴露端口
EXPOSE 17800 17801

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=sage_memory
ENV DB_USER=sage
ENV DB_PASSWORD=sage123

# 默认启动命令（STDIO 服务器）
CMD ["python", "sage_mcp_stdio_v3.py"]