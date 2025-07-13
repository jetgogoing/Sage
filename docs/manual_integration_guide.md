# Sage MCP 自动记忆集成指南

## 概述

本指南说明如何手动配置 Claude Code，使其在任何项目目录下都自动使用 Sage 的记忆功能。

## 集成方案

### 方案1：MCP 配置文件（推荐）

1. 创建 Claude MCP 配置目录：
```bash
mkdir -p ~/.config/claude
```

2. 创建 MCP 配置文件 `~/.config/claude/mcp.json`：
```json
{
  "version": "1.0",
  "servers": {
    "sage": {
      "type": "http",
      "url": "http://localhost:17800/mcp",
      "enabled": true,
      "autoStart": true,
      "description": "Sage Memory System",
      "initialization": {
        "prompts": {
          "system": [
            "You have access to a persistent memory system.",
            "For EVERY message, relevant context is automatically available.",
            "Build on previous conversations and maintain consistency."
          ]
        },
        "autoInject": true,
        "transparentMode": true
      }
    }
  }
}
```

### 方案2：启动脚本

创建 `~/bin/claude-with-memory`：
```bash
#!/bin/bash
# 确保 Sage MCP 服务器运行
cd "/Volumes/1T HDD/Sage"
python3 app/sage_mcp_server.py &
SAGE_PID=$!

# 等待服务器启动
sleep 3

# 启动 Claude Code（需要实际的启动命令）
# claude "$@"

# 清理
trap "kill $SAGE_PID" EXIT
```

### 方案3：环境变量配置

在 shell 配置文件（`~/.zshrc` 或 `~/.bashrc`）中添加：
```bash
# Sage MCP 自动记忆配置
export SAGE_MCP_URL="http://localhost:17800/mcp"
export SAGE_AUTO_MEMORY=true
export MCP_AUTO_START_SAGE=true
```

## 验证集成

### 1. 检查服务器状态
```bash
curl http://localhost:17800/health
```

### 2. 测试记忆功能
```bash
curl -X POST http://localhost:17800/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "tools/call",
    "params": {
      "name": "get_memory_stats"
    }
  }'
```

### 3. 在 Claude Code 中验证

在任意项目目录下启动 Claude Code，应该能够：
- 自动获取相关历史记忆
- 自动保存重要对话
- 无需手动调用记忆工具

## 高级配置

### 自动注入配置

修改 `/Volumes/1T HDD/Sage/app/sage_mcp_interceptor.py` 中的配置：
```python
GLOBAL_AUTO_INJECTION_CONFIG = {
    "enabled": True,
    "inject_on_every_request": True,
    "max_context_length": 2000,
    "cache_duration": 300,
    "auto_save_enabled": True
}
```

### 调试模式

启用详细日志：
```bash
export SAGE_DEBUG=true
tail -f /tmp/sage_mcp_enhanced.log
```

## 故障排除

1. **服务器未启动**
   - 检查端口 17800 是否被占用
   - 查看日志：`/tmp/sage_mcp_server.log`

2. **记忆未自动注入**
   - 确认自动注入已启用
   - 检查 MCP 配置文件

3. **Claude Code 未使用记忆**
   - 验证 MCP 服务器 URL
   - 检查网络连接

## 下一步

完成集成后，Sage 的记忆系统将在后台透明运行，自动增强每次对话。