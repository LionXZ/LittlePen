"""
作文批改流水线 - LangGraph StateGraph
顺序: qr_parse -> ocr -> template_remove -> [grammar_check | scoring] -> aggregate
语法批改和评分并行执行以减少总耗时
"""
from langgraph.graph import StateGraph, END
from src.pipeline.state import EssayGradingState
from src.tools.qr_tool import parse_qr_code
from src.tools.ocr_tool import ocr_handwriting
from src.tools.template_tool import remove_template_text
from src.tools.grammar_tool import grammar_check
from src.tools.scoring_tool import score_essay_4dimensions


# ===== 节点函数 =====

def qr_parse_node(state: EssayGradingState) -> dict:
    """Step 1: 二维码解析"""
    result = parse_qr_code.invoke({"image_base64": state["image_base64"]})

    if result.get("error"):
        return {"error": result["error"], "current_step": "qr_parse_failed"}

    qr_data = result.get("qr_data") or {}
    return {
        "qr_raw": result.get("qr_raw", ""),
        "qr_data": qr_data,
        "subject": qr_data.get("subject", "en"),
        "current_step": "qr_parse_done",
    }


def ocr_node(state: EssayGradingState) -> dict:
    """Step 2: 手写 OCR 识别 (GLM-5V-Turbo)"""
    ocr_text = ocr_handwriting.invoke({
        "image_base64": state["image_base64"],
    })
    return {
        "ocr_raw_text": ocr_text,
        "current_step": "ocr_done",
    }


def template_remove_node(state: EssayGradingState) -> dict:
    """Step 3: 去除模板文字"""
    clean_text = remove_template_text.invoke({
        "ocr_raw_text": state["ocr_raw_text"],
    })
    return {
        "essay_clean_text": clean_text,
        "current_step": "template_remove_done",
    }


def grammar_check_node(state: EssayGradingState) -> dict:
    """Step 4a: 语法批改 (deepseek-v4-pro) - 与评分并行"""
    result = grammar_check.invoke({
        "essay_text": state["essay_clean_text"],
        "subject": state.get("subject", "en"),
    })
    return {
        "grammar_errors": result.get("errors", []),
        "current_step": "grammar_check_done",
    }


def scoring_node(state: EssayGradingState) -> dict:
    """Step 4b: 四维评分 (deepseek-v4-pro) - 与语法批改并行"""
    ocr_text = state.get("ocr_raw_text", "")
    ocr_quality = "OCR 识别完整，字迹清晰可辨" if len(ocr_text) > 50 else "OCR 识别内容较少"
    subject = state.get("subject", "en")

    result = score_essay_4dimensions.invoke({
        "essay_text": state["essay_clean_text"],
        "ocr_quality_note": ocr_quality,
        "subject": subject,
    })
    return {
        "scores": {
            "neatness": result.get("neatness"),
            "content": result.get("content"),
            "language": result.get("language"),
            "structure": result.get("structure"),
        },
        "total_score": result.get("total_score", 0),
        "current_step": "scoring_done",
    }


def aggregate_node(state: EssayGradingState) -> dict:
    """Step 5: 结果聚合"""
    return {"current_step": "done"}


def error_handler_node(state: EssayGradingState) -> dict:
    """错误处理节点"""
    return {"current_step": "error"}


# ===== 路由函数 =====

def should_continue_after_qr(state: EssayGradingState) -> str:
    if state.get("error"):
        return "error_handler"
    return "ocr"


def build_grading_pipeline() -> StateGraph:
    """构建作文批改 LangGraph 流水线"""

    workflow = StateGraph(EssayGradingState)

    # 注册节点
    workflow.add_node("qr_parse", qr_parse_node)
    workflow.add_node("ocr", ocr_node)
    workflow.add_node("template_remove", template_remove_node)
    workflow.add_node("grammar_check", grammar_check_node)
    workflow.add_node("scoring", scoring_node)
    workflow.add_node("aggregate", aggregate_node)
    workflow.add_node("error_handler", error_handler_node)

    # 入口
    workflow.set_entry_point("qr_parse")

    # 顺序流程：qr -> ocr -> template_remove
    workflow.add_conditional_edges("qr_parse", should_continue_after_qr, {
        "ocr": "ocr",
        "error_handler": "error_handler",
    })
    workflow.add_edge("ocr", "template_remove")

    # 并行分支：grammar_check 和 scoring 同时执行
    workflow.add_edge("template_remove", "grammar_check")
    workflow.add_edge("template_remove", "scoring")

    # 汇聚到 aggregate
    workflow.add_edge("grammar_check", "aggregate")
    workflow.add_edge("scoring", "aggregate")

    # 结束
    workflow.add_edge("aggregate", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()


# 全局流水线实例
grading_pipeline = build_grading_pipeline()
