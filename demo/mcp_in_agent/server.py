# 需求清单
# 1.能够查询订单状态
# 2.能沟根据统一的订单查询规范来分析用户订单异常问题

from pydantic import BaseModel
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError


# 1.创建MCPServer
mcp = MCPServer("Order service MCP", instructions="提供订单查询和订单异常分析能力")

# 2. 模拟订单数据库
ORDERS = {
    "ORD-1001": {
        "status": "shipped",
        "estimated_delivery": "2026-11-17",
        "tracking_message": "商品已离开发货仓，正在运输中。",
    },
    "ORD-1002": {
        "status": "processing",
        "estimated_delivery": "2026-11-19",
        "tracking_message": "商家正在准备商品。",
    },
    "ORD-1003": {
        "status": "delivered",
        "estimated_delivery": "2026-11-14",
        "tracking_message": "商品已签收。",
    },
    "ORD-1004": {
        "status": "delivered",
        "estimated_delivery": "2026-11-14",
        "tracking_message": "商品已签收。",
    },
}

# 3.定义结构化返回数据
class OrderStatus(BaseModel):
    # 使用Pandantic返回结构化对象，client能够直接读取JSON格式的结构化结果
    order_id: str
    status: str
    estimated_delivery: str
    tracking_message: str

# 4.定义Tool: 查询订单状态
# @mcp.tool()注解，方法首段写注释，函数的作用、参数、返回值
# 输入order_id, 输出OrderStatus对象
@mcp.tool()
def get_order_status(order_id: str) -> OrderStatus:
    # python SDK后根据类型注解生成对应的JSON Schema
    """
        根据订单编号查询订单状态

        参数：
            order_id: 订单编号，例如ORD-1001 
        返回：
            订单状态、预计送达时间和物流信息
    """
    normalized_order_id = order_id.strip().upper()

    if not normalized_order_id:
        raise ToolError("订单编号不能为空")

    # get如果获取不到key对应的value，返回是None，不是空
    order = ORDERS.get(normalized_order_id)

    # if not order: 无法区分key不存在和键存在但是值为空的情况
    if order is None:
        raise ToolError(f"订单{normalized_order_id}查询不到")

    return OrderStatus(
        order_id=order_id,
        status=order["status"],
        estimated_delivery=order["estimated_delivery"],
        tracking_message=order["tracking_message"]
    )

# 5.定义Tool: 根据状态查询订单
@mcp.tool()
def search_orders(status:str, limit:int=5)->list[OrderStatus]:
    """
        根据订单状态查询订单列表
        参数：
            status: 订单状态，可选processing，shipped，delivered
            limit: 最多返回多少条订单，范围为1到10
        返回：
            符合条件的订单列表 
    """
    # 校验参数
    normalized_status = status.strip().lower()

    allowed_order_status = ["processing", "shipped", "delivered"]

    if normalized_status not in allowed_order_status:
        raise ToolError(f"订单状态错误，仅允许{allowed_order_status}")

    if limit < 1 or limit > 10:
        raise ToolError("订单数量必须在1-10之间")

    order_result = []
    for order_id, order in ORDERS.items():
        if order["status"] != normalized_status:
            continue
        order_result.append(
            OrderStatus(
                order_id=order_id,
                status=order["status"],
                estimated_delivery=order["estimated_delivery"],
                tracking_message=order["tracking_message"],
            )
        )
        if len(order_result) == limit:
            break

    return order_result

# 6.定义Resource： 订单查询规范
@mcp.resource("policy://orders/lookup")
def get_order_policy() -> str:
    """
        提供订单查询规范。
    """
    return """
    企业订单查询规范：
        1.查询订单必须提供有效的订单编号
        2.订单状态包括：
            - processing: 处理中
            - shipped: 运输中
            - delivered: 已签收
        3.不得在查询结果中编造物流信息。
        4.如果订单不存在，应明确告知用户
        5.物流预计送达时间仅供参考
"""


# 7.定义Prompt：订单异常分析
@mcp.prompt(title="订单异常分析")
def analyze_order_issue(order_id:str, symptom: str)->str:
    """
    根据订单编号和异常表现生成分析提示词
    """
    return f"""
    你是一名企业订单业务分析助手

    请分析一下订单异常：
    订单编号: {order_id}
    异常表现: {symptom}

    请按以下结构回答：
    1.当前异常情况
    2.可能原因
    3.建议排查步骤
    4.是否需要人工介入

    注意：
    不允许编造订单系统中不存在的信息。
    """

# 8.启动MCP Server
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
    )