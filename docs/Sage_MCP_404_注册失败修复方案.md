# Claude Code 无法连接 Sage MCP 的根因分析与修复方案

> 🕓 时间：2025-07-14  
> 🧠 场景：执行 `/mcp` 时返回 `Dynamic client registration failed: HTTP 404`

---

## ❗ 问题描述

在将 Sage 作为 Claude Code 的 MCP 服务注册后，运行：

```
claude mcp add sage http://localhost:17800/mcp
```

却持续出现：

```
Status: ✘ failed
Error: Dynamic client registration failed: HTTP 404
```

---

## 🔍 根因分析

根据你在 GitHub 的 `feature/improved-commits` 分支的实际实现逻辑，MCP Server 的端点存在以下问题：

### 1. 缺少 `token` 和 `auth` 路由（客户端动态注册流程失败）

Claude Code 在尝试注册 MCP 服务时，会访问以下路径：

- `POST /mcp/token`：获取 access_token
- `POST /mcp/auth`：注册授权校验

你的 `sage_mcp_server.py` 中没有实现这两个端点，导致请求返回 404。

---

### 2. `.well-known` 配置中 `tools_endpoint` 不一致

你的 `/mcp/.well-known/mcp-configuration` 返回了：

```json
{
  "tools_endpoint": "http://localhost:17800/tools"
}
```

而你实际提供工具调用的地址是：

```
POST /mcp
```

这导致 Claude Code 在调用 `tools/list` 时找不到路由。

---

## ✅ 修复建议

### 1. 添加缺失端点

在 `app/sage_mcp_server.py` 中新增：

```python
@app.post("/mcp/token")
async def mcp_token():
    return {
        "access_token": "not-required",
        "token_type": "Bearer",
        "expires_in": 3600
    }

@app.post("/mcp/auth")
async def mcp_auth():
    return { "status": "ok" }
```

> 👆 这两个端点不做实际校验，只用于满足 Claude Code 的连接流程。

---

### 2. 修复 `.well-known` 中的 `tools_endpoint`

将：

```json
"tools_endpoint": "http://localhost:17800/tools"
```

改为：

```json
"tools_endpoint": "http://localhost:17800/mcp"
```

或者在服务端增加兼容路径：

```python
@app.post("/tools")
async def tools_passthrough(request: Request):
    return await mcp_entrypoint(request)
```

---

## 🔁 测试步骤

```bash
# 重启服务
pkill -f sage_mcp_server.py
python3 app/sage_mcp_server.py &

# 移除旧 MCP 注册
claude mcp remove sage

# 添加新 MCP
claude mcp add sage http://localhost:17800/mcp

# 查看状态
claude mcp list
```

预期结果：

```
1. sage  ✔ connected
```

---

## 📌 结论

Claude Code 的动态注册流程非常严格。确保实现以下内容才能成功注册：

- `.well-known` 配置全面
- `/mcp/token` 和 `/mcp/auth` 存在
- tools_endpoint 与实际路径一致

完成以上修复后，你的 Sage MCP 服务即可被 Claude Code 正确识别并自动连接。
