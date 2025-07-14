# Sage 全局记忆系统注入失败问题排查指南

> 日期：2025-07-13  
> 问题：在窗口 A 输入“猫叫面团”，窗口 B 提问“你还记得我家的猫叫什么名字吗？”，Claude 回答“不记得”，说明记忆注入未生效。

---

## ❗ 当前行为说明了什么？

Claude 没有注入历史上下文，回答的是无记忆模式的默认回答。这说明：

> ❌ Sage 并没有成功在子进程中将“面团”的相关上下文注入到 Claude 提问的 prompt 中。

---

## ✅ 排查清单（按优先级）

### ❶ `CLAUDE_CLI_PATH` 设置错误

- **检查命令：**
```bash
echo $CLAUDE_CLI_PATH
which claude
type sage
```

- **正确设置方式（示例）：**
```bash
export CLAUDE_CLI_PATH=/usr/local/bin/claude
alias sage='python /your/path/sage_mem.py'
```

---

### ❷ 注入逻辑未执行

请打开 `sage_mem.py`，确保有如下代码：

```python
from memory import get_context

context = get_context(query)
prompt = f"{context}\n\n{query}"
```

⚠️ 如果直接将 `query` 原样传给 subprocess，而没有拼接 `context`，那注入当然不会发生。

---

### ❸ 数据库未成功保存

- **搜索确认命令：**
```bash
sage-memory search 面团
```

若查不到“面团”，说明保存失败或嵌入未生效。

---

### ❹ 实际 prompt 没有传递 context

可临时加入以下 debug 语句：

```python
print("======= 最终 Prompt =======")
print(prompt)
```

---

## 🧪 最小验证手动测试

```bash
export CLAUDE_CLI_PATH=/usr/local/bin/claude
export SAGE_CLAUDE_WRAPPER_ACTIVE=""
python sage_mem.py "你记得我刚才说我猫叫什么吗？"
```

并插入调试代码：
```python
print("context:", get_context("你记得我刚才说我猫叫什么吗？"))
```

---

## 🔧 建议下一步

- 打开 `sage_mem.py`，确认是否调用 `get_context()` 并拼接到 `query`
- 执行 `sage-memory search 面团`，确认数据库是否写入成功
- 若方便，可将 `sage_mem.py` 粘贴出来，我可以静态审查逻辑

---

## ✅ 总结

Sage 当前最可能的根因：
- 子进程执行路径绕过了 prompt 注入逻辑
- `CLAUDE_CLI_PATH` 指向了错误的执行文件
- 数据库保存未成功或没有进行上下文向量检索

下一步建议从 prompt 拼接逻辑入手，确保调用链闭环。

