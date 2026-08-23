import asyncio
import time
from rich import print as rprint

async def slow_task(task_id: int) -> str:
    await asyncio.sleep(0.2)
    return f"task_{task_id}_done"

def normal_slow_task(task_id: int) -> str:
    return f"task_{task_id}_done"

# 基础运行方式
rprint("====基础运行方式====")
result = asyncio.run(slow_task(10))
rprint(result)

# 并发运行方式
rprint("====并发运行方式====")
async def main():
    time_star = time.time()
    results = await asyncio.gather(
        slow_task(1),
        slow_task(2),
        slow_task(3),
    )
    time_duration = time.time() - time_star
    rprint(f"time_duration: {time_duration}")  # 约为0.2，证明gather中函数是并发运行的
    rprint(results)

asyncio.run(main())

# 后台调度
async def test():
    task = asyncio.create_task(slow_task(1))  # 立即开始执行调度，可以不管，做其他事情
    rprint("任务已提交，先做点别的...")
    await asyncio.sleep(0.5)
    rprint("随便做什么，暂时不需要task的结果")
    rprint("好了，现在系统空闲了，去拿task的结果")
    rprint("task的执行结果：")
    # rprint(f"type of task {type(task)}, content of task: {task}")
    result = await task  # 拿到任务结果
    rprint(result)

asyncio.run(test())
