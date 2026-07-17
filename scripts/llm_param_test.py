from openai import OpenAI
from core.config import settings
import json

# 只设置了base_url和api_key是为什么？
client = OpenAI(
    api_key = settings.LLM_API_KEY,
    base_url = settings.LLM_BASE_URL,
)

prompt = """
你是意图识别专家。严格按照JSON格式输出，禁止额外文字、禁止markdown。
需求：判断用户提问意图，可选类型：query_order(工单查询), query_customer(客户信息查询), other(无关咨询)
schema:
{
    "intent": str,
    "param": {"order_id": str | null}
}
用户问题：{question}
一步一步给出思考
"""

# question = "帮我查询OD20260701这个工单状态"
question = "帮我查询KCJ201842这个客户信息"

response = client.chat.completions.create(
    messages = [{
        "role": "user",
        "content": prompt.format(question=question)
    }],
    model = settings.LLM_MODEL,
    temperature=0.1
)

print(response.choices[0].message.content)
