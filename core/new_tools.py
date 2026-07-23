from langchain_core.tools import StructuredTool
from core.tools import query_customer_info, query_order_info


# @tool是StructuredTool的语法糖
tools = [
    StructuredTool.from_function(query_customer_info),
    StructuredTool.from_function(query_order_info)
]