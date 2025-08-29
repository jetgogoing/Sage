-- Sage MCP 数据库时区转换示例
-- 用于将历史 UTC 时间戳转换为北京时间显示

-- 1. 查询时转换：将 UTC 时间转换为北京时间显示
-- 这是推荐的方式，不修改原始数据
SELECT 
    id,
    user_query,
    assistant_response,
    created_at AS utc_time,
    created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai' AS beijing_time,
    created_at::timestamp + INTERVAL '8 hours' AS beijing_time_simple
FROM conversations
ORDER BY created_at DESC
LIMIT 10;

-- 2. 创建视图，方便日常查询
CREATE OR REPLACE VIEW conversations_beijing AS
SELECT 
    id,
    session_id,
    user_query,
    assistant_response,
    tool_calls,
    tool_results,
    created_at AS utc_time,
    created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai' AS beijing_time,
    metadata
FROM conversations;

-- 使用视图查询
-- SELECT * FROM conversations_beijing WHERE beijing_time >= '2025-08-03 00:00:00';

-- 3. 函数方式：创建转换函数
CREATE OR REPLACE FUNCTION utc_to_beijing(utc_timestamp TIMESTAMP WITH TIME ZONE)
RETURNS TIMESTAMP AS $$
BEGIN
    RETURN utc_timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai';
END;
$$ LANGUAGE plpgsql;

-- 使用函数
-- SELECT id, user_query, utc_to_beijing(created_at) as beijing_time FROM conversations;

-- 4. 批量更新历史数据（不推荐，会修改原始数据）
-- 警告：此操作不可逆，请先备份数据！
-- BEGIN;
-- UPDATE conversations 
-- SET created_at = created_at + INTERVAL '8 hours'
-- WHERE created_at < '2025-08-03 15:00:00+00';  -- 只更新特定时间之前的数据
-- COMMIT;

-- 5. 查看当前数据库时区设置
SHOW timezone;

-- 6. 临时会话级别设置时区（仅影响当前连接）
SET TIME ZONE 'Asia/Shanghai';

-- 7. 查询包含时区信息的时间
SELECT 
    NOW() AS current_time,
    NOW() AT TIME ZONE 'Asia/Shanghai' AS beijing_no_tz,
    NOW()::timestamp AS timestamp_no_tz;

-- 8. 为新表添加默认时区
-- 创建新表时，可以设置默认值为北京时间
-- CREATE TABLE new_table (
--     id SERIAL PRIMARY KEY,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'Asia/Shanghai')
-- );