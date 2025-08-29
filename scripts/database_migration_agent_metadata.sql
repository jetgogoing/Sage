-- Sage数据库Schema升级脚本
-- 目的：添加Agent元数据支持
-- 执行时间：2025-08-10
-- 版本：1.0.0

-- 开始事务
BEGIN;

-- 1. 添加Agent相关字段到memories表
ALTER TABLE memories 
ADD COLUMN IF NOT EXISTS is_agent_report BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS agent_metadata JSONB;

-- 2. 创建索引以优化Agent报告查询
CREATE INDEX IF NOT EXISTS idx_memories_is_agent_report 
ON memories (is_agent_report) 
WHERE is_agent_report = TRUE;

-- 3. 为agent_metadata创建GIN索引以支持JSONB查询
CREATE INDEX IF NOT EXISTS idx_memories_agent_metadata 
ON memories USING gin (agent_metadata) 
WHERE agent_metadata IS NOT NULL;

-- 4. 创建复合索引优化按Agent名称查询
CREATE INDEX IF NOT EXISTS idx_memories_agent_name 
ON memories ((agent_metadata->>'agent_name')) 
WHERE agent_metadata IS NOT NULL;

-- 5. 创建复合索引优化按任务ID查询
CREATE INDEX IF NOT EXISTS idx_memories_task_id 
ON memories ((agent_metadata->>'task_id')) 
WHERE agent_metadata IS NOT NULL;

-- 6. 创建Agent报告统计视图
CREATE OR REPLACE VIEW agent_reports_summary AS
SELECT 
    agent_metadata->>'agent_name' AS agent_name,
    COUNT(*) AS report_count,
    AVG((agent_metadata->>'quality_score')::NUMERIC) AS avg_quality_score,
    SUM((agent_metadata->>'error_count')::INTEGER) AS total_errors,
    SUM((agent_metadata->>'warning_count')::INTEGER) AS total_warnings,
    MIN(created_at) AS first_report,
    MAX(created_at) AS last_report
FROM memories
WHERE is_agent_report = TRUE 
  AND agent_metadata IS NOT NULL
GROUP BY agent_metadata->>'agent_name';

-- 7. 创建函数：获取Agent执行历史
CREATE OR REPLACE FUNCTION get_agent_execution_history(
    p_agent_name TEXT DEFAULT NULL,
    p_task_id TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    memory_id UUID,
    agent_name TEXT,
    task_id TEXT,
    execution_id TEXT,
    quality_score NUMERIC,
    error_count INTEGER,
    warning_count INTEGER,
    created_at TIMESTAMPTZ,
    user_input TEXT,
    assistant_response TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id AS memory_id,
        m.agent_metadata->>'agent_name' AS agent_name,
        m.agent_metadata->>'task_id' AS task_id,
        m.agent_metadata->>'execution_id' AS execution_id,
        (m.agent_metadata->>'quality_score')::NUMERIC AS quality_score,
        (m.agent_metadata->>'error_count')::INTEGER AS error_count,
        (m.agent_metadata->>'warning_count')::INTEGER AS warning_count,
        m.created_at,
        m.user_input,
        m.assistant_response
    FROM memories m
    WHERE m.is_agent_report = TRUE
      AND (p_agent_name IS NULL OR m.agent_metadata->>'agent_name' = p_agent_name)
      AND (p_task_id IS NULL OR m.agent_metadata->>'task_id' = p_task_id)
    ORDER BY m.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 8. 创建触发器：自动标记Agent报告
CREATE OR REPLACE FUNCTION auto_detect_agent_report()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果metadata中包含agent相关信息，自动设置is_agent_report
    IF NEW.metadata ? 'is_agent_report' AND 
       (NEW.metadata->>'is_agent_report')::BOOLEAN = TRUE THEN
        NEW.is_agent_report := TRUE;
        
        -- 如果metadata中有嵌套的agent_metadata，提取到专用字段
        IF NEW.metadata ? 'agent_metadata' THEN
            NEW.agent_metadata := NEW.metadata->'agent_metadata';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_detect_agent_report
BEFORE INSERT OR UPDATE ON memories
FOR EACH ROW
EXECUTE FUNCTION auto_detect_agent_report();

-- 9. 数据迁移：从现有metadata中提取Agent信息
UPDATE memories
SET 
    is_agent_report = TRUE,
    agent_metadata = metadata->'agent_metadata'
WHERE metadata ? 'is_agent_report' 
  AND (metadata->>'is_agent_report')::BOOLEAN = TRUE
  AND agent_metadata IS NULL;

-- 10. 添加注释说明
COMMENT ON COLUMN memories.is_agent_report IS 'Agent报告标识，TRUE表示此记录为Agent执行报告';
COMMENT ON COLUMN memories.agent_metadata IS 'Agent特定元数据，包含agent_name, task_id, execution_id, performance_metrics等';
COMMENT ON VIEW agent_reports_summary IS 'Agent报告汇总视图，提供各Agent的执行统计';
COMMENT ON FUNCTION get_agent_execution_history IS '获取Agent执行历史记录，支持按Agent名称和任务ID过滤';

-- 提交事务
COMMIT;

-- 验证迁移结果
SELECT 
    'Migration completed successfully!' AS status,
    COUNT(*) FILTER (WHERE is_agent_report = TRUE) AS agent_reports,
    COUNT(*) FILTER (WHERE agent_metadata IS NOT NULL) AS with_metadata
FROM memories;