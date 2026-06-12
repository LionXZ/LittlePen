"""
语法批改工具 - 基于 deepseek-v4-pro
识别英文作文中的语法/拼写/用词/标点错误，给出修正建议和中文解释。
"""
import json
import re
from typing import List
from pydantic import BaseModel, Field
from langchain.tools import tool
from src.models.chat_model import get_grading_model


class GrammarError(BaseModel):
    original: str = Field(description="原文中有语法错误的句子或片段")
    corrected: str = Field(description="修正后的正确表达")
    error_type: str = Field(description="错误类型：语法/拼写/用词/标点")
    explanation: str = Field(description="简短的中文解释，适合儿童理解")


class GrammarCheckResult(BaseModel):
    errors: List[GrammarError] = Field(description="语法错误列表，无错误时为空列表")
    overall_comment: str = Field(description="整体评价")


class GrammarCheckInput(BaseModel):
    essay_text: str = Field(description="去除模板后的纯净学生作文文本")
    subject: str = Field(default="en", description="科目编码: en/cn/ma/sc")


def _extract_json(text: str) -> dict:
    """从 LLM 返回文本中提取 JSON，处理 markdown 代码块包裹等情况"""
    # 尝试匹配 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        text = match.group(1)
    # 尝试匹配 { ... } 直接 JSON
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)


@tool(args_schema=GrammarCheckInput)
def grammar_check(essay_text: str) -> dict:
    """
    使用 deepseek-v4-pro 对学生英文作文进行语法和用词批改。

    识别语法错误、拼写错误、用词不当、标点错误等问题，
    针对每个问题给出修正建议和中文解释（面向儿童）。
    """
    model = get_grading_model()  # temperature=0，确保一致性

    prompt = f"""你是儿童英文作文批改老师。请批改以下小学生英文作文：

<essay>
{essay_text}
</essay>

要求：
1. 找出所有语法错误、拼写错误、用词不当、标点错误
2. 对每个错误给出修正后的句子/片段
3. 解释用简单的中文，适合孩子理解
4. 注意：只指出确实有误的地方，不要过度修改孩子的原创表达
5. 如果作文无错误，返回空的 errors 列表并在 overall_comment 中给予鼓励

请严格按照以下 JSON 格式返回（不要输出其他内容）：
```json
{{
  "errors": [
    {{
      "original": "原文错误句子或片段",
      "corrected": "修正后的正确表达",
      "error_type": "语法|拼写|用词|标点",
      "explanation": "中文解释"
    }}
  ],
  "overall_comment": "整体评价（中文）"
}}
```"""

    response = model.invoke(prompt)
    content = response.content.strip()

    try:
        result = _extract_json(content)
        # 验证必要字段
        if "errors" not in result:
            result["errors"] = []
        if "overall_comment" not in result:
            result["overall_comment"] = ""
        return result
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "errors": [],
            "overall_comment": f"批改结果解析异常，请重试。原始返回: {content[:200]}",
        }
