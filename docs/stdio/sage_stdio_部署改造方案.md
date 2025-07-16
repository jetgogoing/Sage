# 🔧 Sage MCP STDIO 化全面改造实施方案

> 本文档基于 Sage 项目 V1–V4 四个版本演进及五阶段开发报告，重新梳理 STDIO-only 通讯的深度改造计划，确保所有核心功能模块按阶段平滑迁移、验证和上线。

---

## 🚀 一、项目背景与目标

### 1.1 背景

- 原 Sage MCP V4 已集成完整智能记忆能力，包括自动保存、上下文注入、会话管理、记忆分析、智能提示及性能优化。
- 当前部署方案侧重 HTTP 或 stdio 混合，需简化为纯 STDIO 通讯，以适配 Windsurf/Cursor 等 IDE 的 Claude Code 插件。
- 数据存储采用 PostgreSQL + pgvector，已完成数据库与扩展初始化。

### 1.2 目标

1. **纯 STDIO 通讯**：移除所有 HTTP 服务，采用 `memory_server --stdio` 作为唯一接口。
2. **容器化托管**：所有组件（Postgres、MCP Server、各模块）通过 Docker Compose 管理，服务间通过 Docker 网络内通信。
3. **平滑迁移**：分阶段逐步整合已完成的模块（V2–V4）与命令体系，确保功能不丢失。
4. **全面验证**：沿用五阶段测试套件及执行报告中的用例，确保功能、性能及稳定性。

---

## 🗺️ 二、架构概览

## \$1

## 🔍 与 Anthropic MCP 标准契合度

1. **握手流程**：
   - 客户端发起 `initialize` 请求：
     ```json
     {"method":"initialize","params":{"version":"1.0","capabilities":[]}}
     ```
   - 服务端返回初始化结果：
     ```json
     {"result":{"notifications_initialized":true}}
     ```
2. **消息格式一致性**：所有请求/响应均为单行 JSON，UTF-8 编码，符合 MCP Connector STDIO 规范。
3. **事件通知支持**：预留 `notifications` 方法扩展，兼容 MCP Connector 文档中实时事件流。
4. **错误结构兼容**：错误消息使用 `{ "id":<id>, "error": { "message": "..." } }` 格式，与官方示例保持一致。
5. **版本与能力声明**：在 `initialize` 请求中上报 `version` 与 `capabilities`，便于后续协议扩展与兼容。

> 以上改造在彻底保留 Sage V1–V4 智能记忆功能的同时，严格遵守 Anthropic MCP 标准的握手、消息、错误和事件机制要求。

---

## 🛠️ 三、模块与命令一览

| 版本 | 模块 / 文件                                    | 主要功能                                                    | 关键命令                                  |
| -- | ------------------------------------------ | ------------------------------------------------------- | ------------------------------------- |
| V2 | `sage_mcp_stdio_v2.py`                     | 标准 stdio 通信，命令解析与路由                                     | `/SAGE`, `/SAGE-MODE`, `/SAGE-RECALL` |
|    | `sage_mcp_v2_enhanced.py`                  | 自动保存 (`AutoSaveManager`)、上下文注入 (`SmartContextInjector`) | `/SAGE-AUTO`, `/SAGE-INJECT`          |
| V3 | `sage_session_manager_v2.py`               | 会话管理与导出 (`EnhancedSessionManager`)                      | `/SAGE-SESSION search/analyze`        |
|    | `sage_memory_analyzer.py`                  | 多维度记忆分析（聚类、时间模式、知识图谱等）                                  | `/SAGE-ANALYZE`                       |
| V4 | `sage_smart_prompt_system.py`              | 智能提示生成与用户画像管理 (`SmartPromptGenerator`)                  | `/SAGE-PROMPT`, `/SAGE-STATUS`        |
|    | `sage_error_handler.py`、`performance_*` 模块 | 错误处理、熔断、性能监控与优化                                         | 内部自动，无需用户命令                           |

---

## 📅 四、分阶段改造计划

| 阶段         | 时间估算 | 目标               | 产出                                                                             | 验证用例来源 |
| ---------- | ---- | ---------------- | ------------------------------------------------------------------------------ | ------ |
| **Phase1** | 1 天  | **核心 stdio 服务器** | - 合并 `sage_mcp_stdio_v2.py` 与 `sage_mcp_v4_final.py` 为 `memory_server --stdio` |        |

- 集成 `SageCommandParser`, `SageMCPServer`, `EnhancedMemoryAdapter`, `IntelligentRetrievalEngine`, `ConversationTracker`, `SageSessionManager` | 第1、5 阶段命令解析与服务启动用例 (test\_unit\_command\_parser & test\_phase5\_connection) fileciteturn0file0turn0file8 | | **Phase2**| 1 天    | **自动保存与上下文注入**                   | - 将 `AutoSaveManager`, `SmartContextInjector`, `ConversationFlowManager` 纳入 stdio 逻辑  | 第2 阶段自动保存与注入测试 (test\_unit\_auto\_save & test\_unit\_smart\_prompt) fileciteturn0file1 | | **Phase3**| 1 天    | **会话管理与记忆分析**                    | - 集成 `EnhancedSessionManager`, `MemoryAnalyzer` 与对应命令路由                      | 第3 阶段会话与分析测试 (test\_integration\_complete) fileciteturn0file2 | | **Phase4**| 1 天    | **智能提示与错误&性能优化**                | - 加入 `SmartPromptGenerator`, `ErrorHandler`, `PerformanceMonitor`, `CircuitBreaker`   | 第4 阶段智能提示 & 性能测试 (test\_unit\_error\_handler & test\_unit\_all) fileciteturn0file3 | | **Phase5**| 0.5 天  | **容器化与 STDIO 包装脚本**                 | - 编写 `run_sage_stdio.sh`, 精简 Dockerfile, 更新 docker-compose.yml                | Phase5 ⎯ 容器健康检查与连接测试 (test\_mcp\_connection) fileciteturn0file7 | | **Phase6**| 0.5 天  | **文档与持续集成**                        | - 更新 README.md, docs/usage-guide.md, docs/deployment-guide.md
- 添加 CI 脚本自动化验证 STDIO、单元与集成测试 | 第5 阶段文档与测试覆盖报告 (test\_e2e\_scenarios & docs) fileciteturn0file4turn0file5 |

---

## ✅ 五、详细实施内容

### Phase1：核心 stdio 服务器

1. **合并核心**：移除 HTTP 监听逻辑，入口直接为 `--stdio`。
2. **主循环**：读取 stdin 单行 JSON，交由 `SageCommandParser.parse()`，路由到 `SageMCPServer.handle_command()`。
3. **集成模块**：在同一进程中加载：
   - `EnhancedMemoryAdapter`（负责 Embedding + pgvector 检索）
   - `IntelligentRetrievalEngine`（神经网络重排序）
   - `ConversationTracker` + `SageSessionManager`（会话标记）
4. **错误边界**：添加最低限度的 try-catch，输出 `{"error":...}`。

### Phase2：自动保存与上下文注入

1. 调用 `AutoSaveManager.enable()` 或根据命令开关自动跟踪对话。
2. 在 `handle_user_input` 时，触发 `SmartContextInjector.get_context_for_query()`，并将注入内容拼接至原始请求。
3. 在 `handle_assistant_response` 时，调用 `AutoSaveManager.add_response()` & `save_if_complete()`。
4. 验证：对话结束时，Postgres 已持久化完整记录。

### Phase3：会话管理与记忆分析

1. 添加 `/SAGE-SESSION` 子命令，路由至 `EnhancedSessionManager`。
2. 添加 `/SAGE-ANALYZE` 子命令，调用 `MemoryAnalyzer.run(type, params)`。
3. 确保分析结果 JSON 可被 CLI 解析并格式化显示。

### Phase4：智能提示与错误&性能优化

1. 年 `SmartPromptGenerator.generate_smart_prompt()`，提供 `/SAGE-PROMPT` 支持。
2. 全局装饰器：
   - `@with_error_handling` 包裹核心操作
   - `@with_performance_monitoring` 监控延迟
   - `@with_circuit_breaker` 防止故障扩散
3. 日志格式：标准化输出 JSON + console 日志，便于调试。

### Phase5：容器化与 STDIO 包装脚本

1. **Docker Compose**：仅定义 `postgres` 服务，网络 `sage-net`。
2. **镜像构建**：在 `Dockerfile` 中安装依赖、拷贝所有 Python 模块、暴露 STDIO（无需端口）。
3. **包装脚本 **``：
   ```bash
   #!/usr/bin/env bash
   docker compose up -d postgres  # 确保数据库
   exec docker run --rm -i \
     --network sage-net \
     -e DATABASE_URL='postgresql://sage:sage@postgres:5432/sage_memory' \
     ghcr.io/jetgogoing/sage-mcp:latest \
     memory_server --stdio
   ```
4. **注册命令**：`claude mcp add sage ./run_sage_stdio.sh`

### Phase6：文档与 CI/CD

1. 更新 README.md 中部署与使用说明，侧重 STDIO。
2. 修改 docs 文件：添加 STDIO 协议格式、命令表、示例用法。
3. 在 GitHub Actions 中添加工作流：
   - 启动 Postgres 服务（docker-compose up）
   - 执行单元与集成测试（pytest）
   - 执行 E2E 测试（模拟 STDIO 请求）
   - 构建并推送容器镜像。

---

## 🎯 六、验收标准

1. **所有命令**：`/SAGE`, `/SAGE-MODE`, `/SAGE-SESSION`, `/SAGE-ANALYZE`, `/SAGE-PROMPT`, `/SAGE-STATUS` 均可通过 STDIO 调用。
2. **自动保存与注入**：完整对话与上下文注入效果符合 Phase2 测试报告指标。
3. **会话与分析**：支持会话搜索、分析场景，结果与 Phase3 报告一致。
4. **智能提示**：生成时间 <100ms，准确度与 Phase4 报告吻合。
5. **容器化部署**：仅启动 Postgres 服务，`run_sage_stdio.sh` 即可完成所有 MCP 会话。
6. **CI 绿灯**：所有单元、集成与 E2E 测试在 CI 环境中通过。

---

## 📥 获取计划

请点击右侧面板 “导出 Markdown” 按钮，下载本文件作为 `SOLA_deploy_stdio_plan.md`。

---

*文档由 Claude Code Assistant 自动生成，基于项目历史执行报告与源码结构，确保无感部署与全功能保留。*

