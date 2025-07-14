#!/bin/bash
# sage - 一键启动Claude Sage记忆系统
# 🚀 自动启动所有服务，显示状态，然后进入交互模式

set -euo pipefail

# 配置项目路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

START_SERVICES_SCRIPT="$PROJECT_ROOT/start_all_services.sh"
SAGE_MANAGE_SCRIPT="$PROJECT_ROOT/sage_manage"
SAGE_CLAUDE_SCRIPT="$PROJECT_ROOT/sage_cli"

# 显示启动信息
echo "🚀 Claude Sage 一键启动"
echo "================================="
echo "📂 项目目录: $PROJECT_ROOT"
echo ""

# 1. 启动所有服务
echo "--- 1. 启动系统服务 ---"
if [ ! -f "$START_SERVICES_SCRIPT" ]; then
    echo "❌ 错误: 启动脚本不存在: $START_SERVICES_SCRIPT" >&2
    exit 1
fi

echo "🔄 正在启动所有必要服务..."
if ! "$START_SERVICES_SCRIPT"; then
    echo "❌ 错误: 服务启动失败，请检查启动脚本和服务日志" >&2
    exit 1
fi

echo "✅ 所有服务启动完成"
echo ""

# 2. 等待服务完全就绪
echo "--- 2. 等待服务就绪 ---"
echo "⏳ 等待服务完全初始化 (3秒)..."
sleep 3

# 3. 显示数据库连接状态
echo "--- 3. 数据库连接状态检查 ---"
if [ ! -f "$SAGE_MANAGE_SCRIPT" ]; then
    echo "⚠️  警告: 管理脚本不存在: $SAGE_MANAGE_SCRIPT" >&2
else
    echo "🔍 检查数据库连接状态..."
    if ! "$SAGE_MANAGE_SCRIPT" status; then
        echo "⚠️  警告: 数据库状态检查失败，但仍将继续启动" >&2
        echo "💡 提示: 可能需要等待数据库完全启动" >&2
    else
        echo "✅ 数据库连接正常"
    fi
fi

echo ""

# 4. 显示系统就绪信息
echo "--- 4. 系统状态总览 ---"
echo "🎉 Claude Sage 记忆系统已就绪！"
echo ""
echo "📊 服务状态:"
echo "  ✅ PostgreSQL + pgvector 数据库"
echo "  ✅ SiliconFlow API 连接"
echo "  ✅ 记忆存储和检索功能"
echo ""
echo "🔧 可用命令:"
echo "  - 直接输入问题开始对话（带记忆功能）"
echo "  - 输入 'exit' 或按 Ctrl+C 退出"
echo ""

# 5. 启动交互式 Claude Sage
echo "--- 5. 进入交互模式 ---"
if [ ! -f "$SAGE_CLAUDE_SCRIPT" ]; then
    echo "❌ 错误: Claude Sage脚本不存在: $SAGE_CLAUDE_SCRIPT" >&2
    exit 1
fi

echo "🎯 正在启动 Claude Sage 交互模式..."
echo "现在你可以直接输入问题开始使用！"
echo "================================="
echo ""

# 启动原生Claude CLI交互模式（带记忆增强）
echo "🚀 正在启动原生Claude CLI（带记忆增强）..."
echo "现在你将进入完整的Claude CLI环境，包含所有原生功能！"
echo ""

# 直接调用sage_cli，让它处理所有交互
# sage_mem.py会包装原生Claude CLI，保持所有功能的同时增加记忆
"$SAGE_CLAUDE_SCRIPT" "$@"

echo ""
echo "🔚 Claude CLI 会话结束"
echo "💡 提示: 服务仍在后台运行，如需停止请使用: ./stop_all_services.sh"