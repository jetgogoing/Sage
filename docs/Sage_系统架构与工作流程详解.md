# Sage 系统架构审查与工作流程详解（阶段4）

> 🕓 文档生成时间：2025-07-13  
> 📄 来源：阶段4完整执行报告 + Claude Code 集成实测分析

---

## ✅ 一、当前 Sage 架构是否合理？

根据《阶段4完整执行报告》可知，当前系统在以下层面实现了成熟、合理的架构设计：

| 层级 | 描述 | 状态 |
|------|------|------|
| Claude Code 通信机制 | 使用 MCP HTTP 协议连接 Sage | ✅ |
| MCP Server 接口设计 | 实现标准 `/mcp`、`/tools/get_context`、`/tools/save_conversation` 等 | ✅ |
| Prompt 注入机制 | 自动注入上下文，触发 `get_context` 工具 | ✅ |
| 数据存储层 | PostgreSQL + pgvector 向量化存储 | ✅ |
| 自动对话保存 | 每轮用户与助手对话通过 `save_conversation` 工具写入数据库 | ✅ |
| 性能优化 | 延迟低于 0.5s，异步缓存策略生效 | ✅ |
| 安全性 | API Key 管理、加密存储、本地运行 | ✅ |

---

## 🧠 二、每次发送信息时，Sage 在背后如何工作？

### 1️⃣ 用户在 Claude Code 中输入一句话

例如：

```
你还记得我上次说我猫叫什么吗？
```

触发 MCP Prompt 模板中的：

```jinja2
{{tool:get_context query=user_input}}
```

### 2️⃣ Claude Code 调用 Sage 的 `/tools/get_context`

发送请求：

```json
POST /tools/get_context
{
  "query": "你还记得我上次说我猫叫什么吗？",
  "conversation_id": "abc123"
}
```

### 3️⃣ Sage 执行上下文检索逻辑：

- 将 `query` 嵌入为 4096 维向量
- 在 pgvector 中做语义检索（cosine similarity）
- 可选使用 Reranker 精排
- 可选摘要压缩（DeepSeek）
- 返回最终上下文字符串：

```json
{
  "output": "你说过你家猫叫面团，它特别喜欢钻纸箱。"
}
```

### 4️⃣ Claude Code 拼接上下文并生成最终回复

构造完整 prompt：

```
系统提示：
你说过你家猫叫面团，它特别喜欢钻纸箱。

用户输入：
你还记得我上次说我猫叫什么吗？

Claude 回复：
你说你家的猫叫面团。
```

### 5️⃣ Claude Code 自动调用保存工具

发起：

```json
POST /tools/save_conversation
{
  "messages": [
    {"role": "user", "content": "你还记得..."},
    {"role": "assistant", "content": "你说你家的猫叫面团。"}
  ],
  "conversation_id": "abc123"
}
```

### 6️⃣ Sage 保存数据到数据库

- 嵌入每条消息文本
- 插入 PostgreSQL `conversations` 表
- 包含 session_id, turn_id, role, embedding, timestamp 等字段

---

## ✅ 总结：这套系统具备以下特性

| 特性 | 表现 |
|------|------|
| 📦 完全自动化 | 发送信息即触发注入与保存，无需用户操作 |
| 🔁 持续性记忆 | 每轮对话形成长记忆链条 |
| 📊 可监控可调 | 工具可通过 MCP 命令单独调用测试 |
| 💡 架构解耦 | Claude 与 Sage 分离，可独立部署、替换 |
| 🧠 高拓展性 | 支持插件化模型、更换摘要器、缓存、Web UI |
| 🔒 安全合规 | 本地部署，权限隔离，Key 不外泄 |

---

如需图形流程图或 UI 注入模拟，请联系文档作者自动生成 PDF / PNG 图示版本。
