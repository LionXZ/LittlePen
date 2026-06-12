"""
API 路由定义
"""
import asyncio
import base64
import json
import os
import uuid
import zipfile
import io
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from src.api.schemas import (
    GradeRequest, GradeResponse, HealthResponse,
    BatchCreateResponse, BatchItemInfo,
    BatchStatusResponse, BatchItemStatus,
)
from src.pipeline.assistant import essay_agent
from src.config.settings import settings
from src.tools.registry import tool_registry
from src.db.database import (
    save_grading_record, get_grading_record,
    create_pending_record, update_record_status,
    list_records_by_batch, list_grading_records,
    get_stats_overview, get_stats_by_class, get_stats_by_student,
)
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
        await save_grading_record(record_id, request.thread_id, result)

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
    await save_grading_record(record_id, thread_id, result, image_path=image_path)

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
    record = await get_grading_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"批改记录不存在: {record_id}")
    return record


@router.get("/essay/{record_id}/report")
async def download_report(record_id: str):
    """下载批改报告 PDF"""
    from fastapi.responses import FileResponse
    from src.pipeline.report_generator import generate_report

    record = await get_grading_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"批改记录不存在: {record_id}")

    output_dir = os.path.join(settings.UPLOAD_DIR, "reports")
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"{record_id}.pdf")

    generate_report(record, pdf_path)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"批改报告_{record.get('student_name', record_id)}.pdf",
    )


# ===== 统计看板 =====

@router.get("/stats/overview")
async def stats_overview():
    """全局成绩统计"""
    return await get_stats_overview()


@router.get("/stats/class")
async def stats_by_class():
    """按班级统计"""
    return await get_stats_by_class()


@router.get("/stats/student/{student_id}")
async def stats_by_student(student_id: str, limit: int = 20):
    """学生成绩趋势"""
    return await get_stats_by_student(student_id, limit)


# ===== 作业列表 =====

@router.get("/essays")
async def list_essays(limit: int = 50, offset: int = 0):
    """查询全部批改记录列表"""
    records = await list_grading_records(limit=limit, offset=offset)
    return {"items": records, "total": len(records)}


# ===== 批量批改 =====

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg"}


def _is_image_ext(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_IMAGE_EXT


@router.post("/batch/upload")
async def batch_upload(
    files: Optional[List[UploadFile]] = File(default=None, description="多个图片文件"),
    zip_file: Optional[UploadFile] = File(default=None, description="ZIP 压缩包"),
    thread_id: str = Form(default="default"),
):
    """
    批量上传：支持多文件或 zip 压缩包。
    上传后立即返回 batch_id，后台异步处理每张图片。
    """
    batch_id = str(uuid.uuid4())
    upload_files: list[tuple[str, bytes]] = []  # (filename, file_bytes)

    # 处理 zip 文件
    if zip_file is not None and zip_file.filename:
        if not zip_file.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="压缩包必须是 .zip 格式")
        try:
            contents = await zip_file.read()
            with zipfile.ZipFile(io.BytesIO(contents)) as zf:
                for info in zf.infolist():
                    # 处理文件名编码：先尝试 UTF-8，失败回退到 GBK/CP437
                    try:
                        name = info.filename.encode("cp437").decode("utf-8")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        try:
                            name = info.filename.encode("cp437").decode("gbk")
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            name = info.filename  # 原始字符串保底

                    # 跳过目录
                    if name.endswith("/"):
                        continue
                    # 跳过 macOS 隐藏文件（__MACOSX/, ._xxx, .DS_Store）
                    base = os.path.basename(name)
                    if base.startswith("._") or base == ".DS_Store":
                        continue
                    if "__MACOSX" in name.split("/"):
                        continue
                    if not _is_image_ext(name):
                        continue
                    upload_files.append((os.path.basename(name), zf.read(info)))
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="无效的 zip 文件")

    # 处理多个文件
    if files:
        for f in files:
            if not f.filename:
                continue
            if not _is_image_ext(f.filename):
                continue
            upload_files.append((f.filename, await f.read()))

    if not upload_files:
        raise HTTPException(status_code=400, detail="未找到有效的图片文件（支持 png/jpg/jpeg）")

    # 校验每个文件大小
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    for name, data in upload_files:
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"文件 {name} 大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制",
            )

    # 保存文件并创建 pending 记录
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    items = []
    for filename, data in upload_files:
        record_id = str(uuid.uuid4())
        ext = os.path.splitext(filename)[1].lower() or ".png"
        image_path = os.path.join(settings.UPLOAD_DIR, f"{record_id}{ext}")
        with open(image_path, "wb") as f:
            f.write(data)

        await create_pending_record(
            record_id=record_id,
            batch_id=batch_id,
            filename=filename,
            image_path=image_path,
        )
        items.append(BatchItemInfo(record_id=record_id, filename=filename))

    # 启动后台异步处理
    from src.pipeline.batch_processor import process_batch
    asyncio.create_task(process_batch(batch_id))

    logger.info(f"批量批改已创建, batch_id={batch_id}, total={len(items)}")
    return BatchCreateResponse(batch_id=batch_id, total=len(items), items=items)


@router.get("/batch/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """查询批次批改状态"""
    records = await list_records_by_batch(batch_id)
    if not records:
        raise HTTPException(status_code=404, detail=f"批次不存在: {batch_id}")

    items = [
        BatchItemStatus(
            record_id=r["id"],
            filename=r["filename"],
            status=r["status"],
            student_name=r["student_name"],
            total_score=r["total_score"],
            error_msg=r.get("error_msg", ""),
        )
        for r in records
    ]

    total = len(items)
    completed = sum(1 for i in items if i.status == 2)
    failed = sum(1 for i in items if i.status == 3)

    return BatchStatusResponse(
        batch_id=batch_id,
        total=total,
        completed=completed,
        failed=failed,
        items=items,
    )
