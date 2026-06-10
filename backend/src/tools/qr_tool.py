"""
二维码解析工具 - 基于 OpenCV QRCodeDetector
从答题纸图片中识别二维码，解析出课程ID、班级ID、排课ID、学号、学生姓名、性别。
格式：课程ID-班级ID-排课ID-学号-encodeURIComponent(学生姓名)-性别
"""
import base64
import cv2
import numpy as np
from urllib.parse import unquote
from langchain.tools import tool
from pydantic import BaseModel, Field


class QRParseInput(BaseModel):
    image_base64: str = Field(description="答题纸图片的 base64 编码")


@tool(args_schema=QRParseInput)
def parse_qr_code(image_base64: str) -> dict:
    """
    从答题纸图片中识别并解析二维码信息。

    二维码格式：课程ID-班级ID-排课ID-学号-encodeURIComponent(学生姓名)-性别
    姓名段使用 encodeURIComponent 编码，解析时用 decodeURIComponent 还原。

    返回 {"error": str|None, "qr_raw": str, "qr_data": dict|None}
    """
    try:
        image_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        qr_detector = cv2.QRCodeDetector()
        qr_str, points, _ = qr_detector.detectAndDecode(image)

        if not qr_str:
            return {"error": "未检测到二维码", "qr_raw": "", "qr_data": None}

        parts = qr_str.split("-")

        if len(parts) < 6:
            return {
                "error": f"二维码格式异常，期望至少6段，实际{len(parts)}段: {qr_str}",
                "qr_raw": qr_str,
                "qr_data": None,
            }

        qr_data = {
            "course_id": parts[0],
            "class_id": parts[1],
            "schedule_id": parts[2],
            "student_id": parts[3],
            "student_name": unquote(parts[4]),
            "gender": parts[5],
        }

        return {"error": None, "qr_raw": qr_str, "qr_data": qr_data}

    except Exception as e:
        return {"error": f"二维码解析失败: {str(e)}", "qr_raw": "", "qr_data": None}
