"""
模型层：双模型架构
- GLM-5V-Turbo（智谱）：OCR 手写识别（多模态视觉）
- deepseek-v4-pro（DeepSeek）：语法批改 + 四维评分（结构化输出）

两个模型均兼容 OpenAI API 格式，通过 ChatOpenAI 统一接入。
"""
from langchain_openai import ChatOpenAI
from src.config.settings import settings


def get_ocr_model(temperature: float = 0.1) -> ChatOpenAI:
    """
    OCR 视觉模型：GLM-5V-Turbo（智谱）
    用于答题纸图片的手写内容识别，支持多模态图片输入。
    低温度保证识别准确率。
    """
    return ChatOpenAI(
        model=settings.ZHIPU_OCR_MODEL,         # "glm-5v-turbo"
        api_key=settings.ZHIPU_API_KEY or None,
        base_url=settings.ZHIPU_BASE_URL,        # "https://open.bigmodel.cn/api/paas/v4/"
        temperature=temperature,
        max_tokens=4096,
    )


def get_grading_model(temperature: float = 0.3) -> ChatOpenAI:
    """
    作文批改模型：deepseek-v4-pro（DeepSeek）
    用于语法批改、四维评分，支持结构化 JSON 输出 (with_structured_output)。
    """
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,           # "deepseek-v4-pro"
        api_key=settings.DEEPSEEK_API_KEY or None,
        base_url=settings.DEEPSEEK_BASE_URL,      # "https://api.deepseek.com/v1"
        temperature=temperature,
        max_tokens=4096,
    )


def get_light_model(temperature: float = 0.1) -> ChatOpenAI:
    """
    轻量辅助模型：用于模板去除等简单任务。
    优先尝试 DeepSeek 轻量模型，不可用则回退到 GLM-4-Flash。
    """
    if settings.DEEPSEEK_API_KEY:
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=settings.DEEPSEEK_API_KEY or None,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=temperature,
            max_tokens=2048,
        )
    else:
        return ChatOpenAI(
            model="glm-4-flash",
            api_key=settings.ZHIPU_API_KEY or None,
            base_url=settings.ZHIPU_BASE_URL,
            temperature=temperature,
            max_tokens=2048,
        )
