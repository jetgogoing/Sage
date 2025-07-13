# Sage MCP Docker 服务化执行计划

## 项目概述

将 Sage 记忆系统从 CLI 包装器架构转换为基于 Docker 的 MCP 服务器，实现与 Claude Code 的无缝集成。

### 项目目标
- 将 Sage 记忆系统作为整体服务包
- 通过 MCP 协议与 Claude Code 通信
- 保留原有功能（记忆存储、检索、向量化）
- 通过 .env 文件配置模型和 API KEY
- 基于 Docker 实现跨平台兼容（macOS, Windows, Linux）

### 目标架构

```
Claude Code (MCP Client)
         |
         | MCP Protocol (HTTP)
         v
┌─────────────────────────────────┐
│  Sage MCP Server (FastAPI)     │
│  ├─ save_conversation          │
│  ├─ get_context                │
│  └─ search_memory               │
└─────────────┬───────────────────┘
              |
              v
┌─────────────────────────────────┐
│  PostgreSQL + pgvector          │
│  (向量数据库 + 记忆存储)         │
└─────────────────────────────────┘
```

## 执行计划详情

### 第一阶段：MCP协议研究与服务器框架搭建

#### 目标
建立 Sage MCP 服务器的基础框架

#### 关键任务

1. **MCP协议标准研究**
   - 学习 MCP (Model Context Protocol) 规范
   - 分析 Claude Code 期望的 MCP 接口格式
   - 确定需要实现的核心端点
     - `get_context`: 获取相关历史上下文
     - `save_conversation`: 保存对话到数据库
     - `search_memory`: 搜索历史记忆

2. **FastAPI服务器框架**
   - 创建 `app/sage_mcp_server.py` 主服务文件
   - 实现基础的 FastAPI 应用结构
   - 添加路由定义和请求处理
   - 实现健康检查端点 `/health`
   - 添加基础错误处理和日志记录

3. **现有代码适配器**
   - 创建 `app/memory_adapter.py` 桥接现有功能
   - 导入并包装 `memory.py` 的核心函数
   - 保持与 `memory_interface.py` 的兼容性
   - 确保数据库连接正常工作
   - 验证向量化功能可用

#### 预期输出
- 可运行的 FastAPI 服务器（端口17800）
- 基础的 MCP 端点响应框架
- 与现有记忆系统的成功连接
- 基础测试用例通过

#### 技术要点
- 使用 FastAPI 异步特性提高性能
- 实现标准的 MCP 请求/响应格式
- 保持与现有数据库结构的兼容性

### 第二阶段：Docker容器化与配置系统重构

#### 目标
将MCP服务器容器化，重构配置管理系统

#### 关键任务

1. **Docker配置文件创建**
   ```dockerfile
   # Dockerfile 示例结构
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY app/ ./app/
   CMD ["uvicorn", "app.sage_mcp_server:app", "--host", "0.0.0.0", "--port", "17800"]
   ```
   
   - 更新 `docker-compose.yml` 配置
   ```yaml
   services:
     sage-mcp:
       build: .
       ports:
         - "17800:17800"
       depends_on:
         - postgres
       env_file:
         - .env
     
     postgres:
       image: pgvector/pgvector:pg16
       # ... 现有配置
   ```

2. **配置系统重构**
   - 创建新的 `.env.example` 模板
   ```env
   # API Provider Configuration
   SILICONFLOW_API_KEY=sk-xxx
   SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
   
   # Model Configuration
   EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
   SUMMARY_MODEL=deepseek-ai/DeepSeek-V2.5
   RERANKER_MODEL=Qwen/Qwen3-Reranker-8B
   
   # Database Configuration
   DB_HOST=postgres
   DB_PORT=5432
   DB_NAME=mem
   DB_USER=mem
   DB_PASSWORD=mem
   
   # MCP Server Configuration
   MCP_SERVER_PORT=17800
   LOG_LEVEL=INFO
   ```
   
   - 重构 `config_manager.py` 支持容器环境
   - 添加环境变量验证
   - 实现配置热重载机制

3. **依赖管理优化**
   - 创建精简的 `requirements.txt`
   - 使用多阶段构建减少镜像大小
   - 添加依赖版本锁定

#### 预期输出
- 完整的 Docker 部署配置
- 一键启动命令可用
- 配置验证机制完善
- 容器健康检查通过

### 第三阶段：数据库兼容性与迁移工具

#### 目标
确保现有记忆数据完全兼容，提供数据迁移工具

#### 关键任务

1. **数据库结构验证**
   - 检查 conversations 表结构
   - 验证向量维度（4096维）
   - 确保索引正确创建
   - 测试查询性能

2. **数据迁移工具开发**
   ```python
   # app/migration_tool.py 结构
   class MigrationTool:
       def backup_database(self):
           """备份现有数据"""
           pass
       
       def migrate_data(self):
           """迁移数据到新环境"""
           pass
       
       def verify_migration(self):
           """验证迁移完整性"""
           pass
   ```

3. **向量化功能测试**
   - 验证 SiliconFlow API 连接
   - 测试向量生成质量
   - 确保检索准确性

#### 预期输出
- 数据无损迁移完成
- 历史记忆完整保留
- 性能测试通过

### 第四阶段：Claude Code MCP集成与协议实现

#### 目标
实现与Claude Code的完整MCP集成

#### 关键任务

1. **MCP协议完整实现**
   ```python
   # MCP工具定义示例
   @app.post("/tools")
   async def list_tools():
       return {
           "tools": [
               {
                   "name": "save_conversation",
                   "description": "Save conversation to memory",
                   "inputSchema": {
                       "type": "object",
                       "properties": {
                           "user_prompt": {"type": "string"},
                           "assistant_response": {"type": "string"}
                       }
                   }
               },
               {
                   "name": "get_context",
                   "description": "Get relevant context for query",
                   "inputSchema": {
                       "type": "object",
                       "properties": {
                           "query": {"type": "string"}
                       }
                   }
               }
           ]
       }
   ```

2. **Claude Code注册与测试**
   ```bash
   # 注册 MCP 服务器
   claude mcp add sage http://localhost:17800
   ```
   
   - 测试工具发现
   - 验证自动保存
   - 测试上下文注入

3. **错误处理与降级**
   - 实现超时处理
   - 添加重试机制
   - 提供降级策略

#### 预期输出
- Claude Code 成功识别服务
- 对话自动保存功能正常
- 历史上下文正确注入
- 错误处理机制完善

### 第五阶段：跨平台部署验证与性能优化

#### 目标
验证跨平台兼容性，优化性能

#### 关键任务

1. **跨平台测试矩阵**
   
   | 平台 | Docker版本 | 测试项目 | 状态 |
   |------|-----------|---------|------|
   | macOS | 24.x | 部署/性能/稳定性 | ✓ |
   | Windows | 24.x | 部署/性能/稳定性 | ✓ |
   | Linux | 24.x | 部署/性能/稳定性 | ✓ |

2. **性能优化措施**
   - 实现查询结果缓存
   - 优化数据库连接池
   - 添加向量索引优化
   - 实现异步处理

3. **用户体验优化**
   - 简化配置流程
   - 添加配置向导
   - 提供诊断工具
   - 实现自动修复

#### 预期输出
- 全平台部署成功
- 响应时间 < 500ms
- 配置错误率 < 5%
- 用户满意度高

### 第六阶段：文档完善与生产就绪

#### 目标
完善文档，确保生产级别质量

#### 关键任务

1. **文档体系建设**
   ```
   docs/
   ├── README.md              # 项目概述
   ├── INSTALLATION.md        # 安装指南
   ├── CONFIGURATION.md       # 配置说明
   ├── API_REFERENCE.md       # API文档
   ├── TROUBLESHOOTING.md     # 故障排除
   └── CONTRIBUTING.md        # 贡献指南
   ```

2. **配置示例库**
   - 不同API提供商配置
   - 性能调优示例
   - 安全最佳实践
   - 监控配置模板

3. **生产环境准备**
   - 日志聚合配置
   - 监控指标定义
   - 备份恢复脚本
   - 性能基准测试

4. **开源发布准备**
   - 代码审查清单
   - 安全漏洞扫描
   - 许可证选择
   - 版本发布流程

#### 预期输出
- 完整的用户文档
- 开发者友好的API文档
- 生产级别的运维工具
- 开源社区就绪

## 实施建议

### 优先级排序
1. **P0 - 核心功能**：MCP服务器基础实现
2. **P1 - 集成测试**：Claude Code集成验证
3. **P2 - 生产就绪**：性能优化和文档完善

### 风险管理
1. **技术风险**
   - MCP协议理解偏差 → 提前验证原型
   - 性能瓶颈 → 早期性能测试
   - 兼容性问题 → 渐进式迁移

2. **项目风险**
   - 时间延误 → 阶段性交付
   - 需求变更 → 模块化设计
   - 质量问题 → 持续集成测试

### 成功指标
- [ ] Docker一键部署成功率 > 95%
- [ ] Claude Code集成稳定性 > 99%
- [ ] 记忆检索响应时间 < 500ms
- [ ] 用户配置成功率 > 90%
- [ ] 文档完整度评分 > 4.5/5

## 下一步行动

1. **立即开始**：创建项目基础结构和MCP服务器框架
2. **技术验证**：实现最小可行的MCP端点
3. **迭代优化**：基于测试反馈持续改进
4. **社区反馈**：早期用户测试和意见收集

---

*本计划基于当前项目状态和需求分析制定，将根据实施过程中的发现进行适应性调整。*