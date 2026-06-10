"""
持久化层：SQLite 批改记录存储
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from src.config.settings import settings


def _get_conn():
    """获取数据库连接"""
    db_path = settings.SQLITE_DB_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grading_records (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            qr_data TEXT,
            essay_clean_text TEXT,
            grammar_errors TEXT,
            scores TEXT,
            total_score REAL,
            error TEXT,
            image_path TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_grading_record(
    record_id: str,
    thread_id: str,
    result: dict,
    image_path: str = "",
):
    """保存批改记录"""
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO grading_records
        (id, thread_id, qr_data, essay_clean_text, grammar_errors, scores, total_score, error, image_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            thread_id,
            json.dumps(result.get("qr_data"), ensure_ascii=False) if result.get("qr_data") else None,
            result.get("essay_clean_text", ""),
            json.dumps(result.get("grammar_errors", []), ensure_ascii=False),
            json.dumps(result.get("scores"), ensure_ascii=False) if result.get("scores") else None,
            result.get("total_score", 0.0),
            result.get("error"),
            image_path,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_grading_record(record_id: str) -> dict | None:
    """查询批改记录"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM grading_records WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "thread_id": row["thread_id"],
        "qr_data": json.loads(row["qr_data"]) if row["qr_data"] else None,
        "essay_clean_text": row["essay_clean_text"],
        "grammar_errors": json.loads(row["grammar_errors"]) if row["grammar_errors"] else [],
        "scores": json.loads(row["scores"]) if row["scores"] else None,
        "total_score": row["total_score"],
        "error": row["error"],
        "created_at": row["created_at"],
    }


# 启动时初始化
init_db()
