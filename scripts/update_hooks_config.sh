#!/bin/bash

# 更新Claude Code hooks配置为简化版本

echo "=== 更新Claude Code Hooks配置 ==="
echo "将使用简化的Sage系统配置"

# 配置文件路径
HOOKS_CONFIG="/Users/jet/.config/claude/hooks.json"
NEW_CONFIG="/Users/jet/Sage/hooks/new_hooks.json"

# 检查新配置文件是否存在
if [ ! -f "$NEW_CONFIG" ]; then
    echo "❌ 错误: 找不到新配置文件 $NEW_CONFIG"
    exit 1
fi

# 备份当前配置
if [ -f "$HOOKS_CONFIG" ]; then
    BACKUP_FILE="${HOOKS_CONFIG}.backup_$(date +%Y%m%d_%H%M%S)"
    cp "$HOOKS_CONFIG" "$BACKUP_FILE"
    echo "✅ 已备份当前配置到: $BACKUP_FILE"
fi

# 复制新配置
cp "$NEW_CONFIG" "$HOOKS_CONFIG"
if [ $? -eq 0 ]; then
    echo "✅ 配置更新成功!"
    echo ""
    echo "新配置包含:"
    echo "- PreToolUse Hook: 捕获工具调用输入"
    echo "- PostToolUse Hook: 捕获工具调用输出"
    echo "- Stop Hook (简化版): 保存完整对话和工具调用"
    echo ""
    echo "特点:"
    echo "- 无需daemon进程"
    echo "- 每次保存有3-5秒延迟（数据库初始化）"
    echo "- 系统更加简单可靠"
    echo ""
    echo "请重启Claude Code CLI以使配置生效。"
else
    echo "❌ 配置更新失败"
    exit 1
fi