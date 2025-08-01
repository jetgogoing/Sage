#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage Client - 轻量级客户端库
用于与 Sage Persistence Daemon 通信
"""
import socket
import json
import os
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Unix Socket 路径
SOCKET_PATH = "/tmp/sage_daemon.sock"
DEFAULT_TIMEOUT = 30.0  # 默认超时时间


class SageClient:
    """Sage 客户端"""
    
    def __init__(self, socket_path: str = SOCKET_PATH, timeout: float = DEFAULT_TIMEOUT):
        """
        初始化客户端
        
        Args:
            socket_path: Unix Socket 路径
            timeout: 超时时间（秒）
        """
        self.socket_path = socket_path
        self.timeout = timeout
        self._socket = None
        
    def connect(self):
        """连接到守护进程"""
        if self._socket:
            return
        
        try:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect(self.socket_path)
            logger.debug(f"已连接到守护进程: {self.socket_path}")
        except FileNotFoundError:
            raise ConnectionError(f"守护进程未运行或 socket 文件不存在: {self.socket_path}")
        except Exception as e:
            raise ConnectionError(f"连接守护进程失败: {e}")
    
    def disconnect(self):
        """断开连接"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None
            logger.debug("已断开与守护进程的连接")
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送请求并获取响应
        
        Args:
            request: 请求数据
            
        Returns:
            响应数据
        """
        if not self._socket:
            self.connect()
        
        try:
            # 序列化请求
            request_data = json.dumps(request).encode('utf-8')
            
            # 发送请求长度（4字节）
            self._socket.sendall(len(request_data).to_bytes(4, 'big'))
            
            # 发送请求数据
            self._socket.sendall(request_data)
            
            # 读取响应长度
            length_data = self._recv_exact(4)
            response_length = int.from_bytes(length_data, 'big')
            
            # 读取响应数据
            response_data = self._recv_exact(response_length)
            
            # 解析响应
            response = json.loads(response_data.decode('utf-8'))
            
            return response
            
        except socket.timeout:
            raise TimeoutError(f"请求超时（{self.timeout}秒）")
        except Exception as e:
            # 连接可能已断开，尝试重连
            self.disconnect()
            raise ConnectionError(f"通信错误: {e}")
    
    def _recv_exact(self, n: int) -> bytes:
        """精确读取 n 字节数据"""
        data = b''
        while len(data) < n:
            chunk = self._socket.recv(n - len(data))
            if not chunk:
                raise ConnectionError("连接已断开")
            data += chunk
        return data
    
    def save_memory(self, user_input: str, assistant_response: str,
                   metadata: Optional[Dict[str, Any]] = None,
                   session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        保存记忆
        
        Args:
            user_input: 用户输入
            assistant_response: 助手响应
            metadata: 元数据
            session_id: 会话ID
            
        Returns:
            响应结果
        """
        request = {
            'action': 'save_memory',
            'data': {
                'user_input': user_input,
                'assistant_response': assistant_response,
                'metadata': metadata or {},
                'session_id': session_id
            }
        }
        
        return self._send_request(request)
    
    def get_context(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        获取上下文
        
        Args:
            query: 查询内容
            max_results: 最大结果数
            
        Returns:
            响应结果
        """
        request = {
            'action': 'get_context',
            'query': query,
            'max_results': max_results
        }
        
        return self._send_request(request)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取守护进程状态
        
        Returns:
            状态信息
        """
        request = {'action': 'status'}
        return self._send_request(request)
    
    def ping(self) -> bool:
        """
        心跳检测
        
        Returns:
            是否在线
        """
        try:
            response = self._send_request({'action': 'ping'})
            return response.get('status') == 'ok'
        except:
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


def save_memory_quick(user_input: str, assistant_response: str,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    快速保存记忆（便捷函数）
    
    Args:
        user_input: 用户输入
        assistant_response: 助手响应
        metadata: 元数据
        
    Returns:
        是否成功
    """
    try:
        with SageClient() as client:
            response = client.save_memory(user_input, assistant_response, metadata)
            return response.get('status') == 'ok'
    except Exception as e:
        logger.error(f"保存记忆失败: {e}")
        return False


def get_context_quick(query: str, max_results: int = 10) -> Optional[str]:
    """
    快速获取上下文（便捷函数）
    
    Args:
        query: 查询内容
        max_results: 最大结果数
        
    Returns:
        上下文内容或 None
    """
    try:
        with SageClient() as client:
            response = client.get_context(query, max_results)
            if response.get('status') == 'ok':
                return response.get('context')
    except Exception as e:
        logger.error(f"获取上下文失败: {e}")
    
    return None


def is_daemon_running() -> bool:
    """
    检查守护进程是否运行
    
    Returns:
        是否运行中
    """
    try:
        client = SageClient(timeout=2.0)
        return client.ping()
    except:
        return False


if __name__ == "__main__":
    # 测试代码
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("测试 Sage 客户端...")
        
        # 检查守护进程
        if not is_daemon_running():
            print("❌ 守护进程未运行！")
            print("请先运行: python sage_persistence_daemon.py")
            sys.exit(1)
        
        print("✅ 守护进程运行中")
        
        # 测试保存记忆
        print("\n测试保存记忆...")
        success = save_memory_quick(
            "测试用户输入",
            "测试助手响应",
            {"test": True, "timestamp": time.time()}
        )
        
        if success:
            print("✅ 保存成功")
        else:
            print("❌ 保存失败")
        
        # 测试获取上下文
        print("\n测试获取上下文...")
        context = get_context_quick("测试")
        
        if context:
            print("✅ 获取成功")
            print(f"上下文长度: {len(context)} 字符")
        else:
            print("❌ 获取失败")
        
        # 测试状态查询
        print("\n测试状态查询...")
        with SageClient() as client:
            status = client.get_status()
            if status.get('status') == 'ok':
                print("✅ 状态查询成功")
                daemon_info = status.get('daemon', {})
                print(f"运行时间: {daemon_info.get('uptime', 0):.1f} 秒")
                print(f"总请求数: {daemon_info.get('total_requests', 0)}")
            else:
                print("❌ 状态查询失败")
    
    else:
        print("用法: python sage_client.py test")