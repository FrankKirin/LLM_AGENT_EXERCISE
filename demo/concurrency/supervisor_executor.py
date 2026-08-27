import asyncio
import time

async def worker_call_llm(worker_name: str, model: str, delay: int):
    # 模拟API调用
    print(f"{worker_name}_{model}开始调用: {time.strftime('%H:%M:%S')}")
    await asyncio.sleep(delay)
    print(f"{worker_name}_{model}结束调用: {time.strftime('%H:%M:%S')}")

    return f"{worker_name}的{model}返回了结果，耗时{delay}s"

async def main_concurrency():
    start = time.time()
    print("并发模式，Supervisor同时派3个Worker \n")
    await asyncio.gather(
        worker_call_llm("research_worker", "GPT-4", 3),
        worker_call_llm("analysis_worker", "DeepSeek-4", 2),
        worker_call_llm("combine_worker", "GLM5.3", 5),
    )
    end = time.time()
    print(f"总共耗时：{end-start}")

async def main_sequential():
    start = time.time()
    print("串行运行模式：Supervisor逐个派Worker")
    await worker_call_llm("research_worker", "GPT-4", 3)
    await worker_call_llm("analysis_worker", "DeepSeek-4", 2)
    await worker_call_llm("combine_worker", "GLM5.3", 5)
    end = time.time()
    print(f"总共耗时：{end-start}")

async def run_comparison():
    await main_concurrency()
    await main_sequential()

asyncio.run(run_comparison())