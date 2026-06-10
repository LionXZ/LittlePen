"""
四维评分工具 - 基于 deepseek-v4-pro
从卷面整洁、内容要点、语言质量、篇章结构 4 个维度评分。
每维度 0-25 分，综合分 = 四维之和。
"""
import json
import re
from pydantic import BaseModel, Field
from langchain.tools import tool
from src.models.chat_model import get_grading_model
from src.config.settings import settings


class DimensionScore(BaseModel):
    score: float = Field(
        description=f"维度得分，范围 {settings.SCORE_RANGE[0]}-{settings.SCORE_RANGE[1]}"
    )
    comment: str = Field(description="简短的中文评语")


class ScoringResult(BaseModel):
    neatness: DimensionScore = Field(description="卷面整洁：书写工整度、涂改情况、排版整洁程度")
    content: DimensionScore = Field(description="内容要点：是否切题、要点完整、论述充分")
    language: DimensionScore = Field(description="语言质量：词汇丰富度、语法准确性、表达流畅度")
    structure: DimensionScore = Field(description="篇章结构：段落划分、逻辑层次、开头结尾完整性")
    total_score: float = Field(description="综合得分（四维之和）")
    overall_comment: str = Field(description="整体评价（中文，鼓励性）")


class ScoringInput(BaseModel):
    essay_text: str = Field(description="作文纯净文本")
    ocr_quality_note: str = Field(
        default="",
        description="OCR 质量描述，用于辅助评估卷面整洁度",
    )


def _extract_json(text: str) -> dict:
    """从 LLM 返回文本中提取 JSON"""
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        text = match.group(1)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)


@tool(args_schema=ScoringInput)
def score_essay_4dimensions(essay_text: str, ocr_quality_note: str = "") -> dict:
    """
    从4个维度对儿童英文作文进行评分。

    维度：卷面整洁(neatness)、内容要点(content)、语言质量(language)、篇章结构(structure)
    每维度 0-25 分，综合分为四维之和。
    """
    model = get_grading_model(temperature=0.3)
    ocr_hint = f"OCR 识别质量参考: {ocr_quality_note}" if ocr_quality_note else ""

    prompt = f"""你是儿童英文作文评分老师。请从以下4个维度对这篇小学生作文评分：

<essay>
{essay_text}
</essay>

{ocr_hint}

评分标准（每维度 0-25 分）：
1. **卷面整洁** (neatness)：书写工整度、涂改情况、排版整洁程度
2. **内容要点** (content)：作文是否切题、要点是否完整、论述是否充分
3. **语言质量** (language)：词汇丰富度、语法准确性、表达流畅程度
4. **篇章结构** (structure)：段落划分是否合理、逻辑层次是否清晰、开头结尾是否完整

要求：
- 评分要客观公正，同时对小学生的努力给予肯定
- 综合得分 = 四个维度分数之和
- overall_comment 用中文写，以鼓励为主，指出1-2个具体改进方向

请严格按照以下 JSON 格式返回（不要输出其他内容）：
```json
{{
  "neatness": {{"score": 20, "comment": "书写工整，卷面整洁"}},
  "content": {{"score": 18, "comment": "内容较完整，切合主题"}},
  "language": {{"score": 16, "comment": "词汇基本准确，偶有语法错误"}},
  "structure": {{"score": 17, "comment": "段落分明，逻辑清晰"}},
  "total_score": 71,
  "overall_comment": "整体评价"
}}
```"""

    response = model.invoke(prompt)
    content = response.content.strip()

    try:
        result = _extract_json(content)
        # 确保 total_score 存在
        if "total_score" not in result:
            dims = ["neatness", "content", "language", "structure"]
            result["total_score"] = sum(
                result.get(d, {}).get("score", 0) for d in dims
            )
        return result
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "neatness": {"score": 0, "comment": ""},
            "content": {"score": 0, "comment": ""},
            "language": {"score": 0, "comment": ""},
            "structure": {"score": 0, "comment": ""},
            "total_score": 0,
            "overall_comment": f"评分解析异常，请重试",
        }
