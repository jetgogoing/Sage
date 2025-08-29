-- 修复Agent相关函数和触发器

-- 1. 创建函数：获取Agent执行历史
DROP FUNCTION IF EXISTS get_agent_execution_history(TEXT, TEXT, INTEGER);
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

-- 2. 创建触发器函数：自动检测Agent报告
DROP FUNCTION IF EXISTS auto_detect_agent_report() CASCADE;
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

-- 3. 创建触发器
DROP TRIGGER IF EXISTS trg_auto_detect_agent_report ON memories;
CREATE TRIGGER trg_auto_detect_agent_report
BEFORE INSERT OR UPDATE ON memories
FOR EACH ROW
EXECUTE FUNCTION auto_detect_agent_report();

-- 4. 验证函数创建成功
SELECT 'Functions created successfully' AS status;

-- 测试函数
SELECT * FROM get_agent_execution_history() LIMIT 5;