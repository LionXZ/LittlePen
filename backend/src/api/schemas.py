"""
请求/响应 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional


# ===== 请求模型 =====

class GradeRequest(BaseModel):
    """批改请求 - base64 图片"""
    image_base64: str = Field(description="图片 base64 编码")
    thread_id: str = Field(default="default", description="会话 ID")


# ===== 响应子模型 =====

class QRData(BaseModel):
    course_id: str
    class_id: str
    schedule_id: str
    student_id: str
    student_name: str
    gender: str


class GrammarErrorItem(BaseModel):
    original: str
    corrected: str
    error_type: str
    explanation: str


class DimensionScoreItem(BaseModel):
    score: float
    comment: str


class ScoresData(BaseModel):
    neatness: DimensionScoreItem
    content: DimensionScoreItem
    language: DimensionScoreItem
    structure: DimensionScoreItem


# ===== 响应模型 =====

class GradeResponse(BaseModel):
    """批改完整响应"""
    qr_data: Optional[QRData] = None
    essay_clean_text: str = ""
    grammar_errors: List[GrammarErrorItem] = []
    scores: Optional[ScoresData] = None
    total_score: float = 0.0
    error: Optional[str] = None
    thread_id: str = ""


class HealthResponse(BaseModel):
    status: str
    version: str


class SSEProgressEvent(BaseModel):
    """SSE 流式进度事件"""
    step: str
    data: Optional[dict] = None
