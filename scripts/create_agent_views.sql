-- 创建Agent相关视图

-- 1. Agent报告统计视图
DROP VIEW IF EXISTS agent_reports_summary;
CREATE OR REPLACE VIEW agent_reports_summary AS
SELECT 
    agent_metadata->>'agent_name' AS agent_name,
    COUNT(*) AS report_count,
    AVG((agent_metadata->>'quality_score')::NUMERIC) AS avg_quality_score,
    SUM((agent_metadata->>'error_count')::INTEGER) AS total_errors,
    SUM((agent_metadata->>'warning_count')::INTEGER) AS total_warnings,
    MAX(created_at) AS last_report_time,
    MIN(created_at) AS first_report_time
FROM memories
WHERE is_agent_report = TRUE
  AND agent_metadata IS NOT NULL
GROUP BY agent_metadata->>'agent_name';

-- 2. 验证视图创建成功
SELECT 'Views created successfully' AS status;

-- 测试视图
SELECT * FROM agent_reports_summary;