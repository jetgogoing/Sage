#!/bin/bash
# Sage MCP Claude 智能包装器
# 提供记忆功能的同时确保系统稳定性

# === 配置部分 ===
# 原始 Claude 路径（安装时自动检测）
ORIGINAL_CLAUDE_PATH="/Users/jet/.claude/local/claude"

# 记忆脚本路径 - 更新为 sage_minimal.py
MEMORY_SCRIPT_PATH="${SAGE_MEMORY_PATH:-/Volumes/1T HDD/Sage/claude_mem_v3.py}"

# Python 解释器路径 - 使用虚拟环境
PYTHON_PATH="${SAGE_PYTHON_PATH:-/Volumes/1T HDD/Sage/.venv/bin/python}"

# 静默模式（设置为 1 禁用提示信息）
SILENT_MODE="${SAGE_SILENT_MODE:-0}"

# === 功能函数 ===
log_info() {
    if [ "$SILENT_MODE" != "1" ]; then
        echo "[Sage MCP] $1" >&2
    fi
}

# === 主逻辑 ===
# 清理可能存在的递归保护环境变量
unset SAGE_RECURSION_GUARD


# 导出环境变量
export ORIGINAL_CLAUDE_PATH="$ORIGINAL_CLAUDE_PATH"

# 1. 检查记忆系统是否可用
if [ -f "$MEMORY_SCRIPT_PATH" ]; then
    # 2. 验证 Python 环境
    if [ -f "$PYTHON_PATH" ]; then
        # 3. 尝试执行记忆增强版本
        log_info "使用记忆增强模式"
        cd "/Volumes/1T HDD/Sage"
        "$PYTHON_PATH" "$MEMORY_SCRIPT_PATH" "$@"
        exit_code=$?
        
        # 4. 如果记忆系统执行失败，降级到原始命令
        if [ $exit_code -ne 0 ]; then
            log_info "记忆系统异常（错误码: $exit_code），切换到标准模式"
            exec "$ORIGINAL_CLAUDE_PATH" "$@"
        fi
        exit $exit_code
    else
        log_info "Python 环境未就绪，使用标准模式"
    fi
else
    log_info "记忆脚本未找到（$MEMORY_SCRIPT_PATH），使用标准模式"
fi

# 5. 降级执行原始 Claude
exec "$ORIGINAL_CLAUDE_PATH" "$@"