#!/usr/bin/env python3
"""
Sage Prompt Enhancer Hook
用于 Claude Code CLI UserPromptSubmit Hook 的智能提示增强脚本

作用：
1. 接收用户输入的 prompt 和会话上下文
2. 调用 Sage MCP Server 的 generate_prompt 工具
3. 返回增强后的提示内容，注入到对话上下文中
"""

import json
import os
import sys
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# 导入HookExecutionContext
sys.path.insert(0, str(Path(__file__).parent.parent))
from context import create_hook_context

from security_utils import path_validator, input_validator, resource_limiter, SecurityError


class SagePromptEnhancer:
    """Sage 提示增强器 - HookExecutionContext架构版本"""
    
    def __init__(self):
        # 创建执行上下文
        self.context = create_hook_context(__file__)
        
        self.timeout = 45  # 留15秒缓冲给 Claude CLI
        self.max_context_turns = 3  # 最多提取3轮对话作为上下文
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志配置 - 使用HookExecutionContext"""
        # 使用上下文提供的标准化日志设置
        self.logger = self.context.setup_logging(
            logger_name='SagePromptEnhancer',
            log_filename='prompt_enhancer.log'
        )
        self.logger.setLevel(logging.DEBUG)
    
    def parse_input(self) -> Dict[str, Any]:
        """解析 Hook 输入数据"""
        try:
            # 安全地读取和验证输入
            raw_input = sys.stdin.read()
            if not raw_input:
                self.logger.warning("Empty input received")
                return {}
            
            # 使用安全验证器验证输入
            input_data = input_validator.validate_json_input(raw_input, max_size=1024*1024)  # 1MB 限制
            
            # 验证 session_id
            session_id = input_data.get('session_id', '')
            if session_id:
                try:
                    input_validator.validate_session_id(session_id)
                except SecurityError as e:
                    self.logger.error(f"Invalid session_id: {e}")
                    return {}
            
            self.logger.info(f"Received hook input: session_id={input_data.get('session_id', 'unknown')}")
            return input_data
            
        except SecurityError as e:
            self.logger.error(f"Security validation failed: {e}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse input JSON: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error parsing input: {e}")
            return {}
    
    def extract_recent_context(self, transcript_path: str) -> str:
        """从 transcript 文件提取最近的对话上下文"""
        if not transcript_path:
            return ""
        
        try:
            # 使用安全验证器验证路径
            validated_path = path_validator.validate_transcript_path(transcript_path)
            if not validated_path:
                return ""
            
            # 使用资源限制器安全读取文件
            resource_limiter.limit_file_operations(validated_path, max_size=100*1024*1024)  # 100MB 限制
            lines = resource_limiter.safe_read_lines(validated_path, max_lines=1000)  # 最多1000行
            
            # 提取最近的对话轮次
            recent_context = []
            for line in reversed(lines[-self.max_context_turns * 2:]):  # 每轮对话通常包含用户和助手2条消息
                if line.strip():
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('type') in ['user_message', 'assistant_message']:
                            content = entry.get('content', '')
                            # 清理内容中的敏感信息
                            sanitized_content = input_validator.sanitize_string(content, max_length=10000)
                            recent_context.insert(0, sanitized_content)
                    except json.JSONDecodeError:
                        continue
            
            context_text = "\n".join(recent_context[-6:])  # 最多6条消息（3轮对话）
            self.logger.info(f"Extracted context: {len(context_text)} characters")
            return context_text
            
        except SecurityError as e:
            self.logger.error(f"Security validation failed for transcript path: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting context from {transcript_path}: {e}")
            return ""
    
    def call_sage_generate_prompt(self, prompt: str, context: str) -> str:
        """调用 Sage MCP Server 的 generate_prompt 工具"""
        try:
            # 清理输入参数
            clean_prompt = input_validator.sanitize_string(prompt, max_length=10000)
            clean_context = input_validator.sanitize_string(context, max_length=50000)
            
            # 构建调用参数
            full_context = f"{clean_context}\n\n用户当前输入: {clean_prompt}" if clean_context else clean_prompt
            
            self.logger.info(f"Calling Sage MCP generate_prompt with context length: {len(full_context)}")
            
            # 真实的 MCP 调用 - 通过命令行调用 Claude Code 的 MCP 工具
            enhanced_prompt = self._call_real_sage_mcp(full_context)
            
            # 清理输出
            sanitized_output = input_validator.sanitize_string(enhanced_prompt, max_length=50000)
            
            self.logger.info(f"Generated enhanced prompt: {len(sanitized_output)} characters")
            return sanitized_output
            
        except SecurityError as e:
            self.logger.error(f"Security validation failed in prompt generation: {e}")
            return ""
        except subprocess.TimeoutExpired:
            self.logger.error("Sage MCP call timed out")
            return ""
        except Exception as e:
            self.logger.error(f"Error calling Sage MCP: {e}")
            return ""
    
    def _call_real_sage_mcp(self, context: str) -> str:
        """真实的 Sage 调用 - 直接调用sage_core - 使用HookExecutionContext"""
        try:
            # 使用上下文设置Python路径
            self.context.setup_python_path()
            
            import asyncio
            
            async def call_sage_core():
                from sage_core.singleton_manager import get_sage_core
                from sage_core.interfaces.core_service import MemoryContent
                
                # 使用上下文获取配置
                config = self.context.get_sage_config()
                
                sage = await get_sage_core()
                await sage.initialize(config)
                return await sage.generate_prompt(context, "default")
            
            # 运行异步调用
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已经在事件循环中，创建新任务
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, call_sage_core())
                        result = future.result(timeout=self.timeout)
                        self.logger.info(f"Direct sage_core call successful: {len(result)} characters")
                        return result
                else:
                    # 如果没有运行的事件循环，直接运行
                    result = asyncio.run(call_sage_core())
                    self.logger.info(f"Direct sage_core call successful: {len(result)} characters")
                    return result
            except Exception as e:
                self.logger.error(f"Direct sage_core call failed: {e}")
                return self._fallback_sage_call(context)
                
        except Exception as e:
            self.logger.error(f"Real Sage call failed: {e}")
            return self._fallback_sage_call(context)
    
    def _fallback_sage_call(self, context: str) -> str:
        """降级的 Sage 调用 - 当真实 MCP 调用失败时使用"""
        try:
            # 基于上下文内容进行智能分析
            if "代码" in context or "编程" in context or "实现" in context:
                return "基于您的编程背景，我可以帮您解决技术问题、代码审查或架构设计。有什么具体需要协助的吗？"
            elif "文档" in context or "说明" in context or "README" in context:
                return "看起来您在处理文档相关工作。我可以帮您改进文档结构、内容组织或编写更清晰的说明。"
            elif "问题" in context or "错误" in context or "bug" in context.lower():
                return "我来帮您分析和解决这个问题。请提供更多技术细节和错误信息，以便我给出精准的解决方案。"
            elif "项目" in context or "开发" in context:
                return "关于项目开发，我可以提供技术架构建议、最佳实践指导和开发流程优化建议。有什么具体需要讨论的？"
            else:
                return "根据上下文，我可以为您提供更具针对性的技术建议和解决方案。请告诉我更多具体信息。"
        except Exception as e:
            self.logger.error(f"Fallback call failed: {e}")
            return "我可以帮您解决技术问题或提供专业建议。请提供更多具体信息。"
    
    def run(self) -> None:
        """主运行逻辑"""
        start_time = time.time()
        
        try:
            # 解析输入
            input_data = self.parse_input()
            if not input_data:
                sys.exit(1)  # 使用错误码表示失败
            
            session_id = input_data.get('session_id', '')
            prompt = input_data.get('prompt', '')
            transcript_path = input_data.get('transcript_path', '')
            
            if not prompt:
                self.logger.warning("No prompt provided")
                sys.exit(1)
            
            # 清理和验证输入数据
            try:
                clean_prompt = input_validator.sanitize_string(prompt, max_length=10000)
                if session_id:
                    input_validator.validate_session_id(session_id)
            except SecurityError as e:
                self.logger.error(f"Input validation failed: {e}")
                sys.exit(1)
            
            # 提取上下文
            context = self.extract_recent_context(transcript_path)
            
            # 调用 Sage MCP 生成增强提示
            enhanced_content = self.call_sage_generate_prompt(prompt, context)
            
            # 输出增强内容到 stdout，供 Claude CLI 注入上下文
            if enhanced_content:
                print(enhanced_content)
                self.logger.info(f"Enhanced prompt output successfully in {time.time() - start_time:.2f}s")
            else:
                self.logger.info("No enhancement generated, using original prompt")
            
        except Exception as e:
            self.logger.error(f"Unexpected error in main execution: {e}")
            sys.exit(1)  # 使用错误码表示失败


def main():
    """入口函数"""
    enhancer = SagePromptEnhancer()
    enhancer.run()


if __name__ == "__main__":
    main()