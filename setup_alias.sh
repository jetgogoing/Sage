#!/bin/bash
# Sage 记忆系统别名设置脚本

echo "🎯 Sage 记忆系统别名设置"
echo ""

# 检测shell类型
if [[ $SHELL == *"zsh"* ]]; then
    SHELL_CONFIG="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [[ $SHELL == *"bash"* ]]; then
    SHELL_CONFIG="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    echo "❌ 不支持的shell类型: $SHELL"
    exit 1
fi

echo "📝 检测到shell: $SHELL_NAME"
echo "📁 配置文件: $SHELL_CONFIG"
echo ""

# 检查是否已存在别名
if grep -q "sage_manage" "$SHELL_CONFIG" 2>/dev/null; then
    echo "⚠️  别名已存在，跳过设置"
else
    echo "✅ 添加Sage别名到 $SHELL_CONFIG"
    echo "" >> "$SHELL_CONFIG"
    echo "# Sage 记忆系统别名" >> "$SHELL_CONFIG"
    echo 'alias sage="/Users/jet/sage/sage_manage"' >> "$SHELL_CONFIG"
    echo 'export PATH="/Users/jet/sage:$PATH"' >> "$SHELL_CONFIG"
fi

echo ""
echo "🎉 设置完成！"
echo ""
echo "执行以下命令生效："
echo "source $SHELL_CONFIG"
echo ""
echo "然后就可以直接使用："
echo "  sage status                    # 查看记忆系统状态"
echo "  sage search \"关键词\"           # 搜索记忆"
echo ""