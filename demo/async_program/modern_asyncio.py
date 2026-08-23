import asyncio
from rich import print

async def modern_style():

    fut1 = asyncio.Future()

    loop1 = fut1.get_loop()
    # 底层loop不同
    print(f"fut1 loop: {loop1}")

    # 方法2: 显式创建
    loop = asyncio.get_running_loop()
    fut2 = loop.create_future()

    loop2 = fut2.get_loop()
    print(f"fut2 loop: {loop2}")

    print(f"Same type? {type(fut1) == type(fut2)}")

    fut1.set_result("ok1")
    fut2.set_result("ok2")

    print(await fut1)
    print(await fut2)


asyncio.run(modern_style())