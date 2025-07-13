# Sage CLI Wrapper 递归保护方案

在 `feature/stage4-stable-rollback` 分支中，`claude_mem.py` 作为包装器调用自身存在递归风险，导致无限循环。以下为问题分析与解决方案：

---

## ❗ 问题现象

若 `CLAUDE_CLI_PATH` 环境变量未正确配置，或者被设为 alias，例如：

```bash
alias claude='python /path/to/claude_mem.py'
```

那么在 `claude_mem.py` 内部执行：

```python
subprocess.Popen([CLAUDE_CLI_PATH] + sys.argv[1:])
```

将再次调用自身，进入无限递归。

---

## ✅ 解决方案

### 方法一：正确设置 `CLAUDE_CLI_PATH`

确保该环境变量指向 **真实的 Claude 可执行文件路径**，例如：

```bash
export CLAUDE_CLI_PATH=/usr/local/bin/claude
```

不要设置为 `claude` 或指向当前 wrapper。

---

### 方法二：在 wrapper 中添加递归保护逻辑

在 `claude_mem.py` 顶部加入以下代码：

```python
# ───────────────────────────────
# 防止递归保护 Guard
import os, sys, subprocess

if os.environ.get("SAGE_CLAUDE_WRAPPER_ACTIVE") == "1":
    # 已在 wrapper 中，直接调用真实 CLI
    real = os.getenv("CLAUDE_CLI_PATH")
    sys.exit(subprocess.call([real] + sys.argv[1:]))

# 首次进入 wrapper，设置标志
os.environ["SAGE_CLAUDE_WRAPPER_ACTIVE"] = "1"
# ───────────────────────────────
```

该逻辑确保：
- 只在最外层注入上下文；
- 子进程不会再进入注入逻辑，从而避免递归。

---

## 📌 推荐做法

两种方法可以叠加使用，确保系统稳定性与容错性：

- 设置 `CLAUDE_CLI_PATH` 指向真实 CLI；
- 同时启用递归保护代码段。

---

## ✅ 示例：组合使用

```bash
export CLAUDE_CLI_PATH=/usr/local/bin/claude
alias claude='python /path/to/claude_mem.py'
```

`claude_mem.py` 中顶部加上递归保护段即可。

