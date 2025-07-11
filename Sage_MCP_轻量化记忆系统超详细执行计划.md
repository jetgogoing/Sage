# Sage_MCP_轻量化记忆系统超详细执行计划（v1.0）

> 目标：30 分钟内部署完毕，并实现无感注入 + 回写对话 + 历史检索。

---

## ⏳ 总览：五个阶段、快速起步

| 阶段 | 关键目标                     | 输出产物                          |
|------|----------------------------|---------------------------------|
| 0    | 启动 PostgreSQL + pgvector | docker-compose + init SQL     |
| 1    | 实现 claude_mem.py 注入器   | Monkey-Patching 替代 wrapper    |
| 2    | 实现 get_context 查询逻辑   | 从 pgvector 检索并摘要返回        |
| 3    | 实现 save_memory 写入逻辑   | 写入 user 与 claude 两条记录      |
| 4    | 本地 alias 设置              | 无缝替代 claude 命令               |

---

## 0. 启动数据库服务

- 创建 docker-compose.yml：

```yaml
services:
  pg:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: mem
      POSTGRES_PASSWORD: mem
      POSTGRES_DB: mem
    ports:
      - "5432:5432"
    volumes:
      - ./pgdata:/var/lib/postgresql/data
```

- 初始化数据库表：

```bash
psql postgresql://mem:mem@localhost:5432/mem -c "
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS conversations (
  id SERIAL PRIMARY KEY,
  session_id UUID DEFAULT gen_random_uuid(),
  turn_id INT NOT NULL,
  role VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(4096),
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);"
```

---

## 1. 注入器 claude_mem.py

```python
import claude.api
from claude.main import cli
from memory import get_context, save_memory

original = claude.api.send_request

def patched(prompt, **kw):
    context = get_context(prompt)
    full_prompt = f"{context}

{prompt}"
    resp = original(full_prompt, **kw)
    save_memory(prompt, resp.text)
    return resp

claude.api.send_request = patched

if __name__ == "__main__":
    cli()
```

---

## 2. get_context 实现

```python
def get_context(query):
    vec = embed(query)  # Qwen3 Embedding API
    rows = search_pgvector(vec)
    return summarize(rows)  # DeepSeek API
```

---

## 3. save_memory 实现

```python
def save_memory(q, a):
    vq = embed(q)
    va = embed(a)
    insert(role="user", text=q, embedding=vq)
    insert(role="claude", text=a, embedding=va)
```

---

## 4. alias 设置

```bash
alias claude='python /path/to/claude_mem.py'
```

---

## ✅ 成功标志

- `claude "写一段Python排序代码"` 会自动注入上下文
- `.bashrc` alias 生效后无感使用
- 数据会写入 conversations 表，embedding 可查询

