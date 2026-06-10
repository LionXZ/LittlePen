"""
API 路由定义
"""
import base64
import json
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from src.api.schemas import GradeRequest, GradeResponse, HealthResponse
from src.pipeline.assistant import essay_agent
from src.config.settings import settings
from src.tools.registry import tool_registry
from src.db.database import save_grading_record, get_grading_record
from src.utils.logger import logger

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
    )


@router.post("/essay/grade", response_model=GradeResponse)
async def grade_essay(request: GradeRequest):
    """
    同步批改：上传 base64 图片，等待完整批改结果返回。
    """
    try:
        result = await essay_agent.grade(
            image_base64=request.image_base64,
            thread_id=request.thread_id,
        )

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        # 持久化批改记录
        record_id = str(uuid.uuid4())
        save_grading_record(record_id, request.thread_id, result)

        logger.info(f"批改记录已保存, id={record_id}, thread_id={request.thread_id}")
        return GradeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批改接口异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批改失败: {str(e)}")


@router.post("/essay/grade/upload")
async def grade_essay_upload(
    file: UploadFile = File(...),
    thread_id: str = Form(default="default"),
):
    """
    上传图片文件进行批改。
    支持格式：PNG, JPG, JPEG
    """
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPG/JPEG 格式")

    contents = await file.read()

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制",
        )

    image_base64 = base64.b64encode(contents).decode("utf-8")

    # 保存上传文件
    import os
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    image_path = os.path.join(upload_dir, f"{uuid.uuid4()}.{ext}")
    with open(image_path, "wb") as f:
        f.write(contents)

    result = await essay_agent.grade(
        image_base64=image_base64,
        thread_id=thread_id,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    record_id = str(uuid.uuid4())
    save_grading_record(record_id, thread_id, result, image_path=image_path)

    logger.info(f"文件上传批改完成, id={record_id}, file={file.filename}")
    return GradeResponse(**result)


@router.post("/essay/grade/stream")
async def grade_essay_stream(request: GradeRequest):
    """
    流式批改：通过 Server-Sent Events (SSE) 推送每一步的处理进度。

    事件格式:
      data: {"step": "qr_parse_done"}
      data: {"step": "ocr_done"}
      data: {"step": "template_remove_done"}
      data: {"step": "grammar_check_done"}
      data: {"step": "scoring_done"}
      data: {"step": "done", "data": {...完整结果...}}
      data: {"step": "error", "data": {"error": "..."}}
      data: [DONE]
    """
    async def event_stream():
        try:
            async for event in essay_agent.grade_stream(
                image_base64=request.image_base64,
                thread_id=request.thread_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"SSE 流异常: {str(e)}")
            error_event = json.dumps(
                {"step": "error", "data": {"error": str(e)}},
                ensure_ascii=False,
            )
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/essay/{record_id}")
async def get_grading_result(record_id: str):
    """查询历史批改记录"""
    record = get_grading_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"批改记录不存在: {record_id}")
    return record
