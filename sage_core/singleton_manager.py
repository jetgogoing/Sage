#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SageCore 单例管理器 - 确保全局只有一个SageCore实例
避免重复初始化数据库连接和向量化模型，提升性能
"""
import threading
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .core_service import SageCore

logger = logging.getLogger(__name__)


class SageCoreSingleton:
    """SageCore单例管理器"""
    
    _instance: Optional['SageCoreSingleton'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """私有构造函数"""
        if SageCoreSingleton._instance is not None:
            raise RuntimeError("请使用 get_instance() 获取单例")
        
        self._sage_core: Optional[SageCore] = None
        self._initialization_lock = asyncio.Lock()
        self._last_used = datetime.now()
        self._config: Dict[str, Any] = {}
        self._is_initialized = False
        
        # 实例生命周期管理
        self._max_idle_time = timedelta(hours=1)  # 1小时无使用则重置
        self._access_count = 0
        
        logger.info("SageCoreSingleton 创建")
    
    @classmethod
    def get_instance(cls) -> 'SageCoreSingleton':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    async def get_sage_core(self, config: Optional[Dict[str, Any]] = None) -> SageCore:
        """
        获取 SageCore 实例
        
        Args:
            config: 配置信息，如果与现有配置不同则重新初始化
            
        Returns:
            初始化好的 SageCore 实例
        """
        async with self._initialization_lock:
            # 检查是否需要重新初始化
            if self._needs_reinitialization(config):
                await self._initialize_sage_core(config)
            
            # 更新访问信息
            self._last_used = datetime.now()
            self._access_count += 1
            
            if self._access_count % 100 == 0:
                logger.info(f"SageCore 访问统计：{self._access_count} 次")
            
            return self._sage_core
    
    def _needs_reinitialization(self, config: Optional[Dict[str, Any]]) -> bool:
        """检查是否需要重新初始化"""
        # 如果还没初始化
        if self._sage_core is None or not self._is_initialized:
            return True
        
        # 如果配置发生变化
        if config and config != self._config:
            logger.info("配置变化，需要重新初始化")
            return True
        
        # 如果空闲时间过长
        idle_time = datetime.now() - self._last_used
        if idle_time > self._max_idle_time:
            logger.info(f"空闲时间过长 ({idle_time})，需要重新初始化")
            return True
        
        return False
    
    async def _initialize_sage_core(self, config: Optional[Dict[str, Any]]) -> None:
        """初始化或重新初始化 SageCore"""
        try:
            logger.info("开始初始化 SageCore...")
            
            # 如果存在旧实例，先清理
            if self._sage_core is not None:
                await self._cleanup_sage_core()
            
            # 创建新实例
            self._sage_core = SageCore()
            self._config = config or {}
            
            # 初始化
            await self._sage_core.initialize(self._config)
            self._is_initialized = True
            
            logger.info("SageCore 初始化成功")
            
        except Exception as e:
            logger.error(f"SageCore 初始化失败: {e}")
            self._sage_core = None
            self._is_initialized = False
            raise
    
    async def _cleanup_sage_core(self) -> None:
        """清理 SageCore 实例"""
        if self._sage_core is None:
            return
        
        try:
            logger.info("清理旧的 SageCore 实例...")
            
            # 关闭数据库连接
            if hasattr(self._sage_core, 'db_connection') and self._sage_core.db_connection:
                await self._sage_core.db_connection.close()
            
            # 清理其他资源
            if hasattr(self._sage_core, 'cleanup'):
                await self._sage_core.cleanup()
            
            self._sage_core = None
            self._is_initialized = False
            
            logger.info("旧实例清理完成")
            
        except Exception as e:
            logger.error(f"清理 SageCore 失败: {e}")
    
    async def shutdown(self) -> None:
        """关闭单例管理器"""
        logger.info("关闭 SageCoreSingleton...")
        await self._cleanup_sage_core()
        self._access_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'is_initialized': self._is_initialized,
            'last_used': self._last_used.isoformat() if self._last_used else None,
            'access_count': self._access_count,
            'idle_time': str(datetime.now() - self._last_used) if self._last_used else None,
            'config': self._config
        }
    
    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）"""
        with cls._lock:
            if cls._instance:
                # 同步方式清理
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果在异步上下文中，创建任务
                        asyncio.create_task(cls._instance.shutdown())
                    else:
                        # 如果不在异步上下文中，同步运行
                        loop.run_until_complete(cls._instance.shutdown())
                except Exception as e:
                    logger.error(f"重置单例时出错: {e}")
            
            cls._instance = None
            logger.info("SageCoreSingleton 已重置")


# 便捷函数
async def get_sage_core(config: Optional[Dict[str, Any]] = None) -> SageCore:
    """
    获取全局 SageCore 实例
    
    Args:
        config: 配置信息
        
    Returns:
        初始化好的 SageCore 实例
    """
    singleton = SageCoreSingleton.get_instance()
    return await singleton.get_sage_core(config)


def get_sage_stats() -> Dict[str, Any]:
    """获取 SageCore 统计信息"""
    singleton = SageCoreSingleton.get_instance()
    return singleton.get_stats()


if __name__ == "__main__":
    # 测试代码
    import asyncio
    
    async def test_singleton():
        """测试单例模式"""
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 第一次获取
        print("第一次获取 SageCore...")
        core1 = await get_sage_core({'test': 'config1'})
        print(f"实例1: {id(core1)}")
        
        # 第二次获取（应该是同一个实例）
        print("\n第二次获取 SageCore...")
        core2 = await get_sage_core({'test': 'config1'})
        print(f"实例2: {id(core2)}")
        print(f"是否同一实例: {core1 is core2}")
        
        # 获取统计信息
        print("\n统计信息:")
        stats = get_sage_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 重置并再次获取
        print("\n重置单例...")
        SageCoreSingleton.reset()
        
        print("\n重置后获取 SageCore...")
        core3 = await get_sage_core({'test': 'config2'})
        print(f"实例3: {id(core3)}")
        print(f"与实例1是否相同: {core1 is core3}")
    
    # 运行测试
    asyncio.run(test_singleton())