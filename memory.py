#!/usr/bin/env python3
"""
Sage MCP 轻量化记忆系统 - 核心记忆功能模块

主要功能：
1. 文本向量化：使用 Qwen3-Embedding-8B 生成 4096 维向量
2. 相似度搜索：基于 pgvector 的余弦相似度检索
3. 上下文生成：使用 DeepSeek-V2.5 生成相关历史摘要
4. 对话存储：自动保存用户查询和 Claude 响应

数据库结构：
- conversations 表存储所有对话历史
- 每条记录包含：session_id, turn_id, role, content, embedding
- 支持基于向量相似度的快速检索

作者：Sage MCP 项目组
"""

import os
import json
# import psycopg2  # 移到函数内部延迟导入
# from psycopg2.extras import RealDictCursor  # 移到函数内部延迟导入
import requests
from datetime import datetime
import numpy as np
from typing import List, Dict, Optional, Any
import uuid
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'mem'),
    'user': os.getenv('DB_USER', 'mem'),
    'password': os.getenv('DB_PASSWORD', 'mem')
}

# SiliconFlow API 配置
SILICONFLOW_API_KEY = os.getenv('SILICONFLOW_API_KEY')
if not SILICONFLOW_API_KEY:
    raise ValueError("SILICONFLOW_API_KEY 环境变量未设置。请在 .env 文件中设置您的 API 密钥。")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"

# 模型配置
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
LLM_MODEL = "deepseek-ai/DeepSeek-V2.5"

# 全局 session_id（每次程序启动生成新的）
SESSION_ID = str(uuid.uuid4())
TURN_COUNTER = 0

def get_db_connection():
    """获取数据库连接"""
    import psycopg2
    return psycopg2.connect(**DB_CONFIG)

def embed_text(text: str) -> List[float]:
    """
    使用 Qwen3-Embedding-8B 将文本转换为向量
    返回 4096 维向量
    """
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": EMBEDDING_MODEL,
        "input": text,
        "encoding_format": "float"
    }
    
    try:
        response = requests.post(
            f"{SILICONFLOW_BASE_URL}/embeddings",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        embedding = result['data'][0]['embedding']
        
        # 确保返回 4096 维向量
        if len(embedding) != 4096:
            raise ValueError(f"期望 4096 维向量，但得到 {len(embedding)} 维")
            
        return embedding
        
    except Exception as e:
        print(f"向量化失败: {e}")
        # 返回随机向量作为降级方案
        return np.random.rand(4096).tolist()

def search_similar_conversations(query_embedding: List[float], limit: int = 5) -> List[Dict]:
    """
    从数据库中搜索相似的历史对话
    使用余弦相似度排序
    """
    from psycopg2.extras import RealDictCursor
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 使用 pgvector 的余弦相似度搜索
            cur.execute("""
                SELECT 
                    id,
                    session_id,
                    turn_id,
                    role,
                    content,
                    created_at,
                    1 - (embedding <=> %s::vector) as similarity
                FROM conversations
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))
            
            return cur.fetchall()
            
    finally:
        conn.close()

def summarize_context(conversations: List[Dict], query: str) -> str:
    """
    使用 DeepSeek-V2.5 对检索到的历史对话进行摘要
    生成与当前查询相关的上下文
    """
    if not conversations:
        return ""
    
    # 构造对话历史文本
    history_text = "相关历史对话：\n"
    for conv in conversations:
        role_label = "用户" if conv['role'] == 'user' else "Claude"
        similarity = conv.get('similarity', 0)
        history_text += f"\n[{role_label}] (相似度: {similarity:.2f}): {conv['content'][:200]}...\n"
    
    # 调用 DeepSeek API 生成摘要
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""基于以下历史对话，生成一个简洁的上下文摘要，帮助回答用户的当前查询。

{history_text}

当前用户查询：{query}

请生成一个不超过200字的上下文摘要，突出与当前查询相关的要点："""
    
    data = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个专业的对话摘要助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    try:
        response = requests.post(
            f"{SILICONFLOW_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        summary = result['choices'][0]['message']['content']
        
        return f"【相关上下文】\n{summary}"
        
    except Exception as e:
        print(f"摘要生成失败: {e}")
        # 降级方案：返回最相关的一条历史记录
        if conversations:
            most_relevant = conversations[0]
            return f"【相关历史】{most_relevant['content'][:100]}..."
        return ""

def get_context(query: str) -> str:
    """
    主查询函数：获取与当前查询相关的历史上下文
    1. 向量化查询
    2. 搜索相似对话
    3. 生成摘要
    """
    try:
        # 向量化当前查询
        query_embedding = embed_text(query)
        
        # 搜索相似对话
        similar_convs = search_similar_conversations(query_embedding)
        
        # 生成上下文摘要
        context = summarize_context(similar_convs, query)
        
        return context
        
    except Exception as e:
        print(f"获取上下文失败: {e}")
        return ""

def save_memory(user_query: str, claude_response: str):
    """
    保存对话到数据库
    1. 向量化用户查询和 Claude 响应
    2. 写入两条记录到 conversations 表
    """
    global TURN_COUNTER
    
    conn = get_db_connection()
    try:
        # 增加轮次计数
        TURN_COUNTER += 1
        
        # 向量化文本
        user_embedding = embed_text(user_query)
        claude_embedding = embed_text(claude_response)
        
        with conn.cursor() as cur:
            # 插入用户查询记录
            cur.execute("""
                INSERT INTO conversations (
                    session_id, turn_id, role, content, embedding
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                SESSION_ID,
                TURN_COUNTER,
                'user',
                user_query,
                user_embedding
            ))
            
            # 插入 Claude 响应记录
            cur.execute("""
                INSERT INTO conversations (
                    session_id, turn_id, role, content, embedding
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                SESSION_ID,
                TURN_COUNTER,
                'claude',
                claude_response,
                claude_embedding
            ))
            
            conn.commit()
            print(f"[记忆系统] 已保存对话 (session: {SESSION_ID[:8]}..., turn: {TURN_COUNTER})")
            
    except Exception as e:
        print(f"[记忆系统] 保存失败: {e}")
        conn.rollback()
        
    finally:
        conn.close()

def save_conversation_turn(user_prompt: str, assistant_response: str, metadata: Optional[Dict] = None):
    """
    保存完整的对话轮次（新函数，兼容旧接口）
    
    Args:
        user_prompt: 用户输入
        assistant_response: Claude 的响应  
        metadata: 额外元数据（时间戳、模型等）
    """
    # 直接调用原有函数
    save_memory(user_prompt, assistant_response)

def get_memory_stats() -> Dict[str, Any]:
    """获取记忆系统统计信息"""
    conn = get_db_connection()
    from psycopg2.extras import RealDictCursor
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 总记忆数
            cur.execute("SELECT COUNT(*) as total FROM conversations")
            total = cur.fetchone()['total']
            
            # 今日新增
            cur.execute("""
                SELECT COUNT(*) as today 
                FROM conversations 
                WHERE created_at >= CURRENT_DATE
            """)
            today = cur.fetchone()['today']
            
            # 本周活跃
            cur.execute("""
                SELECT COUNT(*) as this_week 
                FROM conversations 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            """)
            this_week = cur.fetchone()['this_week']
            
            # 存储大小（估算）
            cur.execute("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('conversations')) as size,
                    pg_total_relation_size('conversations') as size_bytes
            """)
            size_info = cur.fetchone()
            
            return {
                'total': total,
                'today': today,
                'this_week': this_week,
                'size': size_info['size'],
                'size_mb': size_info['size_bytes'] / (1024 * 1024)
            }
            
    finally:
        conn.close()

def clear_all_memories() -> int:
    """清除所有记忆"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM conversations")
            count = cur.fetchone()[0]
            
            cur.execute("TRUNCATE TABLE conversations")
            conn.commit()
            
            return count
            
    finally:
        conn.close()

def add_memory(content: str, metadata: Optional[Dict] = None):
    """添加单条记忆（用于导入等场景）"""
    global TURN_COUNTER
    
    conn = get_db_connection()
    try:
        TURN_COUNTER += 1
        
        # 向量化内容
        embedding = embed_text(content)
        
        # 默认元数据
        default_metadata = {
            'role': 'user',
            'session_id': SESSION_ID,
            'turn_id': TURN_COUNTER
        }
        
        if metadata:
            default_metadata.update(metadata)
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO conversations (
                    session_id, turn_id, role, content, embedding
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                default_metadata.get('session_id', SESSION_ID),
                default_metadata.get('turn_id', TURN_COUNTER),
                default_metadata.get('role', 'user'),
                content,
                embedding
            ))
            
            conn.commit()
            
    finally:
        conn.close()

def search_memory(query: str, n: int = 5) -> List[Dict[str, Any]]:
    """搜索记忆（供命令行工具使用）"""
    try:
        # 向量化查询
        query_embedding = embed_text(query)
        
        # 搜索相似对话
        results = search_similar_conversations(query_embedding, limit=n)
        
        # 格式化结果
        formatted_results = []
        for r in results:
            formatted_results.append({
                'content': r['content'],
                'role': r['role'],
                'score': r.get('similarity', 0),
                'metadata': {
                    'session_id': r['session_id'],
                    'turn_id': r['turn_id'],
                    'timestamp': r['created_at'].isoformat() if r['created_at'] else None
                }
            })
        
        return formatted_results
        
    except Exception as e:
        print(f"搜索失败: {e}")
        return []