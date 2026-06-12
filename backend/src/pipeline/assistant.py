"""
作文批改 Agent 入口
支持同步批改和流式 SSE 进度推送
"""
import base64
from typing import AsyncIterator, Dict, Any
from src.pipeline.graph import grading_pipeline
from src.pipeline.state import EssayGradingState
from src.utils.logger import logger


def _build_initial_state(image_base64: str) -> dict:
    """构建初始状态"""
    return {
        "image_base64": image_base64,
        "qr_raw": "",
        "qr_data": None,
        "subject": "",
        "ocr_raw_text": "",
        "essay_clean_text": "",
        "grammar_errors": [],
        "scores": None,
        "total_score": 0.0,
        "error": None,
        "current_step": "start",
    }


def _build_result(final_state: dict, thread_id: str) -> Dict[str, Any]:
    """从最终状态构建返回结果"""
    return {
        "qr_data": final_state.get("qr_data"),
        "essay_clean_text": final_state.get("essay_clean_text"),
        "grammar_errors": final_state.get("grammar_errors", []),
        "scores": final_state.get("scores"),
        "total_score": final_state.get("total_score", 0.0),
        "error": final_state.get("error"),
        "thread_id": thread_id,
    }


class EssayGradingAgent:
    """作文批改 Agent"""

    def __init__(self):
        self.pipeline = grading_pipeline

    async def grade(
        self,
        image_path: str = None,
        image_base64: str = None,
        thread_id: str = "default",
    ) -> Dict[str, Any]:
        """
        同步批改：上传图片，等待完整结果返回。

        Args:
            image_path: 图片文件路径
            image_base64: 图片 base64 编码（二选一）
            thread_id: 会话ID

        Returns:
            完整批改结果 dict
        """
        if image_path and not image_base64:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

        if not image_base64:
            return {"error": "请提供 image_path 或 image_base64", "thread_id": thread_id}

        logger.info(f"开始批改, thread_id={thread_id}")

        initial_state = _build_initial_state(image_base64)
        config = {"configurable": {"thread_id": thread_id}}

        try:
            final_state = await self.pipeline.ainvoke(initial_state, config)
            logger.info(f"批改完成, thread_id={thread_id}")
            return _build_result(final_state, thread_id)
        except Exception as e:
            logger.error(f"批改失败, thread_id={thread_id}, error={str(e)}")
            return {
                "error": f"批改流水线执行失败: {str(e)}",
                "thread_id": thread_id,
            }

    async def grade_stream(
        self,
        image_base64: str,
        thread_id: str = "default",
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式批改：通过 SSE 推送每一步的处理进度。

        使用 astream(stream_mode="values") 获取完整状态。
        """
        logger.info(f"开始流式批改, thread_id={thread_id}")

        initial_state = _build_initial_state(image_base64)
        config = {"configurable": {"thread_id": thread_id}}

        try:
            async for state in self.pipeline.astream(
                initial_state, config, stream_mode="values"
            ):
                step = state.get("current_step", "")

                if step == "done":
                    yield {
                        "step": "done",
                        "data": _build_result(state, thread_id),
                    }
                elif step == "error":
                    yield {
                        "step": "error",
                        "data": {"error": state.get("error", "未知错误")},
                    }
                elif step:
                    yield {"step": step}

        except Exception as e:
            logger.error(f"流式批改失败, thread_id={thread_id}, error={str(e)}")
            yield {"step": "error", "data": {"error": str(e)}}


essay_agent = EssayGradingAgent()
