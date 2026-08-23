from core.logger import logger
import time
import asyncio
from core.performance_optimizer import AnswerCache, ConcurrencyLimiter

def test_answer_cache():
    # 相同问题第二次命中，过期后失效
    logger.info("=" * 60)
    logger.info("测试1：答案缓存")
    logger.info("=" * 60)
    cache = AnswerCache(ttl_seconds=2)
    query = "什么是AI Agent？"

    assert cache.get(query) is None
    logger.info("第一次：缓存未命中")

    cache.set(query, "AI Agent是自主能力的智能体")
    result = cache.get(query)
    assert result is not None and "智能体" in result
    logger.info("第二次： 缓存命中")

    time.sleep(2.1)
    assert cache.get(query) is None, "缓存未失效，仍能找到"
    logger.info("过期后，缓存失效")

# test_answer_cache()

async def test_concurrency_limiter():
    limiter = ConcurrencyLimiter(max_concurrent=3)

    async def slow_task(task_id: int) -> str:
        await asyncio.sleep(0.2)
        # time.sleep(0.2)
        return f"task_{task_id}_done"

    start = time.time()
    tasks = [limiter.execute(slow_task, i) for i in range(5)]

    # print("--------------------")
    # print(*tasks)
    results = await asyncio.gather(*tasks)
    total = time.time() - start
    print(f"实际总耗时:{total}")
    assert total >= 0.3 and len(results)==5

asyncio.run(test_concurrency_limiter())