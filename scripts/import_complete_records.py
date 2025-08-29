#!/usr/bin/env python3
"""
完整记录导入工具 - 将Hook记录和Claude CLI transcript导入Docker数据库
支持完整的记录和向量存储
"""

import json
import sys
import asyncio
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ImportCompleteRecords')

class CompleteRecordsImporter:
    """完整记录导入器"""
    
    def __init__(self):
        self.sage_core = None
        self.imported_count = 0
        self.failed_count = 0
        self.vectorized_count = 0
        
        # 数据源路径
        # 使用用户主目录，跨平台兼容
        home_dir = Path.home()
        self.hook_records_dir = home_dir / '.sage_hooks_temp'
        self.claude_transcripts_dir = home_dir / '.claude' / 'projects' / '-Users-jet-sage'
        
        logger.info("完整记录导入器初始化完成")
    
    async def initialize_sage_core(self):
        """初始化Sage Core"""
        try:
            from sage_core.singleton_manager import get_sage_core
            from sage_core.interfaces.core_service import MemoryContent
            
            self.sage_core = await get_sage_core()
            
            # 配置Sage Core
            config = {
                'database_url': 'postgresql://sage:sage123@localhost:5432/sage_memory',
                'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2'
            }
            
            await self.sage_core.initialize(config)
            logger.info("✅ Sage Core初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ Sage Core初始化失败: {e}")
            return False
    
    def parse_hook_record(self, hook_file: Path) -> Optional[Dict[str, Any]]:
        """解析Hook记录文件"""
        try:
            with open(hook_file, 'r', encoding='utf-8') as f:
                hook_data = json.load(f)
            
            pre_call = hook_data.get('pre_call', {})
            post_call = hook_data.get('post_call', {})
            
            # 构建用户输入和助手响应
            tool_name = pre_call.get('tool_name', 'unknown')
            tool_input = pre_call.get('tool_input', {})
            tool_output = post_call.get('tool_output', {})
            
            user_input = f"工具调用: {tool_name}"
            if tool_input:
                user_input += f"\n输入参数: {json.dumps(tool_input, ensure_ascii=False, indent=2)}"
            
            assistant_response = f"工具执行结果:"
            if tool_output:
                # 处理不同类型的工具输出
                if isinstance(tool_output, dict):
                    if 'content' in tool_output:
                        # 文件读取类工具
                        assistant_response += f"\n文件内容:\n{tool_output.get('content', '')}"
                    elif 'stdout' in tool_output:
                        # Bash工具
                        assistant_response += f"\n标准输出:\n{tool_output.get('stdout', '')}"
                        if tool_output.get('stderr'):
                            assistant_response += f"\n错误输出:\n{tool_output.get('stderr', '')}"
                    else:
                        assistant_response += f"\n{json.dumps(tool_output, ensure_ascii=False, indent=2)}"
                else:
                    assistant_response += f"\n{str(tool_output)}"
            
            # 添加执行信息
            execution_time = post_call.get('execution_time_ms')
            if execution_time:
                assistant_response += f"\n\n执行时间: {execution_time}ms"
            
            if post_call.get('is_error'):
                assistant_response += f"\n错误: {post_call.get('error_message', '')}"
            
            # 构建元数据
            metadata = {
                'source': 'hook_record',
                'session_id': pre_call.get('session_id', ''),
                'project_id': pre_call.get('project_id', ''),
                'project_name': pre_call.get('project_name', ''),
                'tool_name': tool_name,
                'call_id': hook_data.get('call_id', ''),
                'timestamp': pre_call.get('timestamp', time.time()),
                'execution_time_ms': execution_time,
                'is_error': post_call.get('is_error', False),
                'format': 'hook_complete_record'
            }
            
            return {
                'user_input': user_input,
                'assistant_response': assistant_response,
                'metadata': metadata,
                'session_id': pre_call.get('session_id', f"hook-{int(time.time())}")
            }
            
        except Exception as e:
            logger.error(f"解析Hook记录失败 {hook_file}: {e}")
            return None
    
    def parse_claude_transcript(self, transcript_file: Path) -> List[Dict[str, Any]]:
        """解析Claude CLI transcript文件"""
        conversations = []
        
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            messages = []
            session_id = transcript_file.stem  # 使用文件名作为session_id
            
            # 解析transcript中的消息
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line.strip())
                    entry_type = entry.get('type', '')
                    
                    if entry_type in ['user', 'assistant']:
                        message = entry.get('message', {})
                        content = message.get('content', [])
                        
                        # 处理内容
                        content_parts = []
                        if isinstance(content, str):
                            content_parts.append(content)
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get('type') == 'text':
                                        content_parts.append(item.get('text', ''))
                                    elif item.get('type') == 'thinking':
                                        thinking_content = item.get('thinking', '')
                                        content_parts.append(f"[思维链]\n{thinking_content}")
                                    elif item.get('type') == 'tool_use':
                                        tool_name = item.get('name', 'unknown_tool')
                                        tool_input = item.get('input', {})
                                        content_parts.append(f"[工具调用: {tool_name}]\n{json.dumps(tool_input, ensure_ascii=False, indent=2)}")
                                elif isinstance(item, str):
                                    content_parts.append(item)
                        
                        if content_parts:
                            role = 'user' if entry_type == 'user' else 'assistant'
                            messages.append({
                                'role': role,
                                'content': '\n'.join(content_parts),
                                'timestamp': entry.get('timestamp'),
                                'uuid': entry.get('uuid')
                            })
                
                except json.JSONDecodeError:
                    continue
            
            # 将消息配对成对话
            user_messages = [m for m in messages if m['role'] == 'user']
            assistant_messages = [m for m in messages if m['role'] == 'assistant']
            
            # 创建完整对话记录
            if user_messages and assistant_messages:
                # 如果有多轮对话，创建一个综合记录
                all_user_content = []
                all_assistant_content = []
                
                for msg in user_messages:
                    all_user_content.append(msg['content'])
                
                for msg in assistant_messages:
                    all_assistant_content.append(msg['content'])
                
                conversation = {
                    'user_input': '\n\n'.join(all_user_content),
                    'assistant_response': '\n\n'.join(all_assistant_content),
                    'metadata': {
                        'source': 'claude_transcript',
                        'session_id': session_id,
                        'project_name': 'Sage',
                        'message_count': len(messages),
                        'user_message_count': len(user_messages),
                        'assistant_message_count': len(assistant_messages),
                        'format': 'claude_cli_transcript',
                        'file_path': str(transcript_file)
                    },
                    'session_id': session_id
                }
                conversations.append(conversation)
            
        except Exception as e:
            logger.error(f"解析Claude transcript失败 {transcript_file}: {e}")
        
        return conversations
    
    async def import_record(self, record: Dict[str, Any]) -> bool:
        """导入单条记录到数据库"""
        try:
            from sage_core.interfaces.core_service import MemoryContent
            
            # 构建MemoryContent对象
            content = MemoryContent(
                user_input=record['user_input'],
                assistant_response=record['assistant_response'],
                metadata=record['metadata'],
                session_id=record['session_id']
            )
            
            # 保存到数据库并向量化
            memory_id = await self.sage_core.save_memory(content)
            
            if memory_id and memory_id != "":
                self.imported_count += 1
                self.vectorized_count += 1
                return True
            else:
                self.failed_count += 1
                return False
                
        except Exception as e:
            logger.error(f"导入记录失败: {e}")
            self.failed_count += 1
            return False
    
    async def import_hook_records(self) -> int:
        """导入Hook完整记录"""
        logger.info(f"开始导入Hook记录从: {self.hook_records_dir}")
        
        if not self.hook_records_dir.exists():
            logger.warning(f"Hook记录目录不存在: {self.hook_records_dir}")
            return 0
        
        hook_files = list(self.hook_records_dir.glob('complete_*.json'))
        logger.info(f"找到 {len(hook_files)} 个Hook记录文件")
        
        imported = 0
        for hook_file in hook_files:
            record = self.parse_hook_record(hook_file)
            if record:
                success = await self.import_record(record)
                if success:
                    imported += 1
                    if imported % 10 == 0:
                        logger.info(f"已导入 {imported}/{len(hook_files)} 个Hook记录")
        
        logger.info(f"✅ Hook记录导入完成: {imported}/{len(hook_files)}")
        return imported
    
    async def import_claude_transcripts(self) -> int:
        """导入Claude CLI transcript文件"""
        logger.info(f"开始导入Claude transcript从: {self.claude_transcripts_dir}")
        
        if not self.claude_transcripts_dir.exists():
            logger.warning(f"Claude transcript目录不存在: {self.claude_transcripts_dir}")
            return 0
        
        transcript_files = list(self.claude_transcripts_dir.glob('*.jsonl'))
        logger.info(f"找到 {len(transcript_files)} 个Claude transcript文件")
        
        imported = 0
        for transcript_file in transcript_files:
            conversations = self.parse_claude_transcript(transcript_file)
            for conversation in conversations:
                success = await self.import_record(conversation)
                if success:
                    imported += 1
            
            if imported % 10 == 0:
                logger.info(f"已处理 {transcript_files.index(transcript_file)+1}/{len(transcript_files)} 个transcript文件")
        
        logger.info(f"✅ Claude transcript导入完成: {imported} 条记录")
        return imported
    
    async def run_import(self):
        """执行完整导入流程"""
        logger.info("🚀 开始完整记录导入流程")
        
        # 初始化Sage Core
        if not await self.initialize_sage_core():
            logger.error("❌ 无法初始化Sage Core，导入终止")
            return
        
        start_time = time.time()
        
        try:
            # 导入Hook记录
            hook_imported = await self.import_hook_records()
            
            # 导入Claude transcript
            claude_imported = await self.import_claude_transcripts()
            
            total_time = time.time() - start_time
            
            # 输出统计结果
            logger.info("=" * 60)
            logger.info("📊 完整记录导入统计:")
            logger.info(f"Hook记录导入: {hook_imported}")
            logger.info(f"Claude transcript导入: {claude_imported}")
            logger.info(f"总导入数量: {self.imported_count}")
            logger.info(f"向量化数量: {self.vectorized_count}")
            logger.info(f"失败数量: {self.failed_count}")
            logger.info(f"总耗时: {total_time:.2f}秒")
            logger.info("=" * 60)
            
            if self.imported_count > 0:
                logger.info("🎉 完整记录导入成功完成！")
            else:
                logger.warning("⚠️ 没有记录被导入")
                
        except Exception as e:
            logger.error(f"❌ 导入过程出现异常: {e}")
        
        finally:
            # 清理资源
            if self.sage_core:
                try:
                    await self.sage_core.close()
                except:
                    pass

async def main():
    """主函数"""
    importer = CompleteRecordsImporter()
    await importer.run_import()

if __name__ == "__main__":
    asyncio.run(main())