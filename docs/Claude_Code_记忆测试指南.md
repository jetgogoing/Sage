# Claude Code Sage记忆功能测试指南

## 🎯 测试目标

验证Sage MCP服务器在Claude Code中的记忆功能是否正常工作，包括：
- 对话自动保存
- 智能上下文检索  
- 记忆搜索功能
- 会话管理

## 🚀 第一步：启动Sage MCP服务器

### 1.1 进入项目目录
```bash
cd "/Volumes/1T HDD/Sage"
```

### 1.2 检查项目结构
```bash
ls -la
```
**期望看到**:
- `app/` 目录（包含MCP服务器代码）
- `docker-compose.yml` 文件
- `requirements.txt` 文件

### 1.3 启动数据库服务（如果使用Docker）
```bash
# 检查Docker服务是否运行
docker ps

# 启动PostgreSQL数据库
docker-compose up -d postgres
```

### 1.4 验证数据库连接
```bash
# 检查数据库容器状态
docker-compose ps

# 测试数据库连接
docker-compose exec postgres psql -U sage_user -d sage_memory -c "SELECT 1;"
```
**期望结果**: 应该返回 `1` 而不是连接错误

### 1.5 安装Python依赖（如果需要）
```bash
# 检查Python版本
python3 --version

# 安装依赖
pip3 install -r requirements.txt
```

### 1.6 启动Sage MCP服务器
```bash
# 方法1: 后台启动
python3 app/sage_mcp_server.py &

# 方法2: 前台启动（推荐用于调试）
python3 app/sage_mcp_server.py
```

**期望看到启动日志**:
```
2025-07-13 17:13:19,284 - ConfigManager - INFO - 配置已加载
2025-07-13 17:13:19,284 - reranker_qwen - INFO - Qwen Reranker initialized
2025-07-13 17:13:19,284 - SageIntelligentRetrieval - INFO - Hybrid reranker initialized
INFO:     Started server process [29027]
INFO:     Waiting for application startup.
2025-07-13 17:13:19,530 - __main__ - INFO - Database connected - Total memories: XX
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:17800
```

## 🔍 第二步：验证Sage系统状态

### 2.1 检查服务器健康状态
```bash
curl -s http://localhost:17800/health
```
**期望返回**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-13T17:13:30.129632",
  "memory_count": 82,
  "database": "connected"
}
```

### 2.2 验证数据库连接
```bash
curl -s http://localhost:17800/health | grep -o '"database":"connected"'
```
**期望返回**: `"database":"connected"`

### 2.3 检查记忆数据
```bash
curl -s -X POST "http://localhost:17800/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "health-check",
    "method": "tools/call",
    "params": {
      "name": "get_memory_stats",
      "arguments": {"include_performance": true}
    }
  }'
```
**期望返回**: 包含记忆统计信息，如总记忆数、性能指标等

### 2.4 验证MCP工具发现
```bash
curl -s -X POST "http://localhost:17800/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "tools-check",
    "method": "tools/list",
    "params": {}
  }'
```
**期望返回**: 应该显示5个工具
- save_conversation
- get_context  
- search_memory
- get_memory_stats
- clear_session

## 🔗 第三步：在Claude Code中注册MCP服务器

### 3.1 检查Claude Code是否可用
```bash
# 检查Claude Code CLI是否安装
claude --version
```

### 3.2 查看当前MCP服务器列表
```bash
claude mcp list
```
**初始状态**: 可能只显示其他服务器，应该看不到sage

### 3.3 注册Sage MCP服务器
```bash
claude mcp add -t http sage http://localhost:17800/mcp
```
**期望提示**: 成功添加服务器的消息

### 3.4 验证注册成功
```bash
claude mcp list
```
**期望看到**:
```
zen: /Users/jet/zen-mcp-server/.zen_venv/bin/python /Users/jet/zen-mcp-server/server.py
sage: http://localhost:17800/mcp (HTTP)
```

### 3.5 测试MCP连接
```bash
# 如果注册失败，可以先删除后重新添加
claude mcp remove sage  # 如果需要
claude mcp add -t http sage http://localhost:17800/mcp
```

## ✅ 第四步：全面系统状态检查

### 4.1 综合状态检查脚本
创建一个快速检查脚本：
```bash
echo "=== Sage MCP 系统状态检查 ==="
echo "1. 检查服务器进程..."
ps aux | grep sage_mcp_server | grep -v grep

echo "2. 检查端口占用..."
lsof -i :17800

echo "3. 检查服务器健康状态..."
curl -s http://localhost:17800/health | head -1

echo "4. 检查MCP注册状态..."
claude mcp list | grep sage

echo "5. 检查工具数量..."
curl -s -X POST "http://localhost:17800/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"test","method":"tools/list","params":{}}' | \
  grep -o '"tools":\[.*\]' | grep -o '{"name":' | wc -l

echo "=== 状态检查完成 ==="
```

### 4.2 故障排除检查列表

**如果服务器无法启动**:
- [ ] 检查端口17800是否被占用: `lsof -i :17800`
- [ ] 检查Python路径和依赖: `which python3` 和 `pip list`
- [ ] 查看详细错误日志: 前台启动查看完整输出

**如果数据库连接失败**:
- [ ] 检查Docker容器状态: `docker-compose ps`
- [ ] 检查数据库日志: `docker-compose logs postgres`
- [ ] 验证数据库配置: 检查环境变量或配置文件

**如果MCP注册失败**:
- [ ] 确认Claude Code版本: `claude --version`
- [ ] 检查网络连接: `curl http://localhost:17800/health`
- [ ] 清除旧配置: `claude mcp remove sage` 后重新添加

## 🧪 第五步：Claude Code中的记忆功能测试

### 5.1 验证MCP工具可用性

在Claude Code中执行以下命令：

```
/MCP
```

**期望结果**: 应该看到sage服务器在MCP列表中

### 5.2 获取记忆统计信息

在Claude Code中发送以下消息：
```
请使用get_memory_stats工具查看当前的记忆统计信息，包括性能指标
```

**期望结果**: 
- 工具应该成功执行
- 返回当前数据库中的记忆数量（应显示82条记忆）
- 显示会话统计和性能指标

### 5.3 保存测试对话

在Claude Code中发送以下消息：
```
请使用save_conversation工具保存这个测试对话：
用户提问："什么是MCP协议？"
助手回答："MCP (Model Context Protocol) 是一个标准化的协议，用于AI模型与外部工具和资源的通信。它基于JSON-RPC 2.0，支持工具发现、调用和资源管理。"
请包含元数据：source: "claude_code_test", timestamp: "2025-07-13T17:15:00Z"
```

**期望结果**:
- 工具成功执行
- 返回新的session_id和turn_id
- 确认对话已保存到数据库

### 5.4 测试智能上下文检索

在Claude Code中发送以下消息：
```
请使用get_context工具搜索与"MCP协议实现"相关的记忆，启用神经重排序和LLM摘要功能，最多返回5个结果
```

**期望结果**:
- 工具成功执行
- 返回相关的上下文信息
- 显示使用了intelligent_retrieval策略
- 显示神经重排序和LLM摘要已启用
- 返回的结果应该与MCP相关

### 5.5 测试基础记忆搜索

在Claude Code中发送以下消息：
```
请使用search_memory工具搜索"阶段4"相关的记忆，返回3个结果
```

**期望结果**:
- 工具成功执行
- 返回包含"阶段4"相关的记忆条目
- 显示相似度评分
- 结果格式清晰易读

### 5.6 测试新对话的自动上下文注入

1. 在Claude Code中开始一个新的对话
2. 发送以下问题：
```
根据之前的讨论，Sage MCP服务器实现了哪些主要功能？
```

**期望结果**:
- Claude Code应该自动调用get_context工具
- 检索到相关的历史对话
- 基于检索到的上下文提供准确回答

### 5.7 验证会话管理

在Claude Code中发送以下消息：
```
请先使用get_memory_stats查看当前会话数量，然后如果有测试会话，可以演示clear_session功能（但不要清除重要的历史记忆）
```

**期望结果**:
- 显示当前会话统计
- 如果执行清除操作，应该正确处理并确认删除的记忆数量

## 📊 测试结果记录

### 功能测试结果

| 测试项目 | 状态 | 备注 |
|---------|------|------|
| 服务器启动 | ⏳ 待测试 | |
| 数据库连接 | ⏳ 待测试 | |
| MCP工具发现 | ⏳ 待测试 | |
| Claude Code注册 | ⏳ 待测试 | |
| MCP工具可用性 | ⏳ 待测试 | |
| 记忆统计查询 | ⏳ 待测试 | |
| 对话保存功能 | ⏳ 待测试 | |
| 智能上下文检索 | ⏳ 待测试 | |
| 基础记忆搜索 | ⏳ 待测试 | |
| 自动上下文注入 | ⏳ 待测试 | |
| 会话管理 | ⏳ 待测试 | |

### 性能指标

| 指标 | 期望值 | 实际值 | 状态 |
|------|--------|--------|------|
| 服务器启动时间 | < 10s | ⏳ | 待测试 |
| 健康检查响应时间 | < 100ms | ⏳ | 待测试 |
| 工具发现响应时间 | < 50ms | ⏳ | 待测试 |
| 对话保存响应时间 | < 200ms | ⏳ | 待测试 |
| 上下文检索响应时间 | < 500ms | ⏳ | 待测试 |
| 并发处理能力 | > 20 QPS | ⏳ | 待测试 |

## 🔧 故障排除

### 常见问题

**问题1**: 服务器启动失败
- **解决**: 检查端口17800是否被占用: `lsof -i :17800`
- **解决**: 检查Python环境和依赖: `python3 --version` 和 `pip list`
- **解决**: 查看完整错误日志: 前台启动服务器

**问题2**: 数据库连接失败
- **解决**: 确认Docker容器运行: `docker-compose ps`
- **解决**: 检查数据库日志: `docker-compose logs postgres`
- **解决**: 测试数据库连接: 使用psql直接连接测试

**问题3**: MCP注册失败
- **解决**: 确认Claude Code版本: `claude --version`
- **解决**: 检查网络连接: `curl http://localhost:17800/health`
- **解决**: 清除旧配置: `claude mcp remove sage` 后重新添加

**问题4**: 工具调用失败
- **解决**: 检查MCP服务器是否正在运行 (`curl http://localhost:17800/health`)
- **解决**: 确认Claude Code中sage服务器注册正确
- **解决**: 查看工具列表: 执行工具发现测试

**问题5**: 记忆检索为空
- **解决**: 确认数据库中有相关记忆
- **解决**: 调整搜索阈值或查询关键词
- **解决**: 检查向量索引状态

**问题6**: 响应时间过长
- **解决**: 检查网络连接
- **解决**: 检查SiliconFlow API配额
- **解决**: 考虑禁用神经重排序以提高速度

### 日志查看

如果遇到问题，可以查看相关日志：
```bash
# 查看MCP服务器实时日志
tail -f /Volumes/1T HDD/Sage/app/sage_mcp_server.log

# 查看数据库日志
docker-compose logs postgres

# 查看所有容器日志
docker-compose logs
```

### 系统诊断脚本

创建完整的诊断脚本：
```bash
#!/bin/bash
echo "=== Sage MCP 完整诊断 ==="

echo "1. 系统环境检查..."
echo "Python版本: $(python3 --version)"
echo "Docker版本: $(docker --version)"
echo "Claude Code版本: $(claude --version)"

echo -e "\n2. 项目文件检查..."
ls -la /Volumes/1T\ HDD/Sage/

echo -e "\n3. Docker容器状态..."
docker-compose ps

echo -e "\n4. 端口占用检查..."
lsof -i :17800

echo -e "\n5. 服务器健康检查..."
curl -s http://localhost:17800/health || echo "服务器不可达"

echo -e "\n6. MCP注册状态..."
claude mcp list | grep sage || echo "sage未注册"

echo -e "\n7. 工具发现测试..."
curl -s -X POST "http://localhost:17800/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"diag","method":"tools/list","params":{}}' | \
  grep -o '"name":"[^"]*"' | wc -l || echo "工具发现失败"

echo -e "\n=== 诊断完成 ==="
```

## 🎉 测试完成标准

✅ 服务器成功启动并通过健康检查  
✅ 数据库连接正常且包含历史记忆数据  
✅ MCP服务器成功注册到Claude Code  
✅ 所有5个工具可正常发现和调用  
✅ 所有7个记忆功能测试步骤成功执行  
✅ 工具响应时间在期望范围内  
✅ 记忆数据正确保存和检索  
✅ 智能检索功能正常工作  
✅ 上下文注入功能自动触发  

## 📝 测试报告

测试完成后，请记录：
1. 系统启动和配置过程中的问题
2. 每个功能的测试结果和响应时间
3. 发现的任何问题或异常
4. 性能表现评估
5. 用户体验反馈
6. 改进建议

---

**注意**: 这个测试将验证Sage MCP服务器与Claude Code的完整集成，确保从系统启动到记忆功能的全流程正常工作。请按照步骤逐一执行，记录每个环节的结果。