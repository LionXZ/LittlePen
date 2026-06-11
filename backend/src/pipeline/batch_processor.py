"""
批量批改异步处理器

- 支持并行处理（asyncio.Semaphore 控制并发数）
- 支持服务重启后恢复未完成任务
"""
import asyncio
import base64
from src.db.database import (
    list_pending_records_by_batch,
    list_unfinished_records,
    update_record_status,
)
from src.pipeline.assistant import essay_agent
from src.utils.logger import logger

# 最大并行批改数（避免大模型 API 限流）
MAX_CONCURRENT = 3
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


async def process_single(record_id: str, image_path: str, filename: str) -> None:
    """处理单个批改任务（带信号量控制并发）"""
    async with _semaphore:
        try:
            logger.info(f"开始处理: {filename} ({record_id})")
            await update_record_status(record_id, status=1)  # 处理中

            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            result = await essay_agent.grade(
                image_base64=image_base64,
                thread_id=record_id,
            )

            if result.get("error"):
                await update_record_status(record_id, status=3, result=result)  # 失败
                logger.warning(f"批改失败: {filename} - {result['error']}")
            else:
                await update_record_status(record_id, status=2, result=result)  # 已完成
                student = result.get("qr_data", {}).get("student_name", "") if result.get("qr_data") else ""
                logger.info(f"批改完成: {filename} ({student})")

        except Exception as e:
            logger.error(f"处理异常: {filename} - {str(e)}")
            await update_record_status(record_id, status=3, result={"error": str(e)})


async def process_batch(batch_id: str):
    """并行处理批次中的所有待处理项"""
    try:
        records = await list_pending_records_by_batch(batch_id)
        if not records:
            return

        logger.info(f"批次 {batch_id}: 开始处理 {len(records)} 项 (最大并发 {MAX_CONCURRENT})")

        tasks = [
            process_single(r["id"], r["image_path"], r.get("filename", ""))
            for r in records
        ]
        await asyncio.gather(*tasks)

        logger.info(f"批次 {batch_id}: 全部处理完毕")

    except Exception as e:
        logger.error(f"批次 {batch_id} 处理失败: {str(e)}")


async def recover_unfinished():
    """服务启动时恢复所有未完成的任务（status=0 待处理, status=1 处理中）"""
    records = await list_unfinished_records()
    if not records:
        return

    # 将处理中的记录重置为待处理
    for r in records:
        if r.get("status") == 1:
            await update_record_status(r["id"], status=0)

    logger.info(f"恢复未完成任务: 共 {len(records)} 项 (最大并发 {MAX_CONCURRENT})")

    tasks = [
        process_single(r["id"], r["image_path"], r.get("filename", ""))
        for r in records
    ]
    asyncio.create_task(asyncio.gather(*tasks))
