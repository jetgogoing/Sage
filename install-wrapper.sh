#!/bin/bash
# Sage MCP 智能包装器安装脚本

set -e  # 遇到错误立即退出

echo "=== Sage MCP Claude 包装器安装程序 ==="
echo

# 1. 检测原始 claude 路径
echo "1. 检测 Claude CLI 路径..."
ORIGINAL_CLAUDE=$(which claude 2>/dev/null || echo "")

if [ -z "$ORIGINAL_CLAUDE" ]; then
    echo "错误：未找到 claude 命令。请先安装 Claude CLI。"
    exit 1
fi

# 解析真实路径（处理别名和符号链接）
if alias claude &>/dev/null; then
    # 如果是别名，提取实际路径
    ALIAS_DEF=$(alias claude | sed "s/alias claude=//g" | tr -d "'\"")
    if [[ "$ALIAS_DEF" == /* ]]; then
        ORIGINAL_CLAUDE="$ALIAS_DEF"
    fi
fi

# 跟随符号链接找到真实路径
ORIGINAL_CLAUDE=$(python3 -c "import os; print(os.path.realpath('$ORIGINAL_CLAUDE'))")

echo "   找到 Claude: $ORIGINAL_CLAUDE"

# 2. 确定 Sage 项目路径
SAGE_PATH=$(cd "$(dirname "$0")" && pwd)
echo "2. Sage 项目路径: $SAGE_PATH"

# 3. 生成包装器脚本
WRAPPER_PATH="$HOME/.local/bin/claude"
mkdir -p "$HOME/.local/bin"

echo "3. 生成包装器脚本..."
cat > "$WRAPPER_PATH" << EOF
#!/bin/bash
# Sage MCP Claude 智能包装器 (自动生成)
# 生成时间: $(date)

# 原始 Claude 路径
ORIGINAL_CLAUDE_PATH="$ORIGINAL_CLAUDE"

# 记忆脚本路径
MEMORY_SCRIPT_PATH="\${SAGE_MEMORY_PATH:-$SAGE_PATH/claude_mem.py}"

# Python 解释器
PYTHON_PATH="\${SAGE_PYTHON_PATH:-python3}"

# 静默模式
SILENT_MODE="\${SAGE_SILENT_MODE:-0}"

log_info() {
    if [ "\$SILENT_MODE" != "1" ]; then
        echo "[Sage] \$1" >&2
    fi
}

# 检查记忆系统
if [ -f "\$MEMORY_SCRIPT_PATH" ] && command -v "\$PYTHON_PATH" &> /dev/null; then
    "\$PYTHON_PATH" "\$MEMORY_SCRIPT_PATH" "\$@"
    exit_code=\$?
    if [ \$exit_code -ne 0 ]; then
        log_info "记忆系统异常，降级到标准模式"
        exec "\$ORIGINAL_CLAUDE_PATH" "\$@"
    fi
    exit \$exit_code
else
    [ "\$SILENT_MODE" != "1" ] && log_info "记忆系统不可用，使用标准模式"
    exec "\$ORIGINAL_CLAUDE_PATH" "\$@"
fi
EOF

chmod +x "$WRAPPER_PATH"
echo "   包装器已创建: $WRAPPER_PATH"

# 4. 配置 PATH
echo "4. 配置环境..."

# 检测 shell 类型
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

# 检查 PATH 配置
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo "" >> "$SHELL_RC"
    echo "# Sage MCP Claude 包装器路径" >> "$SHELL_RC"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
    echo "   已添加 PATH 配置到 $SHELL_RC"
else
    echo "   PATH 已包含 ~/.local/bin"
fi

# 5. 创建控制脚本
echo "5. 创建控制命令..."

# sage-mode 命令：切换记忆模式
cat > "$HOME/.local/bin/sage-mode" << 'EOF'
#!/bin/bash
case "$1" in
    on)
        export SAGE_SILENT_MODE=0
        echo "Sage 记忆模式：已启用（带提示）"
        ;;
    silent)
        export SAGE_SILENT_MODE=1
        echo "Sage 记忆模式：已启用（静默）"
        ;;
    off)
        export SAGE_MEMORY_PATH="/dev/null"
        echo "Sage 记忆模式：已禁用"
        ;;
    status)
        if [ -z "$SAGE_MEMORY_PATH" ] || [ "$SAGE_MEMORY_PATH" = "/dev/null" ]; then
            echo "Sage 记忆模式：禁用"
        elif [ "$SAGE_SILENT_MODE" = "1" ]; then
            echo "Sage 记忆模式：启用（静默）"
        else
            echo "Sage 记忆模式：启用（带提示）"
        fi
        ;;
    *)
        echo "用法: sage-mode [on|silent|off|status]"
        echo "  on     - 启用记忆模式（带提示）"
        echo "  silent - 启用记忆模式（静默）"
        echo "  off    - 禁用记忆模式"
        echo "  status - 查看当前状态"
        ;;
esac
EOF

chmod +x "$HOME/.local/bin/sage-mode"

echo
echo "=== 安装完成 ==="
echo
echo "使用说明："
echo "1. 重启终端或执行: source $SHELL_RC"
echo "2. 正常使用: claude \"你的问题\""
echo "3. 控制记忆模式:"
echo "   - sage-mode on     # 启用（默认）"
echo "   - sage-mode silent # 静默模式"
echo "   - sage-mode off    # 临时禁用"
echo "   - sage-mode status # 查看状态"
echo
echo "4. 直接使用原始 Claude:"
echo "   - $ORIGINAL_CLAUDE \"你的问题\""
echo
echo "提示：包装器会自动检测记忆系统可用性并优雅降级"