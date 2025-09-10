# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Configuration Module

Provides session configuration for the consolidated session framework.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionConfig:
    """Session configuration settings"""
    
    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "vedfolnir:session:"
    redis_timeout: int = 7200  # 2 hours
    
    # Session settings
    session_lifetime: int = 86400  # 24 hours
    cleanup_interval: int = 3600  # 1 hour
    
    # Security settings
    secure_cookies: bool = True
    httponly_cookies: bool = True
    samesite: str = "Lax"
    
    @classmethod
    def from_env(cls):
        """Create configuration from environment variables"""
        return cls(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            redis_prefix=os.getenv("REDIS_SESSION_PREFIX", "vedfolnir:session:"),
            redis_timeout=int(os.getenv("REDIS_SESSION_TIMEOUT", "7200")),
            session_lifetime=int(os.getenv("AUTH_SESSION_LIFETIME", "86400")),
            cleanup_interval=int(os.getenv("REDIS_SESSION_CLEANUP_INTERVAL", "3600")),
            secure_cookies=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
            httponly_cookies=os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true",
            samesite=os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
        )


def get_session_config() -> SessionConfig:
    """Get session configuration instance"""
    return SessionConfig.from_env()