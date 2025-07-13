#!/usr/bin/env python3
"""
Sage MCP 异步事件循环管理器
提供安全、高效的事件循环复用和管理
"""

import asyncio
import atexit
import threading
import weakref
from typing import Optional, Callable, Any, Coroutine, TypeVar
from contextlib import contextmanager
import logging

from exceptions import AsyncRuntimeError, ResourceManagementError

logger = logging.getLogger('SageAsyncManager')

T = TypeVar('T')


class SingletonEventLoop:
    """单例事件循环管理器"""
    
    _instance = None
    _lock = threading.Lock()
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _thread: Optional[threading.Thread] = None
    _running = False
    _tasks = weakref.WeakSet()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化事件循环"""
        atexit.register(self.cleanup)
        logger.debug("SingletonEventLoop 初始化")
    
    def get_loop(self) -> asyncio.AbstractEventLoop:
        """获取或创建事件循环"""
        # 1. 尝试获取当前运行的循环
        try:
            loop = asyncio.get_running_loop()
            logger.debug("使用现有运行循环")
            return loop
        except RuntimeError:
            pass
        
        # 2. 检查是否有我们管理的循环
        with self._lock:
            if self._loop is None or self._loop.is_closed():
                self._create_new_loop()
            return self._loop
    
    def _create_new_loop(self):
        """创建新的事件循环"""
        logger.debug("创建新的事件循环")
        
        # 如果在主线程，直接创建和设置循环
        if threading.current_thread() is threading.main_thread():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._running = False
        else:
            # 在单独线程中运行循环
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._run_loop_in_thread, 
                daemon=True,
                name="SageAsyncLoopThread"
            )
            self._thread.start()
            self._running = True
    
    def _run_loop_in_thread(self):
        """在线程中运行事件循环"""
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
    
    def run_coroutine(self, coro: Coroutine[Any, Any, T]) -> T:
        """安全地运行协程"""
        loop = self.get_loop()
        
        # 如果循环正在运行，使用 run_coroutine_threadsafe
        if self._running and loop == self._loop:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        
        # 如果在异步上下文中
        try:
            running_loop = asyncio.get_running_loop()
            if running_loop == loop:
                # 创建任务并跟踪
                task = running_loop.create_task(coro)
                self._tasks.add(task)
                return asyncio.run_coroutine_threadsafe(
                    self._wait_for_task(task), loop
                ).result()
        except RuntimeError:
            pass
        
        # 否则直接运行
        return loop.run_until_complete(coro)
    
    async def _wait_for_task(self, task):
        """等待任务完成"""
        try:
            return await task
        finally:
            self._tasks.discard(task)
    
    def cleanup(self):
        """清理资源"""
        logger.debug("清理异步资源")
        
        with self._lock:
            # 取消所有待处理的任务
            for task in list(self._tasks):
                if not task.done():
                    task.cancel()
            
            # 停止事件循环
            if self._loop and not self._loop.is_closed():
                if self._running:
                    self._loop.call_soon_threadsafe(self._loop.stop)
                    if self._thread and self._thread.is_alive():
                        self._thread.join(timeout=2.0)
                else:
                    # 运行一次以处理清理任务
                    self._loop.run_until_complete(asyncio.sleep(0))
                
                self._loop.close()
            
            self._loop = None
            self._thread = None
            self._running = False


class AsyncContextManager:
    """异步上下文管理器"""
    
    def __init__(self):
        self._loop_manager = SingletonEventLoop()
        self._resources = []
        self._cleanup_callbacks = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    def register_resource(self, resource: Any, cleanup: Optional[Callable] = None):
        """注册需要清理的资源"""
        self._resources.append(resource)
        if cleanup:
            self._cleanup_callbacks.append(cleanup)
    
    async def cleanup(self):
        """清理所有资源"""
        # 执行清理回调
        for callback in reversed(self._cleanup_callbacks):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"清理回调失败: {e}")
        
        # 清空列表
        self._resources.clear()
        self._cleanup_callbacks.clear()


class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._tasks = weakref.WeakSet()
        self._loop_manager = SingletonEventLoop()
    
    async def run_task(self, coro: Coroutine[Any, Any, T], 
                      name: Optional[str] = None) -> T:
        """运行受限的异步任务"""
        async with self._semaphore:
            task = asyncio.create_task(coro, name=name)
            self._tasks.add(task)
            try:
                return await task
            finally:
                self._tasks.discard(task)
    
    async def wait_all(self, timeout: Optional[float] = None):
        """等待所有任务完成"""
        tasks = list(self._tasks)
        if tasks:
            await asyncio.wait(tasks, timeout=timeout)
    
    def cancel_all(self):
        """取消所有任务"""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()


# 全局实例
_event_loop_manager = None


def get_event_loop_manager() -> SingletonEventLoop:
    """获取全局事件循环管理器"""
    global _event_loop_manager
    if _event_loop_manager is None:
        _event_loop_manager = SingletonEventLoop()
    return _event_loop_manager


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """便捷函数：运行异步协程"""
    manager = get_event_loop_manager()
    return manager.run_coroutine(coro)


@contextmanager
def managed_async_context():
    """托管的异步上下文"""
    context = AsyncContextManager()
    try:
        yield context
    finally:
        # 同步清理
        loop = get_event_loop_manager().get_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(context.cleanup(), loop).result()
        else:
            loop.run_until_complete(context.cleanup())


# 装饰器
def ensure_async_cleanup(func: Callable) -> Callable:
    """确保异步函数的资源清理"""
    async def wrapper(*args, **kwargs):
        async with AsyncContextManager() as ctx:
            # 将上下文注入到kwargs中
            kwargs['_async_context'] = ctx
            return await func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper