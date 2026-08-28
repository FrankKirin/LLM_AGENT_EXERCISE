"""
思路：限流+熔断
1.滑动窗口限流：每个用户每分钟最多N次
实现思路：对于每个api_key，记录每次请求发生的时间
2.熔断器：错误率超阈值快速失败，冷却后半开试探
"""
import time
from enum import Enum
from collections import defaultdict, deque
from core.structured_logger import log_info

class SlidingWindowLimiter:
    """滑动窗口限流器:每个用户在指定时间内最多请求多少次"""
    def __init__(self, max_requests: int=60, windows_seconds: int=60):
        self.max_requests = max_requests
        self.window_seconds = windows_seconds  # 滑动窗口宽度
        # str存放api_key，deque存放api_key的请求时间
        self.requests: dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """
        输入：
        处理：
        输出：
            (是否允许，{"最大限制数","当前限制数","剩余请求数","稍后多久可重试"})
        """
        # 最大请求次数内，保留；滑动窗口时间范围之内保留
        now = time.time()
        # defaultdict(deque), 如果key不存在，就自动创建一个deque()
        queue = self.requests[key]
        # 把不合法的请求时间都抛掉,只能先处理时间，哪些请求合法只跟时间有关
        while queue and now-queue[0] >self.window_seconds:
            queue.popleft()
        current_len = len(queue)
        if current_len >= self.max_requests:
            retry_after = self.window_seconds - (now-queue[0]) if queue else 0  # retry_after其实是最早请求过期时间
            return False, {"limit": self.max_requests, "current": current_len, "remaining": 0, "retry_after": retry_after}
        return True, {"limit": self.max_requests, "current": current_len+1, "remaining": self.max_requests-current_len, "retry_after": retry_after}

class CircuitState(str, Enum):
    CLOSED = "closed" # 正常调用是closed
    OPEN = "open"  # 失败太多就从closed到open状态
    HALF_OPEN = "half_open"  # 等待一段时间变成half_open，测试成功从half_open变成closed

class CircuitBreaker:
    """"""
    def __init__(self, name: str, fail_threshold: float=0.5,
                 recovery_timeout: int=30, min_requests: int=10):
        self.name = name
        self.fail_threshold = fail_threshold
        self.min_requests = min_requests
        self.state = CircuitState.CLOSED
        self.success_count = 0
        self.fail_count = 0
        # self.fail_rate = 100 * (self.fail_count/(self.fail_count+self.success_count))
        self.last_failure_time: float | None = None
        self.revocery_timeout = recovery_timeout

    def can_execute(self) -> bool:
        # 根据实例的state来返回True/False
        if self.state == CircuitState.CLOSED:
            return True
        # 只看上一次失败时间
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time()-self.last_failure_time) > self.revocery_timeout:
                # 修改状态为half_open
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True


    def _reset(self):
        self.fail_count = 0
        self.success_count = 0

rate_limiter = SlidingWindowLimiter(max_requests=60, windows_seconds=60)