# Sage_MCP_轻量化记忆系统设计框架（v1.0）

> **目标**：打造一个为 Claude CLI 插件服务的、本地部署、无感注入、极简依赖的个人记忆系统。

---

## 1. 架构总览

```
┌──────────────────────────────┐
│     用户终端：claude CLI     │
│   (alias -> claude_mem.py)   │
└────────────┬─────────────────┘
             ▼
┌──────────────────────────────┐
│ claude_mem.py（猴子补丁注入器）│
│ ├─ 捕获 query                  │
│ ├─ get_context() 查询历史     │
│ ├─ 调用 claude 原生函数        │
│ └─ save_memory(query, resp)  │
└────────────┬─────────────────┘
             ▼
┌──────────────────────────────┐
│ 本地数据库（PostgreSQL + pgvector） │
│ ├─ conversations 表            │
│ └─ 存文本 + 向量（4096维）     │
└──────────────────────────────┘
```

---

## 2. 技术选型

| 层级     | 组件                     | 选择理由                    |
|--------|------------------------|---------------------------|
| 注入器    | claude_mem.py          | Monkey-Patching 替代 wrapper，稳定无感 |
| 数据库    | PostgreSQL + pgvector | 一体化存储文本与向量，结构化 + 语义检索 |
| 向量模型  | Qwen3-Embedding-8B     | 高质量中文语义向量，SiliconFlow 托管 |
| 摘要模型  | DeepSeek-V2.5-1210     | 多段融合能力强，成本低             |

---

## 3. conversations 表结构

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE conversations (
  id SERIAL PRIMARY KEY,
  session_id UUID DEFAULT gen_random_uuid(),
  turn_id INT NOT NULL,
  role VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(4096),
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. 查询逻辑（get_context）

1. 将用户 query 向量化
2. 查询 conversations 表中与之相似的 embedding
3. 可选：按 session_id / role / 时间过滤
4. 使用 DeepSeek-V2.5 总结为上下文注入片段

---

## 5. 写入逻辑（save_memory）

1. 分别向量化 user query 与 Claude response
2. 插入两条记录（role=user / claude）
3. 与查询过程一致写入 embedding 字段

---

## 6. 注入入口（猴子补丁）

1. 定位 claude CLI 内部的 send_request 函数
2. Monkey Patch 为我们自己的函数：
   - 调用 get_context(query)
   - 拼接为 prompt
   - 调用原 send_request
   - 保存完整对话

---

## 7. 启动方式

通过 alias：

```bash
alias claude='python /path/to/claude_mem.py'
```

运行命令时即自动注入记忆上下文并记录回应。

---

## 8. 后续优化方向

- 精排模型集成 Qwen3-Reranker-8B
- Prompt Token 控制（预算/截断）
- 自动压缩旧会话为“知识卡片”
