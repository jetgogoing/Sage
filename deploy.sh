#!/bin/bash
# deploy.sh - Sage Docker一键部署脚本
# 版本: v1.0
# 作者: Sage Team

set -euo pipefail

# 配置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
CONTAINER_NAME="sage-mcp"
LOG_FILE="$PROJECT_ROOT/deploy.log"

# 错误处理函数
error_exit() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    echo "[ERROR] $1" >> "$LOG_FILE"
    exit 1
}

# 成功信息
success_msg() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
    echo "[SUCCESS] $1" >> "$LOG_FILE"
}

# 警告信息
warning_msg() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
    echo "[WARNING] $1" >> "$LOG_FILE"
}

# 信息输出
info_msg() {
    echo -e "${BLUE}[INFO] $1${NC}"
    echo "[INFO] $1" >> "$LOG_FILE"
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

Sage MCP Docker一键部署脚本

选项:
  -h, --help              显示此帮助信息
  --skip-build            跳过Docker镜像构建，直接启动
  --force-rebuild         强制重新构建Docker镜像
  --cleanup               部署前清理现有容器和数据
  --quick                 快速部署（跳过某些检查）
  --backup                部署前自动备份现有数据
  --no-health-check       跳过健康检查步骤

部署流程:
  1. 环境检查 (Docker、配置文件、端口等)
  2. 数据备份 (可选)
  3. Docker镜像构建
  4. 容器启动
  5. 健康检查
  6. 功能验证

示例:
  ./deploy.sh                     # 标准部署
  ./deploy.sh --backup            # 带备份的部署
  ./deploy.sh --force-rebuild     # 强制重新构建并部署
  ./deploy.sh --cleanup           # 清理并重新部署

EOF
}

# 解析命令行参数
parse_arguments() {
    SKIP_BUILD=false
    FORCE_REBUILD=false
    CLEANUP_BEFORE=false
    QUICK_MODE=false
    BACKUP_DATA=false
    SKIP_HEALTH_CHECK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --force-rebuild)
                FORCE_REBUILD=true
                shift
                ;;
            --cleanup)
                CLEANUP_BEFORE=true
                shift
                ;;
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --backup)
                BACKUP_DATA=true
                shift
                ;;
            --no-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            *)
                error_exit "未知参数: $1"
                ;;
        esac
    done
}

# 初始化部署环境
initialize_deployment() {
    info_msg "初始化Sage MCP Docker部署环境..."
    
    cd "$PROJECT_ROOT"
    
    # 创建部署日志
    echo "=== Sage MCP Docker部署日志 - $(date) ===" > "$LOG_FILE"
    
    # 检查必要文件
    local required_files=(
        "docker-compose.yml"
        "Dockerfile"
        "sage_mcp_stdio_single.py"
        ".env.example"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error_exit "缺少必要文件: $file"
        fi
    done
    
    # 检查目录结构
    local required_dirs=(
        "sage_core"
        "docker"
        "scripts"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            error_exit "缺少必要目录: $dir"
        fi
    done
    
    success_msg "部署环境初始化完成"
}

# 环境检查
check_environment() {
    info_msg "检查部署环境..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        error_exit "Docker未安装，请先安装Docker"
    fi
    
    local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    info_msg "Docker版本: $docker_version"
    
    # 检查docker-compose
    if ! command -v docker-compose &> /dev/null; then
        error_exit "docker-compose未安装，请先安装docker-compose"
    fi
    
    local compose_version=$(docker-compose --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    info_msg "docker-compose版本: $compose_version"
    
    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        error_exit "Docker服务未运行，请启动Docker服务"
    fi
    
    # 检查系统资源
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_memory" -lt 1024 ]; then
        warning_msg "可用内存较低: ${available_memory}MB (建议: >= 1GB)"
    else
        info_msg "可用内存: ${available_memory}MB"
    fi
    
    # 检查磁盘空间
    local available_disk=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$available_disk" -lt 5 ]; then
        warning_msg "可用磁盘空间较低: ${available_disk}GB (建议: >= 5GB)"
    else
        info_msg "可用磁盘空间: ${available_disk}GB"
    fi
    
    # 检查环境变量配置
    if [ ! -f ".env" ]; then
        if [ "$QUICK_MODE" = false ]; then
            warning_msg ".env文件不存在，将使用.env.example创建"
            cp .env.example .env
            warning_msg "请检查并修改.env文件中的配置后重新运行部署"
            exit 1
        else
            info_msg "快速模式：复制.env.example为.env"
            cp .env.example .env
        fi
    fi
    
    success_msg "环境检查完成"
}

# 数据备份
backup_existing_data() {
    if [ "$BACKUP_DATA" = false ]; then
        return 0
    fi
    
    info_msg "备份现有数据..."
    
    local backup_dir="$PROJECT_ROOT/backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$backup_dir/sage_backup_${timestamp}.sql"
    
    mkdir -p "$backup_dir"
    
    # 检查现有容器是否运行
    if docker ps -f name="$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
        info_msg "备份现有数据库数据..."
        
        if docker exec "$CONTAINER_NAME" pg_dump -U sage -d sage_memory > "$backup_file" 2>/dev/null; then
            success_msg "数据备份完成: $backup_file"
        else
            warning_msg "数据备份失败，可能是因为容器未运行或数据库不可访问"
        fi
    else
        info_msg "未发现运行中的容器，跳过数据备份"
    fi
}

# 清理现有环境
cleanup_existing_environment() {
    if [ "$CLEANUP_BEFORE" = false ]; then
        return 0
    fi
    
    info_msg "清理现有Docker环境..."
    
    # 停止并删除现有容器
    if docker-compose ps | grep -q "$CONTAINER_NAME"; then
        info_msg "停止现有容器..."
        docker-compose down -v --remove-orphans 2>/dev/null || true
    fi
    
    # 删除相关镜像（如果强制重建）
    if [ "$FORCE_REBUILD" = true ]; then
        local image_name=$(grep 'image:' docker-compose.yml | awk '{print $2}' | head -1 || echo "sage-mcp:latest")
        if docker images | grep -q "$image_name"; then
            info_msg "删除现有镜像: $image_name"
            docker rmi "$image_name" 2>/dev/null || true
        fi
    fi
    
    success_msg "环境清理完成"
}

# 构建Docker镜像
build_docker_images() {
    if [ "$SKIP_BUILD" = true ]; then
        info_msg "跳过Docker镜像构建"
        return 0
    fi
    
    info_msg "构建Docker镜像..."
    
    local build_args=""
    if [ "$FORCE_REBUILD" = true ]; then
        build_args="--no-cache"
        info_msg "强制重新构建镜像（不使用缓存）"
    fi
    
    # 构建镜像
    if docker-compose build $build_args 2>&1 | tee -a "$LOG_FILE"; then
        success_msg "Docker镜像构建完成"
    else
        error_exit "Docker镜像构建失败"
    fi
}

# 启动Docker容器
start_docker_containers() {
    info_msg "启动Docker容器..."
    
    # 启动容器
    if docker-compose up -d 2>&1 | tee -a "$LOG_FILE"; then
        success_msg "Docker容器启动完成"
    else
        error_exit "Docker容器启动失败"
    fi
    
    # 等待容器启动
    info_msg "等待容器初始化..."
    sleep 10
    
    # 检查容器状态
    if docker ps -f name="$CONTAINER_NAME" --format "{{.Status}}" | grep -q "Up"; then
        success_msg "容器运行状态正常"
    else
        error_exit "容器启动后状态异常"
    fi
}

# 健康检查
perform_health_check() {
    if [ "$SKIP_HEALTH_CHECK" = true ]; then
        info_msg "跳过健康检查"
        return 0
    fi
    
    info_msg "执行系统健康检查..."
    
    # 检查健康检查脚本是否存在
    if [ -f "$PROJECT_ROOT/scripts/health_check.sh" ]; then
        info_msg "运行健康检查脚本..."
        if bash "$PROJECT_ROOT/scripts/health_check.sh" -c "$CONTAINER_NAME" 2>&1 | tee -a "$LOG_FILE"; then
            success_msg "健康检查通过"
        else
            warning_msg "健康检查发现问题，请查看详细日志"
        fi
    else
        # 简单健康检查
        info_msg "执行基础健康检查..."
        
        # 检查PostgreSQL
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if docker exec "$CONTAINER_NAME" pg_isready -U sage -d sage_memory >/dev/null 2>&1; then
                success_msg "PostgreSQL数据库连接正常"
                break
            fi
            info_msg "等待数据库启动... (尝试 $attempt/$max_attempts)"
            sleep 2
            ((attempt++))
        done
        
        if [ $attempt -gt $max_attempts ]; then
            error_exit "数据库启动检查超时"
        fi
        
        # 检查MCP服务
        if docker exec "$CONTAINER_NAME" pgrep -f "sage_mcp_stdio_single.py" >/dev/null 2>&1; then
            success_msg "MCP服务进程运行正常"
        else
            warning_msg "MCP服务进程未运行，尝试启动..."
            docker exec "$CONTAINER_NAME" supervisorctl start sage-mcp || warning_msg "MCP服务启动失败"
        fi
    fi
}

# 功能验证
verify_functionality() {
    info_msg "验证系统功能..."
    
    # 测试MCP协议基础通信
    local test_response=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "deploy-test", "version": "1.0"}}}' | \
        timeout 10 docker exec -i "$CONTAINER_NAME" python3 /app/sage_mcp_stdio_single.py 2>/dev/null || echo "")
    
    if [ -n "$test_response" ] && echo "$test_response" | grep -q "jsonrpc"; then
        success_msg "MCP协议通信验证成功"
    else
        warning_msg "MCP协议通信验证失败"
    fi
    
    # 测试数据库基本操作
    local db_test=$(docker exec "$CONTAINER_NAME" psql -U sage -d sage_memory -c "SELECT COUNT(*) FROM memories;" 2>/dev/null | tail -n +3 | head -n 1 | tr -d ' ' || echo "error")
    
    if [ "$db_test" != "error" ]; then
        success_msg "数据库查询验证成功 (现有记录: $db_test 条)"
    else
        warning_msg "数据库查询验证失败"
    fi
}

# 显示部署结果
show_deployment_result() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}Sage MCP Docker部署完成${NC}"
    echo "========================================"
    
    # 容器状态
    local container_status=$(docker ps -f name="$CONTAINER_NAME" --format "{{.Status}}" 2>/dev/null || echo "未知")
    info_msg "容器状态: $container_status"
    
    # 容器资源使用
    local container_stats=$(docker stats "$CONTAINER_NAME" --no-stream --format "CPU: {{.CPUPerc}}, 内存: {{.MemUsage}}" 2>/dev/null || echo "无法获取")
    info_msg "资源使用: $container_stats"
    
    # 连接信息
    info_msg "MCP服务已启动，可以通过以下方式连接:"
    echo "  Claude CLI: 使用STDIO协议连接容器内的MCP服务"
    echo "  数据库: PostgreSQL在容器内运行 (端口: 5432)"
    
    # 管理命令
    echo ""
    echo "常用管理命令:"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo "  进入容器: docker exec -it $CONTAINER_NAME bash"
    
    if [ -f "$PROJECT_ROOT/scripts/health_check.sh" ]; then
        echo "  健康检查: ./scripts/health_check.sh"
    fi
    
    echo ""
    info_msg "部署日志已保存至: $LOG_FILE"
    echo "========================================"
}

# 主执行流程
main() {
    echo "========================================"
    echo -e "${BLUE}Sage MCP Docker一键部署脚本 v1.0${NC}"
    echo "========================================"
    
    parse_arguments "$@"
    
    info_msg "开始部署Sage MCP Docker服务..."
    info_msg "部署模式: $([ "$QUICK_MODE" = true ] && echo "快速模式" || echo "标准模式")"
    
    # 执行部署流程
    initialize_deployment
    check_environment
    backup_existing_data
    cleanup_existing_environment
    build_docker_images
    start_docker_containers
    perform_health_check
    verify_functionality
    
    show_deployment_result
    
    success_msg "Sage MCP Docker部署成功完成！"
}

# 信号处理
cleanup_on_exit() {
    info_msg "部署脚本退出，清理临时资源..."
}

trap cleanup_on_exit EXIT

# 执行主流程
main "$@"