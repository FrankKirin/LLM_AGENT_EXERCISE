# import os
from openai import OpenAI

client = OpenAI(
    api_key="sk-5783d8313cdf494a84b34da8c5a67b66",
    base_url = "https://api.deepseek.com"
)

response = client.chat.completions.create(
    model = "deepseek-v4-flash", # 指定模型
    # model = "deepseek-v4-pro", # 指定模型
    messages = [              # 对话历史
        {"role": "system", "content": "You are a helpful assistant"},   # 系统提示词
        {"role": "user", "content": "对于锂电池来说，浅充浅放能延长寿命，是否定期也需要充满？"},   # 用户输入的内容
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}}
)

print(response.choices[0].message.content)