#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时文件自动清理工具
解决 os.path.join(os.path.expanduser('~'), '.sage_hooks_temp') 中文件积累问题
"""
import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import threading
import atexit

class TempFileCleaner:
    """临时文件清理器 - 自动清理过期的临时文件"""
    
    def __init__(self, temp_dir: str = None, max_age_hours: float = 24.0):
        """
        初始化清理器
        
        Args:
            temp_dir: 临时文件目录，默认为 ~/.sage_hooks_temp
            max_age_hours: 文件最大保留时间（小时），默认24小时
        """
        self.temp_dir = Path(temp_dir or os.path.expanduser("~/.sage_hooks_temp"))
        self.max_age_seconds = max_age_hours * 3600
        self.cleanup_interval = 3600  # 每小时清理一次
        
        # 设置日志
        self.logger = logging.getLogger('TempFileCleaner')
        self.logger.setLevel(logging.INFO)
        
        # 确保目录存在
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 清理线程
        self._cleanup_thread = None
        self._stop_event = threading.Event()
        
        # 注册退出清理
        atexit.register(self.stop)
    
    def get_file_age(self, file_path: Path) -> float:
        """获取文件年龄（秒）"""
        try:
            stat = file_path.stat()
            age = time.time() - stat.st_mtime
            return age
        except Exception:
            return 0
    
    def should_clean_file(self, file_path: Path) -> bool:
        """判断文件是否应该被清理"""
        # 只清理JSON文件
        if not file_path.suffix == '.json':
            return False
        
        # 检查文件年龄
        age = self.get_file_age(file_path)
        if age < self.max_age_seconds:
            return False
        
        # 检查文件是否正在使用（通过文件锁或打开状态）
        try:
            # 尝试独占打开文件
            with open(file_path, 'r+b') as f:
                # 如果能打开，说明没有被其他进程使用
                return True
        except (IOError, OSError):
            # 文件正在使用中，不清理
            return False
    
    def clean_file(self, file_path: Path) -> bool:
        """安全清理单个文件"""
        try:
            # 再次检查文件是否应该清理
            if not self.should_clean_file(file_path):
                return False
            
            # 记录文件信息
            file_size = file_path.stat().st_size
            file_age_hours = self.get_file_age(file_path) / 3600
            
            # 删除文件
            file_path.unlink()
            
            self.logger.info(
                f"Cleaned file: {file_path.name} "
                f"(size: {file_size} bytes, age: {file_age_hours:.1f} hours)"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clean {file_path}: {e}")
            return False
    
    def cleanup_once(self) -> Dict[str, int]:
        """执行一次清理，返回清理统计"""
        stats = {
            'total_files': 0,
            'cleaned_files': 0,
            'failed_files': 0,
            'total_size_cleaned': 0,
            'skipped_files': 0
        }
        
        try:
            # 扫描所有文件
            for file_path in self.temp_dir.glob('*.json'):
                stats['total_files'] += 1
                
                if self.should_clean_file(file_path):
                    # 获取文件大小（清理前）
                    try:
                        file_size = file_path.stat().st_size
                    except:
                        file_size = 0
                    
                    # 执行清理
                    if self.clean_file(file_path):
                        stats['cleaned_files'] += 1
                        stats['total_size_cleaned'] += file_size
                    else:
                        stats['failed_files'] += 1
                else:
                    stats['skipped_files'] += 1
            
            # 记录清理结果
            if stats['cleaned_files'] > 0:
                self.logger.info(
                    f"Cleanup completed: {stats['cleaned_files']} files cleaned, "
                    f"{stats['total_size_cleaned']} bytes freed, "
                    f"{stats['skipped_files']} files kept"
                )
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
        
        return stats
    
    def start_auto_cleanup(self):
        """启动自动清理线程"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self.logger.warning("Auto cleanup already running")
            return
        
        self._stop_event.clear()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        self.logger.info(f"Auto cleanup started (interval: {self.cleanup_interval}s)")
    
    def _cleanup_loop(self):
        """清理循环"""
        while not self._stop_event.is_set():
            try:
                # 执行清理
                self.cleanup_once()
                
                # 等待下次清理
                self._stop_event.wait(self.cleanup_interval)
                
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                # 出错后等待一段时间再试
                self._stop_event.wait(60)
    
    def stop(self):
        """停止自动清理"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_event.set()
            self._cleanup_thread.join(timeout=5)
            self.logger.info("Auto cleanup stopped")


# 单例实例
_cleaner_instance = None

def get_cleaner(temp_dir: str = None, max_age_hours: float = 24.0) -> TempFileCleaner:
    """获取清理器单例"""
    global _cleaner_instance
    if _cleaner_instance is None:
        _cleaner_instance = TempFileCleaner(temp_dir, max_age_hours)
    return _cleaner_instance


def cleanup_old_files(temp_dir: str = None, max_age_hours: float = 24.0) -> Dict[str, int]:
    """立即清理旧文件（一次性）"""
    cleaner = TempFileCleaner(temp_dir, max_age_hours)
    return cleaner.cleanup_once()


if __name__ == "__main__":
    # 命令行工具模式
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean old temporary files")
    parser.add_argument(
        "--dir", 
        default="~/.sage_hooks_temp",
        help="Temporary directory path"
    )
    parser.add_argument(
        "--max-age", 
        type=float,
        default=24.0,
        help="Maximum file age in hours"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in auto-cleanup mode"
    )
    
    args = parser.parse_args()
    
    # 设置日志输出到控制台
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.auto:
        # 自动清理模式
        cleaner = get_cleaner(args.dir, args.max_age)
        cleaner.start_auto_cleanup()
        
        print(f"Auto cleanup started. Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            cleaner.stop()
    else:
        # 一次性清理
        stats = cleanup_old_files(args.dir, args.max_age)
        print(f"Cleanup completed: {stats}")