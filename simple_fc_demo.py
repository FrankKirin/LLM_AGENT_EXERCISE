# 手动实现函数调用
import json
from core.logger import logger
from openai import OpenAI
from core.config import settings
from core.tools import TOOLS_DEF, TOOLS_MAP

client = OpenAI(base_url=settings.LLM_BASE_URL,api_key=settings.LLM_API_KEY)

# 三引号不需要手动加换行符,如果双引号需要手动加换行符
PROMPT = """
可用工具列表：__TOOLSINFO__
规则:
1.需要调用工具: 返回 {{"need_call":true, "tool_name":"xxx","args":{{}}}}
2.无需调用工具直接回答，返回 {{"need_call":false, "answer":"回答内容"}}
只能输出JSON，不要其他文字
用户问题：__QUERY__
"""

def simple_fc_run(user_query: str):
    """
    如果需要用工具，调用工具
    如果不调用工具，返回答案
    """
    tools_text = json.dumps(TOOLS_DEF, ensure_ascii=False)  # dumps把python对象把包成字符串发出去
    formated_prompt = PROMPT.replace("__TOOLSINFO__", tools_text).replace("__QUERY__", user_query)
    logger.debug(f"处理后的prompt内容: {formated_prompt}")
    chat = client.chat.completions.create(
        model=settings.LLM_MODEL,
        # 从来没说过message需要返回json格式的prompt作为content
        messages=[{"role":"user", "content": formated_prompt}],  # loads把字符串转为python对象
        temperature=0.1
    )

    raw = chat.choices[0].message.content
    logger.debug(f"LLM原始返回内容：{raw}")

    if raw:
        # python中 非空 字符串的布尔值是True
        # 1.如果LLM判断是问题，直接回答
        # 2.如果LLM判断需要function回答，获取function需要的参数，再调用LLM重新组织语言
        try:
            res = json.loads(raw)
            need_tool = res["need_call"]
            logger.debug(f"LLM返回的need_tool的值: {need_tool}")
            if not need_tool:
                logger.debug(f"非函数调用类型,直接回答问题: {res['answer']}")
                return res["answer"]
            # 这里不写else是因为if里是一句return，直接返回
            tool_name = res["tool_name"]
            args = res["args"]
            logger.debug(f"args数据长这个样子：{args}, type是：{type(args)}")
            if tool_name not in TOOLS_MAP:
                return f"工具不存在：{tool_name}"
            func = TOOLS_MAP[tool_name]
            tool_data = func(**args)

            # 看一下这里有f和没有f有什么区别
            summary_promt = f"""
            用户问题: {user_query}
            工具返回数据: {json.dumps(tool_data, ensure_ascii=False)}
            根据数据简单回答用户问题
            """

            final = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role":"user", "content": summary_promt}],
                temperature=0.3
            )

            if final.choices[0]:
                final_res = final.choices[0].message.content
                logger.debug(f"调用函数返回的内容为: {final_res}")
                return final_res

        except json.JSONDecodeError as e:
            logger.error("手动FC解析失败", error=str(e))
            return "指令解析失败，请重新提问"
    else:
        logger.debug(f"LLM返回None")
        return None


if __name__ == "__main__":
    print(simple_fc_run("查OD20260701工单"))
    print("-"*40)
    print(simple_fc_run("客户C1001什么等级"))
    print("-"*40)
    print(simple_fc_run("什么是大模型Agent"))