# 🚀 Sage MCP 项目迁移计划（移至 macOS 系统盘）

> 更新时间：2025-07-13 18:43:31
> 适用于：Intel 芯片 macOS 用户，原始项目位于带空格的移动硬盘路径 `/Volumes/1T HDD/Sage`（现已迁移至 `/Users/jet/sage`）

---

## 🎯 迁移目标

- 避免因空格路径引发的 Claude Code MCP 执行失败
- 提升脚本执行稳定性与权限兼容性
- 保持项目原样迁移，确保 Docker、Python 虚拟环境等继续可用

---

## 📁 建议的新目录结构

```
~/Projects/Sage/
├── start_sage_mcp_stdio.sh
├── sage_mcp_stdio.py
├── docker-compose-sage.yml
├── app/
└── ...
```

---

## 🪜 迁移步骤

### Step 1️⃣：创建目标目录

```bash
mkdir -p ~/Projects
```

---

### Step 2️⃣：移动整个 Sage 项目目录

```bash
mv "/Volumes/1T HDD/Sage" ~/Projects/Sage
```

---

### Step 3️⃣：进入新目录并验证内容

```bash
cd ~/Projects/Sage
ls -la
```

确保你能看到脚本文件、Docker 配置和源码文件。

---

### Step 4️⃣：重新配置 Claude Code MCP

```bash
claude mcp remove sage
claude mcp add sage ~/Projects/Sage/start_sage_mcp_stdio.sh
```

---

### Step 5️⃣：重新启动 Claude Code

重启 VS Code 或终端中的 `claude` CLI，让 MCP 状态刷新。

---

### Step 6️⃣：测试 MCP 是否连接成功

在 Claude Code 控制台输入：

```bash
/status
```

或观察是否从 `◯ connecting…` 变为 `✅ connected`

---

## ✅ 成功标准

| 检查项 | 验证方式 | 成功条件 |
|--------|----------|----------|
| MCP 路径正确 | `claude mcp list` | 显示为系统盘路径 |
| 脚本正常执行 | `bash ~/Projects/Sage/start_sage_mcp_stdio.sh` | 无报错、启动 stdio 包装器 |
| Claude Code 状态正常 | `/status` 或界面状态 | 显示连接成功 |

---

## 📌 注意事项

- 移动硬盘路径中含空格和挂载限制，极易导致 CLI/脚本执行失败
- 系统盘具备完整的执行权限与兼容性，是开发的推荐位置
- 若 `.venv` 虚拟环境已绑定旧路径，请重新创建或更新路径引用

---

## 🧠 总结

迁移 Sage 项目到系统盘（如 `~/Projects/Sage`）是解决 Claude MCP 长连接失败的根本方案。它规避了路径空格、权限限制、挂载逻辑复杂等问题，保证脚本与 Docker 服务稳定运行，是最推荐的结构化部署方式。

