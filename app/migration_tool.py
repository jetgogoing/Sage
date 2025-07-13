#!/usr/bin/env python3
"""
Sage MCP 数据库迁移工具
支持数据备份、迁移、验证和恢复功能
"""

import asyncio
import json
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

# 添加项目路径以导入配置
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import get_config_manager, DatabaseConfig
from memory_interface import get_memory_provider

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigration:
    """数据库迁移工具主类"""
    
    def __init__(self, config_manager=None):
        """初始化迁移工具"""
        self.config_manager = config_manager or get_config_manager()
        self.db_config = self.config_manager.config.db_config
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # 迁移版本管理
        self.migration_version = "1.0"
        self.supported_schemas = ["1.0", "0.9", "legacy"]
        
    async def get_db_connection(self, db_config: DatabaseConfig = None) -> asyncpg.Connection:
        """获取数据库连接"""
        config = db_config or self.db_config
        
        try:
            conn = await asyncpg.connect(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password
            )
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def get_sync_db_connection(self, db_config: DatabaseConfig = None) -> psycopg2.extensions.connection:
        """获取同步数据库连接（用于备份）"""
        config = db_config or self.db_config
        
        try:
            conn = psycopg2.connect(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password
            )
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    async def check_database_structure(self) -> Dict[str, Any]:
        """检查数据库结构"""
        conn = await self.get_db_connection()
        
        try:
            # 检查表结构
            tables_info = {}
            
            # 检查conversations表
            conversations_query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'conversations'
            ORDER BY ordinal_position;
            """
            
            result = await conn.fetch(conversations_query)
            tables_info['conversations'] = [dict(row) for row in result]
            
            # 检查索引
            indexes_query = """
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'conversations';
            """
            
            result = await conn.fetch(indexes_query)
            tables_info['indexes'] = [dict(row) for row in result]
            
            # 检查扩展
            extensions_query = """
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname = 'vector';
            """
            
            result = await conn.fetch(extensions_query)
            tables_info['extensions'] = [dict(row) for row in result]
            
            # 检查数据统计
            stats_query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT session_id) as unique_sessions,
                MIN(created_at) as earliest_record,
                MAX(created_at) as latest_record,
                COUNT(embedding) as records_with_embeddings
            FROM conversations;
            """
            
            result = await conn.fetchrow(stats_query)
            tables_info['statistics'] = dict(result) if result else {}
            
            return tables_info
            
        finally:
            await conn.close()
    
    def backup_database(self, backup_name: str = None) -> str:
        """备份数据库数据"""
        if not backup_name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"sage_backup_{timestamp}"
        
        backup_path = self.backup_dir / f"{backup_name}.json"
        
        logger.info(f"开始备份数据库到: {backup_path}")
        
        conn = self.get_sync_db_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 备份conversations表数据
                cursor.execute("""
                    SELECT 
                        id, session_id, turn_id, role, content,
                        embedding::text as embedding_text,
                        created_at
                    FROM conversations 
                    ORDER BY id
                """)
                
                conversations = []
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    # 处理embedding向量
                    if row_dict['embedding_text']:
                        # 解析向量文本格式 [1,2,3,...] 
                        embedding_str = row_dict['embedding_text'].strip('[]')
                        if embedding_str:
                            row_dict['embedding'] = [float(x) for x in embedding_str.split(',')]
                        else:
                            row_dict['embedding'] = None
                    else:
                        row_dict['embedding'] = None
                    
                    del row_dict['embedding_text']
                    
                    # 处理时间格式
                    if row_dict['created_at']:
                        row_dict['created_at'] = row_dict['created_at'].isoformat()
                    
                    conversations.append(row_dict)
                
                # 创建备份数据结构
                backup_data = {
                    'metadata': {
                        'backup_time': datetime.now().isoformat(),
                        'backup_version': self.migration_version,
                        'source_db': {
                            'host': self.db_config.host,
                            'database': self.db_config.database,
                            'user': self.db_config.user
                        },
                        'total_records': len(conversations)
                    },
                    'schema': {
                        'conversations': {
                            'columns': [
                                'id', 'session_id', 'turn_id', 'role', 'content',
                                'embedding', 'created_at'
                            ],
                            'embedding_dimension': 4096
                        }
                    },
                    'data': {
                        'conversations': conversations
                    }
                }
                
                # 保存备份文件
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"备份完成: {len(conversations)} 条记录已保存到 {backup_path}")
                return str(backup_path)
                
        except Exception as e:
            logger.error(f"备份失败: {e}")
            raise
        finally:
            conn.close()
    
    async def migrate_data(self, source_config: DatabaseConfig, target_config: DatabaseConfig = None) -> bool:
        """迁移数据到新环境"""
        target_config = target_config or self.db_config
        
        logger.info(f"开始数据迁移: {source_config.host}:{source_config.database} -> {target_config.host}:{target_config.database}")
        
        # 先备份源数据
        backup_path = self.backup_database(f"pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        try:
            # 连接源数据库
            source_conn = await self.get_db_connection(source_config)
            target_conn = await self.get_db_connection(target_config)
            
            try:
                # 检查目标数据库结构
                await self._ensure_target_schema(target_conn)
                
                # 获取源数据
                source_data = await source_conn.fetch("""
                    SELECT 
                        session_id, turn_id, role, content, embedding, created_at
                    FROM conversations 
                    ORDER BY created_at
                """)
                
                logger.info(f"找到 {len(source_data)} 条记录需要迁移")
                
                # 批量插入目标数据库
                batch_size = 100
                migrated_count = 0
                
                for i in range(0, len(source_data), batch_size):
                    batch = source_data[i:i + batch_size]
                    
                    await target_conn.executemany("""
                        INSERT INTO conversations (session_id, turn_id, role, content, embedding, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT DO NOTHING
                    """, [
                        (
                            row['session_id'], row['turn_id'], row['role'], 
                            row['content'], row['embedding'], row['created_at']
                        ) for row in batch
                    ])
                    
                    migrated_count += len(batch)
                    logger.info(f"已迁移 {migrated_count}/{len(source_data)} 条记录")
                
                logger.info("数据迁移完成")
                return True
                
            finally:
                await source_conn.close()
                await target_conn.close()
                
        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            logger.info(f"可以使用备份文件恢复: {backup_path}")
            return False
    
    async def _ensure_target_schema(self, conn: asyncpg.Connection):
        """确保目标数据库有正确的schema"""
        # 启用pgvector扩展
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # 创建表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id UUID DEFAULT gen_random_uuid(),
                turn_id INT NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR(4096),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 创建索引
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_embedding 
            ON conversations USING ivfflat (embedding vector_cosine_ops);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
            ON conversations (created_at DESC);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_session_id 
            ON conversations (session_id);
        """)
    
    async def restore_from_backup(self, backup_path: str, target_config: DatabaseConfig = None) -> bool:
        """从备份文件恢复数据"""
        target_config = target_config or self.db_config
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        logger.info(f"开始从备份恢复数据: {backup_path}")
        
        try:
            # 读取备份数据
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            conn = await self.get_db_connection(target_config)
            
            try:
                # 确保schema正确
                await self._ensure_target_schema(conn)
                
                # 清空现有数据（谨慎操作）
                logger.warning("即将清空目标数据库的conversations表")
                await conn.execute("TRUNCATE TABLE conversations RESTART IDENTITY;")
                
                # 恢复数据
                conversations = backup_data['data']['conversations']
                logger.info(f"开始恢复 {len(conversations)} 条记录")
                
                batch_size = 100
                restored_count = 0
                
                for i in range(0, len(conversations), batch_size):
                    batch = conversations[i:i + batch_size]
                    
                    values = []
                    for record in batch:
                        embedding = record['embedding']
                        if embedding:
                            # 确保embedding是正确的向量格式
                            if len(embedding) == 4096:
                                embedding_vector = embedding
                            else:
                                logger.warning(f"记录 {record['id']} 的embedding维度不正确: {len(embedding)}")
                                embedding_vector = None
                        else:
                            embedding_vector = None
                        
                        values.append((
                            record['session_id'],
                            record['turn_id'], 
                            record['role'],
                            record['content'],
                            embedding_vector,
                            record['created_at']
                        ))
                    
                    await conn.executemany("""
                        INSERT INTO conversations (session_id, turn_id, role, content, embedding, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, values)
                    
                    restored_count += len(batch)
                    logger.info(f"已恢复 {restored_count}/{len(conversations)} 条记录")
                
                logger.info("数据恢复完成")
                return True
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"数据恢复失败: {e}")
            return False
    
    async def verify_migration(self, source_config: DatabaseConfig = None, target_config: DatabaseConfig = None) -> Dict[str, Any]:
        """验证迁移完整性"""
        source_config = source_config or self.db_config
        target_config = target_config or self.db_config
        
        logger.info("开始验证迁移完整性")
        
        verification_result = {
            'status': 'success',
            'issues': [],
            'statistics': {},
            'recommendations': []
        }
        
        try:
            source_conn = await self.get_db_connection(source_config)
            target_conn = await self.get_db_connection(target_config)
            
            try:
                # 检查记录数量
                source_count = await source_conn.fetchval("SELECT COUNT(*) FROM conversations")
                target_count = await target_conn.fetchval("SELECT COUNT(*) FROM conversations")
                
                verification_result['statistics']['source_count'] = source_count
                verification_result['statistics']['target_count'] = target_count
                
                if source_count != target_count:
                    verification_result['issues'].append(
                        f"记录数量不匹配: 源 {source_count}, 目标 {target_count}"
                    )
                    verification_result['status'] = 'warning'
                
                # 检查embedding维度
                target_embedding_check = await target_conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(embedding) as with_embedding,
                        COUNT(CASE WHEN array_length(embedding::float[], 1) = 4096 THEN 1 END) as correct_dimension
                    FROM conversations
                    WHERE embedding IS NOT NULL
                """)
                
                if target_embedding_check:
                    stats = dict(target_embedding_check)
                    verification_result['statistics']['embedding_stats'] = stats
                    
                    if stats['with_embedding'] != stats['correct_dimension']:
                        verification_result['issues'].append(
                            f"向量维度问题: {stats['with_embedding']} 个向量中只有 {stats['correct_dimension']} 个是4096维"
                        )
                        verification_result['status'] = 'error'
                
                # 检查索引
                indexes = await target_conn.fetch("""
                    SELECT indexname FROM pg_indexes WHERE tablename = 'conversations'
                """)
                
                index_names = [row['indexname'] for row in indexes]
                required_indexes = [
                    'idx_conversations_embedding',
                    'idx_conversations_created_at', 
                    'idx_conversations_session_id'
                ]
                
                missing_indexes = [idx for idx in required_indexes if idx not in index_names]
                if missing_indexes:
                    verification_result['issues'].append(
                        f"缺少索引: {', '.join(missing_indexes)}"
                    )
                    verification_result['recommendations'].append("重新创建缺少的索引以优化查询性能")
                
                # 检查pgvector扩展
                vector_ext = await target_conn.fetchrow("""
                    SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'
                """)
                
                if not vector_ext:
                    verification_result['issues'].append("pgvector扩展未安装")
                    verification_result['status'] = 'error'
                else:
                    verification_result['statistics']['pgvector_version'] = vector_ext['extversion']
                
                logger.info(f"迁移验证完成: {verification_result['status']}")
                return verification_result
                
            finally:
                await source_conn.close()
                await target_conn.close()
                
        except Exception as e:
            logger.error(f"迁移验证失败: {e}")
            verification_result['status'] = 'error'
            verification_result['issues'].append(f"验证过程出错: {str(e)}")
            return verification_result
    
    async def optimize_database(self) -> bool:
        """优化数据库性能"""
        logger.info("开始优化数据库性能")
        
        conn = await self.get_db_connection()
        
        try:
            # 更新表统计信息
            await conn.execute("ANALYZE conversations;")
            
            # 重建索引（如果需要）
            await conn.execute("REINDEX INDEX idx_conversations_embedding;")
            
            # 设置向量索引参数
            await conn.execute("SET ivfflat.probes = 10;")
            
            logger.info("数据库优化完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
            return False
        finally:
            await conn.close()

# CLI接口
async def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sage MCP 数据库迁移工具')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 检查命令
    check_parser = subparsers.add_parser('check', help='检查数据库结构')
    
    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='备份数据库')
    backup_parser.add_argument('--name', help='备份名称')
    
    # 恢复命令
    restore_parser = subparsers.add_parser('restore', help='从备份恢复')
    restore_parser.add_argument('backup_path', help='备份文件路径')
    
    # 验证命令
    verify_parser = subparsers.add_parser('verify', help='验证迁移')
    
    # 优化命令
    optimize_parser = subparsers.add_parser('optimize', help='优化数据库')
    
    args = parser.parse_args()
    
    migration = DatabaseMigration()
    
    if args.command == 'check':
        structure = await migration.check_database_structure()
        print(json.dumps(structure, indent=2, default=str))
    
    elif args.command == 'backup':
        backup_path = migration.backup_database(args.name)
        print(f"备份已保存到: {backup_path}")
    
    elif args.command == 'restore':
        success = await migration.restore_from_backup(args.backup_path)
        if success:
            print("数据恢复成功")
        else:
            print("数据恢复失败")
    
    elif args.command == 'verify':
        result = await migration.verify_migration()
        print(json.dumps(result, indent=2, default=str))
    
    elif args.command == 'optimize':
        success = await migration.optimize_database()
        if success:
            print("数据库优化成功")
        else:
            print("数据库优化失败")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    asyncio.run(main())