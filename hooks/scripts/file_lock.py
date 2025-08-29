#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件锁实现 - 防止并发竞争
使用文件系统级的锁机制，确保多进程安全
"""
import os
import time
import fcntl
import errno
import logging
from pathlib import Path
from typing import Optional, Union
from contextlib import contextmanager

class FileLock:
    """跨进程文件锁实现"""
    
    def __init__(self, lock_file: Union[str, Path], timeout: float = 10.0):
        """
        初始化文件锁
        
        Args:
            lock_file: 锁文件路径
            timeout: 获取锁的超时时间（秒）
        """
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self.lock_fd = None
        self.is_locked = False
        
        # 确保锁文件目录存在
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(f'FileLock({self.lock_file.name})')
    
    def acquire(self, blocking: bool = True) -> bool:
        """
        获取锁
        
        Args:
            blocking: 是否阻塞等待锁
            
        Returns:
            是否成功获取锁
        """
        if self.is_locked:
            return True
        
        start_time = time.time()
        
        # 打开或创建锁文件
        try:
            self.lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR)
        except Exception as e:
            self.logger.error(f"Failed to open lock file: {e}")
            return False
        
        while True:
            try:
                # 尝试获取独占锁
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.is_locked = True
                
                # 写入进程信息便于调试
                os.write(self.lock_fd, f"{os.getpid()}\n".encode())
                os.fsync(self.lock_fd)
                
                self.logger.debug(f"Acquired lock: {self.lock_file}")
                return True
                
            except IOError as e:
                if e.errno not in (errno.EAGAIN, errno.EACCES):
                    # 意外错误
                    self.logger.error(f"Lock acquisition error: {e}")
                    self._cleanup()
                    return False
                
                # 锁被占用
                if not blocking:
                    self._cleanup()
                    return False
                
                # 检查超时
                if time.time() - start_time > self.timeout:
                    self.logger.warning(f"Lock acquisition timeout: {self.lock_file}")
                    self._cleanup()
                    return False
                
                # 短暂等待后重试
                time.sleep(0.1)
    
    def release(self):
        """释放锁"""
        if not self.is_locked or self.lock_fd is None:
            return
        
        try:
            # 释放锁
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.logger.debug(f"Released lock: {self.lock_file}")
        except Exception as e:
            self.logger.error(f"Failed to release lock: {e}")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        if self.lock_fd is not None:
            try:
                os.close(self.lock_fd)
            except Exception:
                pass
            self.lock_fd = None
        self.is_locked = False
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire lock: {self.lock_file}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
        return False
    
    def __del__(self):
        """析构函数"""
        self.release()


@contextmanager
def file_lock(lock_path: Union[str, Path], timeout: float = 10.0):
    """
    便捷的文件锁上下文管理器
    
    使用示例：
        with file_lock('/tmp/myapp.lock'):
            # 在这里执行需要互斥的操作
            process_file()
    """
    lock = FileLock(lock_path, timeout)
    try:
        if not lock.acquire():
            raise RuntimeError(f"Failed to acquire lock: {lock_path}")
        yield lock
    finally:
        lock.release()


class JsonFileLock:
    """JSON文件的读写锁封装"""
    
    def __init__(self, json_file: Union[str, Path], lock_dir: Optional[Path] = None):
        """
        初始化JSON文件锁
        
        Args:
            json_file: JSON文件路径
            lock_dir: 锁文件目录，默认为JSON文件同目录
        """
        self.json_file = Path(json_file)
        
        # 锁文件路径
        if lock_dir is None:
            lock_dir = self.json_file.parent
        self.lock_file = lock_dir / f".{self.json_file.name}.lock"
        
        self.logger = logging.getLogger(f'JsonFileLock({self.json_file.name})')
    
    @contextmanager
    def read_lock(self, timeout: float = 10.0):
        """
        读锁上下文管理器（当前实现为独占锁）
        
        使用示例：
            with json_lock.read_lock():
                data = json.load(open(json_file))
        """
        with file_lock(self.lock_file, timeout):
            yield
    
    @contextmanager
    def write_lock(self, timeout: float = 10.0):
        """
        写锁上下文管理器
        
        使用示例：
            with json_lock.write_lock():
                json.dump(data, open(json_file, 'w'))
        """
        with file_lock(self.lock_file, timeout):
            yield
    
    def safe_read(self, timeout: float = 10.0) -> Optional[dict]:
        """
        安全读取JSON文件
        
        Returns:
            JSON数据，失败返回None
        """
        import json
        
        try:
            with self.read_lock(timeout):
                if not self.json_file.exists():
                    return None
                
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read JSON file: {e}")
            return None
    
    def safe_write(self, data: dict, timeout: float = 10.0) -> bool:
        """
        安全写入JSON文件
        
        Args:
            data: 要写入的数据
            timeout: 获取锁的超时时间
            
        Returns:
            是否成功写入
        """
        import json
        
        try:
            with self.write_lock(timeout):
                # 先写入临时文件
                temp_file = self.json_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # 原子性替换
                temp_file.replace(self.json_file)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to write JSON file: {e}")
            return False


if __name__ == "__main__":
    # 测试代码
    import json
    import tempfile
    
    # 设置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试基本文件锁
    print("Testing basic file lock...")
    with tempfile.NamedTemporaryFile() as tmp:
        lock_path = f"{tmp.name}.lock"
        
        with file_lock(lock_path) as lock1:
            print("Lock 1 acquired")
            
            # 尝试获取第二个锁（非阻塞）
            lock2 = FileLock(lock_path)
            if not lock2.acquire(blocking=False):
                print("Lock 2 failed to acquire (expected)")
            else:
                print("ERROR: Lock 2 should not have been acquired!")
                lock2.release()
        
        print("Lock 1 released")
    
    # 测试JSON文件锁
    print("\nTesting JSON file lock...")
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        json_path = tmp.name
        
        json_lock = JsonFileLock(json_path)
        
        # 测试写入
        test_data = {"test": "data", "number": 42}
        if json_lock.safe_write(test_data):
            print("JSON write successful")
        
        # 测试读取
        read_data = json_lock.safe_read()
        if read_data == test_data:
            print("JSON read successful")
        else:
            print(f"ERROR: Read data mismatch: {read_data}")
        
        # 清理
        os.unlink(json_path)
    
    print("\nAll tests completed!")