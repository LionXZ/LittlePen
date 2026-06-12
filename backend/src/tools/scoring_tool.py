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
    subject: str = Field(default="en", description="科目编码: en/cn/ma/sc")


def _extract_json(text: str) -> dict:
    """从 LLM 返回文本中提取 JSON"""
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        text = match.group(1)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)


def _build_scoring_prompt(essay_text: str, ocr_hint: str, subject: str) -> str:
    """根据科目生成评分 prompt"""
    if subject == "cn":
        return f"""你是小学语文作文批改老师。请严格按以下标准对这篇小学生语文作文评分：

<essay>
{essay_text}
</essay>

{ocr_hint}

===== 评分标准（每维度 0-25 分）=====

1. 内容立意 (neatness) — 主题明确度、真情实感
   | A 21-25 | 主题突出，有独到见解或真情实感 |
   | B 16-20 | 主题明确，内容较充实 |
   | C 11-15 | 基本切题，内容平淡 |
   | D 6-10  | 部分跑题，内容空洞 |
   | E 0-5   | 完全跑题 |

2. 语言表达 (content) — 用词准确性、语句通顺度、修辞运用
   | A 21-25 | 语言生动，有恰当修辞，表达流畅 |
   | B 16-20 | 语句通顺，用词准确 |
   | C 11-15 | 语句基本通顺，偶有病句 |
   | D 6-10  | 病句较多，表达不清 |
   | E 0-5   | 语句不通，难以理解 |

3. 篇章结构 (language) — 段落划分、开头结尾、逻辑连贯
   | A 21-25 | 结构完整，段落分明，首尾呼应 |
   | B 16-20 | 有开头结尾，层次较清楚 |
   | C 11-15 | 结构基本完整，段落不够清晰 |
   | D 6-10  | 结构混乱，缺少开头或结尾 |
   | E 0-5   | 无结构 |

4. 书写规范 (structure) — 字迹工整度、标点使用、格式规范
   | A 21-25 | 字迹工整，标点正确，格式规范 |
   | B 16-20 | 字迹较工整，偶有标点错误 |
   | C 11-15 | 字迹一般，标点不规范 |
   | D 6-10  | 字迹潦草，标点缺失多 |
   | E 0-5   | 难以辨认 |

请只返回 JSON（档位中间值：A=23, B=18, C=13, D=8, E=3，可微调 ±2）：
```json
{{
  "neatness": {{"score": 18, "comment": "主题明确，内容较充实"}},
  "content": {{"score": 18, "comment": "语句通顺，用词准确"}},
  "language": {{"score": 13, "comment": "结构基本完整"}},
  "structure": {{"score": 18, "comment": "字迹较工整"}},
  "total_score": 67,
  "overall_comment": "你的作文主题明确！下次试试把故事写得更有趣一些，可以加一些比喻哦。"
}}
```"""

    # 英文（默认）
    return f"""你是儿童英文作文评分老师。请严格按以下标准对这篇小学生作文评分：

<essay>
{essay_text}
</essay>

{ocr_hint}

===== 评分标准（每维度 0-25 分）=====

1. 卷面整洁 (neatness) — 书写工整度、涂改情况
   | A 21-25 | 字迹清晰工整，无涂改或极少涂改 |
   | B 16-20 | 字迹基本清晰，有少量涂改但不影响阅读 |
   | C 11-15 | 字迹较潦草或涂改较多，阅读稍困难 |
   | D 6-10  | 字迹潦草，大面积涂改 |
   | E 0-5   | 无法辨认，整篇凌乱 |

2. 内容要点 (content) — 切题度、要点完整性、论述充分度
   | A 21-25 | 完全切题，观点明确，有具体例子或细节支撑 |
   | B 16-20 | 切题，观点较清晰，但细节不够丰富 |
   | C 11-15 | 基本切题但内容单薄，缺少细节描述 |
   | D 6-10  | 部分偏离主题，内容很少 |
   | E 0-5   | 完全跑题或无实质内容 |

3. 语言质量 (language) — 词汇、语法、表达流畅度
   | A 21-25 | 用词丰富准确，语法正确，表达自然流畅 |
   | B 16-20 | 用词基本恰当，偶有语法错误，不影响理解 |
   | C 11-15 | 词汇有限，有多处语法错误，但大意可懂 |
   | D 6-10  | 词汇贫乏，大量语法错误，部分句子难以理解 |
   | E 0-5   | 几乎无完整句子，大量拼写错误 |

4. 篇章结构 (structure) — 段落、逻辑、开头结尾
   | A 21-25 | 段落分明，有清晰的开头-主体-结尾，逻辑连贯 |
   | B 16-20 | 有分段意识，有开头和结尾，逻辑基本清晰 |
   | C 11-15 | 段落划分不明显，逻辑跳跃 |
   | D 6-10  | 无段落划分，结构混乱 |
   | E 0-5   | 仅1-2个句子，无结构可言 |

请只返回 JSON（档位中间值：A=23, B=18, C=13, D=8, E=3，可微调 ±2）：
```json
{{
  "neatness": {{"score": 18, "comment": "字迹基本清晰，少量涂改"}},
  "content": {{"score": 18, "comment": "内容切题，但缺少具体例子"}},
  "language": {{"score": 13, "comment": "词汇有限，有多处语法错误"}},
  "structure": {{"score": 13, "comment": "段落划分不明显"}},
  "total_score": 62,
  "overall_comment": "你能写出完整的想法，真棒！试试在下一次作文中加入一些具体例子。"
}}
```"""


@tool(args_schema=ScoringInput)
def score_essay_4dimensions(essay_text: str, ocr_quality_note: str = "", subject: str = "en") -> dict:
    """
    从4个维度对儿童作文进行评分，支持多科目。

    英语(en): 卷面整洁/内容要点/语言质量/篇章结构
    语文(cn): 内容立意/语言表达/篇章结构/书写规范
    每维度 0-25 分，综合分为四维之和。
    """
    model = get_grading_model()  # temperature=0，确保评分一致
    ocr_hint = f"OCR 识别质量参考: {ocr_quality_note}" if ocr_quality_note else ""
    prompt = _build_scoring_prompt(essay_text, ocr_hint, subject)

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
