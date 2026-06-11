"""
持久化层：MySQL 批改记录存储（SQLAlchemy async + asyncmy）
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, String, Text, JSON, DECIMAL, Integer, DateTime,
    BigInteger, text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine as create_sync_engine

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ===== Async Engine & Session Factory (懒加载，避免事件循环冲突) =====

_async_engine = None
_async_session_factory = None


def _get_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.database_url,
            pool_size=settings.MYSQL_POOL_SIZE,
            max_overflow=20,
            pool_recycle=settings.MYSQL_POOL_RECYCLE,
            echo=settings.DEBUG,
        )
    return _async_engine


def _get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory

# ===== ORM Model =====

class Base(DeclarativeBase):
    pass


class GradingRecord(Base):
    __tablename__ = "grading_records"

    id = Column(BigInteger().with_variant(BigInteger, "mysql"), primary_key=True, autoincrement=True)
    record_uid = Column(String(36), unique=True, nullable=False, comment="UUID 业务标识")
    thread_id = Column(String(128), nullable=False, default="default", index=True, comment="批改会话ID")

    # 学生信息（从 qr_data 展开存储）
    student_name = Column(String(64), default="", index=True, comment="学生姓名")
    student_id = Column(String(64), default="", index=True, comment="学号")
    class_id = Column(String(64), default="", comment="班级ID")
    course_id = Column(String(64), default="", comment="课程ID")
    schedule_id = Column(String(64), default="", comment="课时ID")
    gender = Column(String(8), default="", comment="性别")

    # 批改结果
    essay_clean_text = Column(Text, comment="清洁后的作文文本")
    grammar_errors = Column(JSON, comment="语法错误列表")
    scores = Column(JSON, comment="四维评分详情")
    total_score = Column(DECIMAL(5, 2), default=0.00, comment="总分 0.00-100.00")

    # 批次
    batch_id = Column(String(36), nullable=True, default=None, index=True, comment="批次ID，单张批改时为空")
    filename = Column(String(256), default="", comment="原始文件名")

    # 状态: 0=待处理 1=处理中 2=已完成 3=失败
    status = Column(TINYINT, nullable=False, default=2, comment="0=待处理 1=处理中 2=已完成 3=失败")
    error_msg = Column(Text, comment="失败时的错误信息")
    image_path = Column(String(512), default="", comment="上传图片本地路径")

    # 时间戳
    created_at = Column(
        DateTime, nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime, nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        comment="更新时间",
    )


# ===== 数据库初始化 =====

async def init_db():
    """自动建表 + 迁移已有表结构"""
    async with _get_engine().begin() as conn:
        # 1. 建表（如果不存在）
        await conn.run_sync(Base.metadata.create_all)

        # 2. 增量迁移：添加新列（如果不存在则添加）
        try:
            await conn.execute(text(
                "ALTER TABLE grading_records ADD COLUMN batch_id VARCHAR(36) NULL"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_grading_records_batch_id ON grading_records (batch_id)"
            ))
        except Exception:
            pass  # 列/索引已存在

        try:
            await conn.execute(text(
                "ALTER TABLE grading_records ADD COLUMN filename VARCHAR(256) DEFAULT ''"
            ))
        except Exception:
            pass

        # 3. 迁移旧状态值：旧 0=失败→3=失败, 旧 1=成功→2=已完成
        try:
            await conn.execute(text(
                "UPDATE grading_records SET status = 2 WHERE status = 1"
            ))
            await conn.execute(text(
                "UPDATE grading_records SET status = 3 WHERE status = 0"
            ))
        except Exception:
            pass

    logger.info(f"MySQL 数据库初始化完成: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")


async def close_db():
    """释放连接池"""
    await _get_engine().dispose()


# ===== CRUD =====

def _extract_student_info(qr_data: Optional[dict]) -> dict:
    """从 qr_data 提取学生字段"""
    if not qr_data:
        return {}
    return {
        "student_name": qr_data.get("student_name", ""),
        "student_id": qr_data.get("student_id", ""),
        "class_id": qr_data.get("class_id", ""),
        "course_id": qr_data.get("course_id", ""),
        "schedule_id": qr_data.get("schedule_id", ""),
        "gender": qr_data.get("gender", ""),
    }


async def save_grading_record(
    record_id: str,
    thread_id: str,
    result: dict,
    image_path: str = "",
    batch_id: str = None,
    filename: str = "",
) -> None:
    """保存批改记录"""
    qr_data = result.get("qr_data")
    has_error = bool(result.get("error"))

    record = GradingRecord(
        record_uid=record_id,
        thread_id=thread_id,
        **_extract_student_info(qr_data),
        essay_clean_text=result.get("essay_clean_text", ""),
        grammar_errors=result.get("grammar_errors", []),
        scores=result.get("scores"),
        total_score=result.get("total_score", 0.0),
        status=3 if has_error else 2,  # 2=已完成 3=失败
        error_msg=result.get("error"),
        image_path=image_path,
        batch_id=batch_id,
        filename=filename,
    )

    async with _get_session_factory()() as session:
        session.add(record)
        await session.commit()


# ===== Batch CRUD =====

async def create_pending_record(
    record_id: str,
    batch_id: str,
    filename: str,
    image_path: str,
) -> None:
    """创建待处理的批改记录"""
    async with _get_session_factory()() as session:
        record = GradingRecord(
            record_uid=record_id,
            thread_id=batch_id,
            batch_id=batch_id,
            filename=filename,
            image_path=image_path,
            status=0,  # 待处理
        )
        session.add(record)
        await session.commit()


async def update_record_status(
    record_id: str,
    status: int,
    result: dict = None,
) -> None:
    """更新记录状态和批改结果"""
    async with _get_session_factory()() as session:
        from sqlalchemy import select, update
        stmt = select(GradingRecord).where(GradingRecord.record_uid == record_id)
        result_row = await session.execute(stmt)
        record = result_row.scalar_one_or_none()
        if record is None:
            return

        record.status = status
        if result is not None:
            qr_data = result.get("qr_data")
            if qr_data:
                record.student_name = qr_data.get("student_name", "")
                record.student_id = qr_data.get("student_id", "")
                record.class_id = qr_data.get("class_id", "")
                record.course_id = qr_data.get("course_id", "")
                record.schedule_id = qr_data.get("schedule_id", "")
                record.gender = qr_data.get("gender", "")
            record.essay_clean_text = result.get("essay_clean_text", "")
            record.grammar_errors = result.get("grammar_errors", [])
            record.scores = result.get("scores")
            record.total_score = result.get("total_score", 0.0)
            if result.get("error"):
                record.error_msg = result["error"]
        await session.commit()


async def list_records_by_batch(batch_id: str) -> list:
    """按批次查询所有记录"""
    from sqlalchemy import select

    async with _get_session_factory()() as session:
        stmt = (
            select(GradingRecord)
            .where(GradingRecord.batch_id == batch_id)
            .order_by(GradingRecord.created_at.asc())
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "id": r.record_uid,
                "batch_id": r.batch_id,
                "filename": r.filename,
                "student_name": r.student_name,
                "student_id": r.student_id,
                "total_score": float(r.total_score) if r.total_score else 0.0,
                "status": r.status,
                "error_msg": r.error_msg,
                "image_path": r.image_path,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]


async def list_unfinished_records() -> list:
    """查询所有未完成的记录（status=0 待处理 或 status=1 处理中），用于重启恢复"""
    from sqlalchemy import select

    async with _get_session_factory()() as session:
        stmt = (
            select(GradingRecord)
            .where(GradingRecord.status.in_([0, 1]))
            .order_by(GradingRecord.created_at.asc())
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "id": r.record_uid,
                "batch_id": r.batch_id,
                "image_path": r.image_path,
                "filename": r.filename,
                "status": r.status,
            }
            for r in rows
        ]


async def list_pending_records_by_batch(batch_id: str) -> list:
    """按批次查询待处理记录（按创建时间排序）"""
    from sqlalchemy import select

    async with _get_session_factory()() as session:
        stmt = (
            select(GradingRecord)
            .where(GradingRecord.batch_id == batch_id)
            .where(GradingRecord.status == 0)  # 待处理
            .order_by(GradingRecord.created_at.asc())
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "id": r.record_uid,
                "image_path": r.image_path,
                "filename": r.filename,
            }
            for r in rows
        ]


async def get_grading_record(record_id: str) -> Optional[Dict[str, Any]]:
    """查询批改记录"""
    async with _get_session_factory()() as session:
        from sqlalchemy import select
        stmt = select(GradingRecord).where(GradingRecord.record_uid == record_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return {
            "id": row.record_uid,
            "thread_id": row.thread_id,
            "student_name": row.student_name,
            "student_id": row.student_id,
            "class_id": row.class_id,
            "course_id": row.course_id,
            "schedule_id": row.schedule_id,
            "gender": row.gender,
            "essay_clean_text": row.essay_clean_text,
            "grammar_errors": row.grammar_errors,
            "scores": row.scores,
            "total_score": float(row.total_score) if row.total_score else 0.0,
            "error": row.error_msg,
            "status": row.status,
            "image_path": row.image_path,
            "created_at": row.created_at.isoformat() if row.created_at else "",
        }


async def list_grading_records(
    student_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> list:
    """列表查询批改记录"""
    from sqlalchemy import select

    async with _get_session_factory()() as session:
        stmt = select(GradingRecord).order_by(GradingRecord.created_at.desc())

        if student_id:
            stmt = stmt.where(GradingRecord.student_id == student_id)
        if thread_id:
            stmt = stmt.where(GradingRecord.thread_id == thread_id)

        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "id": r.record_uid,
                "thread_id": r.thread_id,
                "batch_id": r.batch_id,
                "filename": r.filename,
                "student_name": r.student_name,
                "student_id": r.student_id,
                "class_id": r.class_id,
                "course_id": r.course_id,
                "total_score": float(r.total_score) if r.total_score else 0.0,
                "status": r.status,
                "error_msg": r.error_msg,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]
