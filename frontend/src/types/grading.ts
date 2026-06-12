/** 二维码解析数据 */
export interface QRData {
  course_id: string
  class_id: string
  schedule_id: string
  student_id: string
  student_name: string
  gender: string
  subject?: string  // en/cn/ma/sc
}

/** 科目映射 */
export const subjectLabelMap: Record<string, string> = {
  en: '英语',
  cn: '语文',
  ma: '数学',
  sc: '科学',
}

/** 语法错误项 */
export interface GrammarErrorItem {
  original: string
  corrected: string
  error_type: string
  explanation: string
}

/** 维度评分 */
export interface DimensionScore {
  score: number
  comment: string
}

/** 四维评分 */
export interface ScoresData {
  neatness: DimensionScore
  content: DimensionScore
  language: DimensionScore
  structure: DimensionScore
}

/** 批改完整结果 */
export interface GradeResult {
  qr_data: QRData | null
  essay_clean_text: string
  grammar_errors: GrammarErrorItem[]
  scores: ScoresData | null
  total_score: number
  error: string | null
  thread_id: string
}

/** SSE 进度事件 */
export interface SSEProgressEvent {
  step: string
  data?: GradeResult
}

/** 错误类型标签颜色映射 */
export const errorTypeColorMap: Record<string, string> = {
  '语法': 'danger',
  '拼写': 'warning',
  '用词': 'info',
  '标点': '',
}

/** 评分维度中文名 */
export const dimensionLabelMap: Record<string, string> = {
  neatness: '卷面整洁',
  content: '内容要点',
  language: '语言质量',
  structure: '篇章结构',
}

// ===== 批量批改 =====

/** 批量批改创建响应 */
export interface BatchCreateResponse {
  batch_id: string
  total: number
  items: BatchItemInfo[]
}

export interface BatchItemInfo {
  record_id: string
  filename: string
}

/** 批量批改单项状态 */
export interface BatchItemStatus {
  record_id: string
  filename: string
  status: number // 0=待处理 1=处理中 2=已完成 3=失败
  student_name: string
  total_score: number
  error_msg: string
}

/** 批量批改状态响应 */
export interface BatchStatusResponse {
  batch_id: string
  total: number
  completed: number
  failed: number
  items: BatchItemStatus[]
}

/** 批改状态映射 */
export const batchStatusMap: Record<number, { label: string; type: string }> = {
  0: { label: '待处理', type: 'info' },
  1: { label: '处理中', type: 'warning' },
  2: { label: '已完成', type: 'success' },
  3: { label: '失败', type: 'danger' },
}
