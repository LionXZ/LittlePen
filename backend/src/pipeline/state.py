"""
作文批改流水线状态定义 (LangGraph State)
"""
from typing import TypedDict, List, Optional, Annotated


def _pick_latest(left: str, right: str) -> str:
    """Reducer: 并行写入时取最后到达的值"""
    return right


class EssayGradingState(TypedDict):
    # 输入
    image_base64: str

    # QR 解析
    qr_raw: str
    qr_data: Optional[dict]
    subject: str  # 科目: en/cn/ma/sc

    # OCR
    ocr_raw_text: str
    essay_clean_text: str

    # 批改
    grammar_errors: List[dict]

    # 评分
    scores: Optional[dict]
    total_score: float

    # 流程控制 (Annotated 解决并行节点写冲突)
    error: Optional[str]
    current_step: Annotated[str, _pick_latest]
