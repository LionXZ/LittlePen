<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
under `specs/` before starting implementation.
<!-- SPECKIT END -->

# LittlePen — 儿童英文作文 AI 批改系统

## 项目概述

从答题纸图片上传 → 二维码解析 → 手写 OCR → 语法批改 → 四维评分 → 结果展示的全流程 AI 批改系统。

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangChain + LangGraph |
| OCR 模型 | GLM-5V-Turbo (智谱) |
| 批改模型 | deepseek-v4-pro (DeepSeek) |
| 后端 | Python FastAPI + Uvicorn |
| 前端 | Vue 3 + Vite + Element Plus + ECharts |
| 数据库 | MySQL 8.0 + SQLAlchemy 2.0 async |
| 图表 | ECharts 雷达图 |

## 项目结构

```
backend/src/
├── api/          FastAPI 路由 + schemas
├── config/       全局配置 (settings.py, 加载 .env)
├── db/           MySQL CRUD (SQLAlchemy async)
├── pipeline/     LangGraph 批改流水线 (state/graph/assistant/batch_processor)
├── tools/        LangChain Tools (qr/ocr/template/grammar/scoring)
├── models/       模型封装 (ChatOpenAI)
└── app.py        启动入口

frontend/src/
├── api/          API 请求封装 (axios + SSE)
├── components/   通用组件 (UploadPanel, ResultPanel, ScoreBoard 等)
├── views/        页面 (stream-grading, sync-grading, batch-upload, batch-result, records-list)
├── types/        TypeScript 类型
├── router/       路由配置
└── App.vue       根组件 (左侧菜单栏布局)
```

## 启动命令

```bash
# 后端
cd backend && python -m src.app

# 前端
cd frontend && npm run dev
```

## 核心规则

1. **先出方案再写代码** — 任何功能改动必须先用 `/speckit.plan` 出方案并获得确认，禁止直接改代码
2. **复用优先** — 优先使用已有组件和函数，不引入不必要的抽象
3. **批量批改异步处理** — 上传后立即返回，后台 `asyncio.create_task` + Semaphore(3) 并行处理
4. **状态驱动** — status=0 待处理 → 1 处理中 → 2 已完成 → 3 失败，重启自动恢复

## 当前批次批改 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/batch/upload` | 批量上传（多文件/ZIP） |
| GET | `/batch/{batch_id}` | 批次状态 |
| GET | `/essays` | 全部作业列表 |
| GET | `/essay/{record_id}` | 单条详情 |
