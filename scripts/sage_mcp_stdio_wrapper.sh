#!/usr/bin/env bash
# Sage MCP STDIO Wrapper - 为 Claude Code CLI 提供智能启动
# 此脚本检查环境并直接运行 MCP STDIO 服务

set -e

# 配置
IMAGE_NAME="sage-mcp-single:minimal"
DOCKERFILE="docker/single/Dockerfile.single.minimal"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 彩色输出（仅输出到 stderr，保持 stdout 干净）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数（全部输出到 stderr）
log_info() {
    echo -e "${GREEN}[Sage MCP]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[Sage MCP]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[Sage MCP]${NC} $1" >&2
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon 未运行"
        exit 1
    fi
}

# 构建镜像（如果需要）
build_image_if_needed() {
    if ! docker images | grep -q "$IMAGE_NAME"; then
        log_info "首次运行，构建 Docker 镜像..."
        log_info "这可能需要几分钟，请耐心等待..."
        cd "$PROJECT_ROOT"
        if docker build -t "$IMAGE_NAME" -f "$DOCKERFILE" . >&2; then
            log_info "✅ 镜像构建成功"
        else
            log_error "镜像构建失败"
            exit 1
        fi
    fi
}

# 主函数
main() {
    # 仅在第一次或需要调试时显示启动信息
    if [ "$SAGE_MCP_DEBUG" = "1" ] || [ ! -f "$HOME/.sage-mcp-initialized" ]; then
        log_info "正在初始化 Sage MCP 服务..."
        touch "$HOME/.sage-mcp-initialized"
    fi
    
    # 检查 Docker
    check_docker
    
    # 构建镜像（如果需要）
    build_image_if_needed
    
    # 直接运行 MCP STDIO 服务
    # 注意：不使用 -d，这样容器生命周期与 stdio 会话绑定
    # 传递必要的环境变量
    # 挂载主机时区文件（如果存在）
    TIMEZONE_MOUNT=""
    if [ -f /etc/localtime ]; then
        TIMEZONE_MOUNT="-v /etc/localtime:/etc/localtime:ro"
    fi
    
    exec docker run --rm -i \
        -v sage-mcp-data:/var/lib/postgresql/data \
        -v sage-mcp-logs:/var/log/sage \
        $TIMEZONE_MOUNT \
        -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY:-}" \
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
        -e TZ="Asia/Shanghai" \
        "$IMAGE_NAME"
}

# 执行主流程
main "$@"