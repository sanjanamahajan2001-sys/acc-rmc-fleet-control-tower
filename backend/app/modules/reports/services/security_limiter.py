import time
import jwt
from typing import Dict, Any, Tuple
from collections import defaultdict
from fastapi import HTTPException, Request, status

from app.core.config import settings

# Memory-bound Sliding Window Rate Limiter
_request_counters: Dict[str, list] = defaultdict(list)


class SecurityRateLimiter:
    """
    Sliding window rate limiter for security boundary enforcement.
    Fails safely in case of infrastructure issues while enforcing configured request limits.
    """

    @classmethod
    def check_rate_limit(cls, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds

        # Prune old timestamps
        cls._prune(key, cutoff)

        current_count = len(_request_counters[key])
        if current_count >= max_requests:
            retry_after = int(window_seconds - (now - _request_counters[key][0]))
            return False, max(1, retry_after)

        _request_counters[key].append(now)
        return True, 0

    @classmethod
    def _prune(cls, key: str, cutoff: float):
        _request_counters[key] = [t for t in _request_counters[key] if t > cutoff]

    @classmethod
    def reset(cls):
        _request_counters.clear()


class DownloadTokenManager:
    """
    Cryptographically signed, execution-scoped, short-lived download token manager.
    Enforces expiration, subject linkage, execution scope, and format locking.
    """

    @classmethod
    def create_download_token(
        cls,
        execution_id: str,
        user_id: str,
        format_ext: str,
        expires_minutes: int = settings.DOWNLOAD_TOKEN_EXPIRE_MINUTES
    ) -> str:
        now = int(time.time())
        exp = now + (expires_minutes * 60)
        payload = {
            "sub": user_id,
            "exec_id": execution_id,
            "fmt": format_ext.lower().strip("."),
            "type": "download_token",
            "iat": now,
            "exp": exp
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

    @classmethod
    def verify_download_token(cls, token: str, expected_execution_id: str, expected_format: str, expected_user_id: str = None) -> bool:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_exp": True, "verify_iat": True}
            )
            if payload.get("type") != "download_token":
                return False
            if payload.get("exec_id") != expected_execution_id:
                return False
            if payload.get("fmt") != expected_format.lower().strip("."):
                return False
            if expected_user_id and payload.get("sub") != expected_user_id:
                return False
            return True
        except jwt.PyJWTError:
            return False
