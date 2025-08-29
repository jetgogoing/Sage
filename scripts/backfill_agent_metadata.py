#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据回填脚本 - 提取并迁移Agent元数据
用于将metadata中的Agent信息迁移到专用字段
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import asyncpg
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentMetadataBackfiller:
    """Agent元数据回填工具"""
    
    def __init__(self):
        load_dotenv()
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'sage_memory'),
            'user': os.getenv('DB_USER', 'sage'),
            'password': os.getenv('DB_PASSWORD')
        }
        self.conn = None
        
        # Agent报告识别模式
        self.agent_patterns = [
            r'===\s*(?:(.+?)\s+)?Report\s+by\s+@(\w+)\s*===',
            r'===\s*(.+?报告)\s+by\s+@(\w+)\s*===',
            r'Agent\s+Report:\s*(\w+)',
            r'@(\w+)\s+(?:report|completed|finished)',
        ]
        
    async def connect(self):
        """连接数据库"""
        try:
            self.conn = await asyncpg.connect(**self.db_config)
            logger.info("数据库连接成功")
            
            # 检查新字段是否存在
            await self._ensure_columns_exist()
            
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    async def _ensure_columns_exist(self):
        """确保必要的列存在"""
        try:
            # 检查列是否存在
            check_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'memories' 
                AND column_name IN ('is_agent_report', 'agent_metadata')
            """
            
            existing_columns = await self.conn.fetch(check_query)
            existing_names = {row['column_name'] for row in existing_columns}
            
            # 添加缺失的列
            if 'is_agent_report' not in existing_names:
                await self.conn.execute(
                    "ALTER TABLE memories ADD COLUMN is_agent_report BOOLEAN DEFAULT FALSE"
                )
                logger.info("已添加 is_agent_report 列")
                
            if 'agent_metadata' not in existing_names:
                await self.conn.execute(
                    "ALTER TABLE memories ADD COLUMN agent_metadata JSONB"
                )
                logger.info("已添加 agent_metadata 列")
                
        except Exception as e:
            logger.error(f"检查/创建列失败: {e}")
            raise
    
    def detect_agent_report(self, text: str) -> Tuple[bool, Optional[str]]:
        """检测文本是否为Agent报告并提取Agent名称"""
        if not text:
            return False, None
            
        for pattern in self.agent_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                # 提取Agent名称
                groups = match.groups()
                agent_name = groups[-1] if groups else None
                if agent_name:
                    return True, agent_name
                    
        return False, None
    
    def extract_embedded_metadata(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取嵌入的HTML注释元数据"""
        pattern = r'<!--\s*AGENT_METADATA\s+(.*?)\s*-->'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            try:
                metadata_str = match.group(1)
                return json.loads(metadata_str)
            except json.JSONDecodeError:
                logger.warning(f"无法解析嵌入的元数据: {metadata_str[:100]}...")
                
        return None
    
    async def analyze_memories(self):
        """分析现有记忆，识别Agent报告"""
        logger.info("开始分析历史记忆...")
        
        # 查询所有未标记的记忆
        query = """
            SELECT id, user_input, assistant_response, metadata
            FROM memories
            WHERE is_agent_report IS FALSE OR is_agent_report IS NULL
            ORDER BY created_at DESC
        """
        
        records = await self.conn.fetch(query)
        logger.info(f"找到 {len(records)} 条记录需要分析")
        
        agent_reports = []
        
        for record in records:
            # 检查用户输入
            is_agent, agent_name = self.detect_agent_report(record['user_input'] or '')
            
            # 如果用户输入不是，检查助手回复
            if not is_agent:
                is_agent, agent_name = self.detect_agent_report(record['assistant_response'] or '')
            
            # 提取嵌入的元数据
            embedded_meta = None
            if record['assistant_response']:
                embedded_meta = self.extract_embedded_metadata(record['assistant_response'])
            
            # 检查现有metadata
            existing_meta = json.loads(record['metadata']) if record['metadata'] else {}
            
            # 判断是否为Agent报告
            if is_agent or existing_meta.get('is_agent_report') or embedded_meta:
                agent_metadata = embedded_meta or {}
                
                # 从现有metadata中提取Agent信息
                if existing_meta.get('agent_name'):
                    agent_metadata['agent_name'] = existing_meta['agent_name']
                elif agent_name:
                    agent_metadata['agent_name'] = agent_name
                    
                if existing_meta.get('agent_task_id'):
                    agent_metadata['task_id'] = existing_meta['agent_task_id']
                    
                if existing_meta.get('agent_execution_id'):
                    agent_metadata['execution_id'] = existing_meta['agent_execution_id']
                
                agent_reports.append({
                    'id': record['id'],
                    'agent_metadata': agent_metadata,
                    'agent_name': agent_metadata.get('agent_name', 'unknown')
                })
        
        logger.info(f"识别出 {len(agent_reports)} 个Agent报告")
        return agent_reports
    
    async def backfill_agent_data(self, agent_reports):
        """回填Agent数据到新字段"""
        logger.info(f"开始回填 {len(agent_reports)} 条Agent报告...")
        
        success_count = 0
        error_count = 0
        
        for report in agent_reports:
            try:
                update_query = """
                    UPDATE memories
                    SET is_agent_report = TRUE,
                        agent_metadata = $2::jsonb
                    WHERE id = $1
                """
                
                await self.conn.execute(
                    update_query,
                    report['id'],
                    json.dumps(report['agent_metadata'])
                )
                
                success_count += 1
                logger.debug(f"已更新记录 {report['id']} (Agent: {report['agent_name']})")
                
            except Exception as e:
                error_count += 1
                logger.error(f"更新记录 {report['id']} 失败: {e}")
        
        logger.info(f"回填完成: 成功 {success_count}, 失败 {error_count}")
        return success_count, error_count
    
    async def create_indexes(self):
        """创建优化索引"""
        logger.info("创建优化索引...")
        
        indexes = [
            ("idx_memories_is_agent_report", 
             "CREATE INDEX IF NOT EXISTS idx_memories_is_agent_report ON memories (is_agent_report) WHERE is_agent_report = TRUE"),
            
            ("idx_memories_agent_metadata",
             "CREATE INDEX IF NOT EXISTS idx_memories_agent_metadata ON memories USING gin (agent_metadata) WHERE agent_metadata IS NOT NULL"),
            
            ("idx_memories_agent_name",
             "CREATE INDEX IF NOT EXISTS idx_memories_agent_name ON memories ((agent_metadata->>'agent_name')) WHERE agent_metadata IS NOT NULL"),
        ]
        
        for index_name, create_sql in indexes:
            try:
                await self.conn.execute(create_sql)
                logger.info(f"索引 {index_name} 创建成功")
            except Exception as e:
                logger.warning(f"索引 {index_name} 创建失败（可能已存在）: {e}")
    
    async def verify_migration(self):
        """验证迁移结果"""
        logger.info("验证迁移结果...")
        
        # 统计Agent报告
        stats_query = """
            SELECT 
                COUNT(*) FILTER (WHERE is_agent_report = TRUE) as agent_reports,
                COUNT(*) FILTER (WHERE agent_metadata IS NOT NULL) as with_metadata,
                COUNT(DISTINCT agent_metadata->>'agent_name') as unique_agents,
                COUNT(*) as total_memories
            FROM memories
        """
        
        stats = await self.conn.fetchrow(stats_query)
        
        logger.info(f"""
        迁移验证结果:
        - 总记忆数: {stats['total_memories']}
        - Agent报告数: {stats['agent_reports']}
        - 包含元数据: {stats['with_metadata']}
        - 唯一Agent数: {stats['unique_agents']}
        """)
        
        # 显示Agent分布
        if stats['unique_agents'] > 0:
            agent_dist_query = """
                SELECT 
                    agent_metadata->>'agent_name' as agent_name,
                    COUNT(*) as report_count
                FROM memories
                WHERE agent_metadata IS NOT NULL
                GROUP BY agent_metadata->>'agent_name'
                ORDER BY report_count DESC
                LIMIT 10
            """
            
            distributions = await self.conn.fetch(agent_dist_query)
            
            logger.info("Agent报告分布 (Top 10):")
            for dist in distributions:
                logger.info(f"  - {dist['agent_name']}: {dist['report_count']} 条")
    
    async def run(self):
        """执行完整的回填流程"""
        try:
            # 连接数据库
            await self.connect()
            
            # 分析历史记忆
            agent_reports = await self.analyze_memories()
            
            if agent_reports:
                # 执行回填
                success, errors = await self.backfill_agent_data(agent_reports)
                
                # 创建索引
                await self.create_indexes()
                
                # 验证结果
                await self.verify_migration()
                
                logger.info(f"历史数据回填完成！成功: {success}, 失败: {errors}")
            else:
                logger.info("没有发现需要回填的Agent报告")
                
        except Exception as e:
            logger.error(f"回填过程出错: {e}")
            raise
            
        finally:
            if self.conn:
                await self.conn.close()
                logger.info("数据库连接已关闭")


async def main():
    """主函数"""
    backfiller = AgentMetadataBackfiller()
    await backfiller.run()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║          Sage Agent元数据历史数据回填工具                   ║
    ║                                                          ║
    ║  功能：                                                   ║
    ║  1. 识别历史记忆中的Agent报告                              ║
    ║  2. 提取Agent元数据到专用字段                              ║
    ║  3. 创建优化索引提升查询性能                               ║
    ║  4. 验证迁移结果                                         ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())