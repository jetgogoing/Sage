#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0 Authentication - OAuth 认证实现
"""
import secrets
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import jwt
import logging

logger = logging.getLogger(__name__)


class OAuth2Provider:
    """OAuth 2.0 提供者"""
    
    def __init__(self, 
                 client_id: str = "sage-mcp-client",
                 client_secret: str = None,
                 jwt_secret: str = None,
                 token_expire_hours: int = 24):
        """初始化 OAuth 提供者
        
        Args:
            client_id: 客户端ID
            client_secret: 客户端密钥
            jwt_secret: JWT签名密钥
            token_expire_hours: 令牌过期时间（小时）
        """
        self.client_id = client_id
        self.client_secret = client_secret or secrets.token_urlsafe(32)
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.token_expire_hours = token_expire_hours
        
        # 存储授权码（生产环境应使用 Redis 等）
        self.authorization_codes: Dict[str, Dict[str, Any]] = {}
        
        # 存储刷新令牌
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"OAuth2 provider initialized with client_id: {self.client_id}")
    
    def generate_authorization_code(self, 
                                  user_id: str,
                                  redirect_uri: str,
                                  scope: str = "read write") -> str:
        """生成授权码
        
        Args:
            user_id: 用户ID
            redirect_uri: 重定向URI
            scope: 权限范围
            
        Returns:
            授权码
        """
        code = secrets.token_urlsafe(32)
        
        self.authorization_codes[code] = {
            "user_id": user_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "created_at": time.time(),
            "expires_at": time.time() + 600  # 10分钟过期
        }
        
        logger.info(f"Generated authorization code for user: {user_id}")
        return code
    
    def exchange_code_for_token(self,
                              code: str,
                              redirect_uri: str,
                              client_id: str,
                              client_secret: str) -> Optional[Dict[str, Any]]:
        """用授权码换取访问令牌
        
        Args:
            code: 授权码
            redirect_uri: 重定向URI
            client_id: 客户端ID
            client_secret: 客户端密钥
            
        Returns:
            令牌信息或None
        """
        # 验证客户端
        if client_id != self.client_id or client_secret != self.client_secret:
            logger.error("Invalid client credentials")
            return None
        
        # 验证授权码
        if code not in self.authorization_codes:
            logger.error("Invalid authorization code")
            return None
        
        code_data = self.authorization_codes[code]
        
        # 验证过期
        if time.time() > code_data["expires_at"]:
            logger.error("Authorization code expired")
            del self.authorization_codes[code]
            return None
        
        # 验证重定向URI
        if redirect_uri != code_data["redirect_uri"]:
            logger.error("Redirect URI mismatch")
            return None
        
        # 生成令牌
        access_token = self._generate_access_token(
            user_id=code_data["user_id"],
            scope=code_data["scope"]
        )
        
        refresh_token = self._generate_refresh_token(
            user_id=code_data["user_id"],
            scope=code_data["scope"]
        )
        
        # 删除已使用的授权码
        del self.authorization_codes[code]
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_expire_hours * 3600,
            "refresh_token": refresh_token,
            "scope": code_data["scope"]
        }
    
    def refresh_access_token(self,
                           refresh_token: str,
                           client_id: str,
                           client_secret: str) -> Optional[Dict[str, Any]]:
        """刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            client_id: 客户端ID
            client_secret: 客户端密钥
            
        Returns:
            新的令牌信息或None
        """
        # 验证客户端
        if client_id != self.client_id or client_secret != self.client_secret:
            logger.error("Invalid client credentials")
            return None
        
        # 验证刷新令牌
        if refresh_token not in self.refresh_tokens:
            logger.error("Invalid refresh token")
            return None
        
        token_data = self.refresh_tokens[refresh_token]
        
        # 验证过期（刷新令牌有效期更长）
        if time.time() > token_data["expires_at"]:
            logger.error("Refresh token expired")
            del self.refresh_tokens[refresh_token]
            return None
        
        # 生成新的访问令牌
        access_token = self._generate_access_token(
            user_id=token_data["user_id"],
            scope=token_data["scope"]
        )
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_expire_hours * 3600,
            "refresh_token": refresh_token,  # 保持原刷新令牌
            "scope": token_data["scope"]
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证访问令牌
        
        Args:
            token: 访问令牌
            
        Returns:
            令牌载荷或None
        """
        try:
            # 解码和验证 JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"]
            )
            
            # 验证过期时间
            if "exp" in payload and datetime.utcnow().timestamp() > payload["exp"]:
                logger.error("Token expired")
                return None
            
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            return None
    
    def _generate_access_token(self, user_id: str, scope: str) -> str:
        """生成访问令牌
        
        Args:
            user_id: 用户ID
            scope: 权限范围
            
        Returns:
            JWT令牌
        """
        now = datetime.utcnow()
        exp = now + timedelta(hours=self.token_expire_hours)
        
        payload = {
            "sub": user_id,
            "scope": scope,
            "iat": now.timestamp(),
            "exp": exp.timestamp(),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        logger.info(f"Generated access token for user: {user_id}")
        
        return token
    
    def _generate_refresh_token(self, user_id: str, scope: str) -> str:
        """生成刷新令牌
        
        Args:
            user_id: 用户ID
            scope: 权限范围
            
        Returns:
            刷新令牌
        """
        token = secrets.token_urlsafe(32)
        
        self.refresh_tokens[token] = {
            "user_id": user_id,
            "scope": scope,
            "created_at": time.time(),
            "expires_at": time.time() + (30 * 24 * 3600)  # 30天过期
        }
        
        logger.info(f"Generated refresh token for user: {user_id}")
        return token
    
    def revoke_token(self, token: str, token_type: str = "access") -> bool:
        """撤销令牌
        
        Args:
            token: 令牌
            token_type: 令牌类型 (access/refresh)
            
        Returns:
            是否成功
        """
        if token_type == "refresh":
            if token in self.refresh_tokens:
                del self.refresh_tokens[token]
                logger.info("Revoked refresh token")
                return True
        else:
            # 访问令牌是无状态的，需要黑名单机制（未实现）
            logger.warning("Access token revocation not implemented")
        
        return False
    
    def cleanup_expired(self) -> None:
        """清理过期的授权码和刷新令牌"""
        current_time = time.time()
        
        # 清理过期的授权码
        expired_codes = [
            code for code, data in self.authorization_codes.items()
            if current_time > data["expires_at"]
        ]
        for code in expired_codes:
            del self.authorization_codes[code]
        
        if expired_codes:
            logger.info(f"Cleaned up {len(expired_codes)} expired authorization codes")
        
        # 清理过期的刷新令牌
        expired_tokens = [
            token for token, data in self.refresh_tokens.items()
            if current_time > data["expires_at"]
        ]
        for token in expired_tokens:
            del self.refresh_tokens[token]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired refresh tokens")