# Claude-Mem 智能记忆系统完整执行计划

## 执行概要

将 `claude-mem` 升级为透明、智能的记忆层，完全替代原始 `claude` 命令。整个过程分为四个主要阶段，预计需要 3.5-4.5 个开发日。

### 目标达成
- ✅ 用户输入 `claude` 后自动存储完整对话（问题+回答）
- ✅ 每次调用默认检索相关历史上下文
- ✅ 智能拼接历史与当前查询形成增强提示
- ✅ 完全透明，用户无需改变使用习惯

---

## 阶段 1：完整对话捕获与参数透传（1-2天）

这是最关键的阶段，必须正确捕获完整对话并处理所有原生参数。

### 1.1 核心任务

#### 任务 A：修改参数解析逻辑
**文件**：`sage_crossplatform.py`

```python
def parse_claude_arguments_v2(self, args: List[str]) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    智能解析 Claude 命令行参数
    返回：(用户提示, claude参数列表, 解析选项)
    """
    parser = argparse.ArgumentParser(add_help=False)
    
    # 我们自己的参数
    parser.add_argument('--no-memory', action='store_true', help='禁用记忆功能')
    parser.add_argument('--clear-memory', action='store_true', help='清除所有记忆')
    parser.add_argument('--memory-stats', action='store_true', help='显示记忆统计')
    
    # 使用 parse_known_args 分离参数
    our_args, remaining_args = parser.parse_known_args(args)
    
    # 从剩余参数中提取用户提示
    user_prompt = None
    claude_args = []
    
    # Claude 的已知选项参数
    claude_options = {
        '-m', '--model', '-t', '--temperature', '-o', '--output',
        '-f', '--file', '--max-tokens', '--stop-sequences'
    }
    
    i = 0
    while i < len(remaining_args):
        arg = remaining_args[i]
        
        if arg in claude_options:
            # 这是 Claude 的选项，需要包含下一个参数
            claude_args.append(arg)
            if i + 1 < len(remaining_args):
                claude_args.append(remaining_args[i + 1])
                i += 2
            else:
                i += 1
        elif arg.startswith('-'):
            # 其他选项参数
            claude_args.append(arg)
            i += 1
        else:
            # 第一个非选项参数是用户提示
            if user_prompt is None:
                user_prompt = arg
            else:
                claude_args.append(arg)
            i += 1
    
    return user_prompt, claude_args, {
        'no_memory': our_args.no_memory,
        'clear_memory': our_args.clear_memory,
        'memory_stats': our_args.memory_stats
    }
```

#### 任务 B：实现响应捕获机制
**文件**：`sage_crossplatform.py`

```python
def execute_with_capture(self, claude_path: str, user_prompt: str, claude_args: List[str]) -> Tuple[int, str]:
    """
    执行 Claude 并捕获完整响应
    使用 tee 模式：同时显示给用户和保存到变量
    """
    import io
    import threading
    
    # 构建完整命令
    full_command = [claude_path] + claude_args
    if user_prompt:
        full_command.append(user_prompt)
    
    # 创建进程
    process = subprocess.Popen(
        full_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        bufsize=1,  # 行缓冲
        universal_newlines=True
    )
    
    # 响应收集器
    response_lines = []
    response_lock = threading.Lock()
    
    def capture_and_display(pipe, is_stderr=False):
        """捕获并显示输出"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    # 实时显示
                    if is_stderr:
                        sys.stderr.write(line)
                        sys.stderr.flush()
                    else:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    
                    # 保存到列表（仅保存 stdout）
                    if not is_stderr:
                        with response_lock:
                            response_lines.append(line)
        finally:
            pipe.close()
    
    # 创建线程处理输出
    stdout_thread = threading.Thread(
        target=capture_and_display, 
        args=(process.stdout,),
        daemon=True
    )
    stderr_thread = threading.Thread(
        target=capture_and_display, 
        args=(process.stderr, True),
        daemon=True
    )
    
    stdout_thread.start()
    stderr_thread.start()
    
    # 等待进程完成
    return_code = process.wait()
    stdout_thread.join()
    stderr_thread.join()
    
    # 合并响应
    full_response = ''.join(response_lines)
    
    return return_code, full_response
```

#### 任务 C：更新数据库存储逻辑
**文件**：`memory.py`

```python
def save_conversation_turn(user_prompt: str, assistant_response: str, metadata: Optional[Dict] = None):
    """
    保存完整的对话轮次
    
    Args:
        user_prompt: 用户输入
        assistant_response: Claude 的响应
        metadata: 额外元数据（时间戳、模型等）
    """
    timestamp = datetime.now().isoformat()
    
    # 默认元数据
    default_metadata = {
        'timestamp': timestamp,
        'turn_id': str(uuid.uuid4()),
        'model': metadata.get('model', 'unknown') if metadata else 'unknown'
    }
    
    if metadata:
        default_metadata.update(metadata)
    
    # 保存用户消息
    add_memory(
        content=user_prompt,
        metadata={**default_metadata, 'role': 'user'}
    )
    
    # 保存助手响应
    add_memory(
        content=assistant_response,
        metadata={**default_metadata, 'role': 'assistant'}
    )
    
    logger.info(f"对话轮次已保存: {default_metadata['turn_id']}")
```

### 1.2 测试验证

#### 测试用例 1：基础对话捕获
```bash
# 测试简单查询
claude-mem "你好，请介绍一下自己"

# 验证数据库
python -c "from memory import get_all_memories; print(get_all_memories()[-2:])"
```

#### 测试用例 2：复杂参数传递
```bash
# 测试带参数的查询
claude-mem "总结这个文件" -f README.md --model claude-3-haiku

# 测试多个参数
claude-mem "写一个Python函数" --temperature 0.7 --max-tokens 500
```

#### 测试用例 3：流式输出
```bash
# 测试长输出的实时显示
claude-mem "写一个1000字的故事"
```

---

## 阶段 2：记忆增强提示生成（1天）

实现智能上下文检索和提示增强。

### 2.1 核心任务

#### 任务 A：实现智能上下文检索
**文件**：`memory.py`

```python
def retrieve_relevant_context(
    query: str, 
    num_results: int = 5,
    similarity_threshold: float = 0.7,
    time_decay: bool = True,
    max_age_days: int = 30
) -> List[Dict[str, Any]]:
    """
    智能检索相关上下文
    
    Args:
        query: 当前查询
        num_results: 返回结果数量
        similarity_threshold: 相似度阈值
        time_decay: 是否应用时间衰减
        max_age_days: 最大历史天数
    
    Returns:
        相关上下文列表
    """
    # 基础向量检索
    results = search_memory(query, n=num_results * 2)  # 获取更多以便过滤
    
    # 过滤和排序
    filtered_results = []
    now = datetime.now()
    
    for result in results:
        # 相似度过滤
        if result.get('score', 0) < similarity_threshold:
            continue
        
        # 时间过滤
        if max_age_days > 0:
            timestamp = datetime.fromisoformat(result['metadata']['timestamp'])
            age_days = (now - timestamp).days
            if age_days > max_age_days:
                continue
        
        # 时间衰减计算
        if time_decay:
            timestamp = datetime.fromisoformat(result['metadata']['timestamp'])
            age_hours = (now - timestamp).total_seconds() / 3600
            # 指数衰减：24小时内权重为1，每过24小时权重减半
            time_weight = 0.5 ** (age_hours / 24)
            result['final_score'] = result['score'] * time_weight
        else:
            result['final_score'] = result['score']
        
        filtered_results.append(result)
    
    # 按最终得分排序
    filtered_results.sort(key=lambda x: x['final_score'], reverse=True)
    
    # 返回前N个结果
    return filtered_results[:num_results]


def format_context_for_prompt(contexts: List[Dict[str, Any]], max_tokens: int = 2000) -> str:
    """
    格式化上下文为提示文本
    
    Args:
        contexts: 检索到的上下文列表
        max_tokens: 最大token数（粗略估计）
    
    Returns:
        格式化的上下文字符串
    """
    if not contexts:
        return ""
    
    formatted_parts = []
    estimated_tokens = 0
    
    for ctx in contexts:
        role = ctx['metadata'].get('role', 'unknown')
        content = ctx['content']
        timestamp = ctx['metadata'].get('timestamp', '')
        
        # 格式化单条记录
        if role == 'user':
            formatted = f"[用户 {timestamp[:10]}]: {content}"
        elif role == 'assistant':
            formatted = f"[助手 {timestamp[:10]}]: {content}"
        else:
            formatted = f"[{timestamp[:10]}]: {content}"
        
        # 粗略估计 tokens（4个字符约等于1个token）
        part_tokens = len(formatted) // 4
        
        if estimated_tokens + part_tokens > max_tokens:
            # 如果超出限制，截断当前内容
            remaining_tokens = max_tokens - estimated_tokens
            if remaining_tokens > 100:  # 至少保留100个token的内容
                max_chars = remaining_tokens * 4
                formatted = formatted[:max_chars] + "..."
                formatted_parts.append(formatted)
            break
        
        formatted_parts.append(formatted)
        estimated_tokens += part_tokens
    
    return "\n".join(formatted_parts)
```

#### 任务 B：实现提示增强逻辑
**文件**：`sage_crossplatform.py`

```python
def build_enhanced_prompt(self, user_prompt: str, config: Dict[str, Any]) -> str:
    """
    构建增强的提示
    """
    # 检查是否启用记忆
    if not config.get('memory_enabled', True):
        return user_prompt
    
    # 检索相关上下文
    try:
        contexts = retrieve_relevant_context(
            query=user_prompt,
            num_results=config.get('retrieval_count', 3),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            time_decay=config.get('time_decay', True),
            max_age_days=config.get('max_age_days', 30)
        )
        
        if not contexts:
            return user_prompt
        
        # 格式化上下文
        context_str = format_context_for_prompt(
            contexts,
            max_tokens=config.get('max_context_tokens', 2000)
        )
        
        # 使用配置的模板或默认模板
        template = config.get('prompt_template', self.DEFAULT_PROMPT_TEMPLATE)
        
        enhanced_prompt = template.format(
            context=context_str,
            query=user_prompt
        )
        
        # 记录增强信息
        self.logger.info(f"提示已增强，添加了 {len(contexts)} 条相关记忆")
        
        return enhanced_prompt.strip()
        
    except Exception as e:
        self.logger.error(f"提示增强失败: {e}")
        # 失败时返回原始提示
        return user_prompt

# 默认提示模板
DEFAULT_PROMPT_TEMPLATE = """基于我们之前的对话历史，请回答以下问题。

相关历史对话：
{context}

当前问题：{query}

请结合历史上下文（如果相关）来回答。如果历史信息不相关，可以忽略。"""
```

### 2.2 性能优化

#### 任务 A：实现缓存机制
**文件**：`memory_cache.py`（新建）

```python
from functools import lru_cache
from typing import List, Dict, Any
import hashlib
import time

class MemoryCache:
    """内存缓存管理器"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache = {}
        self._access_times = {}
    
    def _get_cache_key(self, query: str, params: Dict) -> str:
        """生成缓存键"""
        param_str = str(sorted(params.items()))
        content = f"{query}:{param_str}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, params: Dict) -> Optional[List[Dict]]:
        """获取缓存的检索结果"""
        key = self._get_cache_key(query, params)
        
        if key in self._cache:
            # 检查是否过期
            if time.time() - self._access_times[key] < self.ttl:
                self._access_times[key] = time.time()  # 更新访问时间
                return self._cache[key]
            else:
                # 过期，删除
                del self._cache[key]
                del self._access_times[key]
        
        return None
    
    def set(self, query: str, params: Dict, results: List[Dict]):
        """设置缓存"""
        key = self._get_cache_key(query, params)
        self._cache[key] = results
        self._access_times[key] = time.time()
        
        # 清理过期缓存（简单策略：当缓存数量超过100时）
        if len(self._cache) > 100:
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, access_time in self._access_times.items()
            if current_time - access_time > self.ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
            del self._access_times[key]

# 全局缓存实例
memory_cache = MemoryCache(ttl_seconds=300)  # 5分钟缓存
```

#### 任务 B：异步保存实现
**文件**：`sage_crossplatform.py`

```python
import concurrent.futures
import atexit

class AsyncSaver:
    """异步保存管理器"""
    
    def __init__(self, max_workers: int = 2):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._futures = []
        
        # 注册退出时的清理函数
        atexit.register(self.shutdown)
    
    def save_async(self, user_prompt: str, response: str, metadata: Dict):
        """异步保存对话"""
        future = self.executor.submit(
            save_conversation_turn,
            user_prompt,
            response,
            metadata
        )
        
        # 添加错误处理
        future.add_done_callback(self._handle_save_result)
        self._futures.append(future)
        
        # 清理已完成的 futures
        self._futures = [f for f in self._futures if not f.done()]
    
    def _handle_save_result(self, future):
        """处理保存结果"""
        try:
            future.result()
        except Exception as e:
            logger.error(f"异步保存失败: {e}")
    
    def shutdown(self):
        """关闭执行器"""
        # 等待所有保存完成
        for future in self._futures:
            try:
                future.result(timeout=5)
            except:
                pass
        
        self.executor.shutdown(wait=True)

# 全局异步保存器
async_saver = AsyncSaver()
```

### 2.3 测试验证

#### 测试用例 1：上下文检索
```python
# 测试脚本：test_context_retrieval.py
from memory import retrieve_relevant_context

# 添加一些测试数据
test_conversations = [
    ("Python中如何处理异常？", "在Python中，使用try-except语句处理异常..."),
    ("解释一下装饰器", "装饰器是Python的一个高级特性..."),
    ("什么是生成器？", "生成器是一种特殊的迭代器...")
]

for q, a in test_conversations:
    save_conversation_turn(q, a)

# 测试检索
results = retrieve_relevant_context("Python的高级特性有哪些？", num_results=3)
for r in results:
    print(f"Score: {r['final_score']:.3f}, Content: {r['content'][:50]}...")
```

#### 测试用例 2：提示增强
```bash
# 先进行几轮对话建立历史
claude-mem "什么是机器学习？"
claude-mem "深度学习和机器学习的区别？"
claude-mem "神经网络的基本原理"

# 测试上下文增强
claude-mem "基于前面的讨论，总结一下AI的核心概念"
```

---

## 阶段 3：配置与用户体验（0.5天）

提供用户控制和透明反馈。

### 3.1 核心任务

#### 任务 A：扩展配置系统
**文件**：`config_manager.py`

```python
# 在 SageConfig 中添加新字段
@dataclass
class SageConfig:
    # ... 现有字段 ...
    
    # 记忆系统配置
    memory_enabled: bool = True
    retrieval_count: int = 3
    similarity_threshold: float = 0.7
    time_decay: bool = True
    max_age_days: int = 30
    max_context_tokens: int = 2000
    async_save: bool = True
    cache_ttl: int = 300
    
    # 提示模板
    prompt_template: str = field(default_factory=lambda: """基于我们之前的对话历史，请回答以下问题。

相关历史对话：
{context}

当前问题：{query}

请结合历史上下文（如果相关）来回答。如果历史信息不相关，可以忽略。""")
    
    # 用户体验
    show_memory_hints: bool = True
    memory_hint_color: str = "cyan"
    verbose_mode: bool = False
```

#### 任务 B：实现用户控制命令
**文件**：`sage_memory_cli.py`（新建）

```python
#!/usr/bin/env python3
"""
Sage 记忆系统管理命令行工具
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from config_manager import get_config_manager
from memory import (
    get_memory_stats, 
    clear_all_memories, 
    delete_memory_by_id,
    search_memory,
    export_memories,
    import_memories
)

class MemoryCLI:
    def __init__(self):
        self.config = get_config_manager()
    
    def cmd_status(self, args):
        """显示记忆系统状态"""
        stats = get_memory_stats()
        
        print(f"🧠 Sage 记忆系统状态")
        print(f"{'='*40}")
        print(f"总记忆数: {stats['total_memories']}")
        print(f"用户消息: {stats['user_messages']}")
        print(f"助手响应: {stats['assistant_messages']}")
        print(f"存储大小: {stats['storage_size_mb']:.2f} MB")
        print(f"最早记忆: {stats['oldest_memory']}")
        print(f"最新记忆: {stats['latest_memory']}")
        print(f"{'='*40}")
        print(f"记忆功能: {'✅ 启用' if self.config.get('memory_enabled') else '❌ 禁用'}")
        print(f"检索数量: {self.config.get('retrieval_count')}")
        print(f"相似度阈值: {self.config.get('similarity_threshold')}")
    
    def cmd_clear(self, args):
        """清除记忆"""
        if args.days:
            # 清除N天前的记忆
            cutoff_date = datetime.now() - timedelta(days=args.days)
            count = clear_memories_before(cutoff_date)
            print(f"✅ 已清除 {count} 条超过 {args.days} 天的记忆")
        elif args.all:
            # 确认清除所有
            response = input("⚠️  确定要清除所有记忆吗？(yes/no): ")
            if response.lower() == 'yes':
                count = clear_all_memories()
                print(f"✅ 已清除所有 {count} 条记忆")
            else:
                print("❌ 操作已取消")
        else:
            print("❌ 请指定 --all 或 --days N")
    
    def cmd_search(self, args):
        """搜索记忆"""
        results = search_memory(args.query, n=args.limit)
        
        if not results:
            print(f"❌ 未找到与 '{args.query}' 相关的记忆")
            return
        
        print(f"🔍 找到 {len(results)} 条相关记忆：")
        print(f"{'='*60}")
        
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] 相似度: {result['score']:.3f}")
            print(f"时间: {result['metadata']['timestamp']}")
            print(f"角色: {result['metadata']['role']}")
            print(f"内容: {result['content'][:200]}...")
            if len(result['content']) > 200:
                print(f"      ... (还有 {len(result['content'])-200} 个字符)")
    
    def cmd_toggle(self, args):
        """切换记忆功能"""
        current = self.config.get('memory_enabled')
        new_state = not current
        self.config.set('memory_enabled', new_state)
        
        if new_state:
            print("✅ 记忆功能已启用")
        else:
            print("❌ 记忆功能已禁用")
    
    def cmd_config(self, args):
        """配置管理"""
        if args.get:
            value = self.config.get(f"memory.{args.get}")
            print(f"{args.get}: {value}")
        elif args.set:
            key, value = args.set
            # 尝试解析值的类型
            try:
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif '.' in value and value.replace('.', '').isdigit():
                    value = float(value)
            except:
                pass
            
            self.config.set(f"memory.{key}", value)
            print(f"✅ 已设置 {key} = {value}")
        else:
            # 显示所有记忆相关配置
            print("📋 记忆系统配置：")
            for key in ['enabled', 'retrieval_count', 'similarity_threshold', 
                       'time_decay', 'max_age_days', 'async_save']:
                value = self.config.get(f"memory.{key}")
                print(f"  {key}: {value}")
    
    def cmd_export(self, args):
        """导出记忆"""
        path = Path(args.output)
        
        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        count = export_memories(
            path,
            start_date=args.from_date,
            end_date=args.to_date,
            format=args.format
        )
        
        print(f"✅ 已导出 {count} 条记忆到 {path}")
    
    def cmd_import(self, args):
        """导入记忆"""
        path = Path(args.input)
        
        if not path.exists():
            print(f"❌ 文件不存在: {path}")
            return
        
        count = import_memories(path, merge=args.merge)
        print(f"✅ 已导入 {count} 条记忆")

def main():
    parser = argparse.ArgumentParser(
        description='Sage 记忆系统管理工具',
        prog='sage-memory'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status 命令
    subparsers.add_parser('status', help='显示记忆系统状态')
    
    # clear 命令
    clear_parser = subparsers.add_parser('clear', help='清除记忆')
    clear_group = clear_parser.add_mutually_exclusive_group(required=True)
    clear_group.add_argument('--all', action='store_true', help='清除所有记忆')
    clear_group.add_argument('--days', type=int, help='清除N天前的记忆')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索记忆')
    search_parser.add_argument('query', help='搜索关键词')
    search_parser.add_argument('--limit', type=int, default=5, help='返回结果数量')
    
    # toggle 命令
    subparsers.add_parser('toggle', help='切换记忆功能开关')
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_group = config_parser.add_mutually_exclusive_group()
    config_group.add_argument('--get', help='获取配置值')
    config_group.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='设置配置值')
    
    # export 命令
    export_parser = subparsers.add_parser('export', help='导出记忆')
    export_parser.add_argument('output', help='输出文件路径')
    export_parser.add_argument('--format', choices=['json', 'csv', 'markdown'], 
                              default='json', help='导出格式')
    export_parser.add_argument('--from-date', type=str, help='开始日期 (YYYY-MM-DD)')
    export_parser.add_argument('--to-date', type=str, help='结束日期 (YYYY-MM-DD)')
    
    # import 命令
    import_parser = subparsers.add_parser('import', help='导入记忆')
    import_parser.add_argument('input', help='输入文件路径')
    import_parser.add_argument('--merge', action='store_true', help='合并而不是替换')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = MemoryCLI()
    
    # 执行对应命令
    cmd_method = getattr(cli, f'cmd_{args.command}', None)
    if cmd_method:
        try:
            cmd_method(args)
        except Exception as e:
            print(f"❌ 错误: {e}")
            sys.exit(1)
    else:
        print(f"❌ 未知命令: {args.command}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### 3.2 用户体验增强

#### 任务 A：添加视觉反馈
**文件**：`sage_crossplatform.py`

```python
def print_memory_status(self, contexts_found: int, memory_enabled: bool):
    """打印记忆系统状态（如果启用提示）"""
    if not self.config.get('show_memory_hints', True):
        return
    
    color = self.config.get('memory_hint_color', 'cyan')
    color_code = {
        'cyan': '\033[96m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m'
    }.get(color, '\033[96m')
    
    reset_code = '\033[0m'
    
    if memory_enabled:
        if contexts_found > 0:
            msg = f"[记忆系统] 找到 {contexts_found} 条相关历史"
        else:
            msg = "[记忆系统] 未找到相关历史"
    else:
        msg = "[记忆系统] 已禁用"
    
    # 输出到 stderr 以免干扰正常输出
    sys.stderr.write(f"{color_code}{msg}{reset_code}\n")
    sys.stderr.flush()
```

### 3.3 测试验证

#### 测试用例 1：配置管理
```bash
# 测试配置命令
sage-memory config --get retrieval_count
sage-memory config --set retrieval_count 5
sage-memory config --set similarity_threshold 0.8

# 测试开关
sage-memory toggle
claude-mem "测试记忆是否禁用"
sage-memory toggle
```

#### 测试用例 2：记忆管理
```bash
# 查看状态
sage-memory status

# 搜索记忆
sage-memory search "Python"

# 清理旧记忆
sage-memory clear --days 7

# 导出记忆
sage-memory export my_memories.json --format json
```

---

## 阶段 4：测试、优化与完成（1天）

### 4.1 集成测试

#### 测试套件：`tests/test_integration.py`

```python
import unittest
import subprocess
import json
import time
from pathlib import Path

class TestClaudeMemIntegration(unittest.TestCase):
    """集成测试套件"""
    
    def setUp(self):
        """测试前准备"""
        # 清空测试记忆
        subprocess.run(['sage-memory', 'clear', '--all'], input='yes\n', text=True)
    
    def test_basic_conversation_flow(self):
        """测试基本对话流程"""
        # 第一轮对话
        result = subprocess.run(
            ['claude-mem', '什么是Python？'],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('Python', result.stdout)
        
        # 等待保存完成
        time.sleep(1)
        
        # 第二轮对话，应该有上下文
        result = subprocess.run(
            ['claude-mem', '它的主要特点是什么？'],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        # 验证是否提到了相关历史
        self.assertIn('[记忆系统]', result.stderr)
    
    def test_parameter_passthrough(self):
        """测试参数透传"""
        test_cases = [
            ['claude-mem', '生成JSON', '--model', 'claude-3-haiku'],
            ['claude-mem', '翻译文本', '--temperature', '0.3'],
            ['claude-mem', '总结内容', '-f', 'test.txt', '--max-tokens', '100']
        ]
        
        for cmd in test_cases:
            with self.subTest(cmd=cmd):
                result = subprocess.run(cmd, capture_output=True, text=True)
                # 不应该有参数解析错误
                self.assertNotIn('unrecognized arguments', result.stderr)
    
    def test_memory_toggle(self):
        """测试记忆开关"""
        # 禁用记忆
        subprocess.run(['sage-memory', 'toggle'])
        
        result = subprocess.run(
            ['claude-mem', '测试查询'],
            capture_output=True,
            text=True
        )
        self.assertIn('[记忆系统] 已禁用', result.stderr)
        
        # 重新启用
        subprocess.run(['sage-memory', 'toggle'])
    
    def test_performance(self):
        """性能测试"""
        # 添加大量记忆
        for i in range(100):
            subprocess.run(
                ['claude-mem', f'测试记忆 {i}'],
                capture_output=True
            )
        
        # 测试检索性能
        start_time = time.time()
        result = subprocess.run(
            ['claude-mem', '基于之前的测试记忆，总结一下'],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start_time
        
        # 应该在合理时间内完成
        self.assertLess(elapsed, 5.0)  # 5秒内完成
        self.assertEqual(result.returncode, 0)

if __name__ == '__main__':
    unittest.main()
```

### 4.2 性能优化检查清单

#### 优化项目

1. **启动时间优化**
   ```python
   # 延迟导入重量级模块
   def lazy_import_chromadb():
       global chromadb
       if 'chromadb' not in globals():
           import chromadb as _chromadb
           chromadb = _chromadb
   ```

2. **向量检索优化**
   - 使用缓存减少重复查询
   - 实现索引预热
   - 考虑使用更快的向量数据库（如 Qdrant）

3. **响应时间监控**
   ```python
   # 添加性能计时
   class PerformanceMonitor:
       def __init__(self):
           self.timings = {}
       
       def time_section(self, name):
           return TimingContext(self, name)
   
   class TimingContext:
       def __init__(self, monitor, name):
           self.monitor = monitor
           self.name = name
       
       def __enter__(self):
           self.start = time.time()
       
       def __exit__(self, *args):
           elapsed = time.time() - self.start
           self.monitor.timings[self.name] = elapsed
   ```

### 4.3 文档更新

#### 更新 README.md

```markdown
# Sage MCP - Claude 智能记忆系统

## 快速开始

安装后，所有 `claude` 命令将自动具备记忆功能：

```bash
# 正常使用 Claude
claude "解释量子计算"

# Claude 会自动记住对话历史
claude "基于刚才的解释，它与经典计算的主要区别是什么？"
```

## 特性

- 🧠 **自动记忆**：所有对话自动保存并向量化
- 🔍 **智能检索**：基于语义相似度检索相关历史
- ⚡ **高性能**：缓存机制确保快速响应
- 🔒 **隐私控制**：支持禁用记忆和清除历史
- 🌍 **跨平台**：支持 Windows、macOS、Linux

## 记忆管理

```bash
# 查看记忆状态
sage-memory status

# 搜索历史对话
sage-memory search "机器学习"

# 清除旧记忆
sage-memory clear --days 30

# 临时禁用记忆
sage-memory toggle
```

## 配置选项

编辑 `~/.sage-mcp/config.json` 或使用命令：

```bash
# 设置检索数量
sage-memory config --set retrieval_count 5

# 设置相似度阈值
sage-memory config --set similarity_threshold 0.8

# 禁用时间衰减
sage-memory config --set time_decay false
```

## 高级用法

### 导出/导入记忆

```bash
# 导出记忆用于备份
sage-memory export my_memories.json

# 导入记忆
sage-memory import backup.json --merge
```

### 传递原生 Claude 参数

所有 Claude 的原生参数都被支持：

```bash
claude "写一首诗" --model claude-3-haiku --temperature 0.9
claude "总结文档" -f document.pdf --max-tokens 500
```

## 故障排除

如果遇到问题，运行诊断：

```bash
sage-doctor
```
```

### 4.4 风险评估与缓解

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|----------|
| 向量检索性能下降 | 高 | 中 | 实现多级缓存，限制检索数量 |
| 数据库连接失败 | 高 | 低 | 优雅降级到无记忆模式 |
| 内存使用过高 | 中 | 中 | 实现 LRU 缓存淘汰策略 |
| 隐私泄露 | 高 | 低 | 支持隐私模式，敏感内容过滤 |
| 递归调用 | 高 | 低 | 严格的递归保护机制 |

### 4.5 部署检查清单

- [ ] 所有测试通过
- [ ] 性能指标达标（<100ms 延迟）
- [ ] 文档更新完成
- [ ] 错误处理完善
- [ ] 日志记录充分
- [ ] 配置选项完整
- [ ] 用户反馈机制正常
- [ ] 向后兼容性保证

---

## 时间线总结

| 阶段 | 预计时间 | 关键交付物 |
|------|----------|------------|
| 阶段 1 | 1-2 天 | 完整对话捕获，参数透传 |
| 阶段 2 | 1 天 | 智能上下文检索，提示增强 |
| 阶段 3 | 0.5 天 | 用户控制命令，配置系统 |
| 阶段 4 | 1 天 | 集成测试，优化，文档 |
| **总计** | **3.5-4.5 天** | **完整的智能记忆系统** |

## 成功标准

1. ✅ 用户无需改变使用习惯
2. ✅ 响应延迟增加 < 100ms
3. ✅ 记忆准确率 > 90%
4. ✅ 支持所有 Claude 原生功能
5. ✅ 完整的用户控制选项
6. ✅ 跨平台兼容性

## 下一步行动

1. 立即开始阶段 1 的响应捕获实现
2. 设置开发环境和测试数据
3. 创建项目看板跟踪进度
4. 每完成一个阶段进行代码审查

---

*本执行计划提供了详尽的技术实现细节和清晰的里程碑，确保 claude-mem 成功演进为透明、智能的记忆增强系统。*