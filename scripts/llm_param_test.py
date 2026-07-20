from openai import OpenAI
from core.config import settings
import json
from core.logger import logger

# 只设置了base_url和api_key是为什么？
client = OpenAI(
    api_key = settings.LLM_API_KEY,
    base_url = settings.LLM_BASE_URL,
    timeout = settings.LLM_TIMEOUT
)

prompt = """
你是意图识别专家。严格按照JSON格式输出，禁止额外文字、禁止markdown。
需求：判断用户提问意图，可选类型：query_order(工单查询), query_customer(客户信息查询), other(无关咨询)
schema:
{
    "intent": str,
    "param": {"order_id": str | null}
}
用户问题：__QUESTION__
一步一步给出思考
"""


def get_answer_fromllm(question: str):

    # 1.优秀的开发者会习惯性把Prompt渲染结果记录下来(DEBUG级别)
    rendered_prompt = prompt.replace("__QUESTION__", question)
    logger.debug(f"Rendered Prompt: {rendered_prompt}")

    response = client.chat.completions.create(
        messages = [
            {"role": "user","content":rendered_prompt}
        ],
        model = settings.LLM_MODEL,
        temperature=0.1
    )
    raw_content = response.choices[0].message.content

    # 解析前，留下审计日志
    logger.debug(f"LLM Raw Response: {raw_content}")

    if raw_content is None:
        logger.warning("LLM返回的content是None！可能触发了工具调用或被安全策略拦截。")
        return None
    else:
        try:
            return raw_content

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败！错误原因：{e.msg}")
            logger.error(f"完整数据如下：\n {raw_content}")

if __name__ == "__main__":
    test_list = [
        "帮我查工单OD20260701",
        "客户C1001信息",
        "Agent是什么东西"
    ]
    for q in test_list:
        print("+"*30)
        res = get_answer_fromllm(q)
