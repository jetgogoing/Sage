#!/bin/bash
# Sage MCP 跨平台版本安装脚本 (Unix/Linux/macOS)
# 使用新的跨平台 Python 实现

set -e  # 遇到错误立即退出

# ANSI 颜色代码
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
RESET='\033[0m'

# 打印彩色输出
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${RESET}"
}

print_header() {
    echo
    print_color "$MAGENTA" "╔══════════════════════════════════════════════════╗"
    print_color "$MAGENTA" "║     Sage MCP Claude 记忆系统安装程序 (v2.0)      ║"
    print_color "$MAGENTA" "╚══════════════════════════════════════════════════╝"
    echo
    print_color "$CYAN" "平台: $(uname -s) | 架构: $(uname -m) | 跨平台版本"
    echo
}

print_step() {
    local step=$1
    local total=$2
    local message=$3
    echo
    print_color "$BLUE" "[$step/$total] $message"
}

print_success() {
    print_color "$GREEN" "[✓] $1"
}

print_error() {
    print_color "$RED" "[✗] $1"
}

print_warning() {
    print_color "$YELLOW" "[!] $1"
}

print_info() {
    print_color "$CYAN" "[i] $1"
}

# 主安装流程
print_header

# 1. 检查 Python 环境
print_step 1 8 "检查 Python 环境..."

if ! command -v python3 &> /dev/null; then
    print_error "未找到 Python 3，请先安装 Python 3.7+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    print_error "Python 版本过低 ($PYTHON_VERSION)，需要 3.7+"
    exit 1
fi

print_success "Python 版本: $PYTHON_VERSION"

# 2. 检测原始 Claude 路径
print_step 2 8 "检测 Claude CLI..."

# 查找原始 Claude
ORIGINAL_CLAUDE=""

# 检查当前的 claude 命令
if command -v claude &>/dev/null; then
    CLAUDE_PATH=$(which claude)
    
    # 检查是否是别名
    if alias claude &>/dev/null 2>&1; then
        print_info "检测到 claude 别名"
        # 尝试从别名中提取路径
        ALIAS_DEF=$(alias claude 2>/dev/null | sed "s/alias claude=//" | tr -d "'\"")
        if [[ "$ALIAS_DEF" == /* ]]; then
            if [ -f "$ALIAS_DEF" ]; then
                ORIGINAL_CLAUDE="$ALIAS_DEF"
            fi
        fi
    fi
    
    # 如果不是别名或别名解析失败，使用 which 的结果
    if [ -z "$ORIGINAL_CLAUDE" ]; then
        # 解析符号链接
        ORIGINAL_CLAUDE=$(python3 -c "import os; print(os.path.realpath('$CLAUDE_PATH'))")
    fi
fi

# 如果还是没找到，检查常见位置
if [ -z "$ORIGINAL_CLAUDE" ]; then
    COMMON_PATHS=(
        "/usr/local/bin/claude"
        "/usr/bin/claude"
        "$HOME/.local/bin/claude"
        "$HOME/.claude/local/claude"
        "/opt/claude/bin/claude"
    )
    
    for path in "${COMMON_PATHS[@]}"; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            ORIGINAL_CLAUDE="$path"
            break
        fi
    done
fi

if [ -z "$ORIGINAL_CLAUDE" ]; then
    print_error "未找到 Claude CLI"
    print_info "请先安装 Claude CLI: https://claude.ai"
    exit 1
fi

print_success "找到 Claude: $ORIGINAL_CLAUDE"

# 3. 确定项目路径
print_step 3 8 "配置项目路径..."

SAGE_PATH=$(cd "$(dirname "$0")" && pwd)
print_success "Sage 项目路径: $SAGE_PATH"

# 4. 创建配置目录
print_step 4 8 "创建配置目录..."

CONFIG_DIR="$HOME/.sage-mcp"
mkdir -p "$CONFIG_DIR"/{logs,bin,backups}
print_success "配置目录: $CONFIG_DIR"

# 5. 生成配置文件
print_step 5 8 "生成配置文件..."

CONFIG_FILE="$CONFIG_DIR/config.json"

# 检测平台
PLATFORM="unknown"
case "$(uname -s)" in
    Darwin*) PLATFORM="macos" ;;
    Linux*)  PLATFORM="linux" ;;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows" ;;
esac

cat > "$CONFIG_FILE" << EOF
{
    "claude_paths": ["$ORIGINAL_CLAUDE"],
    "memory_enabled": true,
    "debug_mode": false,
    "platform": "$PLATFORM",
    "sage_home": "$SAGE_PATH",
    "install_date": "$(date '+%Y-%m-%d %H:%M:%S')",
    "version": "2.0"
}
EOF

print_success "配置文件: $CONFIG_FILE"

# 6. 创建包装脚本
print_step 6 8 "创建包装脚本..."

WRAPPER_PATH="$CONFIG_DIR/bin/claude"

cat > "$WRAPPER_PATH" << EOF
#!/bin/bash
# Sage MCP Claude 跨平台包装器
# 生成时间: $(date)
# 版本: 2.0

# 配置
PYTHON_PATH="\${SAGE_PYTHON_PATH:-python3}"
MEMORY_SCRIPT="\${SAGE_MEMORY_SCRIPT:-$SAGE_PATH/sage_crossplatform.py}"
CONFIG_DIR="\${SAGE_CONFIG_DIR:-$CONFIG_DIR}"

# 导出配置目录供 Python 脚本使用
export SAGE_CONFIG_DIR="\$CONFIG_DIR"

# 检查 Python 脚本是否存在
if [ -f "\$MEMORY_SCRIPT" ]; then
    # 执行跨平台记忆脚本
    exec "\$PYTHON_PATH" "\$MEMORY_SCRIPT" "\$@"
else
    echo "[Sage MCP] 错误：记忆脚本未找到" >&2
    echo "预期路径: \$MEMORY_SCRIPT" >&2
    
    # 降级到原始 Claude
    if [ -f "$ORIGINAL_CLAUDE" ]; then
        echo "[Sage MCP] 降级到原始 Claude" >&2
        exec "$ORIGINAL_CLAUDE" "\$@"
    else
        echo "[Sage MCP] 原始 Claude 也未找到" >&2
        exit 1
    fi
fi
EOF

chmod +x "$WRAPPER_PATH"
print_success "包装器脚本: $WRAPPER_PATH"

# 7. 配置 PATH 和环境
print_step 7 8 "配置环境变量..."

# 检测 shell 类型
SHELL_RC=""
CURRENT_SHELL=$(basename "$SHELL")

case "$CURRENT_SHELL" in
    zsh)  SHELL_RC="$HOME/.zshrc" ;;
    bash) SHELL_RC="$HOME/.bashrc" ;;
    fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
    *)    SHELL_RC="$HOME/.profile" ;;
esac

# 备份配置文件
if [ -f "$SHELL_RC" ]; then
    cp "$SHELL_RC" "$CONFIG_DIR/backups/.$(basename $SHELL_RC).backup.$(date +%Y%m%d%H%M%S)"
    print_info "已备份配置文件"
fi

# 移除旧的 claude 别名（如果存在）
if [ -f "$SHELL_RC" ]; then
    # 创建临时文件
    TEMP_RC=$(mktemp)
    grep -v "alias claude=" "$SHELL_RC" > "$TEMP_RC" || true
    mv "$TEMP_RC" "$SHELL_RC"
fi

# 添加新的 PATH 配置
PATH_EXPORT="export PATH=\"$CONFIG_DIR/bin:\$PATH\""
if ! grep -q "$CONFIG_DIR/bin" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Sage MCP Claude 记忆系统 (v2.0)" >> "$SHELL_RC"
    echo "$PATH_EXPORT" >> "$SHELL_RC"
    echo "export SAGE_MCP_HOME=\"$SAGE_PATH\"" >> "$SHELL_RC"
    echo "export SAGE_CONFIG_DIR=\"$CONFIG_DIR\"" >> "$SHELL_RC"
    print_success "已更新 $SHELL_RC"
else
    print_info "PATH 已配置"
fi

# 8. 创建控制命令
print_step 8 8 "创建控制命令..."

# sage-mode 命令
SAGE_MODE_PATH="$CONFIG_DIR/bin/sage-mode"
cat > "$SAGE_MODE_PATH" << 'EOF'
#!/bin/bash
# Sage 模式控制命令

case "$1" in
    on)
        export SAGE_MEMORY_ENABLED=1
        export SAGE_SILENT_MODE=0
        echo -e "\033[32m[✓] Sage 记忆模式：已启用\033[0m"
        ;;
    off)
        export SAGE_MEMORY_ENABLED=0
        echo -e "\033[33m[!] Sage 记忆模式：已禁用\033[0m"
        ;;
    silent)
        export SAGE_MEMORY_ENABLED=1
        export SAGE_SILENT_MODE=1
        echo -e "\033[36m[i] Sage 记忆模式：静默模式\033[0m"
        ;;
    status)
        if [ "$SAGE_MEMORY_ENABLED" = "0" ]; then
            echo -e "\033[31m[×] Sage 记忆模式：禁用\033[0m"
        elif [ "$SAGE_SILENT_MODE" = "1" ]; then
            echo -e "\033[36m[i] Sage 记忆模式：启用（静默）\033[0m"
        else
            echo -e "\033[32m[✓] Sage 记忆模式：启用\033[0m"
        fi
        ;;
    *)
        echo "用法: sage-mode [on|off|silent|status]"
        echo "  on     - 启用记忆模式"
        echo "  off    - 禁用记忆模式"
        echo "  silent - 静默模式"
        echo "  status - 查看当前状态"
        ;;
esac
EOF

chmod +x "$SAGE_MODE_PATH"

# sage-doctor 诊断命令
SAGE_DOCTOR_PATH="$CONFIG_DIR/bin/sage-doctor"
cat > "$SAGE_DOCTOR_PATH" << EOF
#!/bin/bash
# Sage 诊断工具

echo -e "\033[36m=== Sage MCP 系统诊断 ===\033[0m"
echo

# 检查 Python
echo -n "Python: "
if command -v python3 &>/dev/null; then
    python3 --version
else
    echo -e "\033[31m未找到\033[0m"
fi

# 检查配置
echo -n "配置文件: "
if [ -f "$CONFIG_FILE" ]; then
    echo -e "\033[32m存在\033[0m"
else
    echo -e "\033[31m缺失\033[0m"
fi

# 检查记忆脚本
echo -n "记忆脚本: "
if [ -f "$SAGE_PATH/sage_crossplatform.py" ]; then
    echo -e "\033[32m存在\033[0m"
else
    echo -e "\033[31m缺失\033[0m"
fi

# 检查原始 Claude
echo -n "原始 Claude: "
if [ -f "$ORIGINAL_CLAUDE" ]; then
    echo -e "\033[32m$ORIGINAL_CLAUDE\033[0m"
else
    echo -e "\033[31m未找到\033[0m"
fi

# 检查数据库
echo -n "PostgreSQL: "
if docker ps 2>/dev/null | grep -q sage-pg; then
    echo -e "\033[32m运行中\033[0m"
else
    echo -e "\033[33m未运行或未安装 Docker\033[0m"
fi

echo
echo "环境变量:"
echo "  SAGE_MCP_HOME=$SAGE_MCP_HOME"
echo "  SAGE_CONFIG_DIR=$SAGE_CONFIG_DIR"
echo "  PATH 包含 $CONFIG_DIR/bin: $(echo \$PATH | grep -q "$CONFIG_DIR/bin" && echo "是" || echo "否")"
EOF

chmod +x "$SAGE_DOCTOR_PATH"

print_success "控制命令已创建"

# 9. 安装 Python 依赖
echo
print_color "$BLUE" "安装 Python 依赖..."

cd "$SAGE_PATH"
if python3 -m pip install -r requirements.txt; then
    print_success "依赖安装成功"
else
    print_warning "依赖安装失败，请手动运行: pip install -r requirements.txt"
fi

# 10. 完成安装
echo
print_color "$GREEN" "════════════════════════════════════════"
print_color "$GREEN" "        安装成功完成！"
print_color "$GREEN" "════════════════════════════════════════"
echo

print_color "$CYAN" "使用说明："
echo "1. 重启终端或执行: source $SHELL_RC"
echo "2. 使用命令: claude \"你的问题\""
echo "3. 控制命令:"
echo "   - sage-mode on     # 启用记忆"
echo "   - sage-mode off    # 禁用记忆"
echo "   - sage-mode silent # 静默模式"
echo "   - sage-mode status # 查看状态"
echo "   - sage-doctor      # 系统诊断"
echo
print_color "$CYAN" "配置信息："
echo "- 配置目录: $CONFIG_DIR"
echo "- 项目目录: $SAGE_PATH"
echo "- 原始 Claude: $ORIGINAL_CLAUDE"
echo
print_color "$YELLOW" "提示：新的跨平台版本支持 Windows/macOS/Linux"