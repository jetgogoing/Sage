#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage Persistence Daemon - 长驻服务进程
提供高性能的记忆保存服务，避免重复初始化开销
"""
import asyncio
import os
import sys
import signal
import socket
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
# import aiofiles  # 不需要

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sage_core.singleton_manager import get_sage_core, SageCoreSingleton
from sage_core.interfaces import MemoryContent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/sage_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Unix Socket 路径
SOCKET_PATH = "/tmp/sage_daemon.sock"
PID_FILE = "/tmp/sage_daemon.pid"


class SagePersistenceDaemon:
    """Sage 持久化守护进程"""
    
    def __init__(self):
        """初始化守护进程"""
        self.socket_path = SOCKET_PATH
        self.server = None
        self.sage_core = None
        self.running = False
        self.client_count = 0
        self.total_requests = 0
        self.start_time = datetime.now()
        
    async def initialize(self):
        """初始化服务"""
        try:
            # 初始化 SageCore
            logger.info("正在初始化 SageCore...")
            self.sage_core = await get_sage_core()
            logger.info("SageCore 初始化成功")
            
            # 清理旧的 socket 文件
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            
            # 创建 Unix Socket 服务器
            self.server = await asyncio.start_unix_server(
                self.handle_client,
                path=self.socket_path
            )
            
            # 设置权限
            os.chmod(self.socket_path, 0o666)
            
            logger.info(f"守护进程已启动，监听: {self.socket_path}")
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            raise
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        client_id = self.client_count
        self.client_count += 1
        
        logger.info(f"新客户端连接 (ID: {client_id})")
        
        try:
            while True:
                # 读取请求长度（4字节）
                length_data = await reader.read(4)
                if not length_data:
                    break
                
                request_length = int.from_bytes(length_data, 'big')
                
                # 读取请求数据
                request_data = await reader.read(request_length)
                if not request_data:
                    break
                
                # 解析请求
                request = json.loads(request_data.decode('utf-8'))
                
                # 处理请求
                response = await self.process_request(request)
                
                # 发送响应
                response_data = json.dumps(response).encode('utf-8')
                writer.write(len(response_data).to_bytes(4, 'big'))
                writer.write(response_data)
                await writer.drain()
                
                self.total_requests += 1
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"处理客户端 {client_id} 时出错: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            logger.info(f"客户端 {client_id} 断开连接")
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            action = request.get('action')
            
            if action == 'save_memory':
                # 保存记忆
                result = await self.save_memory(request['data'])
                
            elif action == 'get_context':
                # 获取上下文
                result = await self.get_context(
                    request.get('query', ''),
                    request.get('max_results', 10)
                )
                
            elif action == 'status':
                # 获取状态
                result = await self.get_status()
                
            elif action == 'ping':
                # 心跳检测
                result = {'status': 'ok', 'message': 'pong'}
                
            else:
                result = {'status': 'error', 'message': f'未知操作: {action}'}
            
            # 添加处理时间
            result['processing_time'] = asyncio.get_event_loop().time() - start_time
            
            return result
            
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
    
    async def save_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存记忆"""
        try:
            content = MemoryContent(
                user_input=data['user_input'],
                assistant_response=data['assistant_response'],
                metadata=data.get('metadata', {}),
                session_id=data.get('session_id')
            )
            
            memory_id = await self.sage_core.save_memory(content)
            
            return {
                'status': 'ok',
                'memory_id': str(memory_id),  # 转换为字符串
                'message': '记忆保存成功'
            }
            
        except Exception as e:
            logger.error(f"保存记忆失败: {e}")
            return {
                'status': 'error',
                'message': f'保存失败: {str(e)}'
            }
    
    async def get_context(self, query: str, max_results: int) -> Dict[str, Any]:
        """获取上下文"""
        try:
            context = await self.sage_core.get_context(query, max_results)
            
            return {
                'status': 'ok',
                'context': context,
                'message': '获取上下文成功'
            }
            
        except Exception as e:
            logger.error(f"获取上下文失败: {e}")
            return {
                'status': 'error',
                'message': f'获取失败: {str(e)}'
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """获取守护进程状态"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # 获取 SageCore 统计信息
        from sage_core.singleton_manager import get_sage_stats
        sage_stats = get_sage_stats()
        
        return {
            'status': 'ok',
            'daemon': {
                'uptime': uptime,
                'total_requests': self.total_requests,
                'active_clients': self.client_count,
                'socket_path': self.socket_path,
                'pid': os.getpid()
            },
            'sage_core': sage_stats,
            'message': '状态正常'
        }
    
    async def run(self):
        """运行守护进程"""
        self.running = True
        
        # 写入 PID 文件
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        try:
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            logger.info("守护进程正在关闭...")
        finally:
            self.running = False
            
            # 清理资源
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        logger.info("开始清理资源...")
        
        # 关闭服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # 清理 SageCore
        if self.sage_core:
            await self.sage_core.cleanup()
        
        # 重置单例
        SageCoreSingleton.reset()
        
        # 删除 socket 文件
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        # 删除 PID 文件
        if os.path.exists(PID_FILE):
            os.unlink(PID_FILE)
        
        logger.info("资源清理完成")
    
    def handle_signal(self, signum, frame):
        """处理信号"""
        logger.info(f"收到信号 {signum}")
        if self.running:
            # 创建任务来停止服务器
            asyncio.create_task(self.stop())
    
    async def stop(self):
        """停止守护进程"""
        logger.info("正在停止守护进程...")
        self.running = False
        if self.server:
            self.server.close()


async def main():
    """主函数"""
    daemon = SagePersistenceDaemon()
    
    # 设置信号处理
    signal.signal(signal.SIGTERM, daemon.handle_signal)
    signal.signal(signal.SIGINT, daemon.handle_signal)
    
    try:
        # 初始化
        await daemon.initialize()
        
        # 运行守护进程
        await daemon.run()
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    except Exception as e:
        logger.error(f"守护进程异常: {e}")
    finally:
        logger.info("守护进程已退出")


if __name__ == "__main__":
    # 检查是否已有实例运行
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            old_pid = int(f.read().strip())
        
        # 检查进程是否存在
        try:
            os.kill(old_pid, 0)
            logger.error(f"守护进程已在运行 (PID: {old_pid})")
            sys.exit(1)
        except OSError:
            # 进程不存在，删除旧的 PID 文件
            os.unlink(PID_FILE)
    
    # 运行守护进程
    asyncio.run(main())