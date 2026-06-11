# 儿童英文作文 AI 批改 — 软件设计文档 (SDD)

> 基于 LangChain v1.3 + LangGraph v1.2 Agent 架构，从 0 到 1 构建作文批改系统。
> 需求来源：`1.md`，架构参照：`AI Agent 全流程开发指南-LangChain v1.3从0到1.md`

---

## 目录

- [1. 项目概述与需求分析](#1-项目概述与需求分析)
- [2. 技术栈选型](#2-技术栈选型)
- [3. 系统架构设计](#3-系统架构设计)
- [4. 项目工程结构](#4-项目工程结构)
- [5. 配置管理](#5-配置管理)
- [6. 模型层封装](#6-模型层封装)
- [7. 工具开发](#7-工具开发)
- [8. 批改流水线 Agent (核心)](#8-批改流水线-agent-核心)
- [9. API 服务层](#9-api-服务层)
- [10. 前端界面设计](#10-前端界面设计)
- [11. 测试与评估](#11-测试与评估)
- [12. 生产部署](#12-生产部署)
- [13. 可观测性](#13-可观测性)
- [14. 开发排期与里程碑](#14-开发排期与里程碑)

---

# 1. 项目概述与需求分析

## 1.1 项目定义

构建 **"儿童英文作文 AI 批改系统"（EssayGradingAgent）**，实现从答题纸图片上传 → 二维码解析 → 手写 OCR → AI 批改 → 评分 → 结果展示的全流程。

## 1.2 功能需求映射

| 功能 | 技术方案 | 优先级 |
|------|---------|--------|
| 上传界面 | Vue 3 + Vite + Element Plus 文件上传组件 | P0 |
| 二维码信息识别 | `pyzbar` / `opencv` + `decodeURIComponent` | P0 |
| 手写内容 OCR | GLM-5V-Turbo（智谱多模态视觉模型）| P0 |
| 模板文字剔除 | 轻量 LLM + 提示词去噪 | P0 |
| AI 语法批改 | deepseek-v4-pro + 结构化输出（语法错误 → 修正建议列表）| P0 |
| AI 四维评分 | deepseek-v4-pro + 结构化输出（卷面/内容/语言/结构）| P0 |
| 结果展示 | 同一界面展示全部批改结果 | P0 |
| 批改结果持久化 | MySQL 存储历史批改记录 | P1 |
| 流式批改进度 | SSE 推送处理进度 | P1 |
| 批量批改上传 | 多文件/ZIP 上传 + 后台异步处理 + 作业列表 | P1 |
| 作业列表页 | 全部批改记录展示，状态轮询，详情查看 | P1 |

## 1.3 AI Agent 组件映射

参照指南中的六大核心组件，本系统映射如下：

```
┌──────────────────────────────────────────────────────┐
│               作文批改 Agent                          │
│                                                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐  │
│  │ 双模型   │  │ 无长期  │  │ 工具 (Tools)         │  │
│  │ GLM-5V  │  │ 记忆需  │  │ QR解析/OCR/批改/评分  │  │
│  │ +deepseek│  │ 求（单次 │  │                     │  │
│  │         │  │ 批改）  │  │                     │  │
│  └────┬────┘  └────┬────┘  └───────┬─────────────┘  │
│       │            │               │                 │
│  ┌────┴────┐  ┌────┴────┐  ┌──────┴──────────┐      │
│  │ 流水线  │  │ 工具调用 │  │ Agent 编排       │      │
│  │ Pipeline│  │ ToolCall │  │ LangGraph State │      │
│  └─────────┘  └─────────┘  └─────────────────┘      │
└──────────────────────────────────────────────────────┘
```

- **流水线 Agent**：本系统核心是"顺序批改流水线"，而非自由对话 Agent，因此采用 **LangGraph StateGraph** 构建有状态的多步骤处理流水线。
- **工具开发**：QR 解析、OCR 识别、批改、评分分别封装为 LangChain Tool。
- **结构化输出**：批改和评分使用 LLM `with_structured_output` 强制输出 JSON 格式。

---

# 2. 技术栈选型

| 技术 | 选型 | 原因 |
|------|------|------|
| Agent 框架 | LangChain v1.3 + LangGraph v1.2 | 支持流水线编排、结构化输出、流式事件 |
| **OCR 视觉模型** | **GLM-5V-Turbo**（智谱 ZhipuAI）| 多模态视觉理解，国内合规，手写识别能力强 |
| **作文批改模型** | **deepseek-v4-pro**（DeepSeek）| 结构化输出强，中英文混合处理能力优秀，性价比高 |
| 辅助模型 | GLM-4-Flash / deepseek-chat（轻量模板去除）| 成本优化 |
| 二维码解析 | pyzbar + Pillow | 纯 Python，轻量 |
| Web 框架 | FastAPI | 高性能异步，支持 StreamingResponse |
| 前端 | Vue 3 + Vite + Element Plus | 快速构建上传界面与结果展示 |
| 持久化 | MySQL 8.0 + SQLAlchemy 2.0 (async) | 连接池、异步驱动、支持按学生/班级查询 |
| 图片存储 | 本地文件系统 | 开发阶段 |
| 可观测性 | LangSmith | 全链路 Agent 追踪 |
| 容器化 | Docker + docker-compose | 标准化部署 |

## 2.1 模型分工与职责

| 模型 | 厂商 | 用途 | 关键能力 |
|------|------|------|---------|
| **GLM-5V-Turbo** | 智谱 (ZhipuAI) | OCR 手写识别 + 卷面整洁度辅助判断 | 多模态视觉理解，识别答题纸图片中的手写内容 |
| **deepseek-v4-pro** | DeepSeek | 语法批改 + 内容/语言/结构 三维评分 | 结构化 JSON 输出，中英文双语，批改精准度高 |
| GLM-4-Flash / deepseek-chat | - | 模板文字去除 | 轻量快速，成本低 |

---

# 3. 系统架构设计

## 3.1 分层架构图

```
┌─────────────────────────────────────────────────────────┐
│                   前端 UI 层 (Vue 3)                     │
│   上传界面 ｜ 批改结果展示（QR信息/原文/批改/评分）       │
├─────────────────────────────────────────────────────────┤
│                    API 服务层 (FastAPI)                   │
│   POST /api/v1/essay/grade        ← 上传图片+批改        │
│   GET  /api/v1/essay/grade/stream ← 流式批改(SSE)        │
│   GET  /api/v1/essay/{id}         ← 查询历史批改记录     │
│   GET  /api/v1/health             ← 健康检查             │
├─────────────────────────────────────────────────────────┤
│                 Agent 核心层 (LangGraph)                  │
│   EssayGradingPipeline: 流水线状态图                     │
│   qr_parse → ocr → template_remove → grammar_check       │
│   → scoring_4dim → aggregate                             │
│   每一步是一个 StateGraph Node                            │
├──────────────┬──────────────┬────────────────────────────┤
│   工具层      │   模型层      │   中间件层                 │
│ qr_tool      │ get_main_model│ ModelRetryMiddleware      │
│ ocr_tool     │ get_mini_model│ PerformanceMonitor         │
│ grammar_tool │              │                            │
│ scoring_tool │              │                            │
├──────────────┴──────────────┴────────────────────────────┤
│                   基础设施层                              │
│   MySQL (批改记录)   │  本地文件系统 (图片存储)            │
│   LangSmith (可观测) │  Docker (部署)                    │
└─────────────────────────────────────────────────────────┘
```

## 3.2 批改流水线状态图 (LangGraph)

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │ 上传图片(base64/文件路径)
                    ┌──────▼──────┐
                    │  QR 码解析   │  ← qr_parse_tool
                    │  parse_qr   │
                    └──────┬──────┘
                           │ qr_data (dict)
                    ┌──────▼──────┐
                    │  手写 OCR    │  ← ocr_tool (多模态LLM)
                    │  ocr_text   │
                    └──────┬──────┘
                           │ raw_text (含模板文字)
                    ┌──────▼──────┐
                    │  去模板清洗   │  ← template_remove_tool
                    │  clean_text │
                    └──────┬──────┘
                           │ 纯净手写作文文本
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐      ┌────────▼────────┐
     │  语法批改         │      │  四维评分         │
     │  grammar_check   │      │  scoring_4dim    │
     │  (grammar_tool)  │      │  (scoring_tool)   │
     └────────┬────────┘      └────────┬────────┘
              │ 语法错误列表            │ 4维分值+评语
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │  结果聚合     │
                    │  aggregate  │
                    └──────┬──────┘
                           │ 完整批改结果
                    ┌──────▼──────┐
                    │    END      │
                    └─────────────┘
```

**并行节点**：grammar_check 和 scoring_4dim 可以**并行执行**（两者输入相同，互不依赖），利用 LangGraph 的并行分支能力减少总耗时。

## 3.3 数据流状态定义

```python
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

class EssayGradingState(TypedDict):
    # 输入
    image_base64: str              # 上传的图片 base64

    # QR 解析结果
    qr_raw: str                    # QR 码原始字符串
    qr_data: dict                  # 解析后的结构化字段
    # {course_id, class_id, schedule_id, student_id, student_name, gender}

    # OCR 结果
    ocr_raw_text: str              # OCR 识别原始文本（含模板）
    essay_clean_text: str          # 去除模板后的纯净作文文本

    # 批改结果
    grammar_errors: List[dict]     # 语法错误列表
    # [{original, corrected, error_type, explanation}]

    # 评分结果
    scores: dict                   # 四维评分
    # {neatness: {score, comment}, content: {score, comment},
    #  language: {score, comment}, structure: {score, comment}}
    total_score: float             # 综合得分

    # 流程控制
    error: Optional[str]           # 异常信息
    current_step: str              # 当前步骤（用于流式进度推送）
```

---

# 4. 项目工程结构

```
essay-grading/
├── .env                          # 环境变量（不提交 Git）
├── .env.example                  # 环境变量模板
├── .gitignore
├── Dockerfile
├── docker-compose.yml
│
├── backend/                      # 后端（Python FastAPI）
│   ├── requirements.txt
│   ├── data/
│   │   └── uploads/              # 上传图片存储
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   │
│   │   ├── config/               # 配置层
│   │   │   ├── __init__.py
│   │   │   └── settings.py       # 全局配置（加载 .env）
│   │   │
│   │   ├── models/               # 模型层
│   │   │   ├── __init__.py
│   │   │   └── chat_model.py     # 双模型初始化（GLM-5V-Turbo + deepseek-v4-pro）
│   │   │
│   │   ├── tools/                # 工具层
│   │   │   ├── __init__.py
│   │   │   ├── qr_tool.py        # 二维码解析工具
│   │   │   ├── ocr_tool.py       # OCR 识别工具（GLM-5V-Turbo 多模态）
│   │   │   ├── grammar_tool.py   # 语法批改工具（deepseek-v4-pro 结构化输出）
│   │   │   ├── scoring_tool.py   # 四维评分工具（deepseek-v4-pro 结构化输出）
│   │   │   ├── template_tool.py  # 模板去除工具
│   │   │   └── registry.py       # 工具注册中心
│   │   │
│   │   ├── pipeline/             # 批改流水线（核心）
│   │   │   ├── __init__.py
│   │   │   ├── state.py          # EssayGradingState 定义
│   │   │   ├── graph.py          # LangGraph StateGraph 构建
│   │   │   └── assistant.py      # EssayGradingAgent 入口
│   │   │
│   │   ├── api/                  # API 层
│   │   │   ├── __init__.py
│   │   │   ├── server.py         # FastAPI 服务
│   │   │   ├── routes.py         # 路由定义
│   │   │   └── schemas.py        # 请求/响应 Pydantic 模型
│   │   │
│   │   ├── db/                   # 持久化层
│   │   │   ├── __init__.py
│   │   │   └── database.py       # MySQL CRUD (SQLAlchemy async)
│   │   │
│   │   ├── utils/                # 工具层
│   │   │   ├── __init__.py
│   │   │   └── logger.py         # 日志工具
│   │   │
│   │   └── app.py                # 应用入口
│   │
│   ├── tests/                    # 测试
│   │   ├── __init__.py
│   │   ├── test_qr_tool.py
│   │   ├── test_ocr_tool.py
│   │   ├── test_grammar_tool.py
│   │   ├── test_scoring_tool.py
│   │   └── test_pipeline.py
│   │
│   └── evaluations/              # 评估数据集
│       └── test_essays.json
│
└── frontend/                     # 前端（Vue 3 + Vite）
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    ├── src/
    │   ├── main.ts
    │   ├── App.vue
    │   ├── api/                   # API 调用层
    │   │   └── essay.ts           # 批改相关 API 封装
    │   ├── components/
    │   │   ├── UploadPanel.vue    # 上传组件
    │   │   ├── ResultPanel.vue    # 结果展示组件
    │   │   ├── QRInfoCard.vue     # 二维码信息卡片
    │   │   ├── EssayTextCard.vue  # 作文原文卡片
    │   │   ├── GrammarList.vue    # 语法错误列表
    │   │   └── ScoreBoard.vue     # 评分看板（含雷达图）
    │   ├── composables/           # 组合式函数
    │   │   └── useGrading.ts      # 批改流程控制（上传/进度/结果）
    │   └── types/                 # TypeScript 类型定义
    │       └── grading.ts
    └── public/
```

---

# 5. 配置管理

```python
# src/config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()  # backend/ 目录

class Settings:
    """全局配置"""

    # ===== 项目 =====
    PROJECT_NAME: str = "EssayGradingAgent"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ===== 智谱 GLM（OCR 视觉模型）=====
    ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
    ZHIPU_OCR_MODEL: str = os.getenv("ZHIPU_OCR_MODEL", "glm-5v-turbo")  # GLM-5V-Turbo 多模态
    ZHIPU_BASE_URL: str = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

    # ===== DeepSeek（作文批改模型）=====
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")  # 批改主力
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    # ===== 文件存储 =====
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "data" / "uploads"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

    # ===== MySQL =====
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "LittlePen")
    MYSQL_POOL_SIZE: int = int(os.getenv("MYSQL_POOL_SIZE", "10"))
    MYSQL_POOL_RECYCLE: int = int(os.getenv("MYSQL_POOL_RECYCLE", "3600"))

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    # ===== LangSmith =====
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "essay-grading")
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"

    # ===== Agent =====
    MAX_MODEL_RETRIES: int = int(os.getenv("MAX_MODEL_RETRIES", "3"))
    SCORE_RANGE: tuple = (0, 25)   # 各维度评分范围 0-25 分

    # ===== API =====
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
```

```bash
# .env.example
# 智谱 GLM（OCR 视觉模型）
ZHIPU_API_KEY=your-zhipu-api-key
# DeepSeek（作文批改模型）
DEEPSEEK_API_KEY=your-deepseek-api-key
# LangSmith 可观测性（可选）
LANGSMITH_API_KEY=ls-your-key-here
DEBUG=false
MAX_UPLOAD_SIZE_MB=10
```

---

# 6. 模型层封装

本系统采用**双模型架构**：
- **GLM-5V-Turbo**（智谱）：负责 OCR 手写识别（多模态视觉理解）
- **deepseek-v4-pro**（DeepSeek）：负责语法批改 + 四维评分（结构化输出）

两个模型都兼容 OpenAI API 格式，通过 `init_chat_model` 统一接入。

```python
# src/models/chat_model.py
from langchain.chat_models import init_chat_model
from src.config.settings import settings


def get_ocr_model(temperature: float = 0.1):
    """
    OCR 视觉模型：GLM-5V-Turbo（智谱）
    用于答题纸图片的手写内容识别，支持多模态图片输入。

    低温度保证识别准确率，减少幻觉。
    """
    return init_chat_model(
        model="openai",  # 使用 OpenAI 兼容模式，不指定具体模型名
        api_key=settings.ZHIPU_API_KEY or None,
        base_url=settings.ZHIPU_BASE_URL,
        temperature=temperature,
        max_tokens=4096,
        # 注意：实际调用时通过 model_kwargs 传入 model="glm-5v-turbo"
        # 或者使用 ChatOpenAI(model="glm-5v-turbo", base_url=...)
    )


def get_ocr_model_chat():
    """
    OCR 模型（ChatOpenAI 方式，兼容智谱 OpenAI API）
    直接使用 ChatOpenAI，填入智谱 base_url 和 model 名称
    """
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings.ZHIPU_OCR_MODEL,           # "glm-5v-turbo"
        api_key=settings.ZHIPU_API_KEY or None,
        base_url=settings.ZHIPU_BASE_URL,          # "https://open.bigmodel.cn/api/paas/v4/"
        temperature=0.1,
        max_tokens=4096,
    )


def get_grading_model(temperature: float = 0.3):
    """
    作文批改模型：deepseek-v4-pro（DeepSeek）
    用于语法批改、四维评分，需要结构化 JSON 输出能力。

    注意：deepseek-v4-pro 支持 with_structured_output。
    """
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,             # "deepseek-v4-pro"
        api_key=settings.DEEPSEEK_API_KEY or None,
        base_url=settings.DEEPSEEK_BASE_URL,        # "https://api.deepseek.com/v1"
        temperature=temperature,
        max_tokens=4096,
    )


def get_light_model(temperature: float = 0.1):
    """
    轻量辅助模型：用于模板去除等简单任务。
    优先使用 DeepSeek 轻量模型，如不可用则尝试 GLM-4-Flash。
    """
    from langchain_openai import ChatOpenAI
    try:
        return ChatOpenAI(
            model="deepseek-chat",                  # DeepSeek 轻量模型
            api_key=settings.DEEPSEEK_API_KEY or None,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=temperature,
            max_tokens=2048,
        )
    except Exception:
        # 回退到 GLM
        return ChatOpenAI(
            model="glm-4-flash",
            api_key=settings.ZHIPU_API_KEY or None,
            base_url=settings.ZHIPU_BASE_URL,
            temperature=temperature,
            max_tokens=2048,
        )
```

**关键设计说明：**

1. **GLM-5V-Turbo** 和 **deepseek-v4-pro** 均提供 OpenAI 兼容的 API 端点，因此可直接使用 `langchain_openai.ChatOpenAI`，只需替换 `base_url` 和 `api_key`。

2. **OCR 模型**使用低温度 (0.1) — 保证文字提取的准确性和稳定性。

3. **批改模型**使用中低温度 (0.3) — 在创造性和一致性之间平衡，既能识别灵活的错误模式，又不会给出不一致的评分。

4. 两个模型是**完全独立的 API 提供方**，无共享配额，天然支持并行调用。

---

# 7. 工具开发

## 7.1 二维码解析工具

```python
# src/tools/qr_tool.py
import base64
import io
from urllib.parse import unquote
from PIL import Image
from pyzbar.pyzbar import decode
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

    返回解析后的结构化字段 dict。
    """
    try:
        # 解码 base64 → PIL Image
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))

        # 识别二维码
        decoded_objects = decode(image)
        if not decoded_objects:
            return {"error": "未检测到二维码", "qr_data": None}

        qr_str = decoded_objects[0].data.decode("utf-8")

        # 按 "-" 分段
        parts = qr_str.split("-")
        if len(parts) < 6:
            return {"error": f"二维码格式异常，期望至少6段，实际{len(parts)}段: {qr_str}", "qr_data": None}

        qr_data = {
            "course_id": parts[0],
            "class_id": parts[1],
            "schedule_id": parts[2],
            "student_id": parts[3],
            "student_name": unquote(parts[4]),  # decodeURIComponent 还原中文姓名
            "gender": parts[5],
        }

        return {"error": None, "qr_raw": qr_str, "qr_data": qr_data}

    except Exception as e:
        return {"error": f"二维码解析失败: {str(e)}", "qr_data": None}
```

## 7.2 OCR 识别工具（多模态 LLM）

```python
# src/tools/ocr_tool.py
import base64
from langchain.tools import tool
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from src.models.chat_model import get_main_model


class OCRInput(BaseModel):
    image_base64: str = Field(description="答题纸图片的 base64 编码")
    prompt_instruction: str = Field(
        default="请识别图片中的所有文字内容，包括手写部分和印刷部分。逐行输出，不要遗漏。",
        description="OCR 提示指令"
    )


@tool(args_schema=OCRInput)
def ocr_handwriting(image_base64: str, prompt_instruction: str = "") -> str:
    """
    使用多模态大模型对答题纸图片中的手写内容进行 OCR 识别。

    Args:
        image_base64: 图片的 base64 编码
        prompt_instruction: 可选的 OCR 提示指令
    """
    model = get_main_model(temperature=0.1)  # 低温度保证识别准确

    if not prompt_instruction:
        prompt_instruction = (
            "请仔细识别这张答题纸图片中的所有文字内容。"
            "包括：1) 印刷的模板文字 2) 学生手写的作文内容。"
            "请完整输出所有文字，对于手写内容请用「手写内容」标注。"
        )

    message = HumanMessage(content=[
        {"type": "text", "text": prompt_instruction},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
    ])

    response = model.invoke([message])
    return response.content
```

## 7.3 语法批改工具（结构化输出）

```python
# src/tools/grammar_tool.py
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from src.models.chat_model import get_main_model


class GrammarError(BaseModel):
    original: str = Field(description="原文中有语法错误的句子或片段")
    corrected: str = Field(description="修正后的正确表达")
    error_type: str = Field(description="错误类型：语法/拼写/用词/标点")
    explanation: str = Field(description="简短的中文解释，适合儿童理解")


class GrammarCheckResult(BaseModel):
    errors: List[GrammarError] = Field(description="语法错误列表")
    overall_comment: str = Field(description="整体评价")


class GrammarCheckInput(BaseModel):
    essay_text: str = Field(description="去除模板后的纯净学生作文文本")


@tool(args_schema=GrammarCheckInput)
def grammar_check(essay_text: str) -> dict:
    """
    对学生英文作文进行语法和用词批改。

    识别语法错误、拼写错误、用词不当等问题，
    针对每个问题给出修正建议和中文解释（面向儿童）。

    使用结构化输出确保返回格式一致。
    """
    model = get_main_model(temperature=0.3)
    structured_model = model.with_structured_output(GrammarCheckResult)

    prompt = f"""你是儿童英文作文批改老师。请批改以下小学生英文作文：

<essay>
{essay_text}
</essay>

要求：
1. 找出所有语法错误、拼写错误、用词不当、标点错误
2. 对每个错误给出修正后的句子/片段
3. 解释用简单的中文，适合孩子理解
4. 注意：只指出确实有误的地方，不要过度修改孩子的原创表达
5. 如果作文无错误，返回空的 errors 列表并在 overall_comment 中给予鼓励"""

    result: GrammarCheckResult = structured_model.invoke(prompt)
    return result.model_dump()
```

## 7.4 四维评分工具（结构化输出）

```python
# src/tools/scoring_tool.py
from typing import List
from pydantic import BaseModel, Field
from langchain.tools import tool
from src.models.chat_model import get_main_model, get_mini_model
from src.config.settings import settings


class DimensionScore(BaseModel):
    score: float = Field(description=f"维度得分，范围 {settings.SCORE_RANGE[0]}-{settings.SCORE_RANGE[1]}")
    comment: str = Field(description="简短的中文评语")


class ScoringResult(BaseModel):
    neatness: DimensionScore = Field(description="卷面整洁：书写工整度、涂改情况、排版整洁程度")
    content: DimensionScore = Field(description="内容要点：是否切题、要点完整、论述充分")
    language: DimensionScore = Field(description="语言质量：词汇丰富度、语法准确性、表达流畅度")
    structure: DimensionScore = Field(description="篇章结构：段落划分、逻辑层次、开头结尾完整性")
    total_score: float = Field(description="综合得分")
    overall_comment: str = Field(description="整体评价（中文，鼓励性）")


class ScoringInput(BaseModel):
    essay_text: str = Field(description="作文纯净文本")
    ocr_quality_note: str = Field(
        default="",
        description="OCR 质量描述，用于辅助评估卷面整洁度"
    )


@tool(args_schema=ScoringInput)
def score_essay_4dimensions(essay_text: str, ocr_quality_note: str = "") -> dict:
    """
    从4个维度对儿童英文作文进行评分。

    维度：卷面整洁(neatness)、内容要点(content)、语言质量(language)、篇章结构(structure)
    每维度 0-25 分，综合分为四维之和。

    卷面整洁根据 OCR 识别质量判断；
    内容、语言、结构由作文批改大模型评分。
    """
    model = get_main_model(temperature=0.3)
    structured_model = model.with_structured_output(ScoringResult)

    prompt = f"""你是儿童英文作文评分老师。请从以下4个维度对这篇小学生作文评分：

<essay>
{essay_text}
</essay>

{f"OCR 质量参考: {ocr_quality_note}" if ocr_quality_note else ""}

评分标准（每维度 0-25 分）：
1. **卷面整洁** (neatness)：书写工整度、涂改情况、排版整洁程度
2. **内容要点** (content)：作文是否切题、要点是否完整、论述是否充分
3. **语言质量** (language)：词汇丰富度、语法准确性、表达流畅程度
4. **篇章结构** (structure)：段落划分是否合理、逻辑层次是否清晰、开头结尾是否完整

要求：
- 评分要客观公正，同时对小学生的努力给予肯定
- 综合得分 = 四个维度分数之和
- overall_comment 用中文写，以鼓励为主，指出1-2个具体改进方向"""

    result: ScoringResult = structured_model.invoke(prompt)
    return result.model_dump()
```

## 7.5 模板去除工具

```python
# src/tools/template_tool.py
from langchain.tools import tool
from pydantic import BaseModel, Field
from src.models.chat_model import get_mini_model


class TemplateRemoveInput(BaseModel):
    ocr_raw_text: str = Field(description="OCR 原始识别文本（含模板文字和手写内容）")


@tool(args_schema=TemplateRemoveInput)
def remove_template_text(ocr_raw_text: str) -> str:
    """
    从 OCR 结果中去除预印的模板/固定说明文字，只保留学生手写的作文内容。

    使用轻量模型区分"印刷模板"和"手写内容"。
    """
    model = get_mini_model(temperature=0.1)

    prompt = f"""以下是从答题纸图片 OCR 识别出来的文字，其中包含了：
- 预印的模板文字（如题目说明、要求、得分栏等印刷体固定文字）
- 学生手写的作文内容

请只提取「学生手写的作文正文」，去除所有预印模板文字。
直接返回纯净的作文正文，不要添加任何额外说明。

<ocr_text>
{ocr_raw_text}
</ocr_text>"""

    response = model.invoke(prompt)
    return response.content.strip()
```

## 7.6 工具注册中心

```python
# src/tools/registry.py
from typing import List
from langchain_core.tools import BaseTool
from src.tools.qr_tool import parse_qr_code
from src.tools.ocr_tool import ocr_handwriting
from src.tools.grammar_tool import grammar_check
from src.tools.scoring_tool import score_essay_4dimensions
from src.tools.template_tool import remove_template_text


class ToolRegistry:
    """工具注册中心"""

    _instance = None
    _tools: List[BaseTool] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register_defaults()
        return cls._instance

    def _register_defaults(self):
        self._tools = [
            parse_qr_code,
            ocr_handwriting,
            remove_template_text,
            grammar_check,
            score_essay_4dimensions,
        ]

    def get_all_tools(self) -> List[BaseTool]:
        return self._tools

    def get_tool_by_name(self, name: str) -> BaseTool:
        for tool in self._tools:
            if tool.name == name:
                return tool
        raise ValueError(f"工具 '{name}' 未注册")


tool_registry = ToolRegistry()
```

---

# 8. 批改流水线 Agent（核心）

## 8.1 状态定义

```python
# src/pipeline/state.py
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class EssayGradingState(TypedDict):
    # 输入
    image_base64: str

    # QR 解析
    qr_raw: str
    qr_data: Optional[dict]

    # OCR
    ocr_raw_text: str
    essay_clean_text: str

    # 批改
    grammar_errors: List[dict]

    # 评分
    scores: Optional[dict]
    total_score: float

    # 流程控制
    error: Optional[str]
    current_step: str
```

## 8.2 LangGraph 流水线构建

```python
# src/pipeline/graph.py
from langgraph.graph import StateGraph, END
from langchain.agents.middleware import ModelRetryMiddleware
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

    return {
        "qr_raw": result.get("qr_raw", ""),
        "qr_data": result["qr_data"],
        "current_step": "qr_parse_done",
    }


def ocr_node(state: EssayGradingState) -> dict:
    """Step 2: 手写 OCR 识别"""
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
    """Step 4a: 语法批改（与评分并行）"""
    result = grammar_check.invoke({
        "essay_text": state["essay_clean_text"],
    })

    return {
        "grammar_errors": result.get("errors", []),
        "current_step": "grammar_check_done",
    }


def scoring_node(state: EssayGradingState) -> dict:
    """Step 4b: 四维评分（与语法批改并行）"""
    ocr_quality = "OCR 识别完整"  # 可从 OCR 结果推断

    result = score_essay_4dimensions.invoke({
        "essay_text": state["essay_clean_text"],
        "ocr_quality_note": ocr_quality,
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
    """Step 5: 结果聚合（汇总两个并行分支的输出）"""
    return {
        "current_step": "done",
    }


def error_handler_node(state: EssayGradingState) -> dict:
    """错误处理节点"""
    return {"current_step": "error"}


# ===== 路由函数 =====

def should_continue_after_qr(state: EssayGradingState) -> str:
    if state.get("error"):
        return "error_handler"
    return "ocr"


def build_grading_pipeline() -> StateGraph:
    """构建作文批改流水线"""

    workflow = StateGraph(EssayGradingState)

    # 添加节点
    workflow.add_node("qr_parse", qr_parse_node)
    workflow.add_node("ocr", ocr_node)
    workflow.add_node("template_remove", template_remove_node)
    workflow.add_node("grammar_check", grammar_check_node)
    workflow.add_node("scoring", scoring_node)
    workflow.add_node("aggregate", aggregate_node)
    workflow.add_node("error_handler", error_handler_node)

    # 设置入口
    workflow.set_entry_point("qr_parse")

    # 顺序流程
    workflow.add_conditional_edges("qr_parse", should_continue_after_qr, {
        "ocr": "ocr",
        "error_handler": "error_handler",
    })
    workflow.add_edge("ocr", "template_remove")

    # 并行分支：语法批改 + 评分 同时进行
    workflow.add_edge("template_remove", "grammar_check")
    workflow.add_edge("template_remove", "scoring")

    # 两个分支汇聚到聚合节点
    workflow.add_edge("grammar_check", "aggregate")
    workflow.add_edge("scoring", "aggregate")

    # 结束
    workflow.add_edge("aggregate", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()


# 全局流水线实例
grading_pipeline = build_grading_pipeline()
```

## 8.3 Agent 入口封装

```python
# src/pipeline/assistant.py
import base64
from typing import AsyncIterator, Dict, Any
from pathlib import Path
from src.pipeline.graph import grading_pipeline


class EssayGradingAgent:
    """作文批改 Agent 入口"""

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
            完整的批改结果 dict
        """
        # 如果传的是文件路径，转为 base64
        if image_path and not image_base64:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

        if not image_base64:
            return {"error": "请提供 image_path 或 image_base64"}

        initial_state = {
            "image_base64": image_base64,
            "qr_raw": "",
            "qr_data": None,
            "ocr_raw_text": "",
            "essay_clean_text": "",
            "grammar_errors": [],
            "scores": None,
            "total_score": 0.0,
            "error": None,
            "current_step": "start",
        }

        config = {"configurable": {"thread_id": thread_id}}

        final_state = await self.pipeline.ainvoke(initial_state, config)

        return {
            "qr_data": final_state.get("qr_data"),
            "essay_clean_text": final_state.get("essay_clean_text"),
            "grammar_errors": final_state.get("grammar_errors", []),
            "scores": final_state.get("scores"),
            "total_score": final_state.get("total_score", 0.0),
            "error": final_state.get("error"),
            "thread_id": thread_id,
        }

    async def grade_stream(
        self,
        image_base64: str,
        thread_id: str = "default",
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式批改：通过 SSE 推送每一步的进度和最终结果。

        Yields:
            {"step": "qr_parse_done", "data": {...}}
            {"step": "ocr_done", "data": {...}}
            {"step": "done", "data": {完整结果}}
        """
        initial_state = {
            "image_base64": image_base64,
            "qr_raw": "",
            "qr_data": None,
            "ocr_raw_text": "",
            "essay_clean_text": "",
            "grammar_errors": [],
            "scores": None,
            "total_score": 0.0,
            "error": None,
            "current_step": "start",
        }

        config = {"configurable": {"thread_id": thread_id}}

        async for event in self.pipeline.astream_events(initial_state, config, version="v2"):
            kind = event["event"]

            if kind == "on_chain_end":
                output = event["data"].get("output", {})
                step = output.get("current_step", "")

                if step:
                    yield {
                        "step": step,
                        "data": output if step == "done" else None,
                    }

            elif kind == "on_chain_error":
                yield {
                    "step": "error",
                    "data": {"error": str(event["data"].get("error", "未知错误"))},
                }


# 全局单例
essay_agent = EssayGradingAgent()
```

---

# 9. API 服务层

## 9.1 请求/响应模型

```python
# src/api/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional


class GradeRequest(BaseModel):
    """批改请求 - 支持文件路径或 base64"""
    image_base64: Optional[str] = Field(default=None, description="图片 base64 编码")
    thread_id: str = Field(default="default", description="会话 ID")


class QRData(BaseModel):
    course_id: str
    class_id: str
    schedule_id: str
    student_id: str
    student_name: str
    gender: str


class GrammarErrorItem(BaseModel):
    original: str
    corrected: str
    error_type: str
    explanation: str


class DimensionScoreItem(BaseModel):
    score: float
    comment: str


class ScoresData(BaseModel):
    neatness: DimensionScoreItem
    content: DimensionScoreItem
    language: DimensionScoreItem
    structure: DimensionScoreItem


class GradeResponse(BaseModel):
    """批改完整响应"""
    qr_data: Optional[QRData]
    essay_clean_text: str
    grammar_errors: List[GrammarErrorItem]
    scores: Optional[ScoresData]
    total_score: float
    error: Optional[str]
    thread_id: str


class HealthResponse(BaseModel):
    status: str
    version: str
```

## 9.2 API 路由

```python
# src/api/routes.py
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from src.api.schemas import GradeRequest, GradeResponse, HealthResponse
from src.pipeline.assistant import essay_agent
from src.config.settings import settings
import json

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version=settings.VERSION)


@router.post("/essay/grade", response_model=GradeResponse)
async def grade_essay(request: GradeRequest):
    """
    同步批改：上传 base64 图片，等待完整批改结果返回。
    适用于图片较小、期望一次性获取结果的场景。
    """
    try:
        result = await essay_agent.grade(
            image_base64=request.image_base64,
            thread_id=request.thread_id,
        )

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        return GradeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批改失败: {str(e)}")


@router.post("/essay/grade/upload")
async def grade_essay_upload(
    file: UploadFile = File(...),
    thread_id: str = Form(default="default"),
):
    """
    上传图片文件进行批改。

    支持格式：PNG, JPG, JPEG
    最大文件大小见配置 MAX_UPLOAD_SIZE_MB
    """
    # 校验文件类型
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPG/JPEG 格式")

    # 读取并转 base64
    contents = await file.read()

    # 校验文件大小
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    image_base64 = base64.b64encode(contents).decode("utf-8")

    result = await essay_agent.grade(
        image_base64=image_base64,
        thread_id=thread_id,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return GradeResponse(**result)


@router.post("/essay/grade/stream")
async def grade_essay_stream(request: GradeRequest):
    """
    流式批改：通过 Server-Sent Events 推送每一步的处理进度。

    事件格式:
    - {"step": "qr_parse_done"}
    - {"step": "ocr_done"}
    - {"step": "template_remove_done"}
    - {"step": "grammar_check_done"}
    - {"step": "scoring_done"}
    - {"step": "done", "data": {...完整结果...}}
    - {"step": "error", "data": {"error": "..."}}
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
            yield f"data: {json.dumps({'step': 'error', 'data': {'error': str(e)}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

## 9.3 FastAPI 服务入口

```python
# src/api/server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.api.routes import router
from src.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n{'='*50}")
    print(f"  {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"  API: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"  Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print(f"{'='*50}\n")
    yield
    print("\n  shutting down...\n")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="儿童英文作文 AI 批改系统",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    return app


app = create_app()
```

```python
# src/app.py
import uvicorn
from src.api.server import app
from src.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
```

---

# 10. 前端界面设计

## 10.1 技术栈

| 技术 | 说明 |
|------|------|
| Vue 3 (Composition API) | 组合式 API + `<script setup>` |
| Vite | 开发构建工具 |
| Element Plus | UI 组件库（上传、卡片、表格、进度条）|
| ECharts | 雷达图（四维评分可视化）|
| TypeScript | 类型安全 |
| Axios | HTTP 请求 + EventSource SSE 流式 |

## 10.2 组件树

```
App.vue
├── UploadPanel.vue       # 上传区域
│   ├── el-upload (拖拽上传 / 点击上传)
│   ├── 图片预览
│   ├── el-progress (批改进度条)
│   └── el-button ("开始批改")
│
└── ResultPanel.vue       # 结果展示区域（批改完成后显示）
    ├── QRInfoCard.vue    # 二维码信息卡片 (el-descriptions)
    │   ├── 课程ID / 班级ID / 排课ID
    │   ├── 学号
    │   ├── 学生姓名
    │   └── 性别
    │
    ├── EssayTextCard.vue # OCR 手写原文 (el-card)
    │   └── 去除模板后的纯净作文文本
    │
    ├── GrammarList.vue   # 语法错误列表 (el-table)
    │   ├── 原文（错误高亮）
    │   ├── 修正建议
    │   ├── 错误类型标签 (el-tag)
    │   └── 中文解释
    │
    └── ScoreBoard.vue    # 评分看板
        ├── el-statistic 综合得分（大号数字）
        ├── ECharts 雷达图（四维分值可视化）
        └── el-card 各维度分数 + 评语
```

## 10.3 交互流程

```
1. 用户拖拽/点击上传答题纸图片
2. 图片预览显示
3. 用户点击"开始批改"
4. 显示进度条（QR解析 → OCR → 去模板 → 语法批改 + 评分）
5. 进度完成，切换至 ResultPanel
6. 逐区域展示：QR信息 → 原文 → 错误列表 → 评分看板
```

## 10.4 流式进度交互

前端通过 `useGrading` composable 封装批改流程，使用 EventSource 连接 `/api/v1/essay/grade/stream`，根据 `step` 值更新 `el-progress` 进度条：

| step 值               | 进度 | UI 提示             | 对应模型          |
|-----------------------|------|---------------------|------------------|
| qr_parse_done         | 15%  | 二维码信息识别完成   | pyzbar (本地)     |
| ocr_done              | 35%  | 手写内容识别完成     | GLM-5V-Turbo      |
| template_remove_done  | 50%  | 作文内容提取完成     | deepseek-chat     |
| grammar_check_done    | 75%  | 语法批改完成         | deepseek-v4-pro   |
| scoring_done          | 90%  | 评分完成             | deepseek-v4-pro   |
| done                  | 100% | 展示完整结果         | -                 |

## 10.5 核心 Composable 示例

```typescript
// frontend/src/composables/useGrading.ts
import { ref, reactive } from 'vue'
import type { GradeResult } from '@/types/grading'

export function useGrading() {
  const uploading = ref(false)
  const grading = ref(false)
  const currentStep = ref('')
  const progress = ref(0)
  const result = ref<GradeResult | null>(null)
  const error = ref<string | null>(null)

  const stepProgressMap: Record<string, number> = {
    'qr_parse_done': 15,
    'ocr_done': 35,
    'template_remove_done': 50,
    'grammar_check_done': 75,
    'scoring_done': 90,
    'done': 100,
  }

  async function startGrading(imageBase64: string) {
    grading.value = true
    error.value = null

    // SSE 流式接收批改进度
    const response = await fetch('/api/v1/essay/grade/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: imageBase64 }),
    })

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          currentStep.value = data.step
          progress.value = stepProgressMap[data.step] ?? progress.value
          if (data.step === 'done') {
            result.value = data.data
          }
        }
      }
    }

    grading.value = false
  }

  return { uploading, grading, currentStep, progress, result, error, startGrading }
}
```

---

## 10.6 批量批改

### 10.6.1 概述

支持一次上传多张答题纸图片或 ZIP 压缩包，上传后立即返回，后台异步逐项批改，通过作业列表页查看进度和结果。

### 10.6.2 批量上传流程

```
1. 用户进入批量批改页面
2. 选择上传模式：多文件上传 / ZIP 压缩包
3. 上传文件 → 立即返回 batch_id，跳转到作业列表页
4. 后台 asyncio 异步任务逐项调用 essay_agent.grade()
5. 作业列表每 10 秒轮询更新状态
6. 已完成项点击"查看详情"进入结果页
```

### 10.6.3 ZIP 文件处理

- 解压 ZIP，过滤非图片文件（仅保留 .png/.jpg/.jpeg）
- 跳过 macOS 隐藏文件（`__MACOSX/`、`._` 前缀、`.DS_Store`）
- 文件名编码回退：UTF-8 → GBK → 原始字符串

### 10.6.4 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/batch/upload` | 批量上传（multipart: files 或 zip_file） |
| `GET` | `/api/v1/batch/{batch_id}` | 查询批次处理状态 |
| `GET` | `/api/v1/essays` | 查询全部批改记录列表（支持 limit/offset） |

### 10.6.5 数据库扩展

在 `grading_records` 表新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `batch_id` | VARCHAR(36) | 批次ID，用于分组查询，单张批改时为 NULL |
| `filename` | VARCHAR(256) | 原始文件名 |

`status` 字段语义扩展：0=待处理, 1=处理中, 2=已完成, 3=失败

### 10.6.6 前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 批量上传 | `/batch` | 多文件/ZIP 上传模式切换 |
| 批改详情 | `/batch/:batchId/result/:recordId` | 复用 ResultPanel 组件展示 |
| 作业列表 | `/records` | 全部批改记录，状态标签，10秒轮询，点击查看详情 |

### 10.6.7 待实现功能

- [ ] **目录监听自动批改**：监听指定目录，新图片自动创建批改任务
- [ ] **批量导出结果**：将批改结果导出为 Excel/PDF
- [ ] **批量重试失败项**：对失败的批改项一键重试
- [ ] **并发批改**：支持并行处理多项以提高吞吐量

---

# 11. 测试与评估

## 11.1 工具单元测试

```python
# tests/test_qr_tool.py
import base64
import pytest
from src.tools.qr_tool import parse_qr_code


def test_parse_qr_with_chinese_name():
    """测试中文姓名的 encodeURIComponent 解析"""
    # 模拟二维码内容: course01-class01-sched01-S001-%E5%BC%A0%E4%B8%89-male
    # 其中 %E5%BC%A0%E4%B8%89 = "张三"
    # 需要一张包含该二维码的测试图片
    pass


def test_parse_qr_no_code():
    """测试无二维码图片"""
    # 使用普通图片（无二维码），预期返回 error
    pass
```

```python
# tests/test_grammar_tool.py
import pytest
from src.tools.grammar_tool import grammar_check


def test_grammar_check_with_errors():
    """测试包含语法错误的作文"""
    essay = "I go to school yesterday. My friend are happy."
    result = grammar_check.invoke({"essay_text": essay})

    assert "errors" in result
    assert len(result["errors"]) > 0
    # 应检测到 go→went, are→is
    assert any("went" in str(e) for e in result["errors"])


def test_grammar_check_perfect_essay():
    """测试无错误的作文"""
    essay = "I like apples. They are delicious."
    result = grammar_check.invoke({"essay_text": essay})
    assert "errors" in result
```

```python
# tests/test_scoring_tool.py
def test_scoring_4_dimensions():
    """测试四维评分输出完整性"""
    essay = "My favorite animal is a cat. Cats are cute."
    result = score_essay_4dimensions.invoke({
        "essay_text": essay,
        "ocr_quality_note": "字迹清晰",
    })

    assert "neatness" in result
    assert "content" in result
    assert "language" in result
    assert "structure" in result
    assert "total_score" in result
    assert 0 <= result["neatness"]["score"] <= 25
```

## 11.2 流水线集成测试

```python
# tests/test_pipeline.py
import base64
import pytest
from src.pipeline.assistant import essay_agent


@pytest.mark.asyncio
async def test_full_pipeline():
    """测试完整批改流水线"""
    # 读取测试图片（需预先准备带二维码的答题纸测试图片）
    with open("tests/fixtures/test_answer_sheet.png", "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    result = await essay_agent.grade(
        image_base64=image_base64,
        thread_id="test-001",
    )

    # 验证完整结果结构
    assert "qr_data" in result
    assert "essay_clean_text" in result
    assert "grammar_errors" in result
    assert "scores" in result
    assert "total_score" in result
    assert result.get("error") is None
```

## 11.3 评估数据集

```json
[
    {
        "image": "tests/fixtures/test_essay_level1.png",
        "expected_student_name": "张三",
        "min_total_score": 60,
        "max_total_score": 100,
        "expected_error_types": ["语法", "拼写"]
    },
    {
        "image": "tests/fixtures/test_essay_level2.png",
        "expected_student_name": "李四",
        "min_total_score": 40,
        "max_total_score": 80,
        "expected_error_types": ["语法", "用词", "标点"]
    }
]
```

---

# 12. 生产部署

## 12.1 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 系统依赖（pyzbar 需要 libzbar）
RUN apt-get update && apt-get install -y \
    libzbar0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/src/ src/
COPY backend/data/ data/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "src.app"]
```

## 12.2 docker-compose.yml

```yaml
version: "3.8"

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: LittlePen
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  essay-grading:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      - ZHIPU_API_KEY=${ZHIPU_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=root
      - MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=LittlePen
      - DEBUG=false
    volumes:
      - ./backend/data/uploads:/app/data/uploads
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mysql_data:
```

## 12.3 requirements.txt

```
langchain==1.3.0
langgraph==1.2.0
langchain-core==1.4.0
langchain-openai>=0.3.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
python-dotenv>=1.0.0
langsmith>=0.3.0
httpx>=0.28.0
pyzbar>=0.1.9
Pillow>=10.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
sqlalchemy[asyncio]>=2.0.0
asyncmy>=0.2.9
pymysql>=1.1.0
```

---

# 13. 可观测性

## 13.1 LangSmith 追踪

设置环境变量即可自动追踪：
- 每次批改流水线的完整执行轨迹
- 每步工具调用（QR/OCR/语法/评分）的输入/输出/耗时
- 每次 LLM 调用的 token 消耗和延迟

## 13.2 结构化日志

```python
# src/utils/logger.py
import logging
import json
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(name: str = "essay-grading", level: str = "INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger


logger = setup_logger()
```

---

# 14. 开发排期与里程碑

| 阶段 | 内容 | 预计产出 |
|------|------|---------|
| **Phase 0** 项目搭建 | 项目初始化、配置管理、模型层封装 | 可运行的空项目骨架 |
| **Phase 1** 工具开发 | 开发 QR/OCR/语法批改/评分/去模板 5个工具 | 每个工具的单元测试通过 |
| **Phase 2** 流水线组装 | LangGraph StateGraph 构建、Agent 入口封装 | 端到端流水线可运行 |
| **Phase 3** API 服务 | FastAPI 路由、流式 SSE、文件上传接口 | Swagger 文档 + curl 验证 |
| **Phase 4** 前端界面 | Vue 3 上传组件 + 结果展示组件 + ECharts 评分雷达图 | 完整 UI 交互流程 |
| **Phase 5** 测试评估 | 集成测试、评估数据集、准确率验证 | 批改准确率报告 |
| **Phase 6** 部署上线 | Docker 化、docker-compose、生产环境配置 | 生产可用的容器镜像 |
| **Phase 7** 批量批改 | 多文件/ZIP 上传、后台异步处理、作业列表页 | 完整批量批改功能 |

---

## 架构总览图

```
┌──────────────────────────────────────────────────────────┐
│                    前端 UI (Vue 3 + Vite)                 │
│   UploadPanel → el-progress → ResultPanel                 │
│   QRInfo | EssayText | GrammarList | ScoreBoard + ECharts │
├──────────────────────────────────────────────────────────┤
│                   API 服务 (FastAPI)                       │
│   POST /essay/grade | /essay/grade/upload | /grade/stream │
│   POST /batch/upload | GET /batch/{id} | GET /essays      │
│   GET  /health                                            │
├──────────────────────────────────────────────────────────┤
│              批改流水线 Agent (LangGraph)                   │
│                                                          │
│   qr_parse → ocr → template_remove ─┬→ grammar_check ─┐  │
│         │          │                └→ scoring ──────┤  │
│         │          │                                  │  │
│    [pyzbar]  [GLM-5V-Turbo]    aggregate (汇聚) ←────┘  │
│                              [deepseek-v4-pro ×2 并行]   │
├──────────────┬──────────────┬─────────────────────────────┤
│  工具层       │  模型层       │  中间件                      │
│ qr_tool      │ GLM-5V-Turbo │ ModelRetryMiddleware         │
│ ocr_tool     │ deepseek-v4  │ PerformanceMonitor           │
│ grammar_tool │ deepseek-chat│                              │
│ scoring_tool │              │                              │
│ template_tool│              │                              │
├──────────────┴──────────────┴─────────────────────────────┤
│                   基础设施                                  │
│   MySQL │ 本地文件存储 │ LangSmith │ Docker               │
└──────────────────────────────────────────────────────────┘
```

---

> 本文档基于 LangChain v1.3 + LangGraph v1.2 架构设计了完整的"儿童英文作文AI批改系统"开发方案，涵盖从工具开发、流水线组装到 API 服务、前端界面、测试部署的全流程。所有模块设计遵循单一职责原则，工具可独立测试，流水线通过 LangGraph 状态管理保证处理顺序和数据一致性。
