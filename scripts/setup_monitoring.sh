#!/bin/bash
# Sage MCP 监控和告警设置脚本
# 创建定时备份和数据监控任务

set -euo pipefail

# 配置参数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 错误处理函数
error_exit() {
    echo "[ERROR] $1" >&2
    exit 1
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
  -h, --help          显示此帮助信息
  --setup-cron        设置定时备份任务
  --setup-monitoring  设置数据监控任务
  --remove-cron       移除定时任务
  --status            显示当前监控状态

监控功能:
  1. 每日自动数据备份（凌晨2点）
  2. 每小时数据完整性检查
  3. 磁盘空间监控
  4. 容器健康状态监控
EOF
}

# 设置定时备份任务
setup_cron_backup() {
    echo "[INFO] 设置定时备份任务..."
    
    # 创建cron任务脚本
    local cron_backup_script="${SCRIPT_DIR}/cron_backup.sh"
    
    cat > "$cron_backup_script" << 'EOF'
#!/bin/bash
# 定时备份任务脚本

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目目录
cd "$PROJECT_ROOT"

# 执行备份
echo "[$(date)] 开始定时备份..." >> /var/log/sage_cron.log 2>&1
"$SCRIPT_DIR/backup.sh" >> /var/log/sage_cron.log 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] 定时备份完成" >> /var/log/sage_cron.log 2>&1
else
    echo "[$(date)] 定时备份失败" >> /var/log/sage_cron.log 2>&1
    # 发送告警（可以接入邮件、Slack等）
    echo "Sage MCP 定时备份失败 - $(date)" | logger -t sage-backup
fi
EOF
    
    chmod +x "$cron_backup_script"
    
    # 创建cron配置
    local cron_entry="0 2 * * * $cron_backup_script"
    
    # 检查是否已存在相同的cron任务
    if crontab -l 2>/dev/null | grep -q "$cron_backup_script"; then
        echo "[INFO] 定时备份任务已存在"
    else
        # 添加到crontab
        (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
        echo "[INFO] 定时备份任务已添加: $cron_entry"
    fi
    
    echo "[INFO] 定时备份设置完成"
}

# 设置数据监控任务
setup_monitoring() {
    echo "[INFO] 设置数据监控任务..."
    
    # 创建监控脚本
    local monitoring_script="${SCRIPT_DIR}/cron_monitoring.sh"
    
    cat > "$monitoring_script" << 'EOF'
#!/bin/bash
# 数据监控任务脚本

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目目录
cd "$PROJECT_ROOT"

# 监控日志文件
LOG_FILE="/var/log/sage_monitoring.log"

# 记录监控开始
echo "[$(date)] 开始监控检查..." >> "$LOG_FILE"

# 1. 检查容器状态
if ! docker ps -q -f name="sage-mcp" | grep -q .; then
    echo "[$(date)] 告警: sage-mcp容器未运行" >> "$LOG_FILE"
    echo "Sage MCP 容器未运行 - $(date)" | logger -t sage-monitoring -p user.err
    exit 1
fi

# 2. 检查数据库连接
if ! docker exec sage-mcp pg_isready -U sage -d sage_memory >/dev/null 2>&1; then
    echo "[$(date)] 告警: 数据库连接失败" >> "$LOG_FILE"
    echo "Sage MCP 数据库连接失败 - $(date)" | logger -t sage-monitoring -p user.err
    exit 1
fi

# 3. 检查磁盘空间
DISK_USAGE=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "[$(date)] 警告: 磁盘使用率过高 ${DISK_USAGE}%" >> "$LOG_FILE"
    echo "Sage MCP 磁盘使用率过高 ${DISK_USAGE}% - $(date)" | logger -t sage-monitoring -p user.warning
fi

# 4. 快速数据验证
"$SCRIPT_DIR/verify_data.sh" --quick >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date)] 告警: 数据验证失败" >> "$LOG_FILE"
    echo "Sage MCP 数据验证失败 - $(date)" | logger -t sage-monitoring -p user.err
fi

echo "[$(date)] 监控检查完成" >> "$LOG_FILE"
EOF
    
    chmod +x "$monitoring_script"
    
    # 创建监控cron任务（每小时执行）
    local monitoring_cron_entry="0 * * * * $monitoring_script"
    
    # 检查是否已存在相同的监控任务
    if crontab -l 2>/dev/null | grep -q "$monitoring_script"; then
        echo "[INFO] 数据监控任务已存在"
    else
        # 添加到crontab
        (crontab -l 2>/dev/null; echo "$monitoring_cron_entry") | crontab -
        echo "[INFO] 数据监控任务已添加: $monitoring_cron_entry"
    fi
    
    echo "[INFO] 数据监控设置完成"
}

# 移除定时任务
remove_cron_tasks() {
    echo "[INFO] 移除Sage MCP相关的定时任务..."
    
    # 移除包含sage相关的cron任务
    crontab -l 2>/dev/null | grep -v "sage" | crontab - 2>/dev/null || true
    
    echo "[INFO] 定时任务已移除"
}

# 显示监控状态
show_status() {
    echo "=========================================="
    echo "Sage MCP 监控状态"
    echo "=========================================="
    
    # 显示当前cron任务
    echo "[INFO] 当前定时任务:"
    crontab -l 2>/dev/null | grep -i sage || echo "没有找到相关的定时任务"
    echo
    
    # 显示容器状态
    echo "[INFO] 容器状态:"
    if docker ps -q -f name="sage-mcp" | grep -q .; then
        echo "✓ sage-mcp容器正在运行"
        docker ps -f name="sage-mcp" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo "✗ sage-mcp容器未运行"
    fi
    echo
    
    # 显示磁盘使用情况
    echo "[INFO] 磁盘使用情况:"
    df -h . | head -2
    echo
    
    # 显示日志文件大小
    echo "[INFO] 日志文件大小:"
    local log_files=(
        "/var/log/sage_cron.log"
        "/var/log/sage_monitoring.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            local size=$(ls -lah "$log_file" | awk '{print $5}')
            echo "  $log_file: $size"
        else
            echo "  $log_file: 不存在"
        fi
    done
    echo
    
    # 显示最近的监控日志
    echo "[INFO] 最近的监控记录:"
    if [ -f "/var/log/sage_monitoring.log" ]; then
        tail -5 /var/log/sage_monitoring.log
    else
        echo "监控日志文件不存在"
    fi
    
    echo "=========================================="
}

# 创建logrotate配置
setup_logrotate() {
    echo "[INFO] 设置日志轮转..."
    
    local logrotate_config="/etc/logrotate.d/sage-mcp"
    
    # 需要root权限创建logrotate配置
    if [ "$EUID" -eq 0 ]; then
        cat > "$logrotate_config" << EOF
/var/log/sage_*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
        echo "[INFO] Logrotate配置已创建: $logrotate_config"
    else
        echo "[WARN] 需要root权限创建logrotate配置，请手动执行："
        echo "sudo bash -c 'cat > /etc/logrotate.d/sage-mcp << EOF"
        echo "/var/log/sage_*.log {"
        echo "    daily"
        echo "    missingok"
        echo "    rotate 30"
        echo "    compress"
        echo "    delaycompress"
        echo "    notifempty"
        echo "    copytruncate"
        echo "}"
        echo "EOF'"
    fi
}

# 解析命令行参数
parse_arguments() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 0
    fi
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --setup-cron)
                setup_cron_backup
                setup_logrotate
                shift
                ;;
            --setup-monitoring)
                setup_monitoring
                setup_logrotate
                shift
                ;;
            --remove-cron)
                remove_cron_tasks
                shift
                ;;
            --status)
                show_status
                shift
                ;;
            -*)
                error_exit "未知选项: $1"
                ;;
            *)
                error_exit "未知参数: $1"
                ;;
        esac
    done
}

# 主执行流程
main() {
    echo "[INFO] Sage MCP 监控设置工具"
    
    parse_arguments "$@"
    
    echo "[INFO] 监控设置完成"
}

# 执行主流程
main "$@"