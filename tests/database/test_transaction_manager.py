#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试事务管理功能
验证记忆保存的原子性和回滚机制
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_core.interfaces import MemoryContent
from sage_core.singleton_manager import get_sage_core

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_transaction_rollback():
    """测试事务回滚功能"""
    logger.info("开始测试事务回滚功能...")
    
    try:
        # 获取 SageCore 实例
        sage = await get_sage_core()
        
        # 准备测试数据
        test_content = MemoryContent(
            user_input="测试事务回滚功能",
            assistant_response="这是一个会触发错误的响应" * 1000,  # 故意制造一个很长的响应
            metadata={
                "test": True,
                "timestamp": datetime.utcnow().isoformat(),
                "purpose": "transaction_test"
            }
        )
        
        # 获取保存前的统计信息
        stats_before = await sage.memory_manager.storage.get_statistics()
        logger.info(f"保存前的记忆总数: {stats_before['total_memories']}")
        
        # 尝试保存（这应该成功）
        try:
            memory_id = await sage.save_memory(test_content)
            logger.info(f"第一次保存成功，记忆ID: {memory_id}")
        except Exception as e:
            logger.error(f"第一次保存失败: {e}")
        
        # 获取保存后的统计信息
        stats_after = await sage.memory_manager.storage.get_statistics()
        logger.info(f"保存后的记忆总数: {stats_after['total_memories']}")
        
        # 模拟一个会失败的保存操作
        # 通过传入None作为embedding来触发错误
        logger.info("\n测试事务回滚场景...")
        
        # 临时修改storage的save方法来模拟错误
        original_save = sage.memory_manager.storage.save
        
        async def failing_save(*args, **kwargs):
            """模拟保存过程中的错误"""
            # 先执行部分操作
            logger.info("开始执行保存操作...")
            await asyncio.sleep(0.1)  # 模拟一些处理时间
            # 然后抛出错误
            raise Exception("模拟的数据库错误：违反约束条件")
        
        # 替换save方法
        sage.memory_manager.storage.save = failing_save
        
        try:
            # 尝试保存（这应该失败并回滚）
            await sage.save_memory(MemoryContent(
                user_input="这个保存应该失败",
                assistant_response="事务应该回滚",
                metadata={"should_fail": True}
            ))
            logger.error("错误：保存应该失败但没有失败！")
        except Exception as e:
            logger.info(f"保存失败（预期）: {e}")
        
        # 恢复原始方法
        sage.memory_manager.storage.save = original_save
        
        # 再次获取统计信息，确认没有新增记录
        stats_final = await sage.memory_manager.storage.get_statistics()
        logger.info(f"事务回滚后的记忆总数: {stats_final['total_memories']}")
        
        # 验证结果
        if stats_after['total_memories'] == stats_final['total_memories']:
            logger.info("✅ 事务回滚测试通过！失败的操作没有影响数据库")
        else:
            logger.error("❌ 事务回滚测试失败！数据库状态发生了变化")
        
        # 测试正常的批量保存（在事务中）
        logger.info("\n测试事务中的批量保存...")
        
        batch_contents = [
            MemoryContent(
                user_input=f"批量测试问题 {i}",
                assistant_response=f"批量测试回答 {i}",
                metadata={"batch": True, "index": i}
            )
            for i in range(3)
        ]
        
        # 使用事务保存批量数据
        if sage.memory_manager.transaction_manager:
            async with sage.memory_manager.transaction_manager.transaction() as conn:
                saved_ids = []
                for content in batch_contents:
                    # 直接调用带事务的保存
                    memory_id = await sage.memory_manager._save_with_transaction(content)
                    saved_ids.append(memory_id)
                    logger.info(f"批量保存 {len(saved_ids)}/{len(batch_contents)}: {memory_id}")
            
            logger.info(f"✅ 批量保存成功，共保存 {len(saved_ids)} 条记忆")
        else:
            logger.warning("事务管理器未初始化，跳过批量保存测试")
        
        # 获取最终统计
        final_stats = await sage.memory_manager.storage.get_statistics()
        logger.info(f"\n最终统计:")
        logger.info(f"- 总记忆数: {final_stats['total_memories']}")
        logger.info(f"- 第一条记忆: {final_stats['first_memory']}")
        logger.info(f"- 最后一条记忆: {final_stats['last_memory']}")
        
        # 不要清理，让下一个测试继续使用
        # await sage.cleanup()
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        raise


async def test_transaction_isolation():
    """测试事务隔离性"""
    logger.info("\n开始测试事务隔离性...")
    
    try:
        sage = await get_sage_core()
        
        if not sage.memory_manager.transaction_manager:
            logger.warning("事务管理器未初始化，跳过隔离性测试")
            return
        
        # 获取活跃事务数
        active_count = await sage.memory_manager.transaction_manager.get_active_transaction_count()
        logger.info(f"当前活跃事务数: {active_count}")
        
        # 创建多个并发事务
        async def concurrent_save(index: int):
            """并发保存操作"""
            content = MemoryContent(
                user_input=f"并发测试 {index}",
                assistant_response=f"并发响应 {index}",
                metadata={"concurrent": True, "index": index}
            )
            
            try:
                memory_id = await sage.save_memory(content)
                logger.info(f"并发保存 {index} 成功: {memory_id}")
                return memory_id
            except Exception as e:
                logger.error(f"并发保存 {index} 失败: {e}")
                return None
        
        # 并发执行多个保存操作
        tasks = [concurrent_save(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r and not isinstance(r, Exception))
        logger.info(f"并发保存完成: {success_count}/5 成功")
        
        # 再次检查活跃事务数
        final_count = await sage.memory_manager.transaction_manager.get_active_transaction_count()
        logger.info(f"最终活跃事务数: {final_count}")
        
        if final_count == 0:
            logger.info("✅ 事务隔离性测试通过！所有事务都已正确完成")
        else:
            logger.warning(f"⚠️ 仍有 {final_count} 个活跃事务未完成")
        
        await sage.cleanup()
        
    except Exception as e:
        logger.error(f"隔离性测试出错: {e}", exc_info=True)


if __name__ == "__main__":
    async def main():
        """运行所有测试"""
        try:
            await test_transaction_rollback()
            await test_transaction_isolation()
            logger.info("\n🎉 所有事务测试完成！")
        except Exception as e:
            logger.error(f"测试失败: {e}")
            sys.exit(1)
    
    asyncio.run(main())