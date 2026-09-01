# LLM-as-Judge自动裁判
import json
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI
from core.config import settings
from core.structured_logger import log_warning


JUDGE_PROMPT = """
你是专业的AI Agent评测裁判，请严格按照评分规则对用户问题、Agent回答、参考上下文进行打分。
评分规则：满分10分，保留1位小数

[评分维度]
1.hallucination_score 幻觉分：无编造事实10分，轻微编造6分，严重虚假0分
2.faithfulness忠诚度：完全基于上下文10分，部分脱离5分，完全脱离0分
3.usefulness有用性：精准解决问题10分，回答无关3分，无效回答0分

用户问题: {query}
参考上下文: {context}
Agent回答: {response}

只输出JSON格式，严格遵守以下输出结构
{{"hallucination_score":2.5, "faithfulness": 3.5, 
"usefulness": 5.0, "reason": "幻觉较为严重"}}
"""

class JudgeResult(BaseModel):
    hallucination_score: float = Field(description="幻觉打分0-10")
    faithfulness: float = Field(description="忠诚度打分0-10")
    usefulness: float = Field(description="有用性打分0-10")
    reason: str = Field(description="简短打分原因")

class LLMJudge:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            temperature=0.0
        )

    async def score(self, query: str, context: str, response: str)->JudgeResult | None:
        prompt = JUDGE_PROMPT.format(
            query=query,
            context=context,
            response=response
        )
        res = await self.llm.ainvoke(prompt)
        try:
            if res.content:
                info = json.loads(res.content)
                if info:
                    result = JudgeResult(**info)
                    return result
            return None
        except (ValidationError, json.JSONDecodeError) as e:
            log_warning("LLM Judge结果解析失败", error=str(e))

judge = LLMJudge()