# 模拟工单数据库
MOCK_ORDER_DB = {
    "OD20260701": {"status": "处理中", "handler": "产品专员张三", "create_time": "2026-07-01"},
    "OD20260702": {"status": "已完成", "handler": "售后李四", "create_time": "2026-07-02"}
}

# 模拟客户库
MOCK_CUSTOMER_DB = {
    "C1001": {"level": "VIP客户", "phone": "138xxxx1234"},
    "C1002": {"level": "普通客户", "phone": "139xxxx5678"}
}


# 写一个函数返回工单信息
def query_order_info(order_id: str):
    """
    根据工单id查询工单信息
    :param order_id：工单编号
    """
    return MOCK_ORDER_DB.get(order_id, {"msg":"未查询到该工单"})

def query_customer_info(customer_id: str):
    """
    根据客户id查询客户信息
    :param: customer_id
    """
    return MOCK_CUSTOMER_DB.get(customer_id, {"msg":"未查询到该客户"})

# 工具注册描述，LLM识别
TOOLS_DEF = [
    {
        "type":"function",
        "function":{
            "name": "query_order_info",
            "description": "查询工单详情，需要传入order_id",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id":{"type":"string", "description":"工单编号"}
                },
                "required":["order_id"] # 没看明白，为什么用了[]包起来; 答案：为的是多个args也能使用这个结构
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name": "query_customer_info",
            "description": "查询客户信息，需要customer_id",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type":"string", "description": "客户编号"}
                },
                "required":["customer_id"]
            }
        }
    }
]

# 工具名称映射函数，用户反射调用
TOOLS_MAP = {
    "query_order_info": query_order_info,
    "query_customer_info": query_customer_info
}