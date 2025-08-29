#!/bin/bash
# monitor.sh - Sage MCP 容器监控工具
# 实时监控容器状态、资源使用和服务健康

set -euo pipefail

# 配置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置参数
CONTAINER_NAME="sage-mcp"
REFRESH_INTERVAL=5
MONITOR_DURATION=0  # 0 = 无限制
LOG_FILE=""
AUTO_RESTART=false

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

Sage MCP 容器监控工具

选项:
  -h, --help              显示此帮助信息
  -c, --container NAME    指定容器名称 (默认: $CONTAINER_NAME)
  -i, --interval SECONDS  刷新间隔 (默认: ${REFRESH_INTERVAL}秒)
  -d, --duration SECONDS  监控持续时间 (默认: 无限制)
  -l, --log FILE          将监控数据保存到文件
  --auto-restart          自动重启异常容器
  --dashboard             显示仪表板模式
  --alerts                启用告警模式

监控内容:
  1. 容器运行状态
  2. 资源使用情况 (CPU、内存、网络、磁盘)
  3. 进程状态监控
  4. 服务健康检查
  5. 错误日志监控

快捷键:
  q/Q    - 退出监控
  r/R    - 重启容器
  l/L    - 查看日志
  h/H    - 显示帮助

EOF
}

# 解析命令行参数
parse_arguments() {
    DASHBOARD_MODE=false
    ALERTS_MODE=false
    
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
            -i|--interval)
                REFRESH_INTERVAL="$2"
                shift 2
                ;;
            -d|--duration)
                MONITOR_DURATION="$2"
                shift 2
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            --auto-restart)
                AUTO_RESTART=true
                shift
                ;;
            --dashboard)
                DASHBOARD_MODE=true
                shift
                ;;
            --alerts)
                ALERTS_MODE=true
                shift
                ;;
            *)
                echo "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

# 检查容器是否存在
check_container_exists() {
    if ! docker ps -a -f name="^${CONTAINER_NAME}$" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${RED}错误: 容器 '$CONTAINER_NAME' 不存在${NC}"
        exit 1
    fi
}

# 获取容器状态
get_container_status() {
    local status=$(docker ps -a -f name="^${CONTAINER_NAME}$" --format "{{.Status}}" 2>/dev/null || echo "unknown")
    echo "$status"
}

# 获取容器资源使用情况
get_container_stats() {
    local stats=$(docker stats "$CONTAINER_NAME" --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" 2>/dev/null || echo "0%,0B / 0B,0B / 0B,0B / 0B")
    echo "$stats"
}

# 获取容器进程信息
get_container_processes() {
    docker exec "$CONTAINER_NAME" ps aux --sort=-%cpu 2>/dev/null || echo "无法获取进程信息"
}

# 获取服务状态
get_service_status() {
    local postgres_status="未知"
    local mcp_status="未知"
    
    # 检查PostgreSQL
    if docker exec "$CONTAINER_NAME" pg_isready -U sage -d sage_memory >/dev/null 2>&1; then
        postgres_status="运行中"
    else
        postgres_status="停止"
    fi
    
    # 检查MCP服务
    if docker exec "$CONTAINER_NAME" pgrep -f "sage_mcp_stdio_single.py" >/dev/null 2>&1; then
        mcp_status="运行中"
    else
        mcp_status="停止"
    fi
    
    echo "PostgreSQL:$postgres_status,MCP:$mcp_status"
}

# 获取错误日志
get_error_logs() {
    local recent_errors=$(docker logs "$CONTAINER_NAME" --since=1m 2>&1 | grep -i "error\|exception\|fail" | tail -5 || echo "")
    echo "$recent_errors"
}

# 清屏并移动光标到顶部
clear_screen() {
    printf '\033[2J\033[H'
}

# 显示标题
show_header() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${CYAN}================================================${NC}"
    echo -e "${CYAN}    Sage MCP 容器监控 - $timestamp${NC}"
    echo -e "${CYAN}    容器: $CONTAINER_NAME | 刷新间隔: ${REFRESH_INTERVAL}s${NC}"
    echo -e "${CYAN}================================================${NC}"
    echo ""
}

# 显示容器状态
show_container_status() {
    local status=$(get_container_status)
    
    echo -e "${BLUE}[容器状态]${NC}"
    if echo "$status" | grep -q "Up"; then
        echo -e "  状态: ${GREEN}$status${NC}"
    else
        echo -e "  状态: ${RED}$status${NC}"
        if [ "$AUTO_RESTART" = true ] && echo "$status" | grep -q "Exited"; then
            echo -e "  ${YELLOW}自动重启容器中...${NC}"
            docker start "$CONTAINER_NAME" >/dev/null 2>&1 || true
        fi
    fi
    echo ""
}

# 显示资源使用
show_resource_usage() {
    local stats=$(get_container_stats)
    IFS=',' read -r cpu_usage mem_usage net_io block_io <<< "$stats"
    
    echo -e "${BLUE}[资源使用]${NC}"
    echo "  CPU使用率: $cpu_usage"
    echo "  内存使用: $mem_usage"
    echo "  网络IO:   $net_io"
    echo "  磁盘IO:   $block_io"
    
    # 检查资源使用率告警
    if [ "$ALERTS_MODE" = true ]; then
        local cpu_percent=$(echo "$cpu_usage" | sed 's/%//' | cut -d'.' -f1 2>/dev/null || echo "0")
        if [ "$cpu_percent" -gt 80 ]; then
            echo -e "  ${RED}⚠️  CPU使用率过高: $cpu_usage${NC}"
        fi
        
        if echo "$mem_usage" | grep -q "GiB"; then
            local mem_value=$(echo "$mem_usage" | cut -d'/' -f1 | sed 's/GiB//' | cut -d'.' -f1 2>/dev/null || echo "0")
            if [ "$mem_value" -gt 2 ]; then
                echo -e "  ${RED}⚠️  内存使用过高: $mem_usage${NC}"
            fi
        fi
    fi
    
    echo ""
}

# 显示服务状态
show_service_status() {
    local services=$(get_service_status)
    IFS=',' read -r postgres_info mcp_info <<< "$services"
    
    echo -e "${BLUE}[服务状态]${NC}"
    
    local postgres_status=$(echo "$postgres_info" | cut -d':' -f2)
    if [ "$postgres_status" = "运行中" ]; then
        echo -e "  PostgreSQL: ${GREEN}$postgres_status${NC}"
    else
        echo -e "  PostgreSQL: ${RED}$postgres_status${NC}"
    fi
    
    local mcp_status=$(echo "$mcp_info" | cut -d':' -f2)
    if [ "$mcp_status" = "运行中" ]; then
        echo -e "  MCP服务:    ${GREEN}$mcp_status${NC}"
    else
        echo -e "  MCP服务:    ${RED}$mcp_status${NC}"
    fi
    
    echo ""
}

# 显示进程信息
show_process_info() {
    echo -e "${BLUE}[关键进程]${NC}"
    
    local processes=$(docker exec "$CONTAINER_NAME" ps aux --sort=-%cpu | head -6 2>/dev/null || echo "无法获取进程信息")
    echo "$processes" | while IFS= read -r line; do
        echo "  $line"
    done
    
    echo ""
}

# 显示错误日志
show_error_logs() {
    local errors=$(get_error_logs)
    
    echo -e "${BLUE}[近期错误]${NC}"
    if [ -n "$errors" ]; then
        echo "$errors" | while IFS= read -r line; do
            echo -e "  ${RED}$line${NC}"
        done
    else
        echo -e "  ${GREEN}无近期错误${NC}"
    fi
    
    echo ""
}

# 显示帮助信息
show_interactive_help() {
    echo -e "${BLUE}[快捷键]${NC}"
    echo "  q/Q - 退出监控    r/R - 重启容器    l/L - 查看日志    h/H - 显示帮助"
    echo ""
}

# 仪表板模式显示
show_dashboard() {
    clear_screen
    show_header
    show_container_status
    show_resource_usage
    show_service_status
    
    if [ "$DASHBOARD_MODE" = true ]; then
        show_process_info
        show_error_logs
    fi
    
    show_interactive_help
}

# 记录监控数据到文件
log_monitoring_data() {
    if [ -z "$LOG_FILE" ]; then
        return
    fi
    
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local status=$(get_container_status)
    local stats=$(get_container_stats)
    local services=$(get_service_status)
    
    echo "$timestamp,$status,$stats,$services" >> "$LOG_FILE"
}

# 处理交互式输入
handle_interactive_input() {
    local key=""
    
    # 使用read -t来实现非阻塞输入
    if read -t 0.1 -n 1 key 2>/dev/null; then
        case "$key" in
            q|Q)
                echo -e "\n${GREEN}监控已停止${NC}"
                exit 0
                ;;
            r|R)
                echo -e "\n${YELLOW}重启容器中...${NC}"
                docker restart "$CONTAINER_NAME" >/dev/null 2>&1 || true
                sleep 2
                ;;
            l|L)
                echo -e "\n${BLUE}显示容器日志 (按Ctrl+C返回监控):${NC}"
                docker logs --tail 20 -f "$CONTAINER_NAME" || true
                ;;
            h|H)
                clear_screen
                show_usage
                echo -e "\n按任意键返回监控..."
                read -n 1 -s
                ;;
        esac
    fi
}

# 主监控循环
monitor_loop() {
    local start_time=$(date +%s)
    local iteration=0
    
    # 设置终端为原始模式以支持单字符输入
    if [ -t 0 ]; then
        stty -echo -icanon time 0 min 0 2>/dev/null || true
    fi
    
    while true; do
        show_dashboard
        log_monitoring_data
        
        # 检查监控持续时间
        if [ "$MONITOR_DURATION" -gt 0 ]; then
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            if [ "$elapsed" -ge "$MONITOR_DURATION" ]; then
                echo -e "\n${GREEN}监控时间已到，自动退出${NC}"
                break
            fi
        fi
        
        # 处理交互式输入
        for i in $(seq 1 $((REFRESH_INTERVAL * 10))); do
            handle_interactive_input
            sleep 0.1
        done
        
        ((iteration++))
    done
    
    # 恢复终端设置
    if [ -t 0 ]; then
        stty echo icanon 2>/dev/null || true
    fi
}

# 信号处理
cleanup_on_exit() {
    # 恢复终端设置
    if [ -t 0 ]; then
        stty echo icanon 2>/dev/null || true
    fi
    echo -e "\n${GREEN}监控已停止${NC}"
}

# 主执行流程
main() {
    parse_arguments "$@"
    
    # 检查容器存在
    check_container_exists
    
    # 设置信号处理
    trap cleanup_on_exit EXIT INT TERM
    
    # 初始化日志文件
    if [ -n "$LOG_FILE" ]; then
        echo "timestamp,status,cpu,memory,network,disk,postgres,mcp" > "$LOG_FILE"
        echo -e "${GREEN}监控数据将保存到: $LOG_FILE${NC}"
    fi
    
    echo -e "${GREEN}开始监控容器: $CONTAINER_NAME${NC}"
    echo -e "${YELLOW}按 'q' 退出，'h' 查看帮助${NC}"
    sleep 2
    
    # 开始监控
    monitor_loop
}

# 执行主流程
main "$@"