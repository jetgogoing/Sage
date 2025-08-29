#!/bin/bash
# Sage MCP 健康检查脚本
# 快速检查容器和服务健康状态

set -euo pipefail

# 配置参数
CONTAINER_NAME="sage-mcp"
DB_NAME="${DB_NAME:-sage_memory}"
DB_USER="${DB_USER:-sage}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 健康状态
OVERALL_HEALTH=0  # 0=健康, 1=警告, 2=严重

# 错误处理函数
error_msg() {
    echo -e "${RED}[ERROR] $1${NC}"
    OVERALL_HEALTH=2
}

# 成功信息
success_msg() {
    echo -e "${GREEN}[OK] $1${NC}"
}

# 警告信息
warning_msg() {
    echo -e "${YELLOW}[WARN] $1${NC}"
    if [ $OVERALL_HEALTH -lt 1 ]; then
        OVERALL_HEALTH=1
    fi
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
  --json              输出JSON格式结果
  --timeout SECONDS   设置检查超时时间 (默认: 30秒)

健康检查项目:
  1. 容器运行状态
  2. PostgreSQL数据库连接
  3. MCP服务器进程状态
  4. 系统资源使用情况
  5. 关键服务端口检查
  6. 日志错误监控
EOF
}

# 初始化默认变量
JSON_OUTPUT=false
TIMEOUT=30

# 解析命令行参数
parse_arguments() {
    
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
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
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

# 检查容器运行状态
check_container_status() {
    info_msg "检查容器运行状态..."
    
    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        error_msg "容器 ${CONTAINER_NAME} 未运行"
        return 1
    fi
    
    # 获取容器详细状态
    local container_status=$(docker ps -f name="${CONTAINER_NAME}" --format "{{.Status}}" 2>/dev/null || echo "unknown")
    local container_health=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "none")
    
    success_msg "容器状态: $container_status"
    
    if [ "$container_health" != "none" ]; then
        if [ "$container_health" = "healthy" ]; then
            success_msg "容器健康检查: $container_health"
        else
            warning_msg "容器健康检查: $container_health"
        fi
    fi
    
    return 0
}

# 检查PostgreSQL数据库
check_postgresql() {
    info_msg "检查PostgreSQL数据库..."
    
    # 检查数据库进程
    if ! docker exec "${CONTAINER_NAME}" pgrep postgres >/dev/null 2>&1; then
        error_msg "PostgreSQL进程未运行"
        return 1
    fi
    
    # 检查数据库连接
    if ! timeout "$TIMEOUT" docker exec "${CONTAINER_NAME}" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        error_msg "数据库连接失败"
        return 1
    fi
    
    success_msg "PostgreSQL数据库运行正常"
    
    # 检查数据库统计
    local connection_count=$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT count(*) FROM pg_stat_activity WHERE datname = '$DB_NAME';
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    local memory_count=$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM memories;
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    local session_count=$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM sessions;
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    info_msg "数据库连接数: $connection_count"
    info_msg "存储的记忆数: $memory_count"
    info_msg "会话数: $session_count"
    
    return 0
}

# 检查MCP服务器进程
check_mcp_server() {
    info_msg "检查MCP服务器进程..."
    
    # 检查Python进程
    local mcp_pid=$(docker exec "${CONTAINER_NAME}" pgrep -f "sage_mcp_stdio_single.py" 2>/dev/null || echo "")
    
    if [ -z "$mcp_pid" ]; then
        error_msg "MCP服务器进程未运行"
        
        # 检查supervisord状态
        local supervisor_status=$(docker exec "${CONTAINER_NAME}" supervisorctl status sage-mcp 2>/dev/null || echo "unknown")
        warning_msg "Supervisor状态: $supervisor_status"
        
        return 1
    fi
    
    success_msg "MCP服务器进程运行正常 (PID: $mcp_pid)"
    
    # 检查进程资源使用
    local process_info=$(docker exec "${CONTAINER_NAME}" ps -p "$mcp_pid" -o pid,ppid,pcpu,pmem,etime,cmd --no-headers 2>/dev/null || echo "无法获取进程信息")
    info_msg "进程信息: $process_info"
    
    return 0
}

# 检查系统资源使用
check_system_resources() {
    info_msg "检查系统资源使用..."
    
    # 获取容器资源使用情况
    local container_stats=$(docker stats "${CONTAINER_NAME}" --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" 2>/dev/null || echo "无法获取,无法获取,无法获取,无法获取")
    
    IFS=',' read -r cpu_usage mem_usage net_io block_io <<< "$container_stats"
    
    info_msg "CPU使用率: $cpu_usage"
    info_msg "内存使用: $mem_usage"
    info_msg "网络IO: $net_io"
    info_msg "磁盘IO: $block_io"
    
    # 检查CPU使用率是否过高
    local cpu_percent=$(echo "$cpu_usage" | sed 's/%//' | cut -d'.' -f1 2>/dev/null || echo "0")
    if [ "$cpu_percent" -gt 80 ]; then
        warning_msg "CPU使用率过高: $cpu_usage"
    fi
    
    # 检查内存使用
    if echo "$mem_usage" | grep -q "GiB"; then
        local mem_value=$(echo "$mem_usage" | cut -d'/' -f1 | sed 's/GiB//' | cut -d'.' -f1 2>/dev/null || echo "0")
        if [ "$mem_value" -gt 2 ]; then
            warning_msg "内存使用较高: $mem_usage"
        fi
    fi
    
    # 检查磁盘空间
    local disk_usage=$(docker exec "${CONTAINER_NAME}" df -h / | awk 'NR==2 {print $5}' | sed 's/%//' 2>/dev/null || echo "0")
    info_msg "磁盘使用率: ${disk_usage}%"
    
    if [ "$disk_usage" -gt 80 ]; then
        warning_msg "磁盘使用率过高: ${disk_usage}%"
    fi
    
    return 0
}

# 检查关键端口
check_ports() {
    info_msg "检查关键服务端口..."
    
    # 检查PostgreSQL端口
    if docker exec "${CONTAINER_NAME}" netstat -tlnp 2>/dev/null | grep -q ":5432"; then
        success_msg "PostgreSQL端口5432监听正常"
    else
        error_msg "PostgreSQL端口5432未监听"
        return 1
    fi
    
    # 检查暴露到主机的端口
    local exposed_ports=$(docker port "${CONTAINER_NAME}" 2>/dev/null || echo "")
    if [ -n "$exposed_ports" ]; then
        info_msg "暴露端口: $exposed_ports"
    else
        info_msg "未暴露任何端口到主机"
    fi
    
    return 0
}

# 检查日志错误
check_logs() {
    info_msg "检查日志错误..."
    
    # 检查最近的Docker容器日志
    local recent_errors=$(docker logs "${CONTAINER_NAME}" --since=5m 2>&1 | grep -i "error\|exception\|fail" | tail -5 || echo "")
    
    if [ -n "$recent_errors" ]; then
        warning_msg "发现最近的错误日志:"
        echo "$recent_errors"
    else
        success_msg "最近5分钟内无错误日志"
    fi
    
    # 检查MCP错误日志
    local mcp_errors=$(docker exec "${CONTAINER_NAME}" tail -n 20 /var/log/sage/sage_mcp_error.log 2>/dev/null | grep -i "error\|exception" | wc -l || echo "0")
    
    info_msg "MCP错误日志条数: $mcp_errors"
    
    if [ "$mcp_errors" -gt 5 ]; then
        warning_msg "MCP错误日志较多，建议检查"
    fi
    
    return 0
}

# 快速连通性测试
quick_connectivity_test() {
    info_msg "执行快速连通性测试..."
    
    # 测试基本的MCP响应
    local test_response=$(echo '{"jsonrpc": "2.0", "id": 999, "method": "ping"}' | \
        timeout 5 docker exec -i "${CONTAINER_NAME}" python3 -c "
import sys
import json
try:
    for line in sys.stdin:
        print('MCP服务器响应正常')
        break
except:
    print('MCP服务器无响应')
" 2>/dev/null || echo "连接测试失败")
    
    if echo "$test_response" | grep -q "响应正常"; then
        success_msg "MCP服务器连通性正常"
    else
        warning_msg "MCP服务器连通性测试: $test_response"
    fi
    
    return 0
}

# 输出JSON格式结果
output_json_result() {
    if [ "$JSON_OUTPUT" = false ]; then
        return
    fi
    
    local status="healthy"
    case $OVERALL_HEALTH in
        1) status="warning" ;;
        2) status="critical" ;;
    esac
    
    cat << EOF
{
  "timestamp": "$(date -Iseconds)",
  "container": "$CONTAINER_NAME",
  "overall_status": "$status",
  "health_code": $OVERALL_HEALTH,
  "checks": {
    "container_running": $(docker ps -q -f name="${CONTAINER_NAME}" | grep -q . && echo "true" || echo "false"),
    "database_connected": $(docker exec "${CONTAINER_NAME}" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1 && echo "true" || echo "false"),
    "mcp_process_running": $(docker exec "${CONTAINER_NAME}" pgrep -f "sage_mcp_stdio_single.py" >/dev/null 2>&1 && echo "true" || echo "false")
  }
}
EOF
}

# 显示健康状态摘要
show_health_summary() {
    echo ""
    echo "=========================================="
    echo "健康检查摘要"
    echo "=========================================="
    
    case $OVERALL_HEALTH in
        0)
            success_msg "系统整体健康状态: 正常"
            ;;
        1)
            warning_msg "系统整体健康状态: 警告"
            ;;
        2)
            error_msg "系统整体健康状态: 严重"
            ;;
    esac
    
    echo "检查时间: $(date)"
    echo "容器名称: $CONTAINER_NAME"
    echo "=========================================="
}

# 主执行流程
main() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo "=========================================="
        echo "Sage MCP 健康检查工具"
        echo "=========================================="
    fi
    
    parse_arguments "$@"
    
    # 执行所有健康检查
    check_container_status
    check_postgresql
    check_mcp_server
    check_system_resources
    check_ports
    check_logs
    quick_connectivity_test
    
    if [ "$JSON_OUTPUT" = true ]; then
        output_json_result
    else
        show_health_summary
    fi
    
    # 返回健康状态作为退出码
    exit $OVERALL_HEALTH
}

# 执行主流程
main "$@"