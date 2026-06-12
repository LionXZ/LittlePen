# 短期优化方案：全科批改 + PDF 报告 + 成绩看板

> 目标：复用现有架构，改动最小化，1-2 周完成。

---

## 1. 全科作文批改

### 1.1 需求

当前只支持英文作文，扩展到语文作文。通过二维码中的科目字段路由到不同的批改 prompt。

### 1.2 二维码格式扩展

当前格式（6 段）：
```
课程ID-班级ID-排课ID-学号-encodeURIComponent(姓名)-性别
```

新格式（7 段，第 7 段为科目）：
```
课程ID-班级ID-排课ID-学号-encodeURIComponent(姓名)-性别-科目
```

科目编码：`en`=英语, `cn`=语文, `ma`=数学(预留), `sc`=科学(预留)

兼容性：旧码无第 7 段时默认 `en`（英语），不影响现有功能。

### 1.3 数据流向

```
二维码 → qr_tool 解析出 subject 字段
       → state.subject = "en" | "cn"
       → grammar_check(essay_text, subject)
       → score_essay_4dimensions(essay_text, subject)
       → 按 subject 选择对应 prompt
```

### 1.4 后端改动清单

| 文件 | 改动 | 代码量 |
|------|------|--------|
| `tools/qr_tool.py` | qr_data 新增 `subject` 字段（parts[6]），默认 "en" | 1 行 |
| `tools/scoring_tool.py` | ScoringInput 加 `subject` 参数；`get_scoring_prompt(subject)` 按科目返回不同 prompt | +40 行 |
| `tools/grammar_tool.py` | GrammarCheckInput 加 `subject` 参数；语文走中文语法批改 prompt | +30 行 |
| `pipeline/state.py` | EssayGradingState 新增 `subject: str` | 1 行 |
| `pipeline/graph.py` | qr_parse_node 提取 subject；scoring_node/grammar_check_node 传入 subject | +5 行 |
| `pipeline/assistant.py` | _build_initial_state 新增 subject | 1 行 |
| `db/database.py` | GradingRecord 新增 `subject` 列；CRUD 函数支持 subject | +5 行 |

### 1.5 评分维度对比

| 科目 | 维度 1 | 维度 2 | 维度 3 | 维度 4 |
|------|--------|--------|--------|--------|
| 英语 (en) | 卷面整洁 | 内容要点 | 语言质量 | 篇章结构 |
| 语文 (cn) | 内容立意 | 语言表达 | 篇章结构 | 书写规范 |

### 1.6 语文评分 prompt（参考）

```
你是小学语文作文批改老师。请按以下标准评分（每维度 0-25 分）：

1. 内容立意 - 主题是否明确，观点是否清晰，有无真情实感
   A 21-25: 主题突出，有独特见解或真情实感
   B 16-20: 主题明确，内容较充实
   C 11-15: 基本切题，内容平淡
   D 6-10:  部分跑题，内容空洞
   E 0-5:   完全跑题

2. 语言表达 - 用词准确性，语句通顺度，修辞手法
   A 21-25: 语言生动，有恰当的修辞，表达流畅
   B 16-20: 语句通顺，用词准确
   C 11-15: 语句基本通顺，偶有病句
   D 6-10:  病句较多，表达不清
   E 0-5:   语句不通，难以理解

3. 篇章结构 - 段落划分，开头结尾，逻辑连贯
   A 21-25: 结构完整，段落分明，首尾呼应
   B 16-20: 有开头结尾，层次较清楚
   C 11-15: 结构基本完整，段落划分不够清晰
   D 6-10:  结构混乱，缺少开头或结尾
   E 0-5:   无结构

4. 书写规范 - 字迹工整度，标点使用，格式规范
   A 21-25: 字迹工整，标点正确，格式规范
   B 16-20: 字迹较工整，偶有标点错误
   C 11-15: 字迹一般，标点使用不规范
   D 6-10:  字迹潦草，标点缺失严重
   E 0-5:   难以辨认
```

### 1.7 英文语法批改 prompt 保持不变

英文 prompt 已经写好，无需改动。中文语法批改 prompt 单独写一个。

### 1.8 前端改动

| 文件 | 改动 |
|------|------|
| `types/grading.ts` | QRData 新增 `subject?: string` |
| `components/ScoreBoard.vue` | 根据 `subject` 动态渲染雷达图维度标签 |
| `components/QRInfoCard.vue` | 展示科目信息 |

ScoreBoard 改动要点：当前维度标签是硬编码的 `{neatness: '卷面整洁', ...}`，改为根据 `subject` 动态映射：

```typescript
const dimensionLabels: Record<string, Record<string, string>> = {
  en: { neatness: '卷面整洁', content: '内容要点', language: '语言质量', structure: '篇章结构' },
  cn: { neatness: '书写规范', content: '内容立意', language: '语言表达', structure: '篇章结构' },
}
```

### 1.9 不做什么

- 不新建 Tool，只在现有 tool 加 `if subject` 分支
- 不新建 Pipeline 分支，语法批改+评分两路并行不变
- 数学/科学科目暂不做（中期/长期规划）

---

## 2. PDF 报告导出

### 2.1 需求

已完成的批改结果可以下载为 PDF 报告，包含：学生信息、作文原文、语法错误表、四维评分表、综合评语。

### 2.2 技术选型

**选 weasyprint**（HTML → PDF），不选 reportlab（API 繁琐），不选 headless browser（太重）。

### 2.3 API

```
GET /api/v1/essay/{record_id}/report
返回: Content-Type: application/pdf
```

### 2.4 实现

| 文件 | 改动 |
|------|------|
| `backend/requirements.txt` | 新增 `weasyprint` |
| `backend/src/pipeline/report_generator.py` | **新文件** — HTML 模板 + PDF 生成 |
| `backend/src/api/routes.py` | 新增 `GET /essay/{record_id}/report` |

report_generator.py 核心逻辑：

```python
def generate_report_html(result: dict) -> str:
    """生成报告 HTML"""
    return f"""
    <html><body>
      <h1>作文批改报告</h1>
      <!-- 学生信息表 -->
      <!-- 作文原文 -->
      <!-- 语法错误表 -->
      <!-- 四维评分类 -->
      <!-- 综合评语 -->
    </body></html>
    """

def generate_pdf(html: str, output_path: str):
    HTML(string=html).write_pdf(output_path)
```

**注意：**
- 雷达图在 PDF 中用纯表格替代（ECharts 需要浏览器环境，不做服务端渲染）
- PDF 默认 A4 纵向，中文用系统字体（macOS 默认支持苹方）

### 2.5 前端

- `ResultPanel.vue` 和 `batch-result/index.vue` 新增"下载报告"按钮
- 调用 `GET /essay/{id}/report`，触发浏览器下载

---

## 3. 成绩看板

### 3.1 需求

新页面 `/dashboard`，展示：
- 按班级的整体成绩概览（平均分、最高分、提交数）
- 按学生的成绩趋势（最近 N 次的分数折线图）
- 各维度平均分柱状图

### 3.2 API

```
GET /api/v1/stats/overview    → { total_students, total_records, avg_score }
GET /api/v1/stats/class/{id}  → { class_id, avg_score, record_count, dimension_avgs }
GET /api/v1/stats/student/{id} → [{ date, total_score, scores: {...} }]  最近20次
```

### 3.3 后端

| 文件 | 改动 |
|------|------|
| `backend/src/db/database.py` | 新增 `get_stats_overview()`, `get_stats_by_class()`, `get_stats_by_student()` |
| `backend/src/api/routes.py` | 新增 3 个 `/stats` 端点 |

示例查询：

```sql
SELECT class_id, COUNT(*), AVG(total_score)
FROM grading_records WHERE status = 2
GROUP BY class_id;
```

### 3.4 前端

| 文件 | 改动 |
|------|------|
| `frontend/src/router/index.ts` | 新增 `/dashboard` 路由 |
| `frontend/src/views/dashboard/index.vue` | **新文件** — 成绩看板页面 |
| `frontend/src/App.vue` | 侧边栏新增"成绩看板"菜单项 |
| `frontend/src/api/essay.ts` | 新增 `getStatsOverview()` 等 API 函数 |

页面布局：

```
┌──────────────────────────────────────┐
│  成绩看板                            │
├──────────┬──────────┬────────────────┤
│ 总提交数  │ 平均分   │  最高分        │   ← el-statistic 卡片
├──────────┴──────────┴────────────────┤
│  各维度平均分                        │   ← ECharts 柱状图
│  ████████ 卷面 18.5                  │
│  ██████████ 内容 20.1                │
├──────────────────────────────────────┤
│  学生成绩趋势                        │   ← ECharts 折线图
│    ●──●──●                           │
│   /                                │
│  /                                  │
├──────────────────────────────────────┤
│  班级列表                            │   ← el-table
│  班级 | 人数 | 平均分 | 操作          │
└──────────────────────────────────────┘
```

---

## 4. 实施顺序

```
1. 全科作文批改（后端全改完 → 前端适配）  ← 最先
2. PDF 报告导出（独立功能，无依赖）        ← 可并行
3. 成绩看板（依赖已有批改数据，纯新页面）   ← 最后
```

---

## 5. 验证方式

1. 全科批改：上传英文作文、中文作文各一份，验证评分维度和新 prompt
2. PDF：已完成批改的记录下载 PDF，验证内容完整
3. 看板：有多条批改记录后，访问 `/dashboard` 验证图表数据
