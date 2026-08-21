import asyncio
import hashlib
import json
import time
from typing import Optional, Callable, Any
from collections import defaultdict
from core.config import settings

# 1.答案缓存
class AnswerCache:
    # 内存答案缓存，生产一般用redis
    def __init__(self, ttl_seconds: int=300):
        self.ttl = ttl_seconds  # 设置的过期时间
        self._cache: dict[str, tuple[str, float]] = {}  # 生成的16进制hash码作为key, 

    def _make_key(self, query: str, **kwargs) -> str:
        key_str = f"{query}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, query: str, **kwargs) -> Optional[str]:
        # 我不传**kwargs会怎么样
        key = self._make_key(query, **kwargs)
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                return value
            del self._cache[key]    # 删除对应键值对
        return None

    def set(self, query: str, value: str, **kwargs):
        key = self._make_key(query, **kwargs)
        self._cache[key] = (value, time.time() + self.ttl)

    @property
    def size(self) -> int:
        return len(self._cache)


# 2.并发控制器


# 3.请求合并器