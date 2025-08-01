#!/bin/bash
# Sage Persistence Daemon 管理脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_SCRIPT="$PROJECT_DIR/sage_persistence_daemon.py"
PID_FILE="/tmp/sage_daemon.pid"
LOG_FILE="/tmp/sage_daemon.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误：未找到 python3${NC}"
        exit 1
    fi
}

# 启动守护进程
start_daemon() {
    echo "正在启动 Sage Persistence Daemon..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${YELLOW}守护进程已在运行 (PID: $PID)${NC}"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    # 启动守护进程
    cd "$PROJECT_DIR"
    nohup python3 "$DAEMON_SCRIPT" > "$LOG_FILE" 2>&1 &
    
    # 等待启动
    sleep 2
    
    # 检查是否启动成功
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GREEN}守护进程启动成功 (PID: $PID)${NC}"
            echo "日志文件: $LOG_FILE"
            return 0
        fi
    fi
    
    echo -e "${RED}守护进程启动失败${NC}"
    echo "请查看日志: $LOG_FILE"
    return 1
}

# 停止守护进程
stop_daemon() {
    echo "正在停止 Sage Persistence Daemon..."
    
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}守护进程未运行${NC}"
        return 0
    fi
    
    PID=$(cat "$PID_FILE")
    
    if kill -0 "$PID" 2>/dev/null; then
        kill -TERM "$PID"
        
        # 等待进程退出
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                echo -e "${GREEN}守护进程已停止${NC}"
                rm -f "$PID_FILE"
                return 0
            fi
            sleep 1
        done
        
        # 强制终止
        echo -e "${YELLOW}正在强制终止...${NC}"
        kill -9 "$PID" 2>/dev/null
        rm -f "$PID_FILE"
    else
        echo -e "${YELLOW}进程不存在，清理 PID 文件${NC}"
        rm -f "$PID_FILE"
    fi
    
    return 0
}

# 重启守护进程
restart_daemon() {
    stop_daemon
    sleep 1
    start_daemon
}

# 查看状态
status_daemon() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${RED}守护进程未运行${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}守护进程运行中 (PID: $PID)${NC}"
        
        # 调用客户端获取详细状态
        cd "$PROJECT_DIR"
        python3 -c "
import sys
sys.path.insert(0, '.')
from sage_client import SageClient
try:
    with SageClient(timeout=5.0) as client:
        status = client.get_status()
        if status.get('status') == 'ok':
            daemon = status.get('daemon', {})
            print(f\"运行时间: {daemon.get('uptime', 0):.1f} 秒\")
            print(f\"总请求数: {daemon.get('total_requests', 0)}\")
            print(f\"Socket 路径: {daemon.get('socket_path', 'unknown')}\")
except Exception as e:
    print(f\"获取状态失败: {e}\")
"
        return 0
    else:
        echo -e "${RED}进程不存在，但 PID 文件存在${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 查看日志
view_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}日志文件不存在: $LOG_FILE${NC}"
    fi
}

# 主函数
main() {
    check_python
    
    case "$1" in
        start)
            start_daemon
            ;;
        stop)
            stop_daemon
            ;;
        restart)
            restart_daemon
            ;;
        status)
            status_daemon
            ;;
        logs)
            view_logs
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs}"
            echo ""
            echo "命令说明:"
            echo "  start   - 启动守护进程"
            echo "  stop    - 停止守护进程"
            echo "  restart - 重启守护进程"
            echo "  status  - 查看运行状态"
            echo "  logs    - 查看实时日志"
            exit 1
            ;;
    esac
}

main "$@"