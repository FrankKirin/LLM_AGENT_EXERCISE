import asyncio
import hashlib
import json
import time
from typing import Optional, Callable, Any
from collections import defaultdict
from core.config import settings

# 1.答案缓存
class AnswerCache:
    """
    输入：

    处理：

    输出：

    """
    # 内存答案缓存，生产一般用redis
    def __init__(self, ttl_seconds: int=300):
        self.ttl = ttl_seconds  # 设置的过期时间为5分钟
        self._cache: dict[str, tuple[str, float]] = {}  # 生成的16进制hash码作为key, 

    # 为用户query，以及**kwargs联合内容生成缓存key
    def _make_key(self, query: str, **kwargs) -> str:
        key_str = f"{query}:{json.dumps(kwargs, sort_keys=True)}"   # 拼接query和kwargs, sort_keys是保证能找到缓存的关键
        return hashlib.md5(key_str.encode()).hexdigest()    # md5把长字符串变成一个固定长的字符串

    def get(self, query: str, **kwargs) -> Optional[str]:
        key = self._make_key(query, **kwargs)
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                return value  # 返回答案作为value
            del self._cache[key]    # 删除对应键值对
        return None

    def set(self, query: str, value: str, **kwargs):
        # query一般是问题，value一般是问题的答案
        key = self._make_key(query, **kwargs)
        self._cache[key] = (value, time.time() + self.ttl)

    @property
    def size(self) -> int:  # 可以像访问属性一样访问：cache.size
        return len(self._cache)

answercache = AnswerCache()

# 2.并发控制器
class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.current_running = 0
        self.max_concurrent = max_concurrent

    async def execute(self, func: Callable, *args, **kwargs)->Any:
        async with self.semaphore:
            self.current_running += 1
            try:
                return await func(*args, **kwargs)
            finally:
                self.current_running -= 1

concurrency_limiter = ConcurrencyLimiter(max_concurrent=settings.max_concurrent_requests)

# 3.请求合并器
class RequestBatcher:
    """短时间内想通请求合并为一次调用，结果共享"""
    def __init__(self, batch_window_ms: int=100):
        self.batch_window = batch_window_ms / 1000
        # defaultdict可以做到访问不存在的键，自动创建默认值
        self._pending: dict[str, list[asyncio.Future]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def execute(self, key: str, func: Callable, *args, **kwargs) -> Any:
        loop = asyncio.get_running_loop()   # get_event_loop是老版本，不建议用
        future = loop.create_future()  # 创建一个Future对象

        async with self._lock:
            self._pending[key].append(future)
            is_first = len(self._pending[key]) == 1

        if not is_first:
            return await future

        await asyncio.sleep(self.batch_window)

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                futures = self._pending.pop(key, [])
                for f in futures:
                    if not f.done():
                        f.set_result(result)
            return result
        except Exception as e:
            async with self._lock:
                futures = self._pending.pop(key, [])
                for f in futures:
                    if not f.done():
                        f.set_exception(e)
            raise

request_batcher = RequestBatcher(batch_window_ms=100)  