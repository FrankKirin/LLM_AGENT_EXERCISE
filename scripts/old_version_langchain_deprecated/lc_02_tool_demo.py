from core.lc_baseline import tool_query_order
from core.logger import logger


if __name__ == "__main__":
    # 注册成tool后可以直接调用invoke函数
    res = tool_query_order.invoke({"order_id":"OD20260701"})
    logger.info("工具测试结果:",res = res)
    print(res)