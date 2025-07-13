# Sage 全局记忆系统重构建议方案

> 📅 日期：2025-07-13  
> 🎯 目标：将 Sage 项目简化为稳定、高可用的“全局聊天记忆系统”，不再出现递归、超时、空写等问题。

---

## ✅ 一、目标回顾

Sage 的唯一核心功能是：

> **自动记录所有终端调用 Claude CLI 的历史对话，并在下次提问时注入相关历史上下文。**

---

## 🧱 二、推荐最小架构 (MVP Plus)

| 模块       | 状态       | 说明 |
|------------|------------|------|
| PostgreSQL + pgvector | ✅ 保留 | 使用 `conversations` 表，4096维向量 |
| `sage_mem.py` (包装器) | ✅ 保留 | 注入上下文 + 写入历史 |
| `memory.py` | ✅ 保留 | 嵌入+检索逻辑封装 |
| DeepSeek 摘要 | ❌ 暂停 | 先直接拼接历史上下文，等系统稳定后再加 |
| CLI 工具集 | ⚠️ 精简 | 仅保留 `--memory-stats` `--search` `--clear` |
| 性能与健康监控 | ❌ 移除 | 初期不需要复杂性能组件 |
| 安全机制 | ✅ 强化 | 去除默认 key，数据库强密码 |

---

## 🛠️ 三、关键路径代码建议

### 1. 递归保护（包装器最顶部）

```python
import os, sys, subprocess

if os.environ.get("SAGE_CLAUDE_WRAPPER_ACTIVE") == "1":
    real = os.environ["CLAUDE_CLI_PATH"]
    os.execvpe(real, [real] + sys.argv[1:], os.environ)

os.environ["SAGE_CLAUDE_WRAPPER_ACTIVE"] = "1"
```

### 2. 子进程执行时使用 alias

```bash
alias claude='CLAUDE_CLI_PATH=/usr/local/bin/claude \
              python /path/to/sage_mem.py'
```

---

## 🚀 四、部署脚本（真正 4 步到位）

```bash
git clone https://github.com/jetgogoing/Sage.git
cd Sage/docker && docker compose up -d
cp .env.example .env && vi .env   # 填 API_KEY
./scripts/install_minimal.sh
```

---

## 🔍 五、验证测试

```bash
claude "你好 Sage"
claude --memory-stats
```

确认：
- 终端响应正常
- 数据写入成功
- 统计命令可用

---

## ⚙ 六、未来功能可选增量（按优先级）

| 优先级 | 功能           | 触发场景             |
|--------|----------------|----------------------|
| 🟢 P0  | 上下文 token 限制 | 当出现提示被截断     |
| 🟡 P1  | 嵌入缓存         | 当请求量增长         |
| 🟡 P1  | 搜索分页 / 导出   | 当记录超过 10 万条   |
| 🟠 P2  | reranker + 摘要 | 提升注入质量         |
| 🟠 P2  | 日志 & 监控     | 用于多用户部署场景   |

---

## 📁 七、一页决策表

| 文件 / 模块           | 建议      |
|-----------------------|-----------|
| `sage_mem.py`         | ✅ 保留    |
| `memory.py`           | ✅ 保留    |
| `init.sql`            | ✅ 保留    |
| `performance_optimizer.py` | ❌ 移除 |
| `error_recovery.py`   | ❌ 移除    |
| `sage_memory_cli.py`  | ⚠️ 精简    |
| `.env.example`        | ✅ 保留    |
| `tests/`              | ✅ 保留    |

---

## ✅ 总结

Sage 应回归简单的核心路径：包装器 ➝ 记忆模块 ➝ pgvector 存储。只有确保主流程稳定，才能承载更多插件式功能。将复杂逻辑拆出主干，是本轮架构重构的关键。

