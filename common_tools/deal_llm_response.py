
def clean_json(input:str)-> str:
    # 1.首先判断是否是str
    if not isinstance(input, str):
        raise ValueError("LLM返回内容不是字符串")
    input = input.strip()
    # 2.判断是否为空字符串
    if not input:
        raise ValueError("LLM返回字符串内容为空")
    # 纠正LLM返回的markdown格式```json```
    if input.startswith("```"):
        input = input.replace("```json", "")
        input = input.replace("```", "")
        input = input.strip()
    return input
