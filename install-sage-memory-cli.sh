#!/bin/bash
# 安装 sage-memory 命令行工具

set -e

echo "=== 安装 Sage Memory CLI ==="

# 获取当前目录
SAGE_PATH=$(cd "$(dirname "$0")" && pwd)

# 创建符号链接目录
mkdir -p "$HOME/.local/bin"

# 创建 sage-memory 命令
cat > "$HOME/.local/bin/sage-memory" << EOF
#!/bin/bash
# Sage Memory CLI 包装器
exec python3 "$SAGE_PATH/sage_memory_cli.py" "\$@"
EOF

# 设置执行权限
chmod +x "$HOME/.local/bin/sage-memory"

# 检查 PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo ""
    echo "⚠️  请将以下行添加到你的 shell 配置文件 (~/.bashrc 或 ~/.zshrc):"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "✅ sage-memory 命令已安装"
echo ""
echo "使用示例:"
echo "  sage-memory status     # 查看记忆系统状态"
echo "  sage-memory search xxx # 搜索记忆"
echo "  sage-memory --help     # 查看帮助"