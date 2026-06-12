# LittlePen Constitution

## Core Principles

### I. Spec-First Development (NON-NEGOTIABLE)

任何功能改动必须先出方案、等用户确认后再写代码。禁止跳过规范阶段直接实现。

- 新功能: `/speckit.specify` → `/speckit.plan` → 用户审批 → `/speckit.tasks` → `/speckit.implement`
- Bug 修复: 简短说明原因和方案，得到确认后再改
- 禁止: 用户说"加个功能"就直接改代码

### II. Simple Stack

技术选型保持简单，不引入不必要的抽象层。

- 后端: Python FastAPI + LangChain/LangGraph + SQLAlchemy async
- 前端: Vue 3 + Element Plus + TypeScript
- 数据库: MySQL 8.0
- 不引入: 消息队列（除非 QPS 到瓶颈）、微服务（单体够用）、ORM 过度封装

### III. Single Responsibility for Tools

每个 LangChain Tool 只做一件事，独立可测试。

- 现有工具: qr_tool, ocr_tool, template_tool, grammar_tool, scoring_tool
- 新增工具必须满足: 独立可单元测试、输入输出明确、不与业务逻辑耦合

### IV. State-Driven Pipeline

批改流水线状态驱动，通过数据库 status 字段控制生命周期。

- status=0 待处理 → status=1 处理中 → status=2 已完成 / status=3 失败
- 服务重启后自动恢复未完成任务
- 前端通过轮询感知状态变化

## Development Workflow

1. 新需求 → `/speckit.specify` 生成规范文档到 `specs/`
2. 规范确认 → `/speckit.plan` 生成技术方案
3. 用户审批方案 → `/speckit.tasks` 拆解任务
4. 逐任务实现 → 每完成一个任务测试验证
5. 更新 README 和 SDD 反映最新状态

## Governance

- 本 Constitution 优先级高于其他约定
- 修改 Constitution 需要明确记录变更原因
- CLAUDE.md 是运行时开发指南，Constitution 是项目原则

**Version**: 1.0.0 | **Ratified**: 2026-06-12
