-- Sage数据库性能优化配置
-- 适用于PostgreSQL 15 + pgvector

-- 1. 创建优化的向量索引（使用IVF索引替代默认的HNSW）
-- IVF索引在插入性能上比HNSW快40%，适合写多读少的场景
DROP INDEX IF EXISTS memories_embedding_idx;
CREATE INDEX memories_embedding_idx ON memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);  -- lists参数对应SAGE_VECTOR_INDEX_LISTS

-- 2. 设置搜索参数
ALTER DATABASE sage_memory SET ivfflat.probes = 10;  -- 对应SAGE_VECTOR_PROBES

-- 3. 优化连接池参数
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '16MB';

-- 4. 优化检查点和写入性能
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;  -- SSD优化

-- 5. 启用并行查询
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET max_parallel_maintenance_workers = 4;

-- 6. 创建部分索引（仅索引高相似度记忆）
CREATE INDEX memories_high_similarity_idx 
ON memories (similarity) 
WHERE similarity > 0.5;

-- 7. 创建复合索引（加速会话查询）
CREATE INDEX memories_session_created_idx 
ON memories (session_id, created_at DESC);

-- 8. 添加统计信息自动更新
ALTER TABLE memories SET (autovacuum_analyze_scale_factor = 0.05);
ALTER TABLE memories SET (autovacuum_vacuum_scale_factor = 0.1);

-- 9. 创建物化视图缓存热门查询
CREATE MATERIALIZED VIEW recent_memories_cache AS
SELECT 
    id, 
    user_prompt, 
    assistant_response, 
    embedding,
    created_at,
    session_id
FROM memories
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- 创建自动刷新触发器
CREATE OR REPLACE FUNCTION refresh_recent_memories_cache()
RETURNS trigger AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY recent_memories_cache;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER refresh_cache_trigger
AFTER INSERT OR UPDATE OR DELETE ON memories
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_recent_memories_cache();

-- 10. 分区表设置（适用于大数据量）
-- 按月分区存储历史记忆
CREATE TABLE memories_partitioned (
    LIKE memories INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 创建分区示例
CREATE TABLE memories_2025_08 PARTITION OF memories_partitioned
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

-- 重要：执行后需要重启PostgreSQL
-- docker restart sage-db
-- 或者执行 SELECT pg_reload_conf(); 热加载部分配置