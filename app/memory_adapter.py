#!/usr/bin/env python3
"""
Memory Adapter - Bridge between MCP Server and existing Sage memory system

This module provides an adapter layer that wraps the existing Sage memory
functionality for use in the MCP server. It handles:
- Session management
- Error handling and retries
- Data format conversions
- Backward compatibility
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_interface import get_memory_provider, MemorySearchResult
from config_manager import get_config_manager
from exceptions import SageMemoryError

logger = logging.getLogger(__name__)

class MemoryAdapter:
    """
    Adapter class that provides a clean interface between the MCP server
    and the existing Sage memory system.
    """
    
    def __init__(self):
        """Initialize the memory adapter"""
        self.memory_provider = get_memory_provider()
        self.config_manager = get_config_manager()
        self.current_session_id = str(uuid.uuid4())
        self.current_turn_id = 0
        logger.info(f"Memory adapter initialized with session: {self.current_session_id[:8]}...")
    
    def save_conversation(
        self,
        user_prompt: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a conversation turn with enhanced metadata.
        
        Args:
            user_prompt: The user's input
            assistant_response: The assistant's response
            metadata: Optional metadata to store
            
        Returns:
            Dict containing save status and metadata
        """
        try:
            # Increment turn counter
            self.current_turn_id += 1
            
            # Enhance metadata with session info
            enhanced_metadata = metadata or {}
            enhanced_metadata.update({
                "session_id": self.current_session_id,
                "turn_id": self.current_turn_id,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mcp_server"
            })
            
            # Save using memory provider
            self.memory_provider.save_conversation(
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                metadata=enhanced_metadata
            )
            
            logger.info(
                f"Saved conversation turn {self.current_turn_id} in session {self.current_session_id[:8]}..."
            )
            
            return {
                "success": True,
                "session_id": self.current_session_id,
                "turn_id": self.current_turn_id,
                "timestamp": enhanced_metadata["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise SageMemoryError(f"Save conversation failed: {str(e)}")
    
    def get_context(
        self,
        query: str,
        max_results: int = 3,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Get relevant context with structured results.
        
        Args:
            query: The query to find context for
            max_results: Maximum number of results
            include_metadata: Whether to include metadata in results
            
        Returns:
            Dict containing context string and structured results
        """
        try:
            # Get raw context (for backward compatibility)
            context_str = self.memory_provider.get_context(query)
            
            # Get structured results
            search_results = self.memory_provider.search_memory(query, n=max_results)
            
            # Format results
            formatted_results = []
            for result in search_results:
                formatted_result = {
                    "content": result.content,
                    "role": result.role,
                    "score": result.score
                }
                
                if include_metadata and result.metadata:
                    formatted_result["metadata"] = result.metadata
                    
                formatted_results.append(formatted_result)
            
            return {
                "context": context_str,
                "results": formatted_results,
                "num_results": len(formatted_results),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            raise SageMemoryError(f"Get context failed: {str(e)}")
    
    def search_memory(
        self,
        query: str,
        n: int = 5,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memory with optional filtering.
        
        Args:
            query: Search query
            n: Number of results to return
            similarity_threshold: Optional minimum similarity score
            
        Returns:
            List of search results
        """
        try:
            # Use configured threshold if not specified
            if similarity_threshold is None:
                similarity_threshold = self.config_manager.config.similarity_threshold
            
            # Search memories
            results = self.memory_provider.search_memory(query, n=n)
            
            # Filter by similarity threshold
            filtered_results = []
            for result in results:
                if result.score >= similarity_threshold:
                    filtered_results.append({
                        "content": result.content,
                        "role": result.role,
                        "score": result.score,
                        "metadata": result.metadata or {}
                    })
            
            logger.info(
                f"Search returned {len(filtered_results)} results "
                f"(filtered from {len(results)} by threshold {similarity_threshold})"
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            raise SageMemoryError(f"Search memory failed: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.
        
        Returns:
            Dict containing memory stats
        """
        try:
            stats = self.memory_provider.get_memory_stats()
            
            # Add adapter-specific stats
            stats.update({
                "current_session_id": self.current_session_id,
                "current_turn_id": self.current_turn_id,
                "adapter_version": "1.0.0"
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "error": str(e),
                "current_session_id": self.current_session_id,
                "current_turn_id": self.current_turn_id
            }
    
    def create_new_session(self) -> str:
        """
        Create a new session for conversation tracking.
        
        Returns:
            New session ID
        """
        self.current_session_id = str(uuid.uuid4())
        self.current_turn_id = 0
        logger.info(f"Created new session: {self.current_session_id[:8]}...")
        return self.current_session_id
    
    def format_context_for_prompt(
        self,
        results: List[Dict[str, Any]],
        max_tokens: int = 2000
    ) -> str:
        """
        Format search results into a context string for prompt injection.
        
        Args:
            results: Search results to format
            max_tokens: Maximum tokens to include
            
        Returns:
            Formatted context string
        """
        # Use the memory provider's formatting if available
        if hasattr(self.memory_provider, 'format_context_for_prompt'):
            return self.memory_provider.format_context_for_prompt(results, max_tokens)
        
        # Fallback formatting
        formatted_parts = []
        estimated_tokens = 0
        
        for result in results:
            role = result.get('role', 'unknown')
            content = result.get('content', '')
            
            # Format based on role
            if role == 'user':
                formatted = f"[用户]: {content}"
            elif role == 'assistant':
                formatted = f"[助手]: {content}"
            else:
                formatted = f"[{role}]: {content}"
            
            # Rough token estimate (4 chars ≈ 1 token)
            part_tokens = len(formatted) // 4
            
            if estimated_tokens + part_tokens > max_tokens:
                # Truncate if needed
                remaining_tokens = max_tokens - estimated_tokens
                if remaining_tokens > 50:
                    max_chars = remaining_tokens * 4
                    formatted = formatted[:max_chars] + "..."
                    formatted_parts.append(formatted)
                break
            
            formatted_parts.append(formatted)
            estimated_tokens += part_tokens
        
        return "\n\n".join(formatted_parts)

# Singleton instance
_adapter_instance = None

def get_memory_adapter() -> MemoryAdapter:
    """
    Get or create the singleton memory adapter instance.
    
    Returns:
        MemoryAdapter instance
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = MemoryAdapter()
    return _adapter_instance