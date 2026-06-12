"""
PDF 批改报告生成器
使用 weasyprint 将批改结果渲染为 PDF 报告。
"""
import os
from src.utils.logger import logger

SUBJECT_LABELS = {"en": "英语", "cn": "语文", "ma": "数学", "sc": "科学"}
DIM_LABELS_EN = {"neatness": "卷面整洁", "content": "内容要点", "language": "语言质量", "structure": "篇章结构"}
DIM_LABELS_CN = {"neatness": "内容立意", "content": "语言表达", "language": "篇章结构", "structure": "书写规范"}


def _build_html(record: dict) -> str:
    """根据批改记录构建报告 HTML"""
    subject = record.get("subject", "en")
    dim_labels = DIM_LABELS_CN if subject == "cn" else DIM_LABELS_EN
    scores = record.get("scores") or {}
    grammar_errors = record.get("grammar_errors") or []
    qr_data = record

    # 语法错误表行
    error_rows = ""
    for idx, err in enumerate(grammar_errors, 1):
        error_rows += f"""
        <tr>
            <td>{idx}</td>
            <td>{err.get("original", "")}</td>
            <td>{err.get("corrected", "")}</td>
            <td>{err.get("error_type", "")}</td>
            <td>{err.get("explanation", "")}</td>
        </tr>"""

    # 评分表行
    score_rows = ""
    for key, label in dim_labels.items():
        dim = scores.get(key, {})
        score_rows += f"""
        <tr>
            <td>{label}</td>
            <td>{dim.get("score", 0)} / 25</td>
            <td>{dim.get("comment", "")}</td>
        </tr>"""

    total_score = record.get("total_score", 0)

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; padding: 40px; color: #333; }}
  h1 {{ text-align: center; font-size: 22px; margin-bottom: 8px; }}
  .subtitle {{ text-align: center; color: #888; font-size: 13px; margin-bottom: 30px; }}
  .section {{ margin-bottom: 24px; }}
  .section-title {{ font-size: 16px; font-weight: 700; border-bottom: 2px solid #409eff; padding-bottom: 6px; margin-bottom: 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 10px; text-align: left; }}
  th {{ background: #f5f7fa; font-weight: 600; }}
  .info-table td:first-child {{ width: 100px; color: #888; }}
  .score-total {{ text-align: center; font-size: 36px; font-weight: 700; color: #409eff; margin: 16px 0; }}
  .essay-text {{ white-space: pre-wrap; line-height: 1.8; font-size: 15px; background: #f9fafc; padding: 16px; border-radius: 6px; }}
</style>
</head>
<body>

<h1>作文批改报告</h1>
<p class="subtitle">LittlePen · {SUBJECT_LABELS.get(subject, "未知")}作文 · AI 批改</p>

<div class="section">
  <div class="section-title">学生信息</div>
  <table class="info-table">
    <tr><td>学生姓名</td><td>{qr_data.get("student_name", "-")}</td><td>学号</td><td>{qr_data.get("student_id", "-")}</td></tr>
    <tr><td>班级</td><td>{qr_data.get("class_id", "-")}</td><td>科目</td><td>{SUBJECT_LABELS.get(subject, "-")}</td></tr>
  </table>
</div>

<div class="section">
  <div class="section-title">作文原文</div>
  <div class="essay-text">{record.get("essay_clean_text", "（无内容）")}</div>
</div>

<div class="section">
  <div class="section-title">综合评分</div>
  <div class="score-total">{total_score} / 100</div>
  <table>
    <tr><th>评分维度</th><th>得分</th><th>评语</th></tr>
    {score_rows}
  </table>
</div>

<div class="section">
  <div class="section-title">语法/用词批改</div>
  {f'<table><tr><th>#</th><th>原文</th><th>修正</th><th>类型</th><th>解释</th></tr>{error_rows}</table>' if error_rows else '<p>未发现语法错误，表现优秀！</p>'}
</div>

</body>
</html>"""


def generate_report(record: dict, output_path: str):
    """生成 PDF 报告并保存到 output_path"""
    try:
        from weasyprint import HTML
        html = _build_html(record)
        HTML(string=html).write_pdf(output_path)
        logger.info(f"PDF 报告已生成: {output_path}")
    except ImportError:
        logger.error("weasyprint 未安装，无法生成 PDF 报告。请运行: pip install weasyprint")
        raise
    except Exception as e:
        logger.error(f"PDF 报告生成失败: {str(e)}")
        raise
