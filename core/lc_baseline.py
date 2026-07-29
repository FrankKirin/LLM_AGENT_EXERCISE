from langchain_openai import ChatOpenAI
from core.config import settings
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from core.tools import query_customer_info, query_order_info
from core.logger import logger

# 创建ChatOpenAI
llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    model = settings.LLM_MODEL,
    api_key = settings.LLM_API_KEY,
    temperature = 0.3,
    timeout = settings.LLM_TIMEOUT
)

# 注册query_user_id， query_order_id方法
@tool
def tool_query_user(user_id: str)->str:
    """
    输入userid，查询到user信息后返回
    """
    res = query_customer_info(user_id)
    logger.info("执行工具：查询客户", user_id=user_id)
    return str(res)

@tool
def tool_query_order(order_id: str)->str:
    """
    输入orderid，查询到user信息后返回
    """
    res = query_order_info(order_id)
    # logger.info(f"query order info through tool: {res}")
    logger.info("执行工具：查询工单", order_id=order_id)
    return str(res)

tools = [tool_query_user, tool_query_order]

# 放ReAct标准英文版提示词
REACT_AGENT_PROMPT = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:
{tools}

Use the following format strictly:
Question: input question to answer
Thought: consider what action to take
Action: tool name, one of [{tool_names}]
Action Input: parameters for tool
Observation: result returned by tool
(Repeat Thought/Action/Action Input/Observation as needed)
Thought: I have enough information
Final Answer: natural language final answer

Conversation history:
{chat_history}

Question: {input}
{agent_scratchpad}
""")