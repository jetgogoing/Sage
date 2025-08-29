#!/bin/bash
# Sage MCP 数据恢复脚本
# 从备份文件恢复PostgreSQL数据库

set -euo pipefail

# 配置参数
CONTAINER_NAME="sage-mcp"
DB_NAME="${DB_NAME:-sage_memory}"
DB_USER="${DB_USER:-sage}"
BACKUP_DIR="./backups"

# 错误处理函数
error_exit() {
    echo "[ERROR] $1" >&2
    exit 1
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项] <备份文件>

选项:
  -h, --help          显示此帮助信息
  -f, --force         强制恢复（不确认）
  -c, --container     指定容器名称 (默认: ${CONTAINER_NAME})
  -d, --database      指定数据库名称 (默认: ${DB_NAME})
  -u, --user          指定数据库用户 (默认: ${DB_USER})

示例:
  $0 backups/sage_backup_20250725_143022.sql
  $0 -f backups/sage_backup_20250725_143022.sql.custom
  $0 --container my-sage --database my_db backup.sql

备份文件格式:
  - .sql 文件: SQL文本格式
  - .sql.custom 文件: PostgreSQL自定义格式
EOF
}

# 解析命令行参数
parse_arguments() {
    FORCE_RESTORE=false
    BACKUP_FILE=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--force)
                FORCE_RESTORE=true
                shift
                ;;
            -c|--container)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            -d|--database)
                DB_NAME="$2"
                shift 2
                ;;
            -u|--user)
                DB_USER="$2"
                shift 2
                ;;
            -*)
                error_exit "未知选项: $1"
                ;;
            *)
                if [ -z "$BACKUP_FILE" ]; then
                    BACKUP_FILE="$1"
                else
                    error_exit "只能指定一个备份文件"
                fi
                shift
                ;;
        esac
    done
    
    if [ -z "$BACKUP_FILE" ]; then
        echo "[ERROR] 请指定备份文件"
        echo
        show_usage
        exit 1
    fi
}

# 检查备份文件
check_backup_file() {
    echo "[INFO] 检查备份文件..."
    
    if [ ! -f "$BACKUP_FILE" ]; then
        error_exit "备份文件不存在: $BACKUP_FILE"
    fi
    
    if [ ! -r "$BACKUP_FILE" ]; then
        error_exit "备份文件不可读: $BACKUP_FILE"
    fi
    
    if [ ! -s "$BACKUP_FILE" ]; then
        error_exit "备份文件为空: $BACKUP_FILE"
    fi
    
    # 检查文件格式
    if [[ "$BACKUP_FILE" == *.custom ]]; then
        BACKUP_FORMAT="custom"
        echo "[INFO] 检测到PostgreSQL自定义格式备份"
    elif [[ "$BACKUP_FILE" == *.sql ]]; then
        BACKUP_FORMAT="plain"
        echo "[INFO] 检测到SQL文本格式备份"
        # 验证SQL文件内容
        if ! grep -q "CREATE TABLE\|INSERT INTO\|COPY" "$BACKUP_FILE"; then
            error_exit "SQL备份文件格式无效，缺少表结构或数据"
        fi
    else
        error_exit "不支持的备份文件格式。支持: .sql 或 .sql.custom"
    fi
    
    echo "[INFO] 备份文件检查通过"
}

# 检查Docker容器状态
check_container() {
    echo "[INFO] 检查容器状态..."
    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        error_exit "容器 ${CONTAINER_NAME} 未运行"
    fi
    echo "[INFO] 容器状态正常"
}

# 检查数据库连接
check_database() {
    echo "[INFO] 检查数据库连接..."
    docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" || \
        error_exit "数据库连接失败"
    echo "[INFO] 数据库连接正常"
}

# 获取当前数据库统计
get_database_stats() {
    echo "[INFO] 获取当前数据库统计..."
    docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
        SELECT 
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_rows
        FROM pg_stat_user_tables;
    " 2>/dev/null || echo "无法获取数据库统计信息"
}

# 用户确认
confirm_restore() {
    if [ "$FORCE_RESTORE" = true ]; then
        echo "[INFO] 强制模式，跳过确认"
        return 0
    fi
    
    echo
    echo "=========================================="
    echo "警告: 数据恢复操作将会："
    echo "1. 清空当前数据库中的所有数据"
    echo "2. 恢复备份文件中的数据"
    echo "3. 此操作不可逆转"
    echo
    echo "备份文件: $BACKUP_FILE"
    echo "目标容器: $CONTAINER_NAME"
    echo "目标数据库: $DB_NAME"
    echo "=========================================="
    echo
    
    read -p "确定要继续吗? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "[INFO] 恢复操作已取消"
        exit 0
    fi
}

# 备份当前数据（安全措施）
backup_current_data() {
    echo "[INFO] 创建当前数据的安全备份..."
    
    local safety_backup_dir="${BACKUP_DIR}/safety_backups"
    mkdir -p "$safety_backup_dir"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local safety_backup_file="${safety_backup_dir}/pre_restore_backup_${timestamp}.sql"
    
    docker exec "${CONTAINER_NAME}" pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --no-owner \
        --no-privileges \
        > "$safety_backup_file" 2>/dev/null || {
        echo "[WARN] 安全备份创建失败，但继续恢复过程"
        return 0
    }
    
    echo "[INFO] 安全备份已创建: $safety_backup_file"
}

# 清空数据库
clean_database() {
    echo "[INFO] 清空目标数据库..."
    
    # 获取所有表名并删除
    docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
        DO \$\$ 
        DECLARE
            rec RECORD;
        BEGIN
            -- 删除所有外键约束
            FOR rec IN (SELECT conname FROM pg_constraint WHERE contype = 'f') 
            LOOP
                EXECUTE 'ALTER TABLE ' || quote_ident(rec.conname) || ' DROP CONSTRAINT IF EXISTS ' || quote_ident(rec.conname) || ' CASCADE';
            END LOOP;
            
            -- 删除所有表
            FOR rec IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
            LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(rec.tablename) || ' CASCADE';
            END LOOP;
            
            -- 删除所有序列
            FOR rec IN (SELECT sequencename FROM pg_sequences WHERE schemaname = 'public')
            LOOP
                EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(rec.sequencename) || ' CASCADE';
            END LOOP;
            
            -- 删除所有函数
            FOR rec IN (SELECT proname FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public'))
            LOOP
                EXECUTE 'DROP FUNCTION IF EXISTS ' || quote_ident(rec.proname) || ' CASCADE';
            END LOOP;
        END \$\$;
    " || error_exit "清空数据库失败"
    
    echo "[INFO] 数据库清空完成"
}

# 执行数据恢复
perform_restore() {
    echo "[INFO] 开始数据恢复..."
    
    if [ "$BACKUP_FORMAT" = "custom" ]; then
        # 使用pg_restore恢复自定义格式
        echo "[INFO] 使用pg_restore恢复自定义格式备份..."
        docker exec -i "${CONTAINER_NAME}" pg_restore \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --verbose \
            --clean \
            --no-owner \
            --no-privileges \
            < "$BACKUP_FILE" || error_exit "自定义格式恢复失败"
    else
        # 使用psql恢复SQL格式
        echo "[INFO] 使用psql恢复SQL格式备份..."
        docker exec -i "${CONTAINER_NAME}" psql \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            < "$BACKUP_FILE" || error_exit "SQL格式恢复失败"
    fi
    
    echo "[INFO] 数据恢复完成"
}

# 验证恢复结果
verify_restore() {
    echo "[INFO] 验证恢复结果..."
    
    # 检查表是否存在
    local table_count=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$table_count" -eq 0 ]; then
        error_exit "恢复验证失败：没有找到任何表"
    fi
    
    echo "[INFO] 发现 $table_count 个表"
    
    # 检查关键表
    for table in "memories" "sessions"; do
        local exists=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = '$table'
            );
        " 2>/dev/null | tr -d ' \n' || echo "f")
        
        if [ "$exists" = "t" ]; then
            echo "[INFO] 表 '$table' 恢复成功"
        else
            echo "[WARN] 表 '$table' 未找到"
        fi
    done
    
    # 获取恢复后的统计信息
    echo "[INFO] 恢复后数据库统计："
    get_database_stats
    
    echo "[INFO] 恢复验证完成"
}

# 生成恢复报告
generate_report() {
    echo "[INFO] 生成恢复报告..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${BACKUP_DIR}/restore_report_${timestamp}.txt"
    
    cat > "$report_file" << EOF
Sage MCP 数据恢复报告
====================

恢复时间: $(date)
备份文件: $BACKUP_FILE
备份格式: $BACKUP_FORMAT
容器名称: $CONTAINER_NAME
数据库名: $DB_NAME
数据库用户: $DB_USER

恢复统计:
$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows
FROM pg_stat_user_tables;" 2>/dev/null || echo "无法获取统计信息")

恢复状态: 成功
EOF
    
    echo "[INFO] 恢复报告已生成: $report_file"
}

# 主执行流程
main() {
    echo "[INFO] Sage MCP 数据恢复开始..."
    
    parse_arguments "$@"
    check_backup_file
    check_container
    check_database
    
    echo "[INFO] 恢复前数据库状态："
    get_database_stats
    
    confirm_restore
    backup_current_data
    clean_database
    perform_restore
    verify_restore
    generate_report
    
    echo "[INFO] ====================================="
    echo "[INFO] 数据恢复完成!"
    echo "[INFO] 备份文件: $BACKUP_FILE"
    echo "[INFO] 目标数据库: $DB_NAME"
    echo "[INFO] ====================================="
}

# 执行主流程
main "$@"