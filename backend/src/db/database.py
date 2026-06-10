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

# ===== Async Engine & Session Factory =====

async_engine = create_async_engine(
    settings.database_url,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=20,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    echo=settings.DEBUG,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

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

    # 状态
    status = Column(TINYINT, nullable=False, default=1, comment="0=失败 1=成功")
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
    """自动建表（DDL）"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"MySQL 数据库初始化完成: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")


async def close_db():
    """释放连接池"""
    await async_engine.dispose()


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
        status=0 if has_error else 1,
        error_msg=result.get("error"),
        image_path=image_path,
    )

    async with async_session_factory() as session:
        session.add(record)
        await session.commit()


async def get_grading_record(record_id: str) -> Optional[Dict[str, Any]]:
    """查询批改记录"""
    async with async_session_factory() as session:
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

    async with async_session_factory() as session:
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
                "student_name": r.student_name,
                "student_id": r.student_id,
                "total_score": float(r.total_score) if r.total_score else 0.0,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]
