-- 为memories表的content_hash添加索引以提高去重查询性能
-- 使用GIN索引以支持JSONB字段的高效查询

-- 创建部分索引，只索引包含content_hash的记录
CREATE INDEX IF NOT EXISTS idx_memories_content_hash 
ON memories ((metadata->>'content_hash')) 
WHERE metadata->>'content_hash' IS NOT NULL;

-- 添加复合索引以优化去重查询
CREATE INDEX IF NOT EXISTS idx_memories_session_content_hash 
ON memories (session_id, (metadata->>'content_hash')) 
WHERE metadata->>'content_hash' IS NOT NULL;