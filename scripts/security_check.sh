#!/bin/bash
# Sage MCP 安全检查脚本
# 检查容器和系统的安全配置

set -euo pipefail

# 配置参数
CONTAINER_NAME="sage-mcp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 错误处理函数
error_msg() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

# 成功信息
success_msg() {
    echo -e "${GREEN}[PASS] $1${NC}"
}

# 警告信息
warning_msg() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# 信息输出
info_msg() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
  -h, --help          显示此帮助信息
  -c, --container     指定容器名称 (默认: ${CONTAINER_NAME})
  --quick            快速检查（跳过详细扫描）
  --report           生成详细安全报告
  --fix              自动修复发现的安全问题

安全检查项目:
  1. 容器运行权限检查
  2. 网络端口安全扫描
  3. 文件系统权限验证
  4. 数据库用户权限检查
  5. 环境变量安全审计
  6. 容器配置安全评估
  7. 镜像安全漏洞扫描
EOF
}

# 解析命令行参数
parse_arguments() {
    QUICK_MODE=false
    GENERATE_REPORT=false
    AUTO_FIX=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--container)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --report)
                GENERATE_REPORT=true
                shift
                ;;
            --fix)
                AUTO_FIX=true
                shift
                ;;
            -*)
                error_msg "未知选项: $1"
                exit 1
                ;;
            *)
                error_msg "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

# 检查容器是否运行
check_container_running() {
    info_msg "检查容器运行状态..."
    
    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        error_msg "容器 ${CONTAINER_NAME} 未运行"
        return 1
    fi
    
    success_msg "容器 ${CONTAINER_NAME} 正在运行"
    return 0
}

# 检查容器运行用户权限
check_container_user() {
    info_msg "检查容器运行用户权限..."
    
    # 检查容器内运行的用户
    local running_user=$(docker exec "${CONTAINER_NAME}" whoami 2>/dev/null || echo "unknown")
    local user_id=$(docker exec "${CONTAINER_NAME}" id -u 2>/dev/null || echo "0")
    local group_id=$(docker exec "${CONTAINER_NAME}" id -g 2>/dev/null || echo "0")
    
    echo "运行用户: $running_user (UID: $user_id, GID: $group_id)"
    
    if [ "$user_id" -eq 0 ]; then
        warning_msg "容器以root用户运行，存在安全风险"
        if [ "$AUTO_FIX" = true ]; then
            warning_msg "建议修改Dockerfile使用非特权用户"
        fi
        return 1
    else
        success_msg "容器使用非特权用户运行"
        return 0
    fi
}

# 检查网络端口安全
check_network_security() {
    info_msg "检查网络端口安全..."
    
    # 检查容器暴露的端口
    local exposed_ports=$(docker port "${CONTAINER_NAME}" 2>/dev/null || echo "")
    
    if [ -z "$exposed_ports" ]; then
        success_msg "容器未暴露任何端口"
    else
        echo "暴露的端口:"
        echo "$exposed_ports"
        
        # 检查是否暴露了PostgreSQL端口
        if echo "$exposed_ports" | grep -q "5432"; then
            warning_msg "PostgreSQL端口5432已暴露，生产环境建议移除"
        fi
    fi
    
    # 检查容器内监听的端口
    local listening_ports=$(docker exec "${CONTAINER_NAME}" netstat -tulpn 2>/dev/null | grep LISTEN || echo "")
    
    if [ -n "$listening_ports" ]; then
        echo "容器内监听端口:"
        echo "$listening_ports"
    fi
    
    # 检查防火墙状态（主机级别）
    info_msg "检查主机防火墙状态..."
    
    if command -v ufw >/dev/null 2>&1; then
        local ufw_status=$(sudo ufw status 2>/dev/null || echo "需要sudo权限")
        echo "UFW状态: $ufw_status"
    elif command -v firewall-cmd >/dev/null 2>&1; then
        local firewalld_status=$(sudo firewall-cmd --state 2>/dev/null || echo "需要sudo权限")
        echo "Firewalld状态: $firewalld_status"
    else
        warning_msg "未检测到支持的防火墙工具"
    fi
}

# 检查文件系统权限
check_filesystem_permissions() {
    info_msg "检查文件系统权限..."
    
    # 检查关键目录权限
    local critical_dirs=(
        "/app"
        "/var/log/sage"
        "/var/lib/postgresql/data"
        "/etc/supervisor"
    )
    
    for dir in "${critical_dirs[@]}"; do
        if docker exec "${CONTAINER_NAME}" test -d "$dir" 2>/dev/null; then
            local perms=$(docker exec "${CONTAINER_NAME}" stat -c "%a %U:%G" "$dir" 2>/dev/null || echo "无法获取")
            echo "$dir: $perms"
            
            # 检查敏感目录权限
            if [ "$dir" = "/var/lib/postgresql/data" ]; then
                local perm_octal=$(echo "$perms" | cut -d' ' -f1)
                if [ "$perm_octal" != "700" ]; then
                    warning_msg "PostgreSQL数据目录权限不安全: $perm_octal (建议700)"
                fi
            fi
        else
            warning_msg "目录不存在: $dir"
        fi
    done
    
    # 检查关键文件权限
    local critical_files=(
        "/app/sage_mcp_stdio_single.py"
        "/startup.sh"
    )
    
    for file in "${critical_files[@]}"; do
        if docker exec "${CONTAINER_NAME}" test -f "$file" 2>/dev/null; then
            local perms=$(docker exec "${CONTAINER_NAME}" stat -c "%a %U:%G" "$file" 2>/dev/null || echo "无法获取")
            echo "$file: $perms"
        fi
    done
}

# 检查数据库安全配置
check_database_security() {
    info_msg "检查数据库安全配置..."
    
    # 检查数据库连接
    if ! docker exec "${CONTAINER_NAME}" pg_isready -U postgres >/dev/null 2>&1; then
        error_msg "无法连接到PostgreSQL数据库"
        return 1
    fi
    
    # 检查数据库用户
    local db_users=$(docker exec "${CONTAINER_NAME}" psql -U postgres -d sage_memory -t -c "
        SELECT usename, usesuper, usecreatedb, userepl 
        FROM pg_user 
        ORDER BY usename;
    " 2>/dev/null || echo "无法获取用户信息")
    
    if [ "$db_users" != "无法获取用户信息" ]; then
        echo "数据库用户列表:"
        echo "$db_users"
        
        # 检查是否有非必要的超级用户
        local super_users=$(echo "$db_users" | grep " t " | wc -l)
        if [ "$super_users" -gt 1 ]; then
            warning_msg "发现多个超级用户，建议最小化超级用户权限"
        fi
    fi
    
    # 检查数据库连接配置
    local pg_hba=$(docker exec "${CONTAINER_NAME}" cat /var/lib/postgresql/data/pg_hba.conf 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "无法读取pg_hba.conf")
    
    if [ "$pg_hba" != "无法读取pg_hba.conf" ]; then
        echo "PostgreSQL认证配置:"
        echo "$pg_hba"
        
        # 检查是否存在trust认证
        if echo "$pg_hba" | grep -q "trust"; then
            warning_msg "发现trust认证配置，存在安全风险"
        fi
    fi
    
    # 检查SSL配置
    local ssl_status=$(docker exec "${CONTAINER_NAME}" psql -U postgres -d sage_memory -t -c "SHOW ssl;" 2>/dev/null | tr -d ' \n' || echo "unknown")
    echo "SSL状态: $ssl_status"
    
    if [ "$ssl_status" = "off" ]; then
        warning_msg "数据库SSL未启用，建议启用SSL加密连接"
    fi
}

# 检查环境变量安全
check_environment_security() {
    info_msg "检查环境变量安全..."
    
    # 检查敏感环境变量
    local sensitive_vars=(
        "DB_PASSWORD"
        "POSTGRES_PASSWORD"
        "SILICONFLOW_API_KEY"
        "JWT_SECRET"
    )
    
    for var in "${sensitive_vars[@]}"; do
        local value=$(docker exec "${CONTAINER_NAME}" printenv "$var" 2>/dev/null || echo "")
        if [ -n "$value" ]; then
            # 不显示完整值，只显示长度和格式
            local length=${#value}
            local masked_value=$(echo "$value" | sed 's/./*/g' | cut -c1-8)
            echo "$var: ${masked_value}... (长度: $length)"
            
            # 检查密码强度
            if [[ "$var" == *"PASSWORD"* ]]; then
                if [ "$length" -lt 12 ]; then
                    warning_msg "$var 长度不足12位，建议使用更强密码"
                fi
                
                # 简单的密码复杂度检查
                if ! echo "$value" | grep -q "[A-Z]" || ! echo "$value" | grep -q "[a-z]" || ! echo "$value" | grep -q "[0-9]"; then
                    warning_msg "$var 复杂度不足，建议包含大小写字母和数字"
                fi
            fi
        else
            warning_msg "$var 未设置或为空"
        fi
    done
    
    # 检查.env文件权限（主机上）
    if [ -f "$PROJECT_ROOT/.env" ]; then
        local env_perms=$(stat -c "%a" "$PROJECT_ROOT/.env" 2>/dev/null || stat -f "%Lp" "$PROJECT_ROOT/.env" 2>/dev/null || echo "unknown")
        echo ".env文件权限: $env_perms"
        
        if [ "$env_perms" != "600" ] && [ "$env_perms" != "0600" ]; then
            warning_msg ".env文件权限不安全: $env_perms (建议600)"
            if [ "$AUTO_FIX" = true ]; then
                chmod 600 "$PROJECT_ROOT/.env"
                success_msg "已修复.env文件权限"
            fi
        fi
    fi
}

# 检查容器配置安全
check_container_config() {
    info_msg "检查容器配置安全..."
    
    # 检查容器运行配置
    local container_info=$(docker inspect "${CONTAINER_NAME}" 2>/dev/null || echo "")
    
    if [ -n "$container_info" ]; then
        # 检查特权模式
        local privileged=$(echo "$container_info" | grep '"Privileged"' | cut -d: -f2 | tr -d ' ,' || echo "false")
        echo "特权模式: $privileged"
        
        if [ "$privileged" = "true" ]; then
            error_msg "容器运行在特权模式，存在严重安全风险"
        else
            success_msg "容器未使用特权模式"
        fi
        
        # 检查网络模式
        local network_mode=$(echo "$container_info" | grep '"NetworkMode"' | cut -d'"' -f4 || echo "unknown")
        echo "网络模式: $network_mode"
        
        if [ "$network_mode" = "host" ]; then
            warning_msg "容器使用host网络模式，可能存在安全风险"
        fi
        
        # 检查资源限制
        local memory_limit=$(echo "$container_info" | grep '"Memory"' | head -1 | cut -d: -f2 | tr -d ' ,' || echo "0")
        local cpu_shares=$(echo "$container_info" | grep '"CpuShares"' | cut -d: -f2 | tr -d ' ,' || echo "0")
        
        echo "内存限制: $memory_limit bytes"
        echo "CPU shares: $cpu_shares"
        
        if [ "$memory_limit" = "0" ]; then
            warning_msg "未设置内存限制，建议限制容器资源使用"
        fi
    fi
}

# 扫描镜像安全漏洞
check_image_vulnerabilities() {
    if [ "$QUICK_MODE" = true ]; then
        info_msg "快速模式：跳过镜像漏洞扫描"
        return
    fi
    
    info_msg "扫描镜像安全漏洞..."
    
    # 获取镜像名称
    local image_name=$(docker inspect "${CONTAINER_NAME}" -f '{{.Config.Image}}' 2>/dev/null || echo "unknown")
    echo "镜像名称: $image_name"
    
    # 检查是否有安全扫描工具
    if command -v trivy >/dev/null 2>&1; then
        echo "使用Trivy扫描镜像漏洞..."
        trivy image --severity HIGH,CRITICAL "$image_name" 2>/dev/null || warning_msg "Trivy扫描失败"
    elif command -v docker >/dev/null 2>&1; then
        # 尝试使用Docker的安全扫描（如果可用）
        echo "尝试使用Docker扫描..."
        docker scan "$image_name" 2>/dev/null || warning_msg "Docker扫描不可用或失败"
    else
        warning_msg "未找到镜像安全扫描工具，建议安装Trivy"
    fi
}

# 生成安全报告
generate_security_report() {
    if [ "$GENERATE_REPORT" = false ]; then
        return
    fi
    
    info_msg "生成安全检查报告..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="$PROJECT_ROOT/backups/security_report_${timestamp}.txt"
    
    mkdir -p "$PROJECT_ROOT/backups"
    
    cat > "$report_file" << EOF
Sage MCP 安全检查报告
====================

检查时间: $(date)
容器名称: $CONTAINER_NAME
检查模式: $([ "$QUICK_MODE" = true ] && echo "快速模式" || echo "完整模式")

=== 容器运行信息 ===
容器状态: $(docker ps -f name="${CONTAINER_NAME}" --format "{{.Status}}" 2>/dev/null || echo "未运行")
运行用户: $(docker exec "${CONTAINER_NAME}" whoami 2>/dev/null || echo "unknown")
用户ID: $(docker exec "${CONTAINER_NAME}" id -u 2>/dev/null || echo "unknown")

=== 网络安全 ===
暴露端口:
$(docker port "${CONTAINER_NAME}" 2>/dev/null || echo "无暴露端口")

监听端口:
$(docker exec "${CONTAINER_NAME}" netstat -tulpn 2>/dev/null | grep LISTEN || echo "无监听端口")

=== 文件权限 ===
关键目录权限:
$(for dir in /app /var/log/sage /var/lib/postgresql/data; do
    if docker exec "${CONTAINER_NAME}" test -d "$dir" 2>/dev/null; then
        echo "$dir: $(docker exec "${CONTAINER_NAME}" stat -c "%a %U:%G" "$dir" 2>/dev/null)"
    fi
done)

=== 数据库安全 ===
数据库用户:
$(docker exec "${CONTAINER_NAME}" psql -U postgres -d sage_memory -t -c "SELECT usename, usesuper FROM pg_user;" 2>/dev/null || echo "无法获取")

SSL状态: $(docker exec "${CONTAINER_NAME}" psql -U postgres -d sage_memory -t -c "SHOW ssl;" 2>/dev/null | tr -d ' \n' || echo "unknown")

=== 容器配置 ===
特权模式: $(docker inspect "${CONTAINER_NAME}" --format '{{.HostConfig.Privileged}}' 2>/dev/null || echo "unknown")
网络模式: $(docker inspect "${CONTAINER_NAME}" --format '{{.HostConfig.NetworkMode}}' 2>/dev/null || echo "unknown")
内存限制: $(docker inspect "${CONTAINER_NAME}" --format '{{.HostConfig.Memory}}' 2>/dev/null || echo "unknown")

=== 建议改进 ===
1. 如果以root用户运行，建议使用非特权用户
2. 生产环境移除不必要的端口映射
3. 设置适当的资源限制
4. 启用数据库SSL连接
5. 定期更新基础镜像和依赖
6. 实施日志监控和告警

检查完成时间: $(date)
EOF
    
    success_msg "安全报告已生成: $report_file"
}

# 主执行流程
main() {
    echo "=========================================="
    echo "Sage MCP 安全检查工具"
    echo "=========================================="
    
    parse_arguments "$@"
    
    info_msg "开始安全检查 - 容器: $CONTAINER_NAME"
    
    # 执行所有安全检查
    local check_results=0
    
    check_container_running || ((check_results++))
    check_container_user || ((check_results++))
    check_network_security
    check_filesystem_permissions
    check_database_security
    check_environment_security
    check_container_config
    check_image_vulnerabilities
    
    generate_security_report
    
    echo "=========================================="
    if [ $check_results -eq 0 ]; then
        success_msg "安全检查完成，未发现严重问题"
    else
        warning_msg "安全检查完成，发现 $check_results 个需要关注的问题"
    fi
    echo "=========================================="
    
    return $check_results
}

# 执行主流程
main "$@"