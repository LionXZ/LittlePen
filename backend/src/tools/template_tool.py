"""
模板去除工具
从 OCR 识别结果中去除预印模板文字，只保留学生手写作文内容。
"""
from langchain.tools import tool
from pydantic import BaseModel, Field
from src.models.chat_model import get_light_model


class TemplateRemoveInput(BaseModel):
    ocr_raw_text: str = Field(description="OCR 原始识别文本（含模板文字和手写内容）")


@tool(args_schema=TemplateRemoveInput)
def remove_template_text(ocr_raw_text: str) -> str:
    """
    从 OCR 结果中去除预印的模板/固定说明文字，只保留学生手写的作文内容。

    使用轻量 LLM 区分"印刷模板"和"手写内容"。
    """
    model = get_light_model(temperature=0.1)

    prompt = f"""以下是从答题纸图片 OCR 识别出来的文字，其中包含了：
- 预印的模板文字（如题目说明、要求、得分栏等印刷体固定文字）
- 学生手写的作文内容

请只提取「学生手写的作文正文」，去除所有预印模板文字。
直接返回纯净的作文正文，不要添加任何额外说明或前缀。

<ocr_text>
{ocr_raw_text}
</ocr_text>"""

    response = model.invoke(prompt)
    return response.content.strip()
