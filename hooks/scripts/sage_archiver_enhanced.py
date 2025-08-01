#!/usr/bin/env python3
"""
Enhanced Sage Archiver Hook
增强版对话归档脚本，支持完整数据提取和项目标识

主要增强:
1. 支持提取tool_use和tool_result类型内容
2. 添加跨项目标识机制
3. 保存更完整的交互数据
"""

import json
import sys
import subprocess
import logging
import time
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 尝试导入简化版security_utils，如果失败则定义基本验证
try:
    from security_utils_simple import SimplifiedSecurityUtils as SecurityUtils
except ImportError:
    # 定义基本的安全工具类
    class SecurityUtils:
        @staticmethod
        def validate_basic_input(input_str: str, max_length: int = 100000) -> str:
            if not input_str:
                return ""
            if len(input_str) > max_length:
                return input_str[:max_length]
            return input_str

# 导入数据聚合器
try:
    from hook_data_aggregator import get_aggregator
    has_aggregator = True
except ImportError:
    has_aggregator = False

# 设置默认编码
import locale
locale.setlocale(locale.LC_ALL, '')

class EnhancedSageArchiver:
    """增强版Sage对话归档器"""
    
    def __init__(self):
        self.timeout = 30  # 归档操作超时时间
        self.setup_logging()
        # 添加项目标识
        self.project_id = self.get_project_id()
        self.project_name = os.path.basename(os.getcwd())
        self.logger.info(f"EnhancedSageArchiver initialized for project: {self.project_name} (ID: {self.project_id})")
        
    def get_project_id(self) -> str:
        """获取当前项目的唯一标识"""
        cwd = os.getcwd()
        project_name = os.path.basename(cwd)
        hash_suffix = hashlib.md5(cwd.encode()).hexdigest()[:8]
        return f"{project_name}_{hash_suffix}"
    
    def enhance_metadata_with_project(self, metadata: Dict) -> Dict:
        """为元数据添加项目信息"""
        metadata['project_id'] = self.project_id
        metadata['project_name'] = self.project_name
        metadata['project_path'] = os.getcwd()
        metadata['cross_project_session'] = True  # 标记为跨项目共享会话
        return metadata
        
    def setup_logging(self):
        """设置日志配置"""
        log_dir = Path("/Users/jet/Sage/hooks/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "archiver_enhanced.log"
        
        self.logger = logging.getLogger('EnhancedSageArchiver')
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def extract_complete_interaction(self, transcript_path: str) -> Tuple[Optional[str], Optional[str], List[Dict], List[Dict]]:
        """
        从transcript文件中提取完整的交互数据，支持思维链和完整会话历史
        返回: (user_message, assistant_message, tool_calls, tool_results)
        """
        if not Path(transcript_path).exists():
            self.logger.warning(f"Transcript file not found: {transcript_path}")
            return None, None, [], []
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 收集完整会话数据
            complete_conversation = []
            all_tool_calls = []
            all_tool_results = []
            
            # 正向处理，保持时间顺序
            for line in lines:
                try:
                    entry = json.loads(line.strip())
                    entry_type = entry.get('type', '')
                    
                    # 处理assistant消息（包括thinking）
                    if entry_type == 'assistant':
                        message = entry.get('message', {})
                        if message.get('role') == 'assistant':
                            content_list = message.get('content', [])
                            
                            assistant_parts = []
                            
                            for content_item in content_list:
                                if isinstance(content_item, dict):
                                    content_type = content_item.get('type')
                                    
                                    # 捕获思维链内容
                                    if content_type == 'thinking':
                                        thinking_content = content_item.get('thinking', '')
                                        if thinking_content:
                                            assistant_parts.append(f"[思维过程]\n{thinking_content}")
                                    
                                    # 捕获文本回复
                                    elif content_type == 'text':
                                        text_content = content_item.get('text', '')
                                        if text_content:
                                            assistant_parts.append(text_content)
                                    
                                    # 捕获工具调用
                                    elif content_type == 'tool_use':
                                        tool_call = {
                                            'name': content_item.get('name'),
                                            'input': content_item.get('input', {}),
                                            'id': content_item.get('id'),
                                            'timestamp': entry.get('timestamp')
                                        }
                                        all_tool_calls.append(tool_call)
                                        assistant_parts.append(f"[工具调用: {tool_call['name']}]")
                            
                            if assistant_parts:
                                complete_conversation.append({
                                    'role': 'assistant',
                                    'content': '\n\n'.join(assistant_parts),
                                    'timestamp': entry.get('timestamp')
                                })
                    
                    # 处理user消息（包括tool_result）
                    elif entry_type == 'user':
                        message = entry.get('message', {})
                        if message.get('role') == 'user':
                            content_list = message.get('content', [])
                            user_parts = []
                            
                            for content_item in content_list:
                                if isinstance(content_item, dict):
                                    content_type = content_item.get('type')
                                    
                                    # 用户文本输入
                                    if content_type == 'text':
                                        text_content = content_item.get('text', '')
                                        if text_content:
                                            user_parts.append(text_content)
                                    
                                    # 工具执行结果（在user消息中）
                                    elif content_type == 'tool_result':
                                        tool_result = {
                                            'tool_use_id': content_item.get('tool_use_id'),
                                            'content': content_item.get('content'),
                                            'is_error': content_item.get('is_error', False),
                                            'timestamp': entry.get('timestamp')
                                        }
                                        all_tool_results.append(tool_result)
                                        
                                        # 添加简化的结果摘要到对话中
                                        result_summary = str(tool_result['content'])
                                        if len(result_summary) > 200:
                                            result_summary = result_summary[:200] + "..."
                                        user_parts.append(f"[工具结果: {result_summary}]")
                            
                            if user_parts:
                                complete_conversation.append({
                                    'role': 'user', 
                                    'content': '\n\n'.join(user_parts),
                                    'timestamp': entry.get('timestamp')
                                })
                                
                except json.JSONDecodeError:
                    continue
            
            # 构建完整的对话记录
            if complete_conversation:
                # 获取最后一个用户输入和助手回复
                last_user = None
                last_assistant = None
                
                for conv in reversed(complete_conversation):
                    if conv['role'] == 'assistant' and last_assistant is None:
                        last_assistant = conv['content']
                    elif conv['role'] == 'user' and last_user is None:
                        last_user = conv['content']
                    
                    if last_user and last_assistant:
                        break
                
                # 构建包含完整历史的assistant消息
                full_conversation = []
                for conv in complete_conversation:
                    role_prefix = "助手: " if conv['role'] == 'assistant' else "用户: "
                    full_conversation.append(f"{role_prefix}{conv['content']}")
                
                full_assistant_message = f"[完整会话历史]\n" + "\n\n---\n\n".join(full_conversation)
                
                self.logger.info(f"Enhanced extraction - Conversations: {len(complete_conversation)}, Tools: {len(all_tool_calls)}, Results: {len(all_tool_results)}")
                return last_user, full_assistant_message, all_tool_calls, all_tool_results
            
            self.logger.warning("No conversation found in transcript")
            return None, None, [], []
            
        except Exception as e:
            self.logger.error(f"Error extracting enhanced interaction: {e}")
            return None, None, [], []
    
    def call_sage_save(self, user_input: str, assistant_response: str, metadata: Dict) -> bool:
        """调用 Sage MCP 的保存功能"""
        try:
            # 恢复真正的数据保存功能 - 使用CLI方案（同步调用）
            self.logger.info("Attempting to save to Sage MCP via CLI")
            return self._call_sage_save_via_cli(user_input, assistant_response, metadata)
                
        except Exception as e:
            self.logger.error(f"Error in call_sage_save: {e}")
            return False
    
    def _call_sage_save_via_cli(self, user_input: str, assistant_response: str, metadata: Dict) -> bool:
        """通过直接调用Sage MCP Server（修正方案）"""
        try:
            # 直接通过python调用sage MCP的保存功能
            import asyncio
            import sys
            from pathlib import Path
            
            # 添加sage项目路径
            sage_path = Path(__file__).parent.parent.parent
            if str(sage_path) not in sys.path:
                sys.path.insert(0, str(sage_path))
            
            # 确保可以找到requirements中的包
            import os
            if 'VIRTUAL_ENV' not in os.environ:
                # 如果不在虚拟环境中，尝试添加用户的site-packages
                import site
                site.main()
            
            # 直接导入并调用sage core
            from sage_core import MemoryContent
            from sage_core.singleton_manager import get_sage_core
            
            async def save_to_sage():
                sage = await get_sage_core()
                # 添加必需的配置参数，与sage_mcp_stdio_single.py保持一致
                config = {
                    "database": {
                        "host": os.getenv("DB_HOST", "localhost"),
                        "port": int(os.getenv("DB_PORT", "5432")),
                        "database": os.getenv("DB_NAME", "sage_memory"),
                        "user": os.getenv("DB_USER", "sage"),
                        "password": os.getenv("DB_PASSWORD", "sage123")
                    },
                    "embedding": {
                        "model": os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
                        "device": os.getenv("EMBEDDING_DEVICE", "cpu")
                    }
                }
                await sage.initialize(config)
                
                content = MemoryContent(
                    user_input=user_input,
                    assistant_response=assistant_response,
                    metadata=metadata
                )
                return await sage.save_memory(content)
            
            # 在新的事件循环中运行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                memory_id = loop.run_until_complete(save_to_sage())
                self.logger.info(f"Successfully saved to Sage Core: {memory_id}")
                return True
            finally:
                loop.close()
                
        except ImportError as e:
            missing_module = None
            error_msg = str(e)
            
            # 检测缺失的模块
            if "asyncpg" in error_msg:
                missing_module = "asyncpg>=0.29.0"
            elif "dotenv" in error_msg:
                missing_module = "python-dotenv>=1.0.0"
            elif "aiofiles" in error_msg:
                missing_module = "aiofiles>=23.2.1"
            elif "numpy" in error_msg:
                missing_module = "numpy>=1.24.0"
            elif "PyJWT" in error_msg or "jwt" in error_msg:
                missing_module = "PyJWT>=2.8.0"
            elif "requests" in error_msg:
                missing_module = "requests>=2.31.0"
            
            if missing_module:
                self.logger.error(f"Failed to save via direct call: Missing {missing_module.split('>=')[0]} module. Installing...")
                # 尝试安装缺失的模块
                try:
                    import subprocess
                    result = subprocess.run([sys.executable, "-m", "pip", "install", missing_module], 
                                          capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        self.logger.info(f"Successfully installed {missing_module}, please try again")
                        # 安装成功后可以选择重试一次
                        # 但为了避免无限循环，这里只记录日志
                    else:
                        self.logger.error(f"Failed to install {missing_module}: {result.stderr}")
                except Exception as install_error:
                    self.logger.error(f"Error installing {missing_module}: {install_error}")
            else:
                self.logger.error(f"Failed to save via direct call (ImportError): {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to save via direct call: {e}")
            return False
    
    def process_hook(self, input_data: Dict) -> Dict:
        """处理 Stop Hook 输入"""
        self.logger.info("Processing Stop Hook")
        
        # 提取 transcript 路径
        transcript_path = input_data.get('transcript_path', '')
        if not transcript_path:
            self.logger.error("No transcript_path provided")
            return {"status": "error", "message": "No transcript_path provided"}
        
        # 提取完整交互数据
        user_message, assistant_message, tool_calls, tool_results = self.extract_complete_interaction(str(transcript_path))
        
        if not user_message or not assistant_message:
            self.logger.warning("No complete conversation found to archive")
            return {"status": "skipped", "message": "No complete conversation found"}
        
        # 构建增强的元数据
        metadata = {
            "session_id": input_data.get('session_id', 'unknown'),
            "tags": ["claude-code", "stop-hook", "enhanced"],
            "cwd": str(Path.cwd()),
            "archiver_version": "3.0.0",
            "tool_calls_count": len(tool_calls),
            "tool_results_count": len(tool_results),
            "data_completeness": "enhanced"  # 标记为增强版数据
        }
        
        # 添加项目信息
        metadata = self.enhance_metadata_with_project(metadata)
        
        # 如果有工具调用，添加到元数据
        if tool_calls:
            metadata['tool_calls'] = tool_calls
            metadata['tool_names'] = list(set(tc['name'] for tc in tool_calls if tc.get('name')))
        
        if tool_results:
            metadata['has_tool_errors'] = any(tr.get('is_error', False) for tr in tool_results)
        
        # 使用数据聚合器增强数据（如果可用）
        if has_aggregator:
            try:
                aggregator = get_aggregator()
                session_id = input_data.get('session_id', 'unknown')
                
                # 获取增强的工具调用链和元数据
                enhanced_tool_chain, enhanced_metadata = aggregator.enhance_stop_hook_data(
                    session_id, user_message, assistant_message, tool_calls, tool_results
                )
                
                # 合并增强数据到元数据
                metadata['enhanced_tool_chain'] = enhanced_tool_chain
                metadata['data_completeness_score'] = enhanced_metadata.get('data_completeness_score', 0)
                metadata['aggregation_stats'] = enhanced_metadata.get('aggregation_stats', {})
                metadata['data_sources'] = enhanced_metadata.get('data_sources', {})
                
                self.logger.info(f"Data enhanced with aggregator. Completeness: {metadata['data_completeness_score']:.2%}")
                
                # 生成会话报告（如果工具调用较多）
                if len(enhanced_tool_chain) > 5:
                    report = aggregator.generate_session_report(session_id)
                    metadata['session_report'] = report
                    
            except Exception as e:
                self.logger.error(f"Error using data aggregator: {e}")
                # 继续执行，不影响主流程
        
        # 调用 Sage 保存
        start_time = time.time()
        success = self.call_sage_save(user_message, assistant_message, metadata)
        elapsed_time = time.time() - start_time
        
        self.logger.info(f"Archive operation completed in {elapsed_time:.2f}s")
        
        if success:
            return {
                "status": "success",
                "message": f"Conversation archived successfully for project {self.project_name}",
                "elapsed_time": elapsed_time,
                "project_id": self.project_id,
                "data_completeness": "enhanced"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to archive conversation",
                "elapsed_time": elapsed_time
            }

def main():
    """主函数"""
    try:
        # 读取标准输入
        input_data = json.load(sys.stdin)
        
        # 创建归档器实例并处理
        archiver = EnhancedSageArchiver()
        result = archiver.process_hook(input_data)
        
        # 输出结果
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Hook execution error: {str(e)}"
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()