# Sage MCP 全容器版 Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 MCP 服务端口
EXPOSE 17800

# 启动 MCP 服务
CMD ["python3", "app/sage_mcp_server.py"]
