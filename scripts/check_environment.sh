#!/bin/bash
# check_environment.sh - Sage MCP 环境检查脚本
# 检查Docker部署前的环境准备情况

set -euo pipefail

# 配置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查结果统计
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 错误处理函数
error_msg() {
    echo -e "${RED}[FAIL] $1${NC}"
    ((FAILED_CHECKS++))
}

# 成功信息
success_msg() {
    echo -e "${GREEN}[PASS] $1${NC}"
    ((PASSED_CHECKS++))
}

# 警告信息
warning_msg() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# 信息输出
info_msg() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# 检查包装器
run_check() {
    local check_name="$1"
    local check_function="$2"
    
    ((TOTAL_CHECKS++))
    info_msg "检查: $check_name"
    
    if $check_function; then
        success_msg "$check_name"
        return 0
    else
        error_msg "$check_name"
        return 1
    fi
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

Sage MCP Docker环境检查工具

选项:
  -h, --help          显示此帮助信息
  --json              输出JSON格式结果
  --fix               尝试自动修复发现的问题

检查项目:
  1. Docker环境检查
  2. 系统资源检查
  3. 网络端口检查
  4. 文件权限检查
  5. 配置文件检查
  6. 依赖库检查

EOF
}

# 解析命令行参数
parse_arguments() {
    JSON_OUTPUT=false
    AUTO_FIX=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --fix)
                AUTO_FIX=true
                shift
                ;;
            *)
                error_msg "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

# 检查Docker环境
check_docker_environment() {
    # 检查Docker是否安装
    if ! command -v docker &> /dev/null; then
        echo "Docker未安装"
        return 1
    fi
    
    local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    local required_version="20.10.0"
    
    if [ "$(printf '%s\n' "$required_version" "$docker_version" | sort -V | head -n1)" != "$required_version" ]; then
        echo "Docker版本过低: $docker_version (要求: >= $required_version)"
        return 1
    fi
    
    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        echo "Docker服务未运行"
        if [ "$AUTO_FIX" = true ]; then
            warning_msg "尝试启动Docker服务..."
            sudo systemctl start docker 2>/dev/null || true
        fi
        return 1
    fi
    
    # 检查docker-compose
    if ! command -v docker-compose &> /dev/null; then
        echo "docker-compose未安装"
        return 1
    fi
    
    local compose_version=$(docker-compose --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    local required_compose_version="2.0.0"
    
    if [ "$(printf '%s\n' "$required_compose_version" "$compose_version" | sort -V | head -n1)" != "$required_compose_version" ]; then
        echo "docker-compose版本过低: $compose_version (要求: >= $required_compose_version)"
        return 1
    fi
    
    echo "Docker环境正常 (Docker: $docker_version, Compose: $compose_version)"
    return 0
}

# 检查系统资源
check_system_resources() {
    local issues=()
    
    # 检查内存
    local total_memory=$(free -m | awk 'NR==2{print $2}')
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    
    if [ "$total_memory" -lt 2048 ]; then
        issues+=("总内存不足: ${total_memory}MB (建议: >= 2GB)")
    fi
    
    if [ "$available_memory" -lt 1024 ]; then
        issues+=("可用内存不足: ${available_memory}MB (建议: >= 1GB)")
    fi
    
    # 检查磁盘空间
    local available_disk=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$available_disk" -lt 10 ]; then
        issues+=("可用磁盘空间不足: ${available_disk}GB (建议: >= 10GB)")
    fi
    
    # 检查CPU核心数
    local cpu_cores=$(nproc)
    if [ "$cpu_cores" -lt 2 ]; then
        issues+=("CPU核心数不足: ${cpu_cores}核 (建议: >= 2核)")
    fi
    
    if [ ${#issues[@]} -gt 0 ]; then
        for issue in "${issues[@]}"; do
            echo "$issue"
        done
        return 1
    fi
    
    echo "系统资源充足 (内存: ${total_memory}MB, 磁盘: ${available_disk}GB, CPU: ${cpu_cores}核)"
    return 0
}

# 检查网络端口
check_network_ports() {
    local ports_to_check=(5432)
    local occupied_ports=()
    
    for port in "${ports_to_check[@]}"; do
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            local process=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | head -1)
            occupied_ports+=("$port ($process)")
        fi
    done
    
    if [ ${#occupied_ports[@]} -gt 0 ]; then
        echo "以下端口被占用: ${occupied_ports[*]}"
        if [ "$AUTO_FIX" = true ]; then
            warning_msg "注意: 端口占用可能导致冲突，建议手动检查"
        fi
        return 1
    fi
    
    echo "网络端口检查通过"
    return 0
}

# 检查文件权限
check_file_permissions() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_root="$(dirname "$script_dir")"
    
    local required_files=(
        "$project_root/docker-compose.yml"
        "$project_root/Dockerfile"
        "$project_root/sage_mcp_stdio_single.py"
        "$project_root/docker/startup.sh"
    )
    
    local permission_issues=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            permission_issues+=("文件不存在: $file")
        elif [ ! -r "$file" ]; then
            permission_issues+=("文件不可读: $file")
            if [ "$AUTO_FIX" = true ]; then
                chmod +r "$file" 2>/dev/null || true
            fi
        fi
    done
    
    # 检查启动脚本执行权限
    if [ -f "$project_root/docker/startup.sh" ] && [ ! -x "$project_root/docker/startup.sh" ]; then
        permission_issues+=("启动脚本无执行权限: docker/startup.sh")
        if [ "$AUTO_FIX" = true ]; then
            chmod +x "$project_root/docker/startup.sh" 2>/dev/null || true
        fi
    fi
    
    # 检查部署脚本执行权限
    if [ -f "$project_root/deploy.sh" ] && [ ! -x "$project_root/deploy.sh" ]; then
        permission_issues+=("部署脚本无执行权限: deploy.sh")
        if [ "$AUTO_FIX" = true ]; then
            chmod +x "$project_root/deploy.sh" 2>/dev/null || true
        fi
    fi
    
    if [ ${#permission_issues[@]} -gt 0 ]; then
        for issue in "${permission_issues[@]}"; do
            echo "$issue"
        done
        return 1
    fi
    
    echo "文件权限检查通过"
    return 0
}

# 检查配置文件
check_configuration_files() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_root="$(dirname "$script_dir")"
    
    local config_issues=()
    
    # 检查.env.example文件
    if [ ! -f "$project_root/.env.example" ]; then
        config_issues+=("缺少环境变量模板文件: .env.example")
    fi
    
    # 检查.env文件
    if [ ! -f "$project_root/.env" ]; then
        config_issues+=("缺少环境变量配置文件: .env")
        if [ "$AUTO_FIX" = true ] && [ -f "$project_root/.env.example" ]; then
            warning_msg "自动创建.env文件..."
            cp "$project_root/.env.example" "$project_root/.env"
        fi
    fi
    
    # 检查docker-compose.yml配置
    if [ -f "$project_root/docker-compose.yml" ]; then
        if ! docker-compose -f "$project_root/docker-compose.yml" config >/dev/null 2>&1; then
            config_issues+=("docker-compose.yml配置文件格式错误")
        fi
    fi
    
    # 检查Dockerfile语法
    if [ -f "$project_root/Dockerfile" ]; then
        if ! docker build --dry-run -f "$project_root/Dockerfile" "$project_root" >/dev/null 2>&1; then
            config_issues+=("Dockerfile语法检查失败")
        fi
    fi
    
    if [ ${#config_issues[@]} -gt 0 ]; then
        for issue in "${config_issues[@]}"; do
            echo "$issue"
        done
        return 1
    fi
    
    echo "配置文件检查通过"
    return 0
}

# 检查Python依赖
check_python_dependencies() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_root="$(dirname "$script_dir")"
    
    # 检查requirements.txt
    if [ ! -f "$project_root/requirements.txt" ]; then
        echo "缺少Python依赖文件: requirements.txt"
        return 1
    fi
    
    # 检查Python版本
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
        local required_python_version="3.10"
        
        if [ "$(printf '%s\n' "$required_python_version" "$python_version" | sort -V | head -n1)" != "$required_python_version" ]; then
            echo "Python版本可能不兼容: $python_version (建议: >= $required_python_version)"
            return 1
        fi
    fi
    
    # 检查sage_core模块
    if [ ! -d "$project_root/sage_core" ]; then
        echo "缺少核心模块目录: sage_core"
        return 1
    fi
    
    echo "Python依赖检查通过"
    return 0
}

# 输出JSON格式结果
output_json_result() {
    if [ "$JSON_OUTPUT" = false ]; then
        return
    fi
    
    local status="pass"
    if [ $FAILED_CHECKS -gt 0 ]; then
        status="fail"
    fi
    
    cat << EOF
{
  "timestamp": "$(date -Iseconds)",
  "status": "$status",
  "total_checks": $TOTAL_CHECKS,
  "passed_checks": $PASSED_CHECKS,
  "failed_checks": $FAILED_CHECKS,
  "environment": {
    "docker_available": $(command -v docker &> /dev/null && echo "true" || echo "false"),
    "docker_compose_available": $(command -v docker-compose &> /dev/null && echo "true" || echo "false"),
    "docker_running": $(docker info &> /dev/null && echo "true" || echo "false")
  }
}
EOF
}

# 显示检查摘要
show_check_summary() {
    echo ""
    echo "========================================"
    echo "环境检查摘要"
    echo "========================================"
    
    echo "总检查项: $TOTAL_CHECKS"
    echo -e "通过检查: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "失败检查: ${RED}$FAILED_CHECKS${NC}"
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        success_msg "所有环境检查通过，可以进行部署"
        exit 0
    else
        error_msg "$FAILED_CHECKS 项检查失败，请解决后重试"
        exit 1
    fi
}

# 主执行流程
main() {
    echo "========================================"
    echo "Sage MCP Docker环境检查工具"
    echo "========================================"
    
    parse_arguments "$@"
    
    if [ "$AUTO_FIX" = true ]; then
        info_msg "自动修复模式已启用"
    fi
    
    # 执行所有检查
    run_check "Docker环境检查" check_docker_environment
    run_check "系统资源检查" check_system_resources
    run_check "网络端口检查" check_network_ports
    run_check "文件权限检查" check_file_permissions
    run_check "配置文件检查" check_configuration_files
    run_check "Python依赖检查" check_python_dependencies
    
    if [ "$JSON_OUTPUT" = true ]; then
        output_json_result
    else
        show_check_summary
    fi
}

# 执行主流程
main "$@"