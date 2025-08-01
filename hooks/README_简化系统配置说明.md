# Sage 简化系统配置说明

## 概述

根据您的需求，我们已经实现了一个"简单直接"的方案，在每次Hook中直接初始化SageCore。虽然有3-5秒延迟，但换来的是系统的简单性、可靠性和可维护性。

## 系统特点

- ✅ **无需daemon进程** - 系统更加简单稳定
- ✅ **完整数据捕获** - 包括所有工具调用和对话内容
- ✅ **统一数据模型** - 使用Turn模型表示完整对话轮次
- ✅ **自动数据聚合** - 自动整合pre/post工具调用数据
- ✅ **简单可靠** - 每次调用都是独立的，不依赖外部进程

## 配置步骤

### 1. 更新Claude Code的hooks配置

将以下内容复制到 `/Users/jet/.config/claude/hooks.json`:

```bash
cp /Users/jet/Sage/hooks/new_hooks.json /Users/jet/.config/claude/hooks.json
```

或手动编辑该文件，使用以下内容：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/jet/Sage/hooks/scripts/sage_pre_tool_capture.py",
            "timeout": 5000,
            "env": {
              "SAGE_HOOK_ENABLED": "true",
              "CLAUDE_CODE_HOOK_EVENT": "PreToolUse"
            }
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/jet/Sage/hooks/scripts/sage_post_tool_capture.py",
            "timeout": 5000,
            "env": {
              "SAGE_HOOK_ENABLED": "true",
              "CLAUDE_CODE_HOOK_EVENT": "PostToolUse"
            }
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/jet/Sage/hooks/scripts/sage_stop_hook_simple.py",
            "timeout": 10000,
            "env": {
              "SAGE_HOOK_ENABLED": "true",
              "CLAUDE_CODE_HOOK_EVENT": "Stop"
            }
          }
        ]
      }
    ]
  }
}
```

### 2. 重启Claude Code

配置更新后，需要重启Claude Code CLI以使配置生效。

### 3. 确保Sage MCP Server运行

确保Sage MCP Server正在运行：

```bash
cd /Users/jet/Sage
./start_sage_mcp.sh
```

## 工作流程

1. **PreToolUse Hook** - 在工具调用前捕获输入参数
2. **PostToolUse Hook** - 在工具调用后捕获结果
3. **Stop Hook (简化版)** - 在对话结束时：
   - 提取Human/Assistant对话
   - 聚合所有工具调用数据
   - 初始化SageCore（3-5秒）
   - 保存完整的Turn数据到数据库
   - 清理临时文件

## 测试

运行测试脚本验证系统：

```bash
python3 /Users/jet/Sage/scripts/test_simplified_system.py
```

## 注意事项

1. **初始化延迟** - 每次保存会有3-5秒的延迟，这是初始化数据库连接的时间
2. **临时文件** - 系统会在 `~/.sage_hooks_temp` 创建临时文件，会自动清理
3. **日志文件** - 日志保存在 `/Users/jet/Sage/hooks/logs/` 目录

## 与复杂系统的对比

| 特性 | 简化系统 | 原复杂系统 |
|------|---------|-----------|
| daemon进程 | ❌ 不需要 | ✅ 需要 |
| 初始化时间 | 3-5秒/次 | 首次3-5秒 |
| 系统复杂度 | 低 | 高 |
| 维护难度 | 简单 | 复杂 |
| 稳定性 | 高 | 依赖daemon |
| 适用场景 | 个人使用 | 企业/高并发 |

## 结论

这个简化系统完全满足个人使用需求，虽然每次有几秒延迟，但换来的是：
- 系统的简单性
- 更高的可靠性
- 更容易的维护
- 不需要管理额外的进程

对于个人使用场景，这是最佳选择。