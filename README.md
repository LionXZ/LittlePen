# 儿童英文作文 AI 批改系统

基于 LangChain + LangGraph Agent 架构，从答题纸图片上传到 AI 批改评分的全流程自动化系统。

## 功能概览

| 模块 | 说明 |
|------|------|
| 图片上传 | 支持拖拽/选择上传，支持 PNG/JPG/JPEG 格式，最大 10MB |
| 二维码解析 | 自动识别答题纸二维码，提取学生信息 |
| 手写 OCR | 使用 GLM-5V-Turbo 多模态视觉模型识别手写英文内容 |
| 模板去噪 | 剔除答题纸模板文字，提取纯作文内容 |
| 语法批改 | 使用 deepseek-v4-pro 逐一检查语法错误并给出修改建议 |
| 四维评分 | 卷面整洁度、内容质量、语言表达、篇章结构四个维度打分（各 0-25 分） |
| 结果展示 | 原文图片 + 语法错误列表 + 四维雷达图 + 总分 |
| 流式进度 | SSE 推送每一步处理状态，实时显示批改进度 |
| 批量批改 | 支持多文件/ZIP 压缩包上传，后台异步批改，作业列表查看进度 |
| 历史记录 | MySQL 持久化存储，全部作业列表展示，支持状态轮询 |

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ 上传组件  │  │ 结果展示  │  │ 进度条 (SSE 流式)    │   │
│  └─────┬────┘  └────┬─────┘  └──────────┬───────────┘   │
│        │            │                   │               │
│  ┌─────┴────────────┴───────────────────┴───────────┐   │
│  │              API Client (axios + SSE)             │   │
│  └───────────────────────┬──────────────────────────┘   │
└──────────────────────────┼──────────────────────────────┘
                           │ HTTP (Base64 / FormData / SSE)
┌──────────────────────────┼──────────────────────────────┐
│                    Backend (FastAPI)                     │
│                          │                               │
│  ┌──────────┐  ┌─────────┴─────────┐  ┌────────────┐   │
│  │ /health  │  │  /essay/grade     │  │ /essay/{id} │   │
│  │ /essays  │  │  /essay/grade/    │  │ /batch/     │   │
│  │          │  │  upload           │  │   {id}      │   │
│  │          │  │  /essay/grade/    │  │ /batch/     │   │
│  │          │  │  stream           │  │   upload    │   │
│  │          │  │  /batch/upload    │  │             │   │
│  └──────────┘  └─────────┬─────────┘  └──────┬──────┘   │
│                          │                    │          │
│  ┌───────────────────────┴────────────────────┴──────┐   │
│  │            EssayGradingAgent (LangGraph)           │   │
│  │                                                    │   │
│  │  qr_parse ──▶ ocr ──▶ template_remove              │   │
│  │                           │                        │   │
│  │              ┌────────────┴────────────┐           │   │
│  │              ▼                         ▼           │   │
│  │       grammar_check              scoring           │   │
│  │              │                         │           │   │
│  │              └────────────┬────────────┘           │   │
│  │                           ▼                        │   │
│  │                       aggregate                    │   │
│  └────────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌───────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐   │
│  │ Zhipu │  │ DeepSeek │  │  MySQL   │  │ LangSmith │   │
│  │ (OCR) │  │ (批改/评分)│  │ (持久化) │  │ (可观测)  │   │
│  └───────┘  └──────────┘  └──────────┘  └───────────┘   │
└──────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| Agent 框架 | LangChain + LangGraph | >=1.3.0 / >=1.2.0 |
| OCR 模型 | GLM-5V-Turbo (智谱) | - |
| 批改模型 | deepseek-v4-pro (DeepSeek) | - |
| Web 框架 | FastAPI + Uvicorn | >=0.115 |
| 前端 | Vue 3 + Vite + Element Plus | Vue >=3.5 |
| 图表 | ECharts | >=5.6 |
| 数据库 | MySQL 8.0 + SQLAlchemy 2.0 (async) | - |
| 可观测 | LangSmith | >=0.3 |
| 容器化 | Docker + docker-compose | - |

## 项目结构

```
LittlePen/
├── backend/                     # 后端 Python 服务
│   ├── src/
│   │   ├── api/                 # FastAPI 路由与数据模型
│   │   │   ├── server.py        #   应用入口 + CORS 配置
│   │   │   ├── routes.py        #   路由定义 (health, grade, stream, history)
│   │   │   └── schemas.py       #   Pydantic 请求/响应模型
│   │   ├── config/
│   │   │   └── settings.py      # 全局配置 (API Key, 路径, 参数)
│   │   ├── db/
│   │   │   └── database.py      # MySQL 数据库操作 (SQLAlchemy async + asyncmy)
│   │   ├── models/              # 数据模型层
│   │   ├── pipeline/            # LangGraph 批改流水线 (核心)
│   │   │   ├── state.py         #   状态定义 (EssayGradingState)
│   │   │   ├── graph.py         #   流水线编排 (5节点 + 并行分支)
│   │   │   ├── assistant.py     #   Agent 入口 (同步/流式)
│   │   │   └── batch_processor.py # 批量批改异步处理器
│   │   ├── tools/               # LangChain 工具
│   │   │   ├── qr_tool.py       #   二维码解析工具
│   │   │   ├── ocr_tool.py      #   OCR 识别工具 (GLM-5V)
│   │   │   ├── template_tool.py #   模板文字去除工具
│   │   │   ├── grammar_tool.py  #   语法批改工具 (deepseek)
│   │   │   ├── scoring_tool.py  #   四维评分工具 (deepseek)
│   │   │   └── registry.py      #   工具注册中心
│   │   ├── utils/
│   │   │   └── logger.py        # 日志工具
│   │   └── app.py               # 应用启动入口
│   ├── data/                    # 本地数据目录
│   │   └── uploads/             #   上传图片存储
│   ├── tests/                   # 测试
│   ├── evaluations/             # 评估脚本
│   └── requirements.txt         # Python 依赖
│
├── frontend/                    # 前端 Vue 3 应用
│   ├── src/
│   │   ├── api/                 # API 请求封装 (axios + SSE)
│   │   ├── components/          # 组件
│   │   │   ├── UploadPanel.vue  #   上传面板 (拖拽 + 选择)
│   │   │   └── ResultPanel.vue  #   结果面板 (雷达图 + 错误列表)
│   │   ├── composables/         # Vue Composables
│   │   ├── router/              # 路由配置 (左侧菜单栏)
│   │   ├── views/               # 页面视图
│   │   │   ├── stream-grading/  #   流式批改页
│   │   │   ├── sync-grading/    #   同步批改页
│   │   │   ├── batch-upload/    #   批量上传页
│   │   │   ├── batch-result/    #   批量结果详情页
│   │   │   └── records-list/    #   作业列表页 (全部记录)
│   │   ├── types/               # TypeScript 类型定义
│   │   ├── App.vue              # 根组件 (左侧菜单栏布局)
│   │   └── main.ts              # 应用入口
│   ├── index.html
│   ├── vite.config.ts           # Vite 配置 (含 /api 代理)
│   ├── tsconfig.json
│   └── package.json
│
├── .env.example                 # 环境变量模板 (需要创建)
├── .gitignore
└── README.md
```

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- MySQL >= 8.0
- pnpm (推荐) 或 npm

### 1. 克隆项目

```bash
cd LittlePen
```

### 2. 创建数据库

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS LittlePen CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件，填入 API Key 和数据库密码:

```env
# 智谱 GLM (OCR 模型, 必填)
ZHIPU_API_KEY=your_zhipu_api_key

# DeepSeek (批改模型, 必填)
DEEPSEEK_API_KEY=your_deepseek_api_key

# MySQL 数据库（必填）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=LittlePen

# 以下可选
LANGSMITH_API_KEY=your_langsmith_api_key
API_PORT=8000
DEBUG=false
```

### 4. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m src.app
```

后端运行在 http://localhost:8000，API 文档见 http://localhost:8000/docs

### 5. 启动前端

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

前端运行在 http://localhost:5173，自动代理 `/api` 请求到后端。

### 5. 使用

1. 打开浏览器访问 http://localhost:5173
2. **单张批改**：上传一张英文作文答题纸图片，等待 AI 完成批改
3. **批量批改**：上传多张图片或 ZIP 压缩包，后台异步处理，在"作业列表"中查看进度
4. 查看语法错误列表和四维评分雷达图

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 健康检查 |
| `POST` | `/api/v1/essay/grade` | 同步批改（base64 图片） |
| `POST` | `/api/v1/essay/grade/upload` | 文件上传批改（FormData） |
| `POST` | `/api/v1/essay/grade/stream` | 流式批改（SSE 进度推送） |
| `GET` | `/api/v1/essay/{record_id}` | 查询历史批改记录 |
| `POST` | `/api/v1/batch/upload` | 批量上传（多文件/ZIP） |
| `GET` | `/api/v1/batch/{batch_id}` | 查询批次批改状态 |
| `GET` | `/api/v1/essays` | 查询全部批改记录列表 |

### 同步批改请求示例

```json
{
  "image_base64": "/9j/4AAQSkZJRg...",
  "thread_id": "session-001"
}
```

### 同步批改响应示例

```json
{
  "qr_data": {
    "student_name": "张三",
    "class": "三年级2班"
  },
  "essay_clean_text": "My favorite animal is a dog...",
  "grammar_errors": [
    {
      "original": "I like play football",
      "correction": "I like playing football",
      "explanation": "like 后面接动名词形式"
    }
  ],
  "scores": {
    "neatness": 22,
    "content": 20,
    "language": 18,
    "structure": 19
  },
  "total_score": 79,
  "thread_id": "session-001"
}
```

### 流式批改 SSE 事件

```
data: {"step": "qr_parse_done"}
data: {"step": "ocr_done"}
data: {"step": "template_remove_done"}
data: {"step": "grammar_check_done"}
data: {"step": "scoring_done"}
data: {"step": "done", "data": {...完整结果...}}
data: [DONE]
```

## 批改数据流向

### 单张批改（同步 / 流式）

```
┌─────────┐
│  前端     │ POST /api/v1/essay/grade          POST /api/v1/essay/grade/stream
│ Upload   │ (base64 JSON) 或  multipart upload  (SSE base64 JSON)
│ Panel    │
└────┬─────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  routes.py                                                   │
│  grade_essay() / grade_essay_upload() / grade_essay_stream() │
│  ├─ 校验文件类型/大小                                          │
│  ├─ 文件保存到 data/uploads/ (upload 模式)                     │
│  └─ 调用 essay_agent.grade() 或 .grade_stream()               │
└────┬─────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  assistant.py — EssayGradingAgent                            │
│                                                              │
│  grade(image_base64, thread_id)                              │
│  ├─ _build_initial_state()      → EssayGradingState          │
│  ├─ pipeline.ainvoke(state)     → 同步等待完整结果             │
│  └─ _build_result(final_state)  → {qr_data, essay, errors,   │
│                                      scores, total_score}     │
│                                                              │
│  grade_stream(image_base64, thread_id)                       │
│  ├─ _build_initial_state()      → EssayGradingState          │
│  ├─ pipeline.astream(state, stream_mode="values") → 逐节点... │
│  └─ 每个节点 yield {"step": "xxx_done"}                      │
│     最后 yield {"step": "done", "data": _build_result(...)}  │
└────┬─────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  graph.py — LangGraph StateGraph (编译后的 grading_pipeline)   │
│                                                              │
│  node "qr_parse"          → qr_parse_node()                  │
│  │   调用 parse_qr_code.invoke() → pyzbar 解码二维码           │
│  │   输出: qr_raw, qr_data, current_step="qr_parse_done"      │
│  │   失败 → "error_handler"                                   │
│  ▼                                                           │
│  node "ocr"               → ocr_node()                       │
│  │   调用 ocr_handwriting.invoke() → GLM-5V-Turbo (多模态)    │
│  │   输出: ocr_raw_text, current_step="ocr_done"              │
│  ▼                                                           │
│  node "template_remove"   → template_remove_node()           │
│  │   调用 remove_template_text.invoke() → 轻量 LLM 去模板     │
│  │   输出: essay_clean_text, current_step="template_remove"   │
│  │                                                           │
│  ├──────────── 并行分支 ────────────┤                          │
│  ▼                                 ▼                         │
│  node "grammar_check"    node "scoring"                      │
│  grammar_check_node()    scoring_node()                      │
│  grammar_check.invoke()  score_essay_4dimensions.invoke()    │
│  → deepseek-v4-pro       → deepseek-v4-pro                   │
│  grammar_errors[]        scores{4维 + total_score}            │
│  │                                 │                         │
│  └──────────── 汇聚 ───────────────┘                          │
│  ▼                                                           │
│  node "aggregate"        → aggregate_node()                  │
│    合并两个并行分支结果, current_step="done"                    │
│                                                              │
│  node "error_handler"    → error_handler_node()              │
│    current_step="error"                                      │
└────┬─────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  routes.py (回写)                                             │
│  └─ save_grading_record(record_id, thread_id, result)        │
│     → MySQL grading_records 表                                │
│     status=2(已完成) / status=3(失败)                          │
└──────────────────────────────────────────────────────────────┘
```

### 批量批改

```
┌─────────────┐
│  前端         │ POST /api/v1/batch/upload (multipart: files[] 或 zip_file)
│  BatchUpload │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  routes.py — batch_upload()                                  │
│  ├─ 解压 ZIP / 收集多文件 → upload_files[]                    │
│  ├─ 逐个: 保存文件到 data/uploads/, create_pending_record()    │
│  │        → MySQL: status=0 (待处理), batch_id=UUID           │
│  ├─ asyncio.create_task(process_batch(batch_id))  ← 立即返回   │
│  └─ return {batch_id, total, items[]}                        │
└──────┬───────────────────────────────────────────────────────┘
       │  (异步任务, 不阻塞响应)
       ▼
┌──────────────────────────────────────────────────────────────┐
│  batch_processor.py                                          │
│                                                              │
│  process_batch(batch_id)                                     │
│  ├─ list_pending_records_by_batch() → 查 status=0 的记录      │
│  └─ asyncio.gather(*[process_single() for each])  ← 并行     │
│                                                              │
│  process_single(record_id, image_path, filename)              │
│  ├─ async with _semaphore:          ← 最大 3 并发             │
│  ├─ update_record_status(id, 1)     → status=1 (处理中)       │
│  ├─ essay_agent.grade(image_base64) → 调用完整流水线           │
│  ├─ 成功: update_record_status(id, 2, result) → 已完成         │
│  └─ 失败: update_record_status(id, 3, result) → 失败           │
│                                                              │
│  recover_unfinished()             ← server.py lifespan 调用   │
│  ├─ list_unfinished_records()     → 查 status=0 或 1 的记录   │
│  ├─ 将 status=1 重置为 status=0                                │
│  └─ asyncio.gather(*[process_single() for each])             │
└──────────────────────────────────────────────────────────────┘

前端通过 GET /api/v1/essays (每 10 秒轮询) 感知状态变化:
  status=0 待处理 → status=1 处理中 → status=2 已完成 → 点击查看详情
                                   → status=3 失败   → 显示错误信息
```

### 数据状态流转

```
  upload ──▶ status=0 (待处理) ──▶ status=1 (处理中) ──▶ status=2 (已完成)
               │                     │                     │
               │ 服务重启后自动恢复      │ 重启后重置为0         │ 持久化到 MySQL
               │ recover_unfinished()  │ 重新处理             │ grading_records
               │                     │                     │
               └─────────────────────┴─────────────────────┘
                                       │
                                       ▼
                                  status=3 (失败)
                                  记录 error_msg
```

## 配置参数

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `ZHIPU_API_KEY` | - | 智谱 API Key (必填) |
| `ZHIPU_OCR_MODEL` | `glm-5v-turbo` | OCR 模型名称 |
| `ZHIPU_BASE_URL` | `https://open.bigmodel.cn/api/paas/v4/` | 智谱 API 地址 |
| `DEEPSEEK_API_KEY` | - | DeepSeek API Key (必填) |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | 批改模型名称 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | DeepSeek API 地址 |
| `API_HOST` | `0.0.0.0` | 服务监听地址 |
| `API_PORT` | `8000` | 服务端口 |
| `DEBUG` | `false` | 调试模式 (开启热重载) |
| `MAX_UPLOAD_SIZE_MB` | `10` | 最大上传文件大小 (MB) |
| `UPLOAD_DIR` | `backend/data/uploads` | 上传文件存储目录 |
| `MYSQL_HOST` | `localhost` | MySQL 主机地址 |
| `MYSQL_PORT` | `3306` | MySQL 端口 |
| `MYSQL_USER` | `root` | MySQL 用户名 |
| `MYSQL_PASSWORD` | - | MySQL 密码 (必填) |
| `MYSQL_DATABASE` | `LittlePen` | MySQL 数据库名 |
| `MYSQL_POOL_SIZE` | `10` | 连接池大小 |
| `MYSQL_POOL_RECYCLE` | `3600` | 连接回收时间 (秒) |
| `LANGSMITH_API_KEY` | - | LangSmith API Key (可选，用于追踪) |
| `LANGSMITH_PROJECT` | `essay-grading` | LangSmith 项目名称 |
| `MAX_MODEL_RETRIES` | `3` | LLM 调用最大重试次数 |

## Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 开发

```bash
# 后端测试
cd backend
pytest tests/ -v

# 前端类型检查
cd frontend
pnpm run build
```

## License

MIT
