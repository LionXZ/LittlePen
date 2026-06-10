"""
OCR 识别工具 - 基于 GLM-5V-Turbo 多模态视觉模型
识别答题纸图片中的手写英文作文内容（含印刷模板文字）。
"""
from langchain.tools import tool
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from src.models.chat_model import get_ocr_model


class OCRInput(BaseModel):
    image_base64: str = Field(description="答题纸图片的 base64 编码")
    prompt_instruction: str = Field(
        default="",
        description="可选的 OCR 提示指令，为空则使用默认指令",
    )


@tool(args_schema=OCRInput)
def ocr_handwriting(image_base64: str, prompt_instruction: str = "") -> str:
    """
    使用 GLM-5V-Turbo 多模态大模型对答题纸图片进行 OCR 识别。

    Args:
        image_base64: 图片的 base64 编码
        prompt_instruction: 可选 OCR 提示指令

    Returns:
        识别到的全部文字内容（含模板和手写）
    """
    model = get_ocr_model(temperature=0.1)

    if not prompt_instruction:
        prompt_instruction = (
            "请仔细识别这张答题纸图片中的所有文字内容。"
            "包括：1) 印刷的模板文字（如题目说明、得分栏等）2) 学生手写的英文作文内容。"
            "请完整输出所有文字，不要遗漏任何内容。"
            "对于手写内容，请尽可能准确地识别每个单词。"
        )

    message = HumanMessage(content=[
        {"type": "text", "text": prompt_instruction},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_base64}"},
        },
    ])

    response = model.invoke([message])
    return response.content
